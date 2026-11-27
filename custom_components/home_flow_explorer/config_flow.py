"""Guided setup and options for Home Flow Explorer."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .collect import async_choices
from .const import (
    CONF_AUTOMATIONS,
    CONF_EXCLUDED,
    CONF_HA_LINK,
    CONF_HOST_LABEL,
    CONF_LANGUAGE,
    CONF_MAX_AUTOMATIONS,
    CONF_MAX_GESTURES,
    CONF_OBJECTS,
    CONF_WIFI,
    DEFAULT_MAX_AUTOMATIONS,
    DEFAULT_MAX_GESTURES,
    DOMAIN,
    MEDIA,
    OBJECT_KINDS,
)

LABELS = {
    "it": {
        "direct": "Cavo diretto al router", "via_switch": "Tramite uno switch",
        "wifi_router": "Wi-Fi del router", "wifi_new": "Un access point da aggiungere", "found": "rilevato",
        "kind": {"router": "Router", "access_point": "Access point", "switch": "Switch", "nas": "NAS",
                 "server": "Server", "cloud": "Servizio cloud", "device": "Dispositivo", "other": "Altro"},
        "medium": {"cable": "Cavo", "wifi": "Wi-Fi", "zigbee": "Zigbee / radio", "internet": "Internet",
                   "internal": "Dentro la stessa macchina"},
        "ha": "Home Assistant", "it": "Italiano", "en": "English",
    },
    "en": {
        "direct": "Cable straight to the router", "via_switch": "Through a switch",
        "wifi_router": "The router's Wi-Fi", "wifi_new": "An access point to add", "found": "found",
        "kind": {"router": "Router", "access_point": "Access point", "switch": "Switch", "nas": "NAS",
                 "server": "Server", "cloud": "Cloud service", "device": "Device", "other": "Other"},
        "medium": {"cable": "Cable", "wifi": "Wi-Fi", "zigbee": "Zigbee / radio", "internet": "Internet",
                   "internal": "Inside the same machine"},
        "ha": "Home Assistant", "it": "Italiano", "en": "English",
    },
}


def _lang(hass) -> str:
    return "it" if str(hass.config.language or "").startswith("it") else "en"


def _slug(text: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_") or "obj"
    base = "obj_" + base
    out, n = base, 2
    while out in taken:
        out, n = f"{base}_{n}", n + 1
    return out


def _select(options: list[tuple[str, str]], multiple: bool = False, dropdown: bool = True) -> SelectSelector:
    return SelectSelector(SelectSelectorConfig(
        options=[SelectOptionDict(value=v, label=l) for v, l in options],
        multiple=multiple,
        mode=SelectSelectorMode.DROPDOWN if dropdown else SelectSelectorMode.LIST,
    ))


def _number(lo: int, hi: int) -> NumberSelector:
    return NumberSelector(NumberSelectorConfig(min=lo, max=hi, step=1, mode=NumberSelectorMode.BOX))


class HomeFlowExplorerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Guided setup: the network part Home Assistant cannot see, then what to show."""

    VERSION = 1

    def __init__(self) -> None:
        self._opts: dict[str, Any] = {}
        self._choices: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HomeFlowExplorerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        lab = LABELS[_lang(self.hass)]
        if not self._choices:
            self._choices = await async_choices(self.hass)
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("ha_link") == "switch" and not (user_input.get("switch_name") or "").strip():
                errors["switch_name"] = "required"
            if user_input.get("wifi") == "new" and not (user_input.get("ap_name") or "").strip():
                errors["ap_name"] = "required"
            if not errors:
                objects = [{"id": "router", "name": user_input["router_name"].strip() or "Router", "kind": "router",
                            "address": (user_input.get("router_address") or "").strip()}]
                ha_link = "router"
                if user_input.get("ha_link") == "switch":
                    objects.append({"id": "switch", "name": user_input["switch_name"].strip(), "kind": "switch",
                                    "connected_to": "router", "medium": "cable"})
                    ha_link = "switch"
                wifi = user_input.get("wifi") or "router"
                if wifi == "new":
                    objects.append({"id": "ap", "name": user_input["ap_name"].strip(), "kind": "access_point",
                                    "connected_to": "router", "medium": "cable"})
                    wifi = "ap"
                self._opts = {
                    CONF_LANGUAGE: _lang(self.hass),
                    CONF_OBJECTS: objects,
                    CONF_HA_LINK: ha_link,
                    CONF_WIFI: wifi,
                    CONF_HOST_LABEL: (user_input.get("host_label") or "").strip(),
                }
                return await self.async_step_scope()

        wifi_opts = [("router", lab["wifi_router"])]
        wifi_opts += [(f"auto:{did}", f"{name} ({lab['found']})") for did, name in self._choices["aps"]]
        wifi_opts.append(("new", lab["wifi_new"]))
        default_wifi = wifi_opts[1][0] if len(wifi_opts) > 2 else "router"
        schema = vol.Schema({
            vol.Required("router_name", default="Router"): TextSelector(),
            vol.Optional("router_address", default=""): TextSelector(),
            vol.Required("ha_link", default="router"): _select([("router", lab["direct"]), ("switch", lab["via_switch"])], dropdown=False),
            vol.Optional("switch_name", default=""): TextSelector(),
            vol.Required("wifi", default=default_wifi): _select(wifi_opts),
            vol.Optional("ap_name", default=""): TextSelector(),
            vol.Optional("host_label", default=self._choices.get("host_label") or ""): TextSelector(),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_scope(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._opts.update({
                CONF_EXCLUDED: user_input.get(CONF_EXCLUDED, []),
                CONF_MAX_GESTURES: int(user_input.get(CONF_MAX_GESTURES, DEFAULT_MAX_GESTURES)),
                CONF_MAX_AUTOMATIONS: int(user_input.get(CONF_MAX_AUTOMATIONS, DEFAULT_MAX_AUTOMATIONS)),
                CONF_AUTOMATIONS: user_input.get(CONF_AUTOMATIONS, []),
            })
            return self.async_create_entry(title="Home Flow Explorer", data={}, options=self._opts)
        schema = vol.Schema({
            vol.Optional(CONF_EXCLUDED, default=[]): _select(self._choices["integrations"], multiple=True),
            vol.Required(CONF_MAX_GESTURES, default=DEFAULT_MAX_GESTURES): _number(0, 10),
            vol.Required(CONF_MAX_AUTOMATIONS, default=DEFAULT_MAX_AUTOMATIONS): _number(0, 20),
            vol.Optional(CONF_AUTOMATIONS, default=[]): _select(self._choices["automations"], multiple=True),
        })
        return self.async_show_form(step_id="scope", data_schema=schema)


class HomeFlowExplorerOptionsFlow(OptionsFlow):
    """Add, edit and remove the objects Home Assistant cannot see; change what is shown."""

    def __init__(self) -> None:
        self._opts: dict[str, Any] = {}
        self._editing: str | None = None
        self._choices: dict[str, Any] = {}

    def _load(self) -> None:
        if not self._opts:
            self._opts = {**self.config_entry.data, **self.config_entry.options}
            self._opts[CONF_OBJECTS] = [dict(o) for o in self._opts.get(CONF_OBJECTS, [])]

    @property
    def _lab(self) -> dict:
        return LABELS[_lang(self.hass)]

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._load()
        return self.async_show_menu(step_id="init", menu_options=["add_object", "edit_object", "remove_object", "settings"])

    def _object_schema(self, obj: dict | None = None) -> vol.Schema:
        obj = obj or {}
        lab = self._lab
        targets = [(o["id"], o["name"]) for o in self._opts[CONF_OBJECTS] if o["id"] != obj.get("id")]
        targets.append(("home_assistant", lab["ha"]))
        default_target = obj.get("connected_to") or next((o["id"] for o in self._opts[CONF_OBJECTS] if o.get("kind") == "router"), "home_assistant")
        return vol.Schema({
            vol.Required("name", default=obj.get("name", "")): TextSelector(),
            vol.Required("kind", default=obj.get("kind", "access_point")): _select([(k, lab["kind"][k]) for k in OBJECT_KINDS]),
            vol.Required("connected_to", default=default_target): _select(targets),
            vol.Required("medium", default=obj.get("medium", "cable")): _select([(m, lab["medium"][m]) for m in MEDIA]),
            vol.Optional("address", default=obj.get("address", "")): TextSelector(),
            vol.Optional("info", default=obj.get("info", "")): TextSelector(),
        })

    async def async_step_add_object(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._load()
        if user_input is not None:
            taken = {o["id"] for o in self._opts[CONF_OBJECTS]}
            obj = {k: (v.strip() if isinstance(v, str) else v) for k, v in user_input.items()}
            obj["id"] = _slug(obj["name"], taken)
            self._opts[CONF_OBJECTS].append(obj)
            return self.async_create_entry(data=self._opts)
        return self.async_show_form(step_id="add_object", data_schema=self._object_schema())

    async def async_step_edit_object(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._load()
        if user_input is not None:
            self._editing = user_input["object"]
            return await self.async_step_edit_object_form()
        objs = [(o["id"], o["name"]) for o in self._opts[CONF_OBJECTS]]
        return self.async_show_form(step_id="edit_object", data_schema=vol.Schema({vol.Required("object"): _select(objs)}))

    async def async_step_edit_object_form(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        obj = next(o for o in self._opts[CONF_OBJECTS] if o["id"] == self._editing)
        if user_input is not None:
            obj.update({k: (v.strip() if isinstance(v, str) else v) for k, v in user_input.items()})
            return self.async_create_entry(data=self._opts)
        return self.async_show_form(step_id="edit_object_form", data_schema=self._object_schema(obj),
                                    description_placeholders={"name": obj["name"]})

    async def async_step_remove_object(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._load()
        removable = [(o["id"], o["name"]) for o in self._opts[CONF_OBJECTS] if o.get("kind") != "router"]
        if user_input is not None:
            gone = set(user_input.get("objects", []))
            self._opts[CONF_OBJECTS] = [o for o in self._opts[CONF_OBJECTS] if o["id"] not in gone]
            for o in self._opts[CONF_OBJECTS]:
                if o.get("connected_to") in gone:
                    o["connected_to"] = "router"
            if self._opts.get(CONF_HA_LINK) in gone:
                self._opts[CONF_HA_LINK] = "router"
            if self._opts.get(CONF_WIFI) in gone:
                self._opts[CONF_WIFI] = "router"
            return self.async_create_entry(data=self._opts)
        if not removable:
            return self.async_abort(reason="nothing_to_remove")
        return self.async_show_form(step_id="remove_object",
                                    data_schema=vol.Schema({vol.Optional("objects", default=[]): _select(removable, multiple=True)}))

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        self._load()
        if not self._choices:
            self._choices = await async_choices(self.hass)
        lab = self._lab
        if user_input is not None:
            self._opts.update({
                CONF_LANGUAGE: user_input[CONF_LANGUAGE],
                CONF_HA_LINK: user_input[CONF_HA_LINK],
                CONF_WIFI: user_input[CONF_WIFI],
                CONF_HOST_LABEL: (user_input.get(CONF_HOST_LABEL) or "").strip(),
                CONF_EXCLUDED: user_input.get(CONF_EXCLUDED, []),
                CONF_MAX_GESTURES: int(user_input[CONF_MAX_GESTURES]),
                CONF_MAX_AUTOMATIONS: int(user_input[CONF_MAX_AUTOMATIONS]),
                CONF_AUTOMATIONS: user_input.get(CONF_AUTOMATIONS, []),
            })
            return self.async_create_entry(data=self._opts)
        objs = self._opts[CONF_OBJECTS]
        links = [(o["id"], o["name"]) for o in objs if o.get("kind") in ("router", "switch", "access_point", "server", "nas", "other")]
        wifi = [(o["id"], o["name"]) for o in objs if o.get("kind") in ("router", "access_point")]
        wifi += [(f"auto:{did}", f"{name} ({lab['found']})") for did, name in self._choices["aps"]]
        known_int = {v for v, _ in self._choices["integrations"]}
        known_aut = {v for v, _ in self._choices["automations"]}
        cur_wifi = self._opts.get(CONF_WIFI, "router")
        if cur_wifi not in {v for v, _ in wifi}:
            cur_wifi = wifi[0][0] if wifi else "router"
        schema = vol.Schema({
            vol.Required(CONF_LANGUAGE, default=self._opts.get(CONF_LANGUAGE, _lang(self.hass))): _select([("it", lab["it"]), ("en", lab["en"])], dropdown=False),
            vol.Required(CONF_HA_LINK, default=self._opts.get(CONF_HA_LINK, "router")): _select(links or [("router", "Router")]),
            vol.Required(CONF_WIFI, default=cur_wifi): _select(wifi or [("router", "Router")]),
            vol.Optional(CONF_HOST_LABEL, default=self._opts.get(CONF_HOST_LABEL, "")): TextSelector(),
            vol.Optional(CONF_EXCLUDED, default=[x for x in self._opts.get(CONF_EXCLUDED, []) if x in known_int]): _select(self._choices["integrations"], multiple=True),
            vol.Required(CONF_MAX_GESTURES, default=self._opts.get(CONF_MAX_GESTURES, DEFAULT_MAX_GESTURES)): _number(0, 10),
            vol.Required(CONF_MAX_AUTOMATIONS, default=self._opts.get(CONF_MAX_AUTOMATIONS, DEFAULT_MAX_AUTOMATIONS)): _number(0, 20),
            vol.Optional(CONF_AUTOMATIONS, default=[x for x in self._opts.get(CONF_AUTOMATIONS, []) if x in known_aut]): _select(self._choices["automations"], multiple=True),
        })
        return self.async_show_form(step_id="settings", data_schema=schema)
