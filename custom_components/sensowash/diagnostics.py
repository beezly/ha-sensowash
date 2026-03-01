"""Diagnostics support for SensoWash."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import SensoWashConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: SensoWashConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    caps = coordinator.capabilities

    state_data: dict[str, Any] = {}
    if coordinator.data:
        for key, val in coordinator.data.items():
            if key == "device_info":
                continue  # included separately below
            state_data[key] = repr(val) if hasattr(val, "name") else val

    device_info: dict[str, Any] = {}
    if coordinator.data and (info := coordinator.data.get("device_info")):
        device_info = {
            "manufacturer": getattr(info, "manufacturer", None),
            "model_number": getattr(info, "model_number", None),
            "serial_number": "**REDACTED**",
            "hardware_revision": getattr(info, "hardware_revision", None),
            "software_revision": getattr(info, "software_revision", None),
            "firmware_revision": getattr(info, "firmware_revision", None),
        }

    capabilities: dict[str, Any] = {}
    if caps:
        capabilities = {
            field: getattr(caps, field)
            for field in caps.__dataclass_fields__  # type: ignore[union-attr]
            if field not in ("model_name", "article_number")
        }
        capabilities["model_name"] = getattr(caps, "model_name", None)

    return {
        "address": entry.data.get("address", "**REDACTED**"),
        "protocol": coordinator.data.get("protocol") if coordinator.data else None,
        "connected": coordinator._client is not None and (
            coordinator._client.is_connected if coordinator._client else False
        ),
        "last_update_success": coordinator.last_update_success,
        "state": state_data,
        "device_info": device_info,
        "capabilities": capabilities,
        "options": {
            k: "**REDACTED**" if k == "pairing_key" else v
            for k, v in entry.options.items()
        },
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: SensoWashConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return diagnostics for a device entry (same as config entry diagnostics)."""
    return await async_get_config_entry_diagnostics(hass, entry)
