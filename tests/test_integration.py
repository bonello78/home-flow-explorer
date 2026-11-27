"""End-to-end tests: guided setup, options, websocket command and export action."""

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.home_flow_explorer.const import DOMAIN


async def _populate(hass):
    """A small home: a Zigbee2MQTT light and a cloud thermostat."""
    mqtt_entry = MockConfigEntry(domain="mqtt", title="MQTT")
    mqtt_entry.add_to_hass(hass)
    cloud_entry = MockConfigEntry(domain="netatmo", title="Netatmo")
    cloud_entry.add_to_hass(hass)
    deco_entry = MockConfigEntry(domain="tplink_deco", title="Deco")
    deco_entry.add_to_hass(hass)
    devreg = dr.async_get(hass)
    entreg = er.async_get(hass)
    bridge = devreg.async_get_or_create(config_entry_id=mqtt_entry.entry_id, identifiers={("mqtt", "zigbee2mqtt_bridge_0x1")},
                                        manufacturer="Zigbee2MQTT", name="Zigbee2MQTT Bridge")
    lamp = devreg.async_get_or_create(config_entry_id=mqtt_entry.entry_id, identifiers={("mqtt", "zigbee2mqtt_0x2")},
                                      manufacturer="IKEA", name="Floor lamp", via_device=("mqtt", "zigbee2mqtt_bridge_0x1"))
    valve = devreg.async_get_or_create(config_entry_id=cloud_entry.entry_id, identifiers={("netatmo", "v1")},
                                       manufacturer="Netatmo", name="Living valve")
    devreg.async_get_or_create(config_entry_id=deco_entry.entry_id, identifiers={("tplink_deco", "ap1")},
                               manufacturer="TP-Link", model="Deco M4R", name="Deco")
    entreg.async_get_or_create("light", "mqtt", "lamp1", device_id=lamp.id, suggested_object_id="floor_lamp")
    entreg.async_get_or_create("climate", "netatmo", "valve1", device_id=valve.id, suggested_object_id="living")
    return bridge


async def _setup(hass):
    await _populate(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "router_name": "Fritz!Box", "router_address": "192.168.0.1", "ha_link": "switch", "switch_name": "",
        "wifi": "new", "ap_name": "", "host_label": "Mini PC"})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"switch_name": "required", "ap_name": "required"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "router_name": "Fritz!Box", "router_address": "192.168.0.1", "ha_link": "switch", "switch_name": "Switch",
        "wifi": "new", "ap_name": "Attic AP", "host_label": "Mini PC"})
    assert result["step_id"] == "scope"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "excluded_integrations": [], "max_gestures": 5, "max_automations": 6, "automations": []})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return hass.config_entries.async_entries(DOMAIN)[0]


async def test_setup_and_graph(hass, hass_ws_client):
    assert await async_setup_component(hass, "http", {})
    entry = await _setup(hass)
    kinds = {o["id"]: o["kind"] for o in entry.options["objects"]}
    assert kinds == {"router": "router", "switch": "switch", "ap": "access_point"}

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": f"{DOMAIN}/graph"})
    msg = await client.receive_json()
    assert msg["success"], msg
    graph = msg["result"]
    ids = {n["id"] for n in graph["nodes"]}
    assert {"router", "switch", "ap", "ha", "mqtt", "z2m", "coord", "grp_zigbee2mqtt", "grp_netatmo", "cloud_netatmo"} <= ids
    edges = {tuple(sorted(e[:2])) for e in graph["edges"]}
    for s in graph["scenarios"]:
        for st in s["steps"]:
            for a, b in zip(st["path"], st["path"][1:]):
                assert tuple(sorted((a, b))) in edges, (s["id"], a, b)
    titles = [s["title"] for s in graph["scenarios"]]
    assert any("Floor lamp" in t for t in titles)
    assert any("Living valve" in t for t in titles)

    resp = await hass.services.async_call(DOMAIN, "export", {}, blocking=True, return_response=True)
    assert resp["nodes"]


async def test_options(hass):
    assert await async_setup_component(hass, "http", {})
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "add_object"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "name": "HomeNAS", "kind": "nas", "connected_to": "switch", "medium": "cable", "address": "192.168.0.40", "info": ""})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    objs = {o["id"]: o for o in entry.options["objects"]}
    assert objs["obj_homenas"]["kind"] == "nas"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "edit_object"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"object": "obj_homenas"})
    assert result["step_id"] == "edit_object_form"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "name": "NAS", "kind": "nas", "connected_to": "router", "medium": "cable", "address": "", "info": "Backups"})
    await hass.async_block_till_done()
    assert {o["id"]: o for o in entry.options["objects"]}["obj_homenas"]["name"] == "NAS"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "settings"})
    assert result["step_id"] == "settings"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {
        "language": "it", "ha_link": "switch", "wifi": "ap", "host_label": "Proxmox", "excluded_integrations": ["netatmo"],
        "max_gestures": 3, "max_automations": 2, "automations": []})
    await hass.async_block_till_done()
    assert entry.options["excluded_integrations"] == ["netatmo"]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "remove_object"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"objects": ["obj_homenas"]})
    await hass.async_block_till_done()
    assert "obj_homenas" not in {o["id"] for o in entry.options["objects"]}

    resp = await hass.services.async_call(DOMAIN, "export", {}, blocking=True, return_response=True)
    assert resp["language"] == "it"
    assert "grp_netatmo" not in {n["id"] for n in resp["nodes"]}


async def test_single_instance(hass):
    assert await async_setup_component(hass, "http", {})
    await _setup(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == data_entry_flow.FlowResultType.ABORT


async def test_automation_scenario(hass, fake_frontend):
    assert await async_setup_component(hass, "http", {})
    await _populate(hass)
    assert await async_setup_component(hass, "automation", {"automation": [{
        "id": "a1", "alias": "Lamp warms the living room",
        "triggers": [{"trigger": "state", "entity_id": "light.floor_lamp", "to": "on"}],
        "actions": [{"action": "climate.set_temperature", "target": {"entity_id": "climate.living"}, "data": {"temperature": 21}}],
    }]})
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "router_name": "Router", "router_address": "", "ha_link": "router", "switch_name": "",
        "wifi": "router", "ap_name": "", "host_label": ""})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {
        "excluded_integrations": [], "max_gestures": 2, "max_automations": 5, "automations": []})
    await hass.async_block_till_done()
    fake_frontend.assert_called_once()
    assert "/home_flow_explorer_static/home-flow-explorer.js" in fake_frontend.call_args[0][1]
    resp = await hass.services.async_call(DOMAIN, "export", {}, blocking=True, return_response=True)
    auto = [s for s in resp["scenarios"] if s["group"] == "automazioni"]
    assert auto and auto[0]["title"] == "Lamp warms the living room"
    paths = [st["path"] for st in auto[0]["steps"]]
    assert paths[0][0] == "grp_zigbee2mqtt" and paths[0][-1] == "ha"
    assert paths[-1][-1] == "grp_netatmo" and auto[0]["steps"][-1].get("out") is True
