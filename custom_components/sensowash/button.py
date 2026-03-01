"""Button entities for SensoWash (one-shot actions)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .lib.models import (
    DryerSpeed,
    DryerTemperature,
    NozzlePosition,
    TankDrainage,
    WaterFlow,
    WaterTemperature,
)

from . import SensoWashConfigEntry
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashButtonDescription(ButtonEntityDescription):
    """Extends ButtonEntityDescription with command method, kwargs, and capability guard."""

    method: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    # capability name on DeviceCapabilities; None = always show
    capability: str | None = None


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
        capability="rear_wash",
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
        capability="lady_wash",
    ),
    SensoWashButtonDescription(
        key="stop",
        translation_key="stop",
        icon="mdi:stop-circle-outline",
        method="stop",
        capability=None,  # always available
    ),
    SensoWashButtonDescription(
        key="flush",
        translation_key="flush",
        icon="mdi:toilet",
        method="flush",
        capability="flush",
    ),
    SensoWashButtonDescription(
        key="open_lid",
        translation_key="open_lid",
        icon="mdi:seat-outline",
        method="open_lid",
        capability="lid",
    ),
    SensoWashButtonDescription(
        key="close_lid",
        translation_key="close_lid",
        icon="mdi:seat",
        method="close_lid",
        capability="lid",
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
        capability="dryer",
    ),
    SensoWashButtonDescription(
        key="stop_dryer",
        translation_key="stop_dryer",
        icon="mdi:hair-dryer-outline",
        method="stop_dryer",
        capability="dryer",
    ),
    SensoWashButtonDescription(
        key="eco_flush",
        translation_key="eco_flush",
        icon="mdi:water-minus",
        method="eco_flush",
        capability="flush",
    ),
    SensoWashButtonDescription(
        key="start_descaling",
        translation_key="start_descaling",
        icon="mdi:water-sync",
        method="start_descaling",
        capability="descaling",
    ),
    SensoWashButtonDescription(
        key="nozzle_self_clean",
        translation_key="nozzle_self_clean",
        icon="mdi:spray",
        method="nozzle_self_clean",
        capability=None,
    ),
    SensoWashButtonDescription(
        key="nozzle_manual_clean",
        translation_key="nozzle_manual_clean",
        icon="mdi:spray-bottle",
        method="nozzle_manual_clean",
        capability=None,
    ),
    SensoWashButtonDescription(
        key="drain_tank",
        translation_key="drain_tank",
        icon="mdi:water-pump",
        method="drain_tank",
        kwargs={"drainage": TankDrainage.EN_1717},
        capability=None,
    ),
    SensoWashButtonDescription(
        key="factory_reset",
        translation_key="factory_reset",
        icon="mdi:restore-alert",
        method="factory_reset",
        capability=None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SensoWashConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SensoWashButton(coordinator, description)
        for description in BUTTONS
        if description.capability is None or coordinator.supports(description.capability)
    )


class SensoWashButton(SensoWashEntity, ButtonEntity):
    """A button entity for SensoWash."""

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
