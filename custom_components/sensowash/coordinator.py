"""DataUpdateCoordinator for SensoWash — maintains the BLE connection and state."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from sensowash.client import SensoWashClient
from sensowash.exceptions import ConnectionError as SensoConnectionError, PairingRequired
from sensowash.models import DeviceCapabilities, ErrorCode

from .const import CONF_PAIRING_KEY, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SensoWashCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Manages the BLE connection to a SensoWash toilet.

    State is primarily push-based (BLE notifications), with periodic full polls
    as a fallback. Automatically uses HA Bluetooth proxies if the device is
    reachable via one.

    ``capabilities`` is populated after the first successful connection.
    Platform setup functions use it to only register entities the toilet supports.
    """

    capabilities: DeviceCapabilities | None = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"SensoWash {entry.title}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self._entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.device_name: str = entry.title
        self._client: SensoWashClient | None = None
        self._lock = asyncio.Lock()

    # ── Pairing key ────────────────────────────────────────────────────────────

    @property
    def _pairing_key(self) -> bytes | None:
        """Return the stored pairing key (from options), or None."""
        hex_key: str | None = self._entry.options.get(CONF_PAIRING_KEY)
        if hex_key:
            try:
                return bytes.fromhex(hex_key)
            except ValueError:
                _LOGGER.warning("Invalid pairing key in options (not valid hex)")
        return None

    # ── BLE connection ─────────────────────────────────────────────────────────

    async def _get_client(self) -> SensoWashClient:
        """Return a connected SensoWashClient, reconnecting if needed."""
        async with self._lock:
            if self._client and self._client.is_connected:
                return self._client

            # Resolve BLEDevice through HA's Bluetooth registry.
            # This transparently routes through Bluetooth proxies (ESPHome etc.)
            ble_device = async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                raise UpdateFailed(
                    f"SensoWash {self.address} not reachable via Bluetooth. "
                    "Ensure the toilet is powered and a Bluetooth adapter or proxy is nearby."
                )

            _LOGGER.debug("Connecting to %s (%s)", self.device_name, self.address)

            async def _factory(device, disconnected_cb, timeout):
                """Use bleak_retry_connector for robust proxy-aware connections.

                - Retries up to 3 times on transient BLE failures
                - BleakClientWithServiceCache caches GATT service discovery,
                  avoiding a slow re-discovery on every reconnect (important
                  over ESPHome Bluetooth proxies where discovery takes 2-3 s)
                """
                return await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    self.device_name,
                    disconnected_callback=disconnected_cb,
                    max_attempts=3,
                )

            client = SensoWashClient(
                ble_device,
                notification_cb=self._on_notification,
                pairing_key=self._pairing_key,
                bleak_client_factory=_factory,
            )
            try:
                await client.connect()
            except PairingRequired as exc:
                raise UpdateFailed(
                    f"{self.device_name} requires pairing. Go to the integration options "
                    "to enter the pairing key, or use the sensowash-ble pair() tool to "
                    "obtain one by pressing the Bluetooth button on the toilet."
                ) from exc
            except SensoConnectionError as exc:
                raise UpdateFailed(str(exc)) from exc
            except Exception as exc:  # noqa: BLE001
                raise UpdateFailed(
                    f"Unexpected error connecting to {self.device_name}: {exc}"
                ) from exc

            self._client = client
            _LOGGER.info(
                "Connected to %s (protocol: %s)", self.device_name, client.protocol
            )
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

    def _on_notification(self, uuid: str, data: bytes) -> None:
        """Handle a BLE characteristic notification from the toilet.

        Updates the coordinator data in-place and signals listeners without
        doing a full poll.
        """
        from sensowash.constants import CHARACTERISTICS
        from sensowash.models import (
            DryerSpeed,
            DryerTemperature,
            LidState,
            NozzlePosition,
            OnOff,
            SeatTemperature,
            WaterFlow,
            WaterHardness,
            WaterTemperature,
        )

        # Synthetic disconnect event from SensoWashClient._on_disconnect
        if uuid == "disconnected":
            _LOGGER.debug("%s: BLE connection dropped", self.device_name)
            self._client = None
            return

        # Serial protocol push event — toilet state changed
        # op 0x53 = toilet state response (also sent as unsolicited event on state change)
        if uuid == "serial:0x53":
            self._handle_serial_state(data)
            return

        if not data or self.data is None:
            return

        _CHAR_DECODERS: dict[str, tuple[str, Any]] = {
            CHARACTERISTICS["WASH_STATE"].lower():          ("wash_state",         OnOff),
            CHARACTERISTICS["WATER_FLOW"].lower():          ("water_flow",         WaterFlow),
            CHARACTERISTICS["WATER_TEMPERATURE"].lower():   ("water_temperature",  WaterTemperature),
            CHARACTERISTICS["NOZZLE_POSITION"].lower():     ("nozzle_position",    NozzlePosition),
            CHARACTERISTICS["DRYER_STATE"].lower():         ("dryer_state",        OnOff),
            CHARACTERISTICS["DRYER_TEMPERATURE"].lower():   ("dryer_temperature",  DryerTemperature),
            CHARACTERISTICS["DRYER_SPEED"].lower():         ("dryer_speed",        DryerSpeed),
            CHARACTERISTICS["FLUSH_AUTOMATIC"].lower():     ("flush_automatic",    OnOff),
            CHARACTERISTICS["LID_STATE"].lower():           ("lid_state",          LidState),
            CHARACTERISTICS["SEAT_STATE"].lower():          ("seat_state",         OnOff),
            CHARACTERISTICS["SEAT_TEMPERATURE"].lower():    ("seat_temperature",   SeatTemperature),
            CHARACTERISTICS["SEAT_ACTUAL_TEMP"].lower():    ("seat_actual_temp",   None),
            CHARACTERISTICS["SEAT_PROXIMITY"].lower():      ("seat_proximity",     OnOff),
            CHARACTERISTICS["DEODORIZATION_STATE"].lower(): ("deodorization",      OnOff),
            CHARACTERISTICS["DEODORIZATION_AUTO"].lower():  ("deodorization_auto", OnOff),
            CHARACTERISTICS["AMBIENT_LIGHT_STATE"].lower(): ("ambient_light",      OnOff),
            CHARACTERISTICS["UVC_STATE"].lower():           ("uvc_light",          OnOff),
            CHARACTERISTICS["UVC_AUTOMATIC"].lower():       ("uvc_auto",           OnOff),
            CHARACTERISTICS["MUTE"].lower():                ("mute",               OnOff),
            CHARACTERISTICS["ERROR_CODES"].lower():         ("errors",             "errors"),
            CHARACTERISTICS["WATER_HARDNESS"].lower():      ("water_hardness",     WaterHardness),
        }

        entry = _CHAR_DECODERS.get(uuid.lower())
        if entry is None:
            return

        key, decoder = entry
        if decoder == "errors":
            self.data[key] = ErrorCode.decode_payload(data)
        elif decoder is None:
            self.data[key] = data[0]
        else:
            try:
                self.data[key] = decoder(data[0])
            except ValueError:
                self.data[key] = data[0]

        self.async_set_updated_data(dict(self.data))

    # ── DataUpdateCoordinator ──────────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll the toilet for a full state + device info snapshot.

        Also fetches capabilities on the first successful connection —
        platform setup functions read ``self.capabilities`` to decide
        which entities to register.
        """
        try:
            client = await self._get_client()

            # Fetch capabilities once per connection (after connect/reconnect)
            if self.capabilities is None:
                try:
                    self.capabilities = await client.get_capabilities()
                    _LOGGER.debug(
                        "%s capabilities: %s",
                        self.device_name,
                        self.capabilities,
                    )
                    # Serial devices with seat sensor: poll more frequently so
                    # occupancy state stays current between push events
                    if (
                        client.protocol == "serial"
                        and self.capabilities.seat_occupied_sensor
                        and self.update_interval.seconds > 10
                    ):
                        self.update_interval = timedelta(seconds=10)
                        _LOGGER.debug(
                            "%s: reduced poll interval to 10s for serial occupancy",
                            self.device_name,
                        )
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning(
                        "Could not fetch capabilities from %s: %s — "
                        "all entities will be registered",
                        self.device_name,
                        exc,
                    )

            state = await client.get_full_state()
            state["device_info"] = await client.get_device_info()
            return state

        except UpdateFailed:
            raise
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "Lost connection to %s: %s. Will retry.", self.device_name, exc
            )
            async with self._lock:
                self._client = None
            raise UpdateFailed(
                f"Connection to {self.device_name} failed: {exc}"
            ) from exc

    # ── Command helpers (used by entity platforms) ─────────────────────────────

    async def async_command(self, method: str, *args: Any, **kwargs: Any) -> None:
        """Call a named method on the connected SensoWashClient and re-raise on failure."""
        try:
            client = await self._get_client()
            await getattr(client, method)(*args, **kwargs)
        except UpdateFailed:
            raise
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Command %s failed on %s: %s", method, self.device_name, exc)
            raise

    def _handle_serial_state(self, data: bytes) -> None:
        """Decode a serial toilet-state packet and push updated state to listeners.

        Called both from unsolicited push events (op 0x53) and indirectly from
        the periodic poll via get_full_state(). Merges into existing data so
        GATT-sourced keys are not overwritten.
        """
        if not data or len(data) < 2 or self.data is None:
            return

        b0, b1 = data[0], data[1]
        updates = {
            "washing":            bool(b0 & 0x01),
            "wash_initializing":  bool(b0 & 0x02),
            "seated_wash":        bool(b0 & 0x04),
            "wash_powered":       bool(b0 & 0x08),
            "drying":             bool(b0 & 0x10),
            "dry_initializing":   bool(b0 & 0x20),
            "seated_dry":         bool(b0 & 0x40),
            "dry_powered":        bool(b0 & 0x80),
            "deodorizing":        bool(b1 & 0x02),
            # Occupied = seated during wash OR seated during dry
            "seated":             bool((b0 & 0x04) or (b0 & 0x40)),
        }
        self.data.update(updates)
        self.async_set_updated_data(dict(self.data))
        _LOGGER.debug("%s: serial state push → seated=%s", self.device_name, updates["seated"])

    def supports(self, capability: str) -> bool:
        """Return True if the toilet has this capability, or if capabilities are unknown."""
        if self.capabilities is None:
            return True  # unknown — show everything
        return bool(getattr(self.capabilities, capability, False))
