"""Duravit SensoWash Home Assistant integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SensoWashCoordinator

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BUTTON,
]

# Type alias — all platform files should import and use this instead of ConfigEntry
type SensoWashConfigEntry = ConfigEntry[SensoWashCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SensoWashConfigEntry) -> bool:
    """Set up SensoWash from a config entry."""
    coordinator = SensoWashCoordinator(hass, entry)

    # Connect and do first full poll — fetches state AND capabilities.
    # Raises ConfigEntryNotReady if the device is unreachable.
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in entry.runtime_data (HA 2024.1+ pattern)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SensoWashConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_disconnect()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: SensoWashConfigEntry
) -> None:
    """Reload entry when options change (e.g. pairing key updated)."""
    await hass.config_entries.async_reload(entry.entry_id)
