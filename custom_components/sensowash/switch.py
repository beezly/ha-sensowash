"""Switches for SensoWash."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from sensowash.models import OnOff

from .const import DOMAIN, ENTRY_COORDINATOR
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashSwitchDescription(SwitchEntityDescription):
    state_key: str
    turn_on_method: str
    turn_off_method: str
    turn_on_kwargs: dict[str, Any] | None = None
    turn_off_kwargs: dict[str, Any] | None = None


SWITCHES: tuple[SensoWashSwitchDescription, ...] = (
    SensoWashSwitchDescription(
        key="ambient_light",
        translation_key="ambient_light",
        icon="mdi:lightbulb-outline",
        state_key="ambient_light",
        turn_on_method="set_ambient_light",
        turn_off_method="set_ambient_light",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
    SensoWashSwitchDescription(
        key="uvc_light",
        translation_key="uvc_light",
        icon="mdi:uv",
        state_key="uvc_light",
        turn_on_method="set_uvc_light",
        turn_off_method="set_uvc_light",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
    SensoWashSwitchDescription(
        key="uvc_auto",
        translation_key="uvc_auto",
        icon="mdi:uv",
        state_key="uvc_auto",
        turn_on_method="set_uvc_auto",
        turn_off_method="set_uvc_auto",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
    SensoWashSwitchDescription(
        key="deodorization",
        translation_key="deodorization",
        icon="mdi:air-filter",
        state_key="deodorization",
        turn_on_method="set_deodorization",
        turn_off_method="set_deodorization",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
    SensoWashSwitchDescription(
        key="deodorization_auto",
        translation_key="deodorization_auto",
        icon="mdi:air-filter",
        state_key="deodorization_auto",
        turn_on_method="set_deodorization_auto",
        turn_off_method="set_deodorization_auto",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
    SensoWashSwitchDescription(
        key="auto_flush",
        translation_key="auto_flush",
        icon="mdi:toilet",
        state_key="flush_automatic",
        turn_on_method="set_auto_flush",
        turn_off_method="set_auto_flush",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
    SensoWashSwitchDescription(
        key="pre_flush",
        translation_key="pre_flush",
        icon="mdi:toilet",
        state_key="flush_pre_flush",
        turn_on_method="set_pre_flush",
        turn_off_method="set_pre_flush",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
    SensoWashSwitchDescription(
        key="proximity_detection",
        translation_key="proximity_detection",
        icon="mdi:motion-sensor",
        state_key="seat_proximity",
        turn_on_method="set_proximity_detection",
        turn_off_method="set_proximity_detection",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
    SensoWashSwitchDescription(
        key="mute",
        translation_key="mute",
        icon="mdi:volume-off",
        state_key="mute",
        turn_on_method="set_mute",
        turn_off_method="set_mute",
        turn_on_kwargs={"muted": True},
        turn_off_kwargs={"muted": False},
    ),
    SensoWashSwitchDescription(
        key="seat_auto",
        translation_key="seat_auto",
        icon="mdi:seat",
        state_key="seat_auto",
        turn_on_method="set_seat_auto",
        turn_off_method="set_seat_auto",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SensoWashCoordinator = hass.data[DOMAIN][entry.entry_id][ENTRY_COORDINATOR]
    async_add_entities(
        SensoWashSwitch(coordinator, description) for description in SWITCHES
    )


class SensoWashSwitch(SensoWashEntity, SwitchEntity):
    entity_description: SensoWashSwitchDescription

    def __init__(
        self,
        coordinator: SensoWashCoordinator,
        description: SensoWashSwitchDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self.entity_description.state_key)
        if val is None:
            return None
        if isinstance(val, OnOff):
            return val == OnOff.ON
        return bool(val)

    async def async_turn_on(self, **kwargs: Any) -> None:
        desc = self.entity_description
        await self.coordinator.async_command(
            desc.turn_on_method, **(desc.turn_on_kwargs or {})
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        desc = self.entity_description
        await self.coordinator.async_command(
            desc.turn_off_method, **(desc.turn_off_kwargs or {})
        )
        await self.coordinator.async_request_refresh()
