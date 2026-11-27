"""Home Flow Explorer: a map of how messages travel through your home."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .collect import async_snapshot
from .const import CARD_FILE, DOMAIN, URL_BASE, VERSION
from .graph import build

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the card, register the websocket command and the export action."""
    www = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(www), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILE}?v={VERSION}")
    websocket_api.async_register_command(hass, ws_graph)

    async def export(call: ServiceCall) -> ServiceResponse:
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if user is None or not user.is_admin:
                raise Unauthorized()
        entry = _entry(hass)
        if entry is None:
            raise HomeAssistantError("Home Flow Explorer is not set up")
        return await async_graph(hass, entry)

    hass.services.async_register(DOMAIN, "export", export, schema=vol.Schema({}),
                                 supports_response=SupportsResponse.ONLY)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Nothing to start: the map is built on request."""
    entry.async_on_unload(entry.add_update_listener(_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload."""
    return True


async def _updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Options changed: nothing is cached, the next request rebuilds the map."""


@callback
def _entry(hass: HomeAssistant) -> ConfigEntry | None:
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


async def async_graph(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Build the card configuration from the current registries."""
    snap = await async_snapshot(hass)
    opts = {**entry.data, **entry.options}
    try:
        return build(snap, opts)
    except Exception as err:  # noqa: BLE001
        _LOGGER.exception("Could not build the map")
        raise HomeAssistantError(f"Could not build the map: {err}") from err


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/graph"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_graph(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """Return the map for the card. Admins only: it describes the whole network."""
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "Home Flow Explorer is not set up")
        return
    try:
        data = await async_graph(hass, entry)
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "build_failed", str(err))
        return
    connection.send_result(msg["id"], data)
