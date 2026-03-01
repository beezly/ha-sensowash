"""Button entities for SensoWash (one-shot actions)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from sensowash.models import WaterFlow, WaterTemperature, NozzlePosition, DryerTemperature, DryerSpeed

from .const import DOMAIN, ENTRY_COORDINATOR
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashButtonDescription(ButtonEntityDescription):
    method: str
    kwargs: dict[str, Any] = field(default_factory=dict)


BUTTONS: tuple[SensoWashButtonDescription, ...] = (
    SensoWashButtonDescription(
        key="start_rear_wash",
        translation_key="start_rear_wash",
        icon="mdi:shower",
        method="start_rear_wash",
        kwargs={
            "water_flow": WaterFlow.MEDIUM,
            "water_temperature": WaterTemperature.TEMP_2,
            "nozzle_position": NozzlePosition.POSITION_2,
        },
    ),
    SensoWashButtonDescription(
        key="start_lady_wash",
        translation_key="start_lady_wash",
        icon="mdi:shower",
        method="start_lady_wash",
        kwargs={
            "water_flow": WaterFlow.MEDIUM,
            "water_temperature": WaterTemperature.TEMP_2,
            "nozzle_position": NozzlePosition.POSITION_2,
        },
    ),
    SensoWashButtonDescription(
        key="stop",
        translation_key="stop",
        icon="mdi:stop-circle-outline",
        method="stop",
    ),
    SensoWashButtonDescription(
        key="flush",
        translation_key="flush",
        icon="mdi:toilet",
        method="flush",
    ),
    SensoWashButtonDescription(
        key="open_lid",
        translation_key="open_lid",
        icon="mdi:seat-outline",
        method="open_lid",
    ),
    SensoWashButtonDescription(
        key="close_lid",
        translation_key="close_lid",
        icon="mdi:seat",
        method="close_lid",
    ),
    SensoWashButtonDescription(
        key="start_dryer",
        translation_key="start_dryer",
        icon="mdi:hair-dryer",
        method="start_dryer",
        kwargs={
            "temperature": DryerTemperature.TEMP_2,
            "speed": DryerSpeed.SPEED_0,
        },
    ),
    SensoWashButtonDescription(
        key="stop_dryer",
        translation_key="stop_dryer",
        icon="mdi:hair-dryer-outline",
        method="stop_dryer",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SensoWashCoordinator = hass.data[DOMAIN][entry.entry_id][ENTRY_COORDINATOR]
    async_add_entities(
        SensoWashButton(coordinator, description) for description in BUTTONS
    )


class SensoWashButton(SensoWashEntity, ButtonEntity):
    entity_description: SensoWashButtonDescription

    def __init__(
        self,
        coordinator: SensoWashCoordinator,
        description: SensoWashButtonDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.coordinator.async_command(
            self.entity_description.method,
            **self.entity_description.kwargs,
        )
