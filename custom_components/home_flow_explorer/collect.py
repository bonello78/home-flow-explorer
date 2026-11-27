"""Read Home Assistant's registries into the plain snapshot graph.build() expects."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.loader import async_get_integrations

_LOGGER = logging.getLogger(__name__)


async def async_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    """Return devices, entities, integrations and automations as plain data."""
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    entries = hass.config_entries.async_entries()
    entry_domain = {e.entry_id: e.domain for e in entries}

    domains = {e.domain for e in entries}
    integrations: dict[str, dict] = {}
    try:
        loaded = await async_get_integrations(hass, domains)
    except Exception:  # noqa: BLE001 - a broken custom integration must not break the map
        loaded = {}
    for dom, integ in loaded.items():
        if isinstance(integ, Exception):
            continue
        integrations[dom] = {
            "name": getattr(integ, "name", dom),
            "iot_class": getattr(integ, "iot_class", None),
            "type": getattr(integ, "integration_type", None),
        }

    devices = []
    host_label = None
    for d in dev_reg.devices.values():
        entry_id = getattr(d, "primary_config_entry", None) or next(iter(d.config_entries), None)
        ident = [list(i) for i in d.identifiers]
        if ident and ident[0][0] == "hassio" and ident[0][1] == "OS":
            host_label = d.model or d.name
        devices.append({
            "id": d.id,
            "name": d.name_by_user or d.name or "",
            "domain": entry_domain.get(entry_id),
            "via": d.via_device_id,
            "identifiers": ident,
            "manufacturer": d.manufacturer,
            "model": d.model,
            "entry_type": d.entry_type.value if d.entry_type else None,
            "disabled": d.disabled_by is not None,
            "area": d.area_id,
        })

    entities = []
    for e in ent_reg.entities.values():
        entities.append({
            "entity_id": e.entity_id,
            "device_id": e.device_id,
            "platform": e.platform,
            "name": e.name or e.original_name,
            "entity_category": e.entity_category.value if e.entity_category else None,
            "disabled": e.disabled_by is not None,
        })

    automations = []
    component = hass.data.get("automation")
    for ent in list(getattr(component, "entities", []) or []):
        cfg = getattr(ent, "raw_config", None)
        if not isinstance(cfg, dict):
            continue
        state = hass.states.get(ent.entity_id)
        automations.append({
            "entity_id": ent.entity_id,
            "name": (state.attributes.get("friendly_name") if state else None) or cfg.get("alias") or ent.entity_id,
            "enabled": state is None or state.state != "off",
            "config": cfg,
        })

    return {
        "language": hass.config.language,
        "host_label": host_label,
        "integrations": integrations,
        "entries": [{"entry_id": e.entry_id, "domain": e.domain, "disabled": e.disabled_by is not None} for e in entries],
        "devices": devices,
        "entities": entities,
        "automations": automations,
    }


async def async_choices(hass: HomeAssistant) -> dict[str, Any]:
    """Data the setup and options forms need: integrations with devices, APs found, automations."""
    from .graph import IGNORE_DOMAINS, NETWORK_DOMAINS  # pylint: disable=import-outside-toplevel

    snap = await async_snapshot(hass)
    counts: dict[str, int] = {}
    aps: list[tuple[str, str]] = []
    for d in snap["devices"]:
        dom = d["domain"]
        if not dom or d["disabled"] or d["entry_type"] == "service":
            continue
        if dom in NETWORK_DOMAINS and not d["via"]:
            aps.append((d["id"], d["name"] or d["model"] or dom))
        if dom in IGNORE_DOMAINS:
            continue
        counts[dom] = counts.get(dom, 0) + 1
    names = {k: v.get("name") or k for k, v in snap["integrations"].items()}
    return {
        "integrations": sorted(((dom, f"{names.get(dom, dom)} ({n})") for dom, n in counts.items() if n),
                               key=lambda x: x[1].lower()),
        "aps": aps,
        "automations": sorted(((a["entity_id"], a["name"]) for a in snap["automations"]), key=lambda x: x[1].lower()),
        "host_label": snap["host_label"],
        "language": snap["language"],
    }
