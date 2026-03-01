"""Select entities for SensoWash (enum settings)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from sensowash.models import (
    WaterFlow, WaterTemperature, NozzlePosition,
    SeatTemperature, DryerTemperature, DryerSpeed, WaterHardness,
)

from .const import DOMAIN, ENTRY_COORDINATOR
from .coordinator import SensoWashCoordinator
from .entity import SensoWashEntity


@dataclass(frozen=True, kw_only=True)
class SensoWashSelectDescription(SelectEntityDescription):
    state_key: str
    set_method: str
    options_map: dict[str, Any]   # option label → enum value
    reverse_map: dict[Any, str] | None = None  # enum value → label (auto-built if None)


def _build(enum_class, labels: list[str]) -> tuple[dict[str, Any], dict[Any, str]]:
    """Build forward and reverse maps from an enum class and display labels."""
    members = list(enum_class)
    fwd = {label: member for label, member in zip(labels, members)}
    rev = {member: label for label, member in fwd.items()}
    return fwd, rev


_WF_FWD, _WF_REV = _build(WaterFlow, ["Low", "Medium", "High"])
_WT_FWD, _WT_REV = _build(WaterTemperature, ["Off", "Warm", "Warmer", "Hot"])
_NP_FWD, _NP_REV = _build(NozzlePosition, ["1 (forward)", "2", "3 (centre)", "4", "5 (rear)"])
_ST_FWD, _ST_REV = _build(SeatTemperature, ["Off", "Warm", "Warmer", "Hot"])
_DT_FWD, _DT_REV = _build(DryerTemperature, ["Off", "Warm", "Warmer", "Hot"])
_DS_FWD, _DS_REV = _build(DryerSpeed, ["Normal", "Turbo"])
_WH_FWD, _WH_REV = _build(WaterHardness, ["Soft", "Medium-soft", "Medium", "Medium-hard", "Hard"])


SELECTS: tuple[SensoWashSelectDescription, ...] = (
    SensoWashSelectDescription(
        key="water_flow",
        translation_key="water_flow",
        icon="mdi:water",
        state_key="water_flow",
        set_method="set_water_flow",
        options=list(_WF_FWD),
        options_map=_WF_FWD,
        reverse_map=_WF_REV,
    ),
    SensoWashSelectDescription(
        key="water_temperature",
        translation_key="water_temperature",
        icon="mdi:thermometer-water",
        state_key="water_temperature",
        set_method="set_water_temperature",
        options=list(_WT_FWD),
        options_map=_WT_FWD,
        reverse_map=_WT_REV,
    ),
    SensoWashSelectDescription(
        key="nozzle_position",
        translation_key="nozzle_position",
        icon="mdi:arrow-expand-vertical",
        state_key="nozzle_position",
        set_method="set_nozzle_position",
        options=list(_NP_FWD),
        options_map=_NP_FWD,
        reverse_map=_NP_REV,
    ),
    SensoWashSelectDescription(
        key="seat_temperature",
        translation_key="seat_temperature",
        icon="mdi:seat-recline-normal",
        state_key="seat_temperature",
        set_method="set_seat_temperature",
        options=list(_ST_FWD),
        options_map=_ST_FWD,
        reverse_map=_ST_REV,
    ),
    SensoWashSelectDescription(
        key="dryer_temperature",
        translation_key="dryer_temperature",
        icon="mdi:hair-dryer-outline",
        state_key="dryer_temperature",
        set_method="set_dryer_temperature",
        options=list(_DT_FWD),
        options_map=_DT_FWD,
        reverse_map=_DT_REV,
    ),
    SensoWashSelectDescription(
        key="dryer_speed",
        translation_key="dryer_speed",
        icon="mdi:fan",
        state_key="dryer_speed",
        set_method="set_dryer_speed",
        options=list(_DS_FWD),
        options_map=_DS_FWD,
        reverse_map=_DS_REV,
    ),
    SensoWashSelectDescription(
        key="water_hardness",
        translation_key="water_hardness",
        icon="mdi:water-check",
        state_key="water_hardness",
        set_method="set_water_hardness",
        options=list(_WH_FWD),
        options_map=_WH_FWD,
        reverse_map=_WH_REV,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SensoWashCoordinator = hass.data[DOMAIN][entry.entry_id][ENTRY_COORDINATOR]
    async_add_entities(
        SensoWashSelect(coordinator, description) for description in SELECTS
    )


class SensoWashSelect(SensoWashEntity, SelectEntity):
    entity_description: SensoWashSelectDescription

    def __init__(
        self,
        coordinator: SensoWashCoordinator,
        description: SensoWashSelectDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_options = description.options

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self.entity_description.state_key)
        if val is None:
            return None
        rev = self.entity_description.reverse_map
        if rev and val in rev:
            return rev[val]
        return str(val)

    async def async_select_option(self, option: str) -> None:
        enum_val = self.entity_description.options_map[option]
        await self.coordinator.async_command(
            self.entity_description.set_method, enum_val
        )
        await self.coordinator.async_request_refresh()
