"""Base entity for SensoWash."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SensoWashCoordinator


class SensoWashEntity(CoordinatorEntity[SensoWashCoordinator]):
    """Base class for all SensoWash entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SensoWashCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.address}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        info = self.coordinator.data.get("device_info") if self.coordinator.data else None
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.address)},
            name=self.coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=getattr(info, "model_number", None) or "SensoWash",
            sw_version=getattr(info, "firmware_revision", None),
            hw_version=getattr(info, "hardware_revision", None),
            serial_number=getattr(info, "serial_number", None),
        )
