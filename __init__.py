"""EseeCloud PTZ integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DEFAULT_PORT, DIRECTIONS, DOMAIN, MOVE_DIRECTIONS, SERVICE_MOVE,
    SERVICE_START_MOVE, SERVICE_STOP,
)
from .protocol import EseeCloudProtocolError, EseeCloudSessionManager

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

BASE_SCHEMA = {
    vol.Required("host"): cv.string,
    vol.Optional("port", default=DEFAULT_PORT): cv.port,
    vol.Required("channel"): vol.All(vol.Coerce(int), vol.Range(min=0, max=3)),
}

MOVE_SCHEMA = vol.Schema({
    **BASE_SCHEMA,
    vol.Required("direction"): vol.In(DIRECTIONS),
    vol.Optional("duration_ms", default=120): vol.All(vol.Coerce(int), vol.Range(min=20, max=5000)),
    vol.Optional("repeat_ms", default=80): vol.All(vol.Coerce(int), vol.Range(min=20, max=1000)),
})

START_SCHEMA = vol.Schema({
    **BASE_SCHEMA,
    vol.Required("direction"): vol.In(MOVE_DIRECTIONS),
    vol.Optional("repeat_ms", default=80): vol.All(vol.Coerce(int), vol.Range(min=20, max=1000)),
})

STOP_SCHEMA = vol.Schema(BASE_SCHEMA)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    manager = EseeCloudSessionManager()
    hass.data[DOMAIN] = manager

    async def _raise(callable_coro) -> None:
        try:
            await callable_coro
        except EseeCloudProtocolError as err:
            raise HomeAssistantError(f"EseeCloud PTZ command failed: {err}") from err
        except (OSError, TimeoutError, ValueError) as err:
            raise HomeAssistantError(
                f"EseeCloud PTZ command could not be executed: {err}"
            ) from err

    async def handle_move(call: ServiceCall) -> None:
        await _raise(manager.async_move(
            call.data["host"], call.data["port"], call.data["channel"],
            call.data["direction"], call.data["duration_ms"], call.data["repeat_ms"],
        ))

    async def handle_start_move(call: ServiceCall) -> None:
        await _raise(manager.async_start_move(
            call.data["host"], call.data["port"], call.data["channel"],
            call.data["direction"], call.data["repeat_ms"],
        ))

    async def handle_stop(call: ServiceCall) -> None:
        await _raise(manager.async_stop(
            call.data["host"], call.data["port"], call.data["channel"],
        ))

    async def async_shutdown(_event) -> None:
        await manager.async_close_all()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_shutdown)
    hass.services.async_register(DOMAIN, SERVICE_MOVE, handle_move, schema=MOVE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_START_MOVE, handle_start_move, schema=START_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP, handle_stop, schema=STOP_SCHEMA)
    return True
