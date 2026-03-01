"""Config flow for Duravit SensoWash."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback

from .const import CONF_PAIRING_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

_SENSOWASH_PREFIXES = ("SensoWash", "DuraSystem", "DURAVIT")
_SERIAL_PREFIXES = ("DURAVIT_BT", "DURAVIT")

# Pairing key: 4 hex bytes, optionally colon/space separated
_PAIRING_KEY_RE = re.compile(
    r"^([0-9a-fA-F]{2}[:\s]?){3}[0-9a-fA-F]{2}$|^[0-9a-fA-F]{8}$"
)

# How long to wait for the user to press the toilet's Bluetooth button
_PAIR_TIMEOUT = 60.0


def _is_sensowash(service_info: BluetoothServiceInfoBleak) -> bool:
    name = service_info.name or ""
    return any(name.startswith(p) for p in _SENSOWASH_PREFIXES)


def _is_serial(service_info: BluetoothServiceInfoBleak) -> bool:
    name = service_info.name or ""
    return any(name.startswith(p) for p in _SERIAL_PREFIXES)


def _normalise_key(raw: str) -> str:
    return re.sub(r"[:\s]", "", raw).lower()


class SensoWashConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SensoWash."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}
        self._selected: BluetoothServiceInfoBleak | None = None
        self._pairing_task: asyncio.Task | None = None
        self._pairing_key: str | None = None

    # ── Bluetooth auto-discovery ───────────────────────────────────────────────

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth auto-discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._selected = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }

        if _is_serial(discovery_info):
            return await self.async_step_pairing()

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm Bluetooth auto-discovery of a GATT device."""
        assert self._selected is not None

        if user_input is not None:
            return self.async_create_entry(
                title=self._selected.name or self._selected.address,
                data={CONF_ADDRESS: self._selected.address},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._selected.name or self._selected.address,
                "address": self._selected.address,
            },
        )

    # ── Serial pairing ─────────────────────────────────────────────────────────

    async def async_step_pairing(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show pairing instructions and wait for the user to press the toilet button.

        Uses async_show_progress so the UI stays responsive while we wait for
        the BLE pairing handshake (up to 60 seconds).
        """
        assert self._selected is not None

        # If we already have a key (retry after timeout), go straight to confirm
        if self._pairing_key:
            return await self.async_step_pairing_confirm()

        if self._pairing_task is None:
            self._pairing_task = self.hass.async_create_task(
                self._do_pair(self._selected.address),
                name=f"sensowash_pair_{self._selected.address}",
            )

        if not self._pairing_task.done():
            return self.async_show_progress(
                step_id="pairing",
                progress_action="waiting_for_button",
                progress_task=self._pairing_task,
                description_placeholders={
                    "name": self._selected.name or self._selected.address,
                    "timeout": str(int(_PAIR_TIMEOUT)),
                },
            )

        # Task finished — check result
        try:
            key_bytes: bytes = self._pairing_task.result()
            self._pairing_key = key_bytes.hex()
            _LOGGER.info(
                "Pairing successful for %s, key: %s",
                self._selected.address,
                self._pairing_key,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Pairing failed for %s: %s", self._selected.address, exc)
            self._pairing_task = None
            return self.async_show_progress_done(next_step_id="pairing_failed")

        return self.async_show_progress_done(next_step_id="pairing_confirm")

    async def async_step_pairing_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pairing succeeded — confirm and create entry."""
        assert self._selected is not None
        assert self._pairing_key is not None

        if user_input is not None:
            return self.async_create_entry(
                title=self._selected.name or self._selected.address,
                data={CONF_ADDRESS: self._selected.address},
                options={CONF_PAIRING_KEY: self._pairing_key},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="pairing_confirm",
            description_placeholders={
                "name": self._selected.name or self._selected.address,
            },
        )

    async def async_step_pairing_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pairing timed out or failed — offer to retry."""
        assert self._selected is not None

        if user_input is not None:
            if user_input.get("retry"):
                # Reset and try again
                self._pairing_task = None
                self._pairing_key = None
                return await self.async_step_pairing()
            # User gave up — abort
            return self.async_abort(reason="pairing_failed")

        return self.async_show_form(
            step_id="pairing_failed",
            data_schema=vol.Schema({vol.Required("retry", default=True): bool}),
            description_placeholders={
                "name": self._selected.name or self._selected.address,
                "timeout": str(int(_PAIR_TIMEOUT)),
            },
        )

    async def _do_pair(self, address: str) -> bytes:
        """Run the BLE pairing handshake in the background."""
        from sensowash.serial import pair as serial_pair
        return await serial_pair(address, timeout=_PAIR_TIMEOUT)

    # ── Manual setup ───────────────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual setup — picker of discovered devices or free-text MAC entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            info = self._discovered.get(address)
            self._selected = info
            title = getattr(info, "name", None) or address

            # Serial device selected manually → go through pairing
            if info and _is_serial(info):
                return await self.async_step_pairing()

            return self.async_create_entry(
                title=title,
                data={CONF_ADDRESS: address},
            )

        # Populate discovered devices
        current_addresses = self._async_current_ids()
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address not in current_addresses and _is_sensowash(info):
                self._discovered[info.address] = info

        if self._discovered:
            schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            addr: f"{info.name} ({addr})"
                            for addr, info in self._discovered.items()
                        }
                    )
                }
            )
        else:
            schema = vol.Schema({vol.Required(CONF_ADDRESS): str})

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "found": str(len(self._discovered)) if self._discovered else "none"
            },
        )

    # ── Options flow ───────────────────────────────────────────────────────────

    @classmethod
    @callback
    def async_get_options_flow(cls, config_entry: ConfigEntry) -> OptionsFlow:
        return SensoWashOptionsFlow()


class SensoWashOptionsFlow(OptionsFlow):
    """Options flow — allows re-pairing or updating the serial pairing key."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_key: str = user_input.get(CONF_PAIRING_KEY, "").strip()
            if raw_key:
                if not _PAIRING_KEY_RE.match(raw_key):
                    errors[CONF_PAIRING_KEY] = "invalid_pairing_key"
                else:
                    return self.async_create_entry(
                        data={CONF_PAIRING_KEY: _normalise_key(raw_key)}
                    )
            else:
                return self.async_create_entry(data={})

        current_key: str = self.config_entry.options.get(CONF_PAIRING_KEY, "")
        display_key = (
            ":".join(current_key[i:i+2] for i in range(0, len(current_key), 2))
            if current_key else ""
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Optional(CONF_PAIRING_KEY, default=display_key): str}
            ),
            errors=errors,
            description_placeholders={
                "address": self.config_entry.data.get(CONF_ADDRESS, ""),
            },
        )
