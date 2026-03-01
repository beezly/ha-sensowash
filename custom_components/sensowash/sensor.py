"""Sensors for SensoWash."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .lib.models import DescalingState, ErrorCode

from . import SensoWashConfigEntry
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with value/attributes callbacks and capability guard."""

    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict] | None = None
    # capability name on DeviceCapabilities; None = always show
    capability: str | None = None


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
        capability="actual_seat_temperature",
    ),
    SensoWashSensorDescription(
        key="error_status",
        translation_key="error_status",
        icon="mdi:alert-circle-outline",
        value_fn=_error_state,
        attributes_fn=_error_attrs,
        capability="error_codes",
    ),
    SensoWashSensorDescription(
        key="descaling_status",
        translation_key="descaling_status",
        icon="mdi:water-sync",
        value_fn=lambda d: (
            d["descaling_state"].status.name.lower()
            if isinstance(d.get("descaling_state"), DescalingState)
            else None
        ),
        capability="descaling",
    ),
    SensoWashSensorDescription(
        key="descaling_remaining_time",
        translation_key="descaling_remaining_time",
        icon="mdi:timer-sand",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda d: d.get("descaling_remaining_time"),
        capability="descaling",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SensoWashConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SensoWashSensor(coordinator, description)
        for description in SENSORS
        if description.capability is None or coordinator.supports(description.capability)
    )


class SensoWashSensor(SensoWashEntity, SensorEntity):
    """A sensor entity for SensoWash."""

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
