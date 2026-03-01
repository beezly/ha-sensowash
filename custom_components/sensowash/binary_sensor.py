"""Binary sensors for SensoWash."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from sensowash.models import OnOff, LidState

from .const import DOMAIN, ENTRY_COORDINATOR
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[SensoWashBinarySensorDescription, ...] = (
    SensoWashBinarySensorDescription(
        key="wash_active",
        translation_key="wash_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.get("wash_state") == OnOff.ON,
    ),
    SensoWashBinarySensorDescription(
        key="dryer_active",
        translation_key="dryer_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.get("dryer_state") == OnOff.ON,
    ),
    SensoWashBinarySensorDescription(
        key="lid_open",
        translation_key="lid_open",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda d: d.get("lid_state") == LidState.OPEN,
    ),
    SensoWashBinarySensorDescription(
        key="seated",
        translation_key="seated",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda d: d.get("seat_state") == OnOff.ON,
    ),
    SensoWashBinarySensorDescription(
        key="deodorizing",
        translation_key="deodorizing",
        value_fn=lambda d: d.get("deodorization") == OnOff.ON,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SensoWashCoordinator = hass.data[DOMAIN][entry.entry_id][ENTRY_COORDINATOR]
    async_add_entities(
        SensoWashBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class SensoWashBinarySensor(SensoWashEntity, BinarySensorEntity):
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
