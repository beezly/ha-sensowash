"""Config flow for Duravit SensoWash."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

# Device name prefixes that identify SensoWash devices
_SENSOWASH_PREFIXES = ("SensoWash", "DuraSystem")


def _is_sensowash(service_info: BluetoothServiceInfoBleak) -> bool:
    name = service_info.name or ""
    return any(name.startswith(p) for p in _SENSOWASH_PREFIXES)


class SensoWashConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SensoWash."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}
        self._selected: BluetoothServiceInfoBleak | None = None

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
        """Confirm Bluetooth discovery."""
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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup — shows a picker of discovered devices or free-text entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address.upper())
            self._abort_if_unique_id_configured()
            name = self._discovered.get(address, {})
            title = getattr(name, "name", None) or address
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
            schema = vol.Schema(
                {vol.Required(CONF_ADDRESS): str}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "found": str(len(self._discovered)) if self._discovered else "none"
            },
        )
