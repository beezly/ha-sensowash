"""Switches for SensoWash."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .lib.models import OnOff

from . import SensoWashConfigEntry
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashSwitchDescription(SwitchEntityDescription):
    """Extends SwitchEntityDescription with state key, command methods, and capability guard."""

    state_key: str
    turn_on_method: str
    turn_off_method: str
    turn_on_kwargs: dict[str, Any] | None = None
    turn_off_kwargs: dict[str, Any] | None = None
    # capability name on DeviceCapabilities; None = always show
    capability: str | None = None


SWITCHES: tuple[SensoWashSwitchDescription, ...] = (
    SensoWashSwitchDescription(
        key="uvc_light",
        translation_key="uvc_light",
        icon="mdi:radioactive",
        state_key="uvc_light",
        turn_on_method="set_uvc_light",
        turn_off_method="set_uvc_light",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
        capability="uvc_light",
    ),
    SensoWashSwitchDescription(
        key="uvc_auto",
        translation_key="uvc_auto",
        icon="mdi:radioactive",
        state_key="uvc_auto",
        turn_on_method="set_uvc_auto",
        turn_off_method="set_uvc_auto",
        turn_on_kwargs={"enabled": True},
        turn_off_kwargs={"enabled": False},
        capability="uvc_auto",
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
        capability="deodorization",
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
        capability="deodorization_auto",
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
        capability="auto_flush",
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
        capability="pre_flush",
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
        capability="mute",
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
        capability="seat_auto",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SensoWashConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SensoWashSwitch(coordinator, description)
        for description in SWITCHES
        if description.capability is None or coordinator.supports(description.capability)
    )


class SensoWashSwitch(SensoWashEntity, SwitchEntity):
    """A switch entity for SensoWash."""

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
