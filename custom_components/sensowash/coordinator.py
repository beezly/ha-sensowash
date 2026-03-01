"""DataUpdateCoordinator for SensoWash — maintains the BLE connection and state."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

from homeassistant.components.bluetooth import (
    async_ble_device_from_address,
    async_last_service_info,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from sensowash.client import SensoWashClient
from sensowash.models import ErrorCode

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SensoWashCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Manages the BLE connection to a SensoWash toilet.

    State is primarily push-based (BLE notifications), with periodic full polls
    as a fallback. Automatically uses HA Bluetooth proxies if the device is
    reachable via one.
    """

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"SensoWash {name}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.address = address
        self.device_name = name
        self._client: SensoWashClient | None = None
        self._lock = asyncio.Lock()

    # ── BLE connection ─────────────────────────────────────────────────────────

    async def _get_client(self) -> SensoWashClient:
        """Return a connected SensoWashClient, reconnecting if needed."""
        async with self._lock:
            if self._client and self._client.is_connected:
                return self._client

            # Resolve BLEDevice through HA's bluetooth registry.
            # This transparently routes through Bluetooth proxies (ESPHome etc.)
            ble_device = async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                raise UpdateFailed(
                    f"SensoWash {self.address} not reachable via Bluetooth"
                )

            _LOGGER.debug("Connecting to %s (%s)", self.device_name, self.address)
            client = SensoWashClient(
                ble_device,
                notification_cb=self._on_notification,
            )
            await client.connect()
            self._client = client
            _LOGGER.info("Connected to %s", self.device_name)
            return client

    async def async_disconnect(self) -> None:
        """Cleanly disconnect from the toilet."""
        async with self._lock:
            if self._client:
                try:
                    await self._client.disconnect()
                except Exception:  # noqa: BLE001
                    pass
                self._client = None

    # ── Push notifications ─────────────────────────────────────────────────────

    @callback
    def _on_notification(self, uuid: str, data: bytes) -> None:
        """Handle a BLE characteristic notification from the toilet."""
        from sensowash.constants import CHARACTERISTICS
        from sensowash.models import (
            OnOff, WaterFlow, WaterTemperature, NozzlePosition,
            SeatTemperature, DryerTemperature, DryerSpeed, LidState, WaterHardness,
        )

        if not data:
            return

        _CHAR_DECODERS = {
            CHARACTERISTICS["WASH_STATE"]:          ("wash_state",         OnOff),
            CHARACTERISTICS["WATER_FLOW"]:          ("water_flow",         WaterFlow),
            CHARACTERISTICS["WATER_TEMPERATURE"]:   ("water_temperature",  WaterTemperature),
            CHARACTERISTICS["NOZZLE_POSITION"]:     ("nozzle_position",    NozzlePosition),
            CHARACTERISTICS["DRYER_STATE"]:         ("dryer_state",        OnOff),
            CHARACTERISTICS["DRYER_TEMPERATURE"]:   ("dryer_temperature",  DryerTemperature),
            CHARACTERISTICS["DRYER_SPEED"]:         ("dryer_speed",        DryerSpeed),
            CHARACTERISTICS["FLUSH_AUTOMATIC"]:     ("flush_automatic",    OnOff),
            CHARACTERISTICS["LID_STATE"]:           ("lid_state",          LidState),
            CHARACTERISTICS["SEAT_STATE"]:          ("seat_state",         OnOff),
            CHARACTERISTICS["SEAT_TEMPERATURE"]:    ("seat_temperature",   SeatTemperature),
            CHARACTERISTICS["SEAT_ACTUAL_TEMP"]:    ("seat_actual_temp",   None),
            CHARACTERISTICS["SEAT_PROXIMITY"]:      ("seat_proximity",     OnOff),
            CHARACTERISTICS["DEODORIZATION_STATE"]: ("deodorization",      OnOff),
            CHARACTERISTICS["DEODORIZATION_AUTO"]:  ("deodorization_auto", OnOff),
            CHARACTERISTICS["AMBIENT_LIGHT_STATE"]: ("ambient_light",      OnOff),
            CHARACTERISTICS["UVC_STATE"]:           ("uvc_light",          OnOff),
            CHARACTERISTICS["UVC_AUTOMATIC"]:       ("uvc_auto",           OnOff),
            CHARACTERISTICS["MUTE"]:                ("mute",               OnOff),
            CHARACTERISTICS["ERROR_CODES"]:         ("error_codes",        "errors"),
        }

        entry = _CHAR_DECODERS.get(uuid.lower())
        if entry is None:
            return

        key, decoder = entry
        if self.data is None:
            return

        if decoder == "errors":
            self.data[key] = ErrorCode.decode_payload(data)
        elif decoder is None:
            self.data[key] = data[0]
        else:
            try:
                self.data[key] = decoder(data[0])
            except ValueError:
                self.data[key] = data[0]

        self.async_set_updated_data(self.data)

    # ── DataUpdateCoordinator ──────────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll the toilet for a full state snapshot."""
        try:
            client = await self._get_client()
            state = await client.get_full_state()
            state["device_info"] = await client.get_device_info()
            return state
        except UpdateFailed:
            raise
        except Exception as ex:
            # Connection dropped — clear client so we reconnect next time
            _LOGGER.warning(
                "Lost connection to %s: %s. Will retry.", self.device_name, ex
            )
            async with self._lock:
                self._client = None
            raise UpdateFailed(f"Connection to {self.device_name} failed: {ex}") from ex

    # ── Command helpers (used by entity platforms) ─────────────────────────────

    async def async_command(self, method: str, *args, **kwargs) -> None:
        """Call a method on the connected SensoWashClient."""
        try:
            client = await self._get_client()
            await getattr(client, method)(*args, **kwargs)
        except Exception as ex:
            _LOGGER.error("Command %s failed: %s", method, ex)
            raise
