"""Config flow for Duravit SensoWash."""
from __future__ import annotations

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

from .const import CONF_PAIRING_KEY, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

# Device name prefixes that identify SensoWash devices
_SENSOWASH_PREFIXES = ("SensoWash", "DuraSystem", "DURAVIT")

# Validates a pairing key: 4 hex bytes = 8 hex chars (optionally colon/space separated)
_PAIRING_KEY_RE = re.compile(
    r"^([0-9a-fA-F]{2}[:\s]?){3}[0-9a-fA-F]{2}$|^[0-9a-fA-F]{8}$"
)


def _is_sensowash(service_info: BluetoothServiceInfoBleak) -> bool:
    name = service_info.name or ""
    return any(name.startswith(p) for p in _SENSOWASH_PREFIXES)


def _normalise_key(raw: str) -> str:
    """Strip separators and return lowercase hex string."""
    return re.sub(r"[:\s]", "", raw).lower()


class SensoWashConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SensoWash."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}
        self._selected: BluetoothServiceInfoBleak | None = None

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
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm Bluetooth auto-discovery."""
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

    # ── Manual setup ───────────────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup — picker of discovered devices or free-text MAC entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            info = self._discovered.get(address)
            title = getattr(info, "name", None) or address
            return self.async_create_entry(title=title, data={CONF_ADDRESS: address})

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
        """Return the options flow handler."""
        return SensoWashOptionsFlow()


class SensoWashOptionsFlow(OptionsFlow):
    """Options flow for SensoWash — allows configuring the serial pairing key."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_key: str = user_input.get(CONF_PAIRING_KEY, "").strip()

            if raw_key:
                # Validate pairing key
                if not _PAIRING_KEY_RE.match(raw_key):
                    errors[CONF_PAIRING_KEY] = "invalid_pairing_key"
                else:
                    normalised = _normalise_key(raw_key)
                    return self.async_create_entry(
                        data={CONF_PAIRING_KEY: normalised}
                    )
            else:
                # Clearing the pairing key
                return self.async_create_entry(data={})

        current_key: str = self.config_entry.options.get(CONF_PAIRING_KEY, "")
        # Display stored key in groups of 2 for readability
        display_key = (
            ":".join(current_key[i:i+2] for i in range(0, len(current_key), 2))
            if current_key
            else ""
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_PAIRING_KEY, default=display_key): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "address": self.config_entry.data.get(CONF_ADDRESS, ""),
            },
        )
