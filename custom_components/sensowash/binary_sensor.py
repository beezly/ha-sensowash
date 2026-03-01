"""Binary sensors for SensoWash."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .lib.models import LidState, OnOff

from . import SensoWashConfigEntry
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashBinarySensorDescription(BinarySensorEntityDescription):
    """Extends BinarySensorEntityDescription with value callback and capability guard."""

    value_fn: Callable[[dict[str, Any]], bool | None]
    # capability name on DeviceCapabilities; None = always show
    capability: str | None = None


BINARY_SENSORS: tuple[SensoWashBinarySensorDescription, ...] = (
    SensoWashBinarySensorDescription(
        key="wash_active",
        translation_key="wash_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.get("wash_state") == OnOff.ON,
        capability="rear_wash",
    ),
    SensoWashBinarySensorDescription(
        key="dryer_active",
        translation_key="dryer_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.get("dryer_state") == OnOff.ON,
        capability="dryer",
    ),
    SensoWashBinarySensorDescription(
        key="lid_open",
        translation_key="lid_open",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda d: d.get("lid_state") == LidState.OPEN,
        capability="lid",
    ),
    SensoWashBinarySensorDescription(
        key="seated",
        translation_key="seated",
        icon="mdi:toilet",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        # Serial protocol only — reads bitmask bits from toilet state response.
        # Not available on GATT devices (no live occupancy characteristic exists).
        value_fn=lambda d: bool(d.get("seated")),
        capability="seat_occupied_sensor",
    ),
    SensoWashBinarySensorDescription(
        key="deodorizing",
        translation_key="deodorizing",
        icon="mdi:air-filter",
        value_fn=lambda d: (
            d.get("deodorizing")        # serial state dict key
            if "deodorizing" in d
            else d.get("deodorization") == OnOff.ON
        ),
        capability="deodorization",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SensoWashConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SensoWashBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if description.capability is None or coordinator.supports(description.capability)
    )


class SensoWashBinarySensor(SensoWashEntity, BinarySensorEntity):
    """A binary sensor entity for SensoWash."""

    entity_description: SensoWashBinarySensorDescription

    def __init__(
        self,
        coordinator: SensoWashCoordinator,
        description: SensoWashBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
