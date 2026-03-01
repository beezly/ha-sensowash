"""Sensors for SensoWash."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from sensowash.models import ErrorCode

from .const import DOMAIN, ENTRY_COORDINATOR
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    # Optional: function to produce extra state attributes
    attributes_fn: Callable[[dict[str, Any]], dict] | None = None


def _error_state(data: dict) -> str:
    errors: list[ErrorCode] = data.get("errors", [])
    if not errors:
        return "ok"
    return ", ".join(str(e.code) for e in errors)


def _error_attrs(data: dict) -> dict:
    errors: list[ErrorCode] = data.get("errors", [])
    return {
        "active_errors": [
            {
                "code": e.code,
                "category": e.category,
                "title": e.title,
                "service_ref": e.service_code,
                "action": e.action,
            }
            for e in errors
        ]
    }


SENSORS: tuple[SensoWashSensorDescription, ...] = (
    SensoWashSensorDescription(
        key="seat_actual_temp",
        translation_key="seat_actual_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("seat_actual_temp"),
    ),
    SensoWashSensorDescription(
        key="error_status",
        translation_key="error_status",
        value_fn=_error_state,
        attributes_fn=_error_attrs,
        icon="mdi:alert-circle-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SensoWashCoordinator = hass.data[DOMAIN][entry.entry_id][ENTRY_COORDINATOR]
    async_add_entities(
        SensoWashSensor(coordinator, description) for description in SENSORS
    )


class SensoWashSensor(SensoWashEntity, SensorEntity):
    entity_description: SensoWashSensorDescription

    def __init__(
        self,
        coordinator: SensoWashCoordinator,
        description: SensoWashSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        if not self.coordinator.data or not self.entity_description.attributes_fn:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
