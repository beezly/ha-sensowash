"""Custom services for SensoWash scheduling."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .lib.models import (
    SeatHeatingSchedule,
    SeatScheduleWindow,
    SeatTemperature,
    UvcSchedule,
    UvcScheduleTime,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ── Seat heating schedule ──────────────────────────────────────────────────────

_WINDOW_SCHEMA = vol.Schema({
    vol.Required("from_hour"):   vol.All(int, vol.Range(min=0, max=23)),
    vol.Required("from_minute"): vol.All(int, vol.Range(min=0, max=59)),
    vol.Required("to_hour"):     vol.All(int, vol.Range(min=0, max=23)),
    vol.Required("to_minute"):   vol.All(int, vol.Range(min=0, max=59)),
    vol.Required("days"):        vol.All(
        [vol.All(int, vol.Range(min=1, max=7))],
        vol.Length(min=1),
    ),
})

SET_SEAT_SCHEDULE_SCHEMA = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Optional("enabled", default=True): cv.boolean,
    vol.Optional("temperature", default=1): vol.All(int, vol.Range(min=0, max=3)),
    vol.Optional("windows", default=[]): [_WINDOW_SCHEMA],
})

GET_SCHEDULE_SCHEMA = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
})

# ── UVC schedule ───────────────────────────────────────────────────────────────

_TRIGGER_SCHEMA = vol.Schema({
    vol.Required("hour"):   vol.All(int, vol.Range(min=0, max=23)),
    vol.Required("minute"): vol.All(int, vol.Range(min=0, max=59)),
})

SET_UVC_SCHEDULE_SCHEMA = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Optional("triggers", default=[]): [_TRIGGER_SCHEMA],
})


def _get_coordinator(hass: HomeAssistant, call: ServiceCall):
    entry_id = call.data["config_entry_id"]
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ValueError(f"Unknown config entry: {entry_id}")
    return entry.runtime_data


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register custom SensoWash services."""

    async def handle_set_seat_heating_schedule(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        windows = [
            SeatScheduleWindow(
                from_hour=w["from_hour"],
                from_minute=w["from_minute"],
                to_hour=w["to_hour"],
                to_minute=w["to_minute"],
                days=tuple(w["days"]),
            )
            for w in call.data.get("windows", [])
        ]
        try:
            temperature = SeatTemperature(call.data.get("temperature", 1))
        except ValueError:
            temperature = SeatTemperature.TEMP_1

        schedule = SeatHeatingSchedule(
            enabled=call.data.get("enabled", True),
            temperature=temperature,
            windows=windows,
        )
        await coordinator.async_command("set_seat_heating_schedule", schedule)
        _LOGGER.info("%s: seat heating schedule updated", coordinator.device_name)

    async def handle_get_seat_heating_schedule(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        client = await coordinator._get_client()
        schedule = await client.get_seat_heating_schedule()
        if schedule:
            _LOGGER.info(
                "%s: seat heating schedule — enabled=%s temp=%s windows=%s",
                coordinator.device_name,
                schedule.enabled,
                schedule.temperature.name,
                [
                    {
                        "from": f"{w.from_hour:02d}:{w.from_minute:02d}",
                        "to": f"{w.to_hour:02d}:{w.to_minute:02d}",
                        "days": list(w.days),
                    }
                    for w in schedule.windows
                ],
            )

    async def handle_set_uvc_schedule(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        triggers = [
            UvcScheduleTime(hour=t["hour"], minute=t["minute"])
            for t in call.data.get("triggers", [])
        ]
        schedule = UvcSchedule(triggers=triggers)
        await coordinator.async_command("set_uvc_schedule", schedule)
        _LOGGER.info("%s: UVC schedule updated", coordinator.device_name)

    async def handle_set_uvc_schedule_default(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.async_command("set_uvc_schedule_default")
        _LOGGER.info("%s: UVC schedule reset to default", coordinator.device_name)

    async def handle_clear_seat_heating_schedule(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.async_command("clear_seat_heating_schedule")
        _LOGGER.info("%s: seat heating schedule cleared", coordinator.device_name)

    hass.services.async_register(
        DOMAIN, "set_seat_heating_schedule",
        handle_set_seat_heating_schedule,
        schema=SET_SEAT_SCHEDULE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "get_seat_heating_schedule",
        handle_get_seat_heating_schedule,
        schema=GET_SCHEDULE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "clear_seat_heating_schedule",
        handle_clear_seat_heating_schedule,
        schema=GET_SCHEDULE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "set_uvc_schedule",
        handle_set_uvc_schedule,
        schema=SET_UVC_SCHEDULE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, "set_uvc_schedule_default",
        handle_set_uvc_schedule_default,
        schema=GET_SCHEDULE_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove SensoWash services."""
    for service in (
        "set_seat_heating_schedule",
        "get_seat_heating_schedule",
        "clear_seat_heating_schedule",
        "set_uvc_schedule",
        "set_uvc_schedule_default",
    ):
        hass.services.async_remove(DOMAIN, service)
