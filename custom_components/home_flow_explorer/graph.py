"""Build the Home Flow Explorer map from a plain snapshot of Home Assistant.

Nothing in this module imports Home Assistant: collect.py turns the registries
into plain dicts, this module turns those dicts into the card configuration
(nodes, edges, boxes, scenarios). That keeps the logic testable offline.
"""

from __future__ import annotations

from collections import Counter, deque
import re
from typing import Any

from .const import (
    CONF_AUTOMATIONS,
    CONF_EXCLUDED,
    CONF_HA_LINK,
    CONF_HOST_LABEL,
    CONF_MAX_AUTOMATIONS,
    CONF_MAX_GESTURES,
    CONF_OBJECTS,
    CONF_WIFI,
    DEFAULT_MAX_AUTOMATIONS,
    DEFAULT_MAX_GESTURES,
    OBJECT_KINDS,
)

# Integrations whose devices are network gear: shown as infrastructure, not as device groups.
NETWORK_DOMAINS = {
    "tplink_deco", "tplink_omada", "unifi", "fritz", "asuswrt", "netgear", "luci", "ubus",
    "mikrotik", "keenetic_ndms2", "huawei_lte", "vodafone_station", "ruckus_unleashed",
    "aruba", "cisco_ios", "linksys_smart", "tplink_router", "openwrt", "eero", "google_wifi",
    "nest_wifi", "orbi", "devolo_home_network", "ubiquiti",
}
NAS_DOMAINS = {"synology_dsm", "qnap", "qnap_qsw", "truenas", "unraid", "openmediavault"}
# Integrations that never make sense as a group of physical devices.
IGNORE_DOMAINS = {
    "hassio", "homeassistant", "backup", "cloud", "sun", "met", "nmap_tracker", "ping",
    "thermal_comfort", "scheduler", "alarmo", "nodered", "mobile_app", "zone", "person",
    "speedtestdotnet", "dnsip", "upnp", "co2signal", "forecast_solar", "open_meteo", "pun",
    "season", "workday", "holiday", "moon", "time_date", "uptime", "systemmonitor",
    "google_translate", "radio_browser", "shopping_list", "local_calendar", "local_todo",
    "home_flow_explorer", "ha_mcp_tools", "hacs", "spotify", "watchman",
}
IGNORE_TYPES = {"service", "system", "helper", "entity", "virtual", "hardware"}
HELPER_DOMAINS = {
    "input_boolean", "input_number", "input_select", "input_text", "input_datetime",
    "input_button", "counter", "timer", "group", "template", "script", "automation",
    "scene", "schedule", "variable", "zone", "person", "sun",
}
ZIGBEE_TECH = {"zigbee2mqtt", "zha", "deconz", "zwave"}
# switch comes late: many integrations expose settings as switches next to the real device
CONTROL_PRIORITY = [
    "light", "cover", "climate", "media_player", "fan", "lock", "valve", "vacuum",
    "lawn_mower", "humidifier", "water_heater", "switch",
]
SENSOR_DOMAINS = {"binary_sensor", "sensor", "event"}

T = {
    "it": {
        "title": "Come viaggiano i messaggi in casa",
        "note": "Mappa generata da Home Flow Explorer. Topic e payload sono esempi.",
        "router": "Router", "router_sub": "rete di casa", "ha": "Home Assistant",
        "host": "Server", "mqtt": "MQTT", "mqtt_sub": "broker", "z2m": "Z2M", "z2m_sub": "Zigbee2MQTT",
        "coord": "Coordinatore", "coord_sub": "Zigbee", "zw_coord": "Controller", "zw_sub": "Z-Wave",
        "matter": "Matter", "matter_sub": "server",
        "phones": "Telefoni", "phones_sub": "{n} app", "away": "Telefono", "away_sub": "fuori casa",
        "nabu": "Nabu Casa", "nabu_sub": "accesso remoto", "push": "Notifiche push", "push_apns": "APNs",
        "push_fcm": "FCM", "push_both": "APNs / FCM", "cloud_sub": "cloud",
        "devices": "{n} dispositivi", "device": "1 dispositivo",
        "iot": {
            "local_push": "locale, aggiornamenti immediati", "local_polling": "locale, a intervalli",
            "cloud_push": "cloud, aggiornamenti immediati", "cloud_polling": "cloud, a intervalli",
            "assumed_state": "stato presunto", "calculated": "calcolato",
        },
        "group_info": "{n} dispositivi dell'integrazione {name} ({iot}). Esempi: {examples}.",
        "cloud_info": "Il cloud usato dall'integrazione {name}: i comandi e gli stati passano da qui.",
        "nabu_info": "Tunnel cifrato che Home Assistant apre verso Nabu Casa: lo usano l'app fuori casa e gli assistenti vocali.",
        "push_info": "Il servizio che consegna le notifiche dell'app di Home Assistant ai telefoni.",
        "phones_info": "Telefoni e tablet con l'app di Home Assistant: {names}.",
        "away_info": "Il telefono su rete mobile, con l'app di Home Assistant.",
        "ha_info": "Il centro di tutto: integrazioni, automazioni e interfaccia.",
        "mqtt_info": "Broker MQTT: ci passano Zigbee2MQTT e i dispositivi che parlano MQTT.",
        "z2m_info": "Traduce i messaggi Zigbee in MQTT e viceversa.",
        "coord_info": "La chiavetta o il gateway che parla con la rete Zigbee.",
        "zw_info": "Il controller che parla con la rete Z-Wave.",
        "matter_info": "Il Matter Server che parla con i dispositivi Matter.",
        "router_info": "Il router di casa.",
        "infra_info": "Rilevato dall'integrazione {name}.",
        "nas_info": "NAS rilevato dall'integrazione {name}.",
        # gestures
        "g_light": "Accendo {name} dall'app", "g_switch": "Accendo {name} dall'app",
        "g_cover": "Apro {name} dall'app", "g_climate": "Cambio la temperatura di {name}",
        "g_fan": "Accendo {name} dall'app", "g_media_player": "Accendo {name} dall'app",
        "g_lock": "Apro {name} dall'app", "g_valve": "Apro {name} dall'app",
        "g_vacuum": "Avvio {name} dall'app", "g_default": "Comando {name} dall'app",
        "g_summary_local": "Dall'app a {name}: il comando resta in casa, passando per {path}.",
        "g_summary_cloud": "Dall'app a {name}: il comando passa dal cloud {cloud}.",
        "off_local": "Senza internet funziona lo stesso: resta tutto in casa.",
        "off_cloud": "Senza internet non funziona: passa dal cloud {cloud}.",
        "s_tap": "Tocchi {name} nell'app", "s_tap_t": "L'app parla con Home Assistant sulla rete di casa e chiede il comando.",
        "s_ui": "Comando dall'interfaccia", "s_ui_t": "Dall'interfaccia di Home Assistant parte il comando.",
        "s_cmd": "Il comando arriva al dispositivo",
        "t_zigbee2mqtt": "Home Assistant pubblica il comando su MQTT, Zigbee2MQTT lo traduce in un messaggio Zigbee e il coordinatore lo trasmette.",
        "t_zha": "Home Assistant passa il comando al coordinatore Zigbee, che lo trasmette.",
        "t_deconz": "Home Assistant passa il comando al gateway deCONZ, che lo trasmette in Zigbee.",
        "t_zwave": "Home Assistant passa il comando al controller Z-Wave, che lo trasmette.",
        "t_mqtt": "Home Assistant pubblica il comando sul broker MQTT: il dispositivo è iscritto e lo esegue.",
        "t_matter": "Home Assistant passa il comando al Matter Server, che lo invia al dispositivo in rete locale.",
        "t_cloud": "L'integrazione {name} chiama il cloud del produttore, che inoltra il comando al dispositivo.",
        "t_local": "Home Assistant comanda il dispositivo in rete locale con l'integrazione {name}.",
        "t_local_generic": "Home Assistant comanda il dispositivo in rete locale con la sua integrazione.",
        "others": "Altri", "others_info": "{n} dispositivi locali di integrazioni diverse: {names}.",
        "s_push": "Il dispositivo conferma lo stato",
        "t_push": "Il dispositivo manda subito il nuovo stato: è questa conferma ad aggiornare l'interfaccia.",
        "t_push_cloud": "Il nuovo stato passa dal cloud prima di arrivare a Home Assistant.",
        "s_poll": "Home Assistant rilegge lo stato",
        "t_poll": "L'integrazione funziona a intervalli: Home Assistant chiede lo stato ogni tanto, quindi la conferma può arrivare con qualche secondo di ritardo.",
        "s_app": "L'app si aggiorna", "t_app": "Home Assistant manda il nuovo stato all'app.",
        "k_service": "Servizio", "k_entity": "Entità", "k_topic": "Topic", "k_payload": "Payload",
        "k_integration": "Integrazione", "k_class": "Tipo", "k_note": "Nota", "k_example": "esempio",
        "k_trigger": "Trigger", "k_automation": "Automazione", "k_conditions": "Condizioni", "k_mode": "Modalità",
        "k_cloud": "Cloud",
        # extra gestures
        "n_title": "Arriva una notifica sul telefono",
        "n_summary": "Home Assistant consegna la notifica al servizio push, che la porta al telefono.",
        "n_off": "Senza internet la notifica non arriva: passa dai server push.",
        "n_s1": "Home Assistant manda la notifica", "n_t1": "Il servizio di notifica dell'app consegna il messaggio al servizio push del telefono.",
        "n_s2": "Arriva sul telefono", "n_t2": "Il servizio push la consegna al telefono, in casa o fuori.",
        "v_title": "Chiedo ad Alexa di accendere {name}",
        "v_summary": "La voce va ad Amazon, Amazon passa il comando a Nabu Casa e Home Assistant accende {name}.",
        "v_off": "Senza internet Alexa non capisce nulla: la voce viene riconosciuta nel cloud.",
        "v_s1": "Parli con l'Echo", "v_t1": "L'Echo registra la frase e la manda ad Amazon.",
        "v_s2": "Amazon chiama Nabu Casa", "v_t2": "La skill di Home Assistant riceve il comando per l'entità esposta.",
        "v_s3": "Entra dal tunnel", "v_t3": "Il comando arriva a Home Assistant dal tunnel Nabu Casa, senza porte aperte.",
        "v_note": "solo se l'entità è esposta ad Alexa",
        "e_title": "Un sensore {tech} cambia stato",
        "e_summary": "{name} manda il nuovo stato a Home Assistant.",
        "e_s1": "{name} rileva qualcosa", "e_t1": "Il sensore si sveglia e manda il nuovo stato sulla sua rete.",
        "e_s2": "Arriva a Home Assistant", "e_t2": "Home Assistant aggiorna l'entità, che da qui può far partire automazioni.",
        # automations
        "a_summary": "Quando {trigger}, Home Assistant {action}.",
        "a_trigger_dev": "si attiva {name}", "a_trigger_time": "è l'orario impostato", "a_trigger_sun": "alba o tramonto",
        "a_trigger_other": "scatta il trigger", "a_action_dev": "comanda {name}", "a_action_other": "esegue le azioni",
        "a_s_trig": "{name} si attiva", "a_t_trig": "Il cambio di stato arriva a Home Assistant e fa partire l'automazione.",
        "a_s_time": "Arriva l'orario", "a_s_sun": "Alba o tramonto", "a_s_other": "Scatta il trigger",
        "a_s_start": "Home Assistant si avvia", "a_s_stop": "Home Assistant si sta spegnendo",
        "a_trigger_start": "il sistema si avvia", "a_trigger_stop": "il sistema si spegne", "a_action_notify": "manda una notifica",
        "a_s_trig_more": "{name} e altri {n}", "a_trigger_dev_more": "si attiva {name} (o uno degli altri {n})",
        "a_t_internal": "Il trigger nasce dentro Home Assistant.",
        "a_s_eval": "Home Assistant valuta l'automazione", "a_t_eval": "Controlla le condizioni e decide cosa fare.",
        "a_s_act": "Comanda {name}", "a_t_act_local": "Il comando arriva al dispositivo in casa.",
        "a_t_act_cloud": "Il comando passa dal cloud {cloud}.",
        "a_s_notify": "Manda una notifica", "a_s_helper": "Aggiorna {name}", "a_t_helper": "Cambia un'entità interna di Home Assistant.",
        "a_off_local": "Funziona anche senza internet.",
        "a_off_cloud": "Senza internet non si completa: passa da {cloud}.",
        "time_at": "alle {at}", "sunrise": "all'alba", "sunset": "al tramonto",
    },
    "en": {
        "title": "How messages travel in our home",
        "note": "Map generated by Home Flow Explorer. Topics and payloads are examples.",
        "router": "Router", "router_sub": "home network", "ha": "Home Assistant",
        "host": "Server", "mqtt": "MQTT", "mqtt_sub": "broker", "z2m": "Z2M", "z2m_sub": "Zigbee2MQTT",
        "coord": "Coordinator", "coord_sub": "Zigbee", "zw_coord": "Controller", "zw_sub": "Z-Wave",
        "matter": "Matter", "matter_sub": "server",
        "phones": "Phones", "phones_sub": "{n} apps", "away": "Phone", "away_sub": "away",
        "nabu": "Nabu Casa", "nabu_sub": "remote access", "push": "Push service", "push_apns": "APNs",
        "push_fcm": "FCM", "push_both": "APNs / FCM", "cloud_sub": "cloud",
        "devices": "{n} devices", "device": "1 device",
        "iot": {
            "local_push": "local, instant updates", "local_polling": "local, polled",
            "cloud_push": "cloud, instant updates", "cloud_polling": "cloud, polled",
            "assumed_state": "assumed state", "calculated": "calculated",
        },
        "group_info": "{n} devices from the {name} integration ({iot}). For example: {examples}.",
        "cloud_info": "The cloud used by the {name} integration: commands and states go through it.",
        "nabu_info": "Encrypted tunnel opened by Home Assistant to Nabu Casa, used by the app away from home and by voice assistants.",
        "push_info": "The service that delivers Home Assistant app notifications to phones.",
        "phones_info": "Phones and tablets with the Home Assistant app: {names}.",
        "away_info": "Your phone on mobile data, with the Home Assistant app.",
        "ha_info": "The hub: integrations, automations and the interface.",
        "mqtt_info": "MQTT broker for Zigbee2MQTT and devices that speak MQTT.",
        "z2m_info": "Translates Zigbee messages into MQTT and back.",
        "coord_info": "The stick or gateway that talks to the Zigbee network.",
        "zw_info": "The controller that talks to the Z-Wave network.",
        "matter_info": "The Matter Server that talks to Matter devices.",
        "router_info": "Your home router.",
        "infra_info": "Found by the {name} integration.",
        "nas_info": "NAS found by the {name} integration.",
        "g_light": "I turn on {name} from the app", "g_switch": "I turn on {name} from the app",
        "g_cover": "I open {name} from the app", "g_climate": "I change the temperature of {name}",
        "g_fan": "I turn on {name} from the app", "g_media_player": "I turn on {name} from the app",
        "g_lock": "I unlock {name} from the app", "g_valve": "I open {name} from the app",
        "g_vacuum": "I start {name} from the app", "g_default": "I control {name} from the app",
        "g_summary_local": "From the app to {name}: the command stays home, through {path}.",
        "g_summary_cloud": "From the app to {name}: the command goes through the {cloud} cloud.",
        "off_local": "Works without internet: everything stays home.",
        "off_cloud": "Does not work without internet: it goes through the {cloud} cloud.",
        "s_tap": "You tap {name} in the app", "s_tap_t": "The app talks to Home Assistant on the home network and asks for the command.",
        "s_ui": "Command from the interface", "s_ui_t": "The command starts from the Home Assistant interface.",
        "s_cmd": "The command reaches the device",
        "t_zigbee2mqtt": "Home Assistant publishes the command on MQTT, Zigbee2MQTT turns it into a Zigbee message and the coordinator sends it.",
        "t_zha": "Home Assistant hands the command to the Zigbee coordinator, which sends it.",
        "t_deconz": "Home Assistant hands the command to the deCONZ gateway, which sends it over Zigbee.",
        "t_zwave": "Home Assistant hands the command to the Z-Wave controller, which sends it.",
        "t_mqtt": "Home Assistant publishes the command on the MQTT broker: the device is subscribed and runs it.",
        "t_matter": "Home Assistant hands the command to the Matter Server, which sends it to the device on the local network.",
        "t_cloud": "The {name} integration calls the vendor cloud, which forwards the command to the device.",
        "t_local": "Home Assistant controls the device on the local network with the {name} integration.",
        "t_local_generic": "Home Assistant controls the device on the local network with its integration.",
        "others": "Others", "others_info": "{n} local devices from different integrations: {names}.",
        "s_push": "The device confirms its state",
        "t_push": "The device sends its new state right away: this confirmation is what updates the interface.",
        "t_push_cloud": "The new state goes through the cloud before reaching Home Assistant.",
        "s_poll": "Home Assistant reads the state again",
        "t_poll": "The integration polls: Home Assistant asks for the state every so often, so the confirmation can take a few seconds.",
        "s_app": "The app updates", "t_app": "Home Assistant sends the new state to the app.",
        "k_service": "Action", "k_entity": "Entity", "k_topic": "Topic", "k_payload": "Payload",
        "k_integration": "Integration", "k_class": "Type", "k_note": "Note", "k_example": "example",
        "k_trigger": "Trigger", "k_automation": "Automation", "k_conditions": "Conditions", "k_mode": "Mode",
        "k_cloud": "Cloud",
        "n_title": "A notification reaches my phone",
        "n_summary": "Home Assistant hands the notification to the push service, which delivers it to the phone.",
        "n_off": "Without internet the notification does not arrive: it goes through the push servers.",
        "n_s1": "Home Assistant sends the notification", "n_t1": "The app notification action hands the message to the phone's push service.",
        "n_s2": "It reaches the phone", "n_t2": "The push service delivers it, at home or away.",
        "v_title": "I ask Alexa to turn on {name}",
        "v_summary": "Your voice goes to Amazon, Amazon hands the command to Nabu Casa and Home Assistant turns on {name}.",
        "v_off": "Without internet Alexa understands nothing: speech recognition happens in the cloud.",
        "v_s1": "You talk to the Echo", "v_t1": "The Echo records the phrase and sends it to Amazon.",
        "v_s2": "Amazon calls Nabu Casa", "v_t2": "The Home Assistant skill receives the command for the exposed entity.",
        "v_s3": "Through the tunnel", "v_t3": "The command reaches Home Assistant through the Nabu Casa tunnel, with no open ports.",
        "v_note": "only if the entity is exposed to Alexa",
        "e_title": "A {tech} sensor changes state",
        "e_summary": "{name} sends its new state to Home Assistant.",
        "e_s1": "{name} detects something", "e_t1": "The sensor wakes up and sends its new state over its network.",
        "e_s2": "It reaches Home Assistant", "e_t2": "Home Assistant updates the entity, which can start automations from here.",
        "a_summary": "When {trigger}, Home Assistant {action}.",
        "a_trigger_dev": "{name} changes", "a_trigger_time": "the set time comes", "a_trigger_sun": "the sun rises or sets",
        "a_trigger_other": "the trigger fires", "a_action_dev": "controls {name}", "a_action_other": "runs the actions",
        "a_s_trig": "{name} changes", "a_t_trig": "The state change reaches Home Assistant and starts the automation.",
        "a_s_time": "The time comes", "a_s_sun": "Sunrise or sunset", "a_s_other": "The trigger fires",
        "a_s_start": "Home Assistant starts", "a_s_stop": "Home Assistant is shutting down",
        "a_trigger_start": "the system starts", "a_trigger_stop": "the system shuts down", "a_action_notify": "sends a notification",
        "a_s_trig_more": "{name} and {n} more", "a_trigger_dev_more": "{name} (or one of {n} others) fires",
        "a_t_internal": "The trigger starts inside Home Assistant.",
        "a_s_eval": "Home Assistant runs the automation", "a_t_eval": "It checks the conditions and decides what to do.",
        "a_s_act": "Controls {name}", "a_t_act_local": "The command reaches the device at home.",
        "a_t_act_cloud": "The command goes through the {cloud} cloud.",
        "a_s_notify": "Sends a notification", "a_s_helper": "Updates {name}", "a_t_helper": "Changes an internal Home Assistant entity.",
        "a_off_local": "Works without internet.",
        "a_off_cloud": "Does not complete without internet: it goes through {cloud}.",
        "time_at": "at {at}", "sunrise": "at sunrise", "sunset": "at sunset",
    },
}

# short names for the map; anything else uses the integration name
SHORT_NAMES = {
    "alexa_media": "Echo", "homekit_controller": "HomeKit", "meross_lan": "Meross", "braviatv": "Bravia",
    "tuya_local": "Tuya", "cast": "Cast", "apple_tv": "Apple TV", "google_assistant": "Google",
    "zcsazzurro": "ZCS Azzurro", "esphome": "ESPHome", "tasmota": "Tasmota", "hue": "Hue",
    "sonos": "Sonos", "philips_js": "Philips TV", "samsungtv": "Samsung TV", "webostv": "LG TV",
    "tplink": "TP-Link", "tuya": "Tuya", "xiaomi_miio": "Xiaomi", "smartthings": "SmartThings",
    "nest": "Nest", "ring": "Ring", "netatmo": "Netatmo", "reolink": "Reolink", "unifiprotect": "Protect",
}
TECH_NAMES = {"zigbee2mqtt": "Zigbee", "zha": "Zigbee", "deconz": "Zigbee", "zwave": "Z-Wave", "mqtt": "MQTT"}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s or "x"


def _short(text: str, n: int = 16) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _is_template(v: Any) -> bool:
    return isinstance(v, str) and ("{{" in v or "{%" in v)


def _as_list(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, (list, tuple, set)):
        return [x for x in v if x is not None]
    return [v]


class Graph:
    """Nodes, edges and shortest paths."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: list[list[str]] = []
        self.adj: dict[str, set[str]] = {}

    def node(self, nid: str, **kw: Any) -> str:
        if nid not in self.nodes:
            self.nodes[nid] = {"id": nid, **kw}
            self.adj.setdefault(nid, set())
        return nid

    def edge(self, a: str, b: str, medium: str) -> None:
        if a == b or b in self.adj.get(a, set()):
            return
        self.edges.append([a, b, medium])
        self.adj.setdefault(a, set()).add(b)
        self.adj.setdefault(b, set()).add(a)

    def path(self, a: str, b: str, avoid: set[str] | None = None) -> list[str]:
        if a == b:
            return [a]
        avoid = avoid or set()
        prev = {a: None}
        q = deque([a])
        while q:
            cur = q.popleft()
            for nxt in sorted(self.adj.get(cur, ())):
                if nxt in prev or (nxt in avoid and nxt != b):
                    continue
                prev[nxt] = cur
                if nxt == b:
                    out = [b]
                    while prev[out[-1]] is not None:
                        out.append(prev[out[-1]])
                    return out[::-1]
                q.append(nxt)
        return [a, b] if b in self.adj.get(a, set()) else [a]

    def via(self, *points: str) -> list[str]:
        out: list[str] = []
        for a, b in zip(points, points[1:]):
            seg = self.path(a, b)
            out.extend(seg if not out else seg[1:])
        return out or list(points[:1])


def build(snap: dict, opts: dict) -> dict:
    """Return the card configuration for a snapshot and the user's options."""
    lang = opts.get("language") or snap.get("language") or "en"
    lang = "it" if str(lang).startswith("it") else "en"
    t = T[lang]
    g = Graph()
    integrations: dict[str, dict] = snap.get("integrations", {})
    excluded = set(opts.get(CONF_EXCLUDED) or [])
    devices = {d["id"]: {**d, "name": (d.get("name") or "").strip()} for d in snap.get("devices", [])}
    entities = snap.get("entities", [])
    ent_by_id = {e["entity_id"]: e for e in entities}
    ents_by_dev: dict[str, list[dict]] = {}
    for e in entities:
        if e.get("device_id") and not e.get("disabled"):
            ents_by_dev.setdefault(e["device_id"], []).append(e)
    entry_domains = {e["domain"] for e in snap.get("entries", []) if not e.get("disabled")}
    addons = {d["identifiers"][0][1] for d in devices.values()
              if d.get("identifiers") and d["identifiers"][0][0] == "hassio"}

    def iname(domain: str) -> str:
        return integrations.get(domain, {}).get("name") or domain.replace("_", " ").title()

    def iot(domain: str) -> str:
        return integrations.get(domain, {}).get("iot_class") or "local_push"

    # ---------------- infrastructure ----------------
    objects: list[dict] = list(opts.get(CONF_OBJECTS) or [])
    if not any(o.get("kind") == "router" for o in objects):
        objects.insert(0, {"id": "router", "name": t["router"], "kind": "router"})
    boxes: list[dict] = [{"id": "ha_host", "label": opts.get(CONF_HOST_LABEL) or snap.get("host_label") or t["host"]}]
    # router first among net nodes: the card lays the first net node out as the router
    objects.sort(key=lambda o: 0 if o.get("kind") == "router" else 1)
    router_id = next(o["id"] for o in objects if o.get("kind") == "router")
    for o in objects:
        zone = OBJECT_KINDS.get(o.get("kind", "other"), "device")
        extra = {}
        if zone == "server":
            boxes.append({"id": f"box_{o['id']}", "label": o.get("name")})
            extra["box"] = f"box_{o['id']}"
        g.node(o["id"], name=_short(o.get("name") or o["id"], 18), sub=_short(o.get("address") or "", 16),
               zone=zone, info=o.get("info") or "", **extra)
    g.node("ha", name=t["ha"], sub=_short(snap.get("ha_address") or "", 16), zone="server", box="ha_host", info=t["ha_info"])
    ha_link = opts.get(CONF_HA_LINK) or router_id
    if ha_link not in g.nodes:
        ha_link = router_id
    g.edge("ha", ha_link, "cable")
    for o in objects:
        target = o.get("connected_to") or (None if o["id"] == router_id else router_id)
        if target == "home_assistant":
            target = "ha"
        if target and target in g.nodes and target != o["id"]:
            zone = g.nodes[o["id"]]["zone"]
            medium = o.get("medium") or ("internet" if zone == "cloud" else "cable")
            g.edge(o["id"], target, medium)

    # auto-detected network gear and NAS
    infra_ids: dict[str, str] = {}
    for d in devices.values():
        dom = d.get("domain")
        if not dom or dom in excluded or d.get("disabled") or d.get("via"):
            continue
        if d.get("entry_type") == "service":
            continue
        if dom in NETWORK_DOMAINS or dom in NAS_DOMAINS:
            nid = "infra_" + d["id"][:8]
            is_nas = dom in NAS_DOMAINS
            extra = {}
            if is_nas:
                boxes.append({"id": f"box_{nid}", "label": _short(d["name"], 20)})
                extra["box"] = f"box_{nid}"
            g.node(nid, name=_short(d["name"], 16), sub=_short(d.get("model") or iname(dom), 16),
                   zone="server" if is_nas else "net",
                   info=(t["nas_info"] if is_nas else t["infra_info"]).format(name=iname(dom)), **extra)
            g.edge(nid, router_id, "cable")
            infra_ids[d["id"]] = nid

    wifi = opts.get(CONF_WIFI) or ""
    if wifi.startswith("auto:"):
        wifi = infra_ids.get(wifi[5:], "")
    if wifi not in g.nodes:
        aps = [nid for nid in infra_ids.values() if g.nodes[nid]["zone"] == "net"]
        user_aps = [o["id"] for o in objects if o.get("kind") == "access_point"]
        wifi = (user_aps or aps or [router_id])[0]

    # ---------------- device groups ----------------
    def tech_of(d: dict) -> str:
        dom = d.get("domain")
        ids = [i[1] for i in d.get("identifiers") or [] if len(i) > 1 and isinstance(i[1], str)]
        via = devices.get(d.get("via") or "")
        if any(i.startswith("zigbee2mqtt_") for i in ids) or (via and (via.get("manufacturer") == "Zigbee2MQTT")):
            return "zigbee2mqtt"
        if dom == "zwave_js":
            return "zwave"
        return dom or ""

    groups: dict[str, dict] = {}
    phones: list[dict] = []
    for d in devices.values():
        dom = d.get("domain")
        if not dom or d.get("disabled") or d.get("entry_type") == "service":
            continue
        if dom == "mobile_app":
            phones.append(d)
            continue
        if dom in excluded or dom in IGNORE_DOMAINS or dom in NETWORK_DOMAINS or dom in NAS_DOMAINS:
            continue
        ids = [i[1] for i in d.get("identifiers") or [] if len(i) > 1 and isinstance(i[1], str)]
        if any(i.startswith("zigbee2mqtt_bridge") for i in ids):
            continue
        tech = tech_of(d)
        info = integrations.get(dom, {})
        if tech not in ZIGBEE_TECH and dom != "mqtt" and (
                info.get("type") in IGNORE_TYPES or info.get("iot_class") == "calculated"):
            continue
        grp = groups.setdefault(tech, {"tech": tech, "domain": dom, "devices": [], "domains": Counter()})
        grp["devices"].append(d)
        for e in ents_by_dev.get(d["id"], []):
            grp["domains"][e["entity_id"].split(".")[0]] += 1

    # entities without a device created by MQTT (e.g. relays configured in YAML)
    mqtt_loose = [e for e in entities if e.get("platform") == "mqtt" and not e.get("device_id")
                  and not e.get("disabled") and e["entity_id"].split(".")[0] in CONTROL_PRIORITY]
    if mqtt_loose and "mqtt" not in excluded:
        grp = groups.setdefault("mqtt", {"tech": "mqtt", "domain": "mqtt", "devices": [], "domains": Counter()})
        grp["loose"] = mqtt_loose
        for e in mqtt_loose:
            grp["domains"][e["entity_id"].split(".")[0]] += 1

    # single local devices from many small integrations: one "other devices" node instead of ten
    alias: dict[str, str] = {}
    small = [k for k, gp in groups.items() if k not in ZIGBEE_TECH and k != "mqtt" and len(gp["devices"]) <= 1
             and not iot(gp["domain"]).startswith("cloud") and not gp.get("loose")]
    if len(small) >= 3:
        other = {"tech": "altri", "domain": "altri", "devices": [], "domains": Counter(), "members": []}
        for k in small:
            gp = groups.pop(k)
            other["devices"] += gp["devices"]
            other["domains"].update(gp["domains"])
            other["members"].append(iname(gp["domain"]))
            alias[k] = "altri"
        groups["altri"] = other

    def group_of(d: dict | None) -> dict | None:
        if not d:
            return None
        gp = groups.get(alias.get(tech_of(d), tech_of(d)))
        return gp if gp and d in gp["devices"] else None

    # ---------------- hubs inside the HA box ----------------
    has_mqtt = "mqtt" in entry_domains or any(gp["tech"] in ("zigbee2mqtt", "mqtt") for gp in groups.values())
    if has_mqtt:
        g.node("mqtt", name=t["mqtt"], sub=t["mqtt_sub"], zone="server", box="ha_host", info=t["mqtt_info"])
        g.edge("ha", "mqtt", "internal")
    zig_hub: dict[str, str] = {}
    if "zigbee2mqtt" in groups:
        g.node("z2m", name=t["z2m"], sub=t["z2m_sub"], zone="server", box="ha_host", info=t["z2m_info"])
        g.edge("mqtt", "z2m", "internal")
        g.node("coord", name=t["coord"], sub=t["coord_sub"], zone="server", box="ha_host", info=t["coord_info"])
        g.edge("z2m", "coord", "internal")
        zig_hub["zigbee2mqtt"] = "coord"
    for tech, label in (("zha", "coord"), ("deconz", "coord")):
        if tech in groups:
            nid = "coord_" + tech
            g.node(nid, name=t["coord"], sub=t["coord_sub"], zone="server", box="ha_host", info=t["coord_info"])
            g.edge("ha", nid, "internal")
            zig_hub[tech] = nid
    if "zwave" in groups:
        g.node("zw", name=t["zw_coord"], sub=t["zw_sub"], zone="server", box="ha_host", info=t["zw_info"])
        g.edge("ha", "zw", "internal")
        zig_hub["zwave"] = "zw"
    if "matter" in groups:
        g.node("matter_srv", name=t["matter"], sub=t["matter_sub"], zone="server", box="ha_host", info=t["matter_info"])
        g.edge("ha", "matter_srv", "internal")

    # ---------------- cloud nodes ----------------
    has_nabu = "cloud" in entry_domains
    if has_nabu:
        g.node("nabu", name=t["nabu"], sub=t["nabu_sub"], zone="cloud", info=t["nabu_info"])
        g.edge("nabu", router_id, "internet")
    if phones:
        mans = {(p.get("manufacturer") or "").lower() for p in phones}
        apple = any("apple" in m for m in mans)
        other = any(m and "apple" not in m for m in mans)
        sub = t["push_both"] if apple and other else (t["push_apns"] if apple else t["push_fcm"])
        g.node("push", name=t["push"], sub=sub, zone="cloud", info=t["push_info"])
        g.edge("push", router_id, "internet")
        if has_nabu:
            g.node("away", name=t["away"], sub=t["away_sub"], zone="cloud", info=t["away_info"])
            g.edge("away", "nabu", "internet")
            g.edge("push", "away", "internet")

    # ---------------- group nodes ----------------
    def cloud_of(grp: dict) -> str | None:
        return f"cloud_{grp['domain']}" if iot(grp["domain"]).startswith("cloud") else None

    ordered = sorted(groups.values(), key=lambda gp: (gp["tech"] not in ZIGBEE_TECH, -len(gp["devices"]) - len(gp.get("loose", []))))
    for grp in ordered:
        tech, dom = grp["tech"], grp["domain"]
        nid = "grp_" + _slug(tech)
        grp["node"] = nid
        n = len(grp["devices"]) + len(grp.get("loose", []))
        names = [d.get("name") for d in grp["devices"][:4] if d.get("name")]
        if not names:
            names = [e.get("name") or e["entity_id"] for e in grp.get("loose", [])[:4]]
        display = t["others"] if tech == "altri" else (TECH_NAMES.get(tech) or SHORT_NAMES.get(dom) or iname(dom))
        info_txt = (t["others_info"].format(n=n, names=", ".join(grp["members"])) if tech == "altri" else
                    t["group_info"].format(n=n, name=iname(dom) if tech not in TECH_NAMES else TECH_NAMES[tech],
                                           iot=t["iot"].get(iot(dom), iot(dom)), examples=", ".join(names)))
        g.node(nid, name=_short(display, 12), sub=f"×{n}", zone="device",
               info=info_txt)
        if tech in zig_hub:
            g.edge(zig_hub[tech], nid, "zigbee")
        else:
            g.edge(wifi, nid, "wifi")
        cloud = cloud_of(grp)
        if cloud and tech not in ZIGBEE_TECH:
            g.node(cloud, name=_short(SHORT_NAMES.get(dom) or iname(dom), 12), sub=t["cloud_sub"], zone="cloud",
                   info=t["cloud_info"].format(name=iname(dom)))
            g.edge(cloud, router_id, "internet")
            grp["cloud"] = cloud
        grp["display"] = display
    # Amazon <-> Nabu Casa for voice requests
    if has_nabu and "alexa_media" in groups and groups["alexa_media"].get("cloud"):
        g.edge(groups["alexa_media"]["cloud"], "nabu", "internet")

    if phones:
        pn = [p.get("name") for p in phones]
        g.node("phones", name=t["phones"], sub=f"×{len(phones)}", zone="device",
               info=t["phones_info"].format(names=", ".join(n for n in pn if n)))
        g.edge(wifi, "phones", "wifi")

    # ---------------- helpers for scenarios ----------------
    def ent_device(eid: str) -> dict | None:
        e = ent_by_id.get(eid)
        return devices.get(e["device_id"]) if e and e.get("device_id") else None

    def ent_group(eid: str) -> dict | None:
        e = ent_by_id.get(eid)
        if not e:
            return None
        if e.get("device_id"):
            return group_of(devices.get(e["device_id"]))
        if e.get("platform") == "mqtt" and "mqtt" in groups:
            return groups["mqtt"]
        return None

    def ent_label(eid: str) -> str:
        d = ent_device(eid)
        if d and d.get("name"):
            return d["name"]
        e = ent_by_id.get(eid)
        return (e or {}).get("name") or eid.split(".", 1)[-1].replace("_", " ")

    def to_device(grp: dict) -> list[str]:
        tech = grp["tech"]
        if tech == "zigbee2mqtt":
            return g.via("ha", "mqtt", "z2m", "coord", grp["node"])
        if tech in zig_hub:
            return g.via("ha", zig_hub[tech], grp["node"])
        if tech == "mqtt":
            return g.via("ha", "mqtt", "ha", grp["node"]) if "mqtt" in g.nodes else g.via("ha", grp["node"])
        if tech == "matter" and "matter_srv" in g.nodes:
            return g.via("ha", "matter_srv", "ha", grp["node"])
        if grp.get("cloud"):
            return g.via("ha", grp["cloud"], grp["node"])
        return g.via("ha", grp["node"])

    def from_device(grp: dict) -> list[str]:
        tech = grp["tech"]
        if tech == "zigbee2mqtt":
            return g.via(grp["node"], "coord", "z2m", "mqtt", "ha")
        if tech in zig_hub:
            return g.via(grp["node"], zig_hub[tech], "ha")
        if tech == "mqtt" and "mqtt" in g.nodes:
            return g.via(grp["node"], "ha", "mqtt", "ha")
        if tech == "matter" and "matter_srv" in g.nodes:
            return g.via(grp["node"], "ha", "matter_srv", "ha")
        if grp.get("cloud"):
            return g.via(grp["node"], grp["cloud"], "ha")
        return g.via(grp["node"], "ha")

    def cmd_text(grp: dict) -> str:
        tech = grp["tech"]
        if grp.get("cloud"):
            return t["t_cloud"].format(name=iname(grp["domain"]))
        if tech == "altri":
            return t["t_local_generic"]
        key = "t_" + tech
        return t[key] if key in t else t["t_local"].format(name=iname(grp["domain"]))

    def is_push(grp: dict) -> bool:
        return grp["tech"] in ZIGBEE_TECH or iot(grp["domain"]).endswith("push") or grp["tech"] == "mqtt"

    def cloud_name(grp: dict) -> str:
        return iname(grp["domain"])

    def payload_rows(grp: dict, domain: str, dev_name: str) -> list[list[str]]:
        if grp["tech"] == "zigbee2mqtt":
            pl = '{"state": "ON"}' if domain in ("light", "switch", "fan") else '{"...": "..."}'
            return [[t["k_topic"], f"zigbee2mqtt/{dev_name}/set"], [t["k_payload"], pl], [t["k_note"], t["k_example"]]]
        if grp["tech"] == "altri":
            return []
        return [[t["k_integration"], iname(grp["domain"])], [t["k_class"], t["iot"].get(iot(grp["domain"]), "")]]

    def example_entity(grp: dict, domain: str) -> tuple[str, str] | None:
        for d in grp["devices"]:
            for e in ents_by_dev.get(d["id"], []):
                if e["entity_id"].startswith(domain + ".") and not e.get("entity_category"):
                    return e["entity_id"], d.get("name") or e["entity_id"]
        for e in grp.get("loose", []):
            if e["entity_id"].startswith(domain + "."):
                return e["entity_id"], e.get("name") or e["entity_id"].split(".", 1)[1].replace("_", " ")
        return None

    def service_for(domain: str) -> str:
        return {"cover": "cover.open_cover", "climate": "climate.set_temperature", "lock": "lock.unlock",
                "valve": "valve.open_valve", "vacuum": "vacuum.start", "lawn_mower": "lawn_mower.start_mowing"
                }.get(domain, f"{domain}.turn_on")

    scenarios: list[dict] = []

    # ---------------- gestures ----------------
    max_g = int(opts.get(CONF_MAX_GESTURES, DEFAULT_MAX_GESTURES))
    cands = []
    for grp in groups.values():
        for prio, domain in enumerate(CONTROL_PRIORITY):
            if grp["domains"].get(domain):
                cands.append((grp, domain, prio))
                break
    # spread: zigbee first, then local Wi-Fi, then cloud, then the rest by size
    def g_rank(c: tuple) -> tuple:
        grp, domain, prio = c
        kind = 0 if grp["tech"] in ZIGBEE_TECH else (2 if grp.get("cloud") else 1)
        return (kind, prio, -len(grp["devices"]))
    cands.sort(key=g_rank)
    seen_kinds: list = []
    picked = []
    for c in cands:
        k = 0 if c[0]["tech"] in ZIGBEE_TECH else (2 if c[0].get("cloud") else 1)
        if k not in seen_kinds:
            picked.append(c)
            seen_kinds.append(k)
    for c in cands:
        if c not in picked:
            picked.append(c)
    gesture_count = 0
    first_light: tuple | None = None
    for grp, domain, _ in picked:
        if gesture_count >= max_g:
            break
        ex = example_entity(grp, domain)
        if not ex:
            continue
        eid, dname = ex
        if first_light is None and domain in ("light", "switch") and not grp.get("cloud"):
            first_light = (grp, domain, eid, dname)
        steps = []
        if phones:
            steps.append({"title": t["s_tap"].format(name=dname), "path": g.via("phones", "ha"), "text": t["s_tap_t"],
                          "data": [[t["k_service"], service_for(domain)], [t["k_entity"], eid]]})
        else:
            steps.append({"title": t["s_ui"], "path": ["ha"], "text": t["s_ui_t"],
                          "data": [[t["k_service"], service_for(domain)], [t["k_entity"], eid]]})
        steps.append({"title": t["s_cmd"], "path": to_device(grp), "out": bool(grp.get("cloud")),
                      "text": cmd_text(grp), "data": payload_rows(grp, domain, dname)})
        if is_push(grp):
            steps.append({"title": t["s_push"], "path": from_device(grp), "out": bool(grp.get("cloud")),
                          "text": t["t_push_cloud"] if grp.get("cloud") else t["t_push"]})
        else:
            steps.append({"title": t["s_poll"], "path": from_device(grp), "out": bool(grp.get("cloud")),
                          "text": t["t_poll"]})
        if phones:
            steps.append({"title": t["s_app"], "path": g.via("ha", "phones"), "text": t["t_app"]})
        hops = [g.nodes[x]["name"] for x in to_device(grp)[1:-1]]
        summary = (t["g_summary_cloud"].format(name=dname, cloud=cloud_name(grp)) if grp.get("cloud")
                   else t["g_summary_local"].format(name=dname, path=", ".join(hops) or t["ha"]))
        scenarios.append({"id": f"g_{_slug(grp['tech'])}_{domain}", "group": "gesti",
                          "title": t.get("g_" + domain, t["g_default"]).format(name=dname),
                          "summary": summary,
                          "offline": t["off_cloud"].format(cloud=cloud_name(grp)) if grp.get("cloud") else t["off_local"],
                          "steps": steps})
        gesture_count += 1

    # voice
    if has_nabu and "alexa_media" in groups and groups["alexa_media"].get("cloud") and first_light and gesture_count < max_g + 1:
        grp, domain, eid, dname = first_light
        amz = groups["alexa_media"]
        steps = [
            {"title": t["v_s1"], "path": g.via(amz["node"], amz["cloud"]), "out": True, "text": t["v_t1"]},
            {"title": t["v_s2"], "path": g.via(amz["cloud"], "nabu"), "out": True, "text": t["v_t2"],
             "data": [[t["k_entity"], eid], [t["k_note"], t["v_note"]]]},
            {"title": t["v_s3"], "path": g.via("nabu", "ha"), "out": True, "text": t["v_t3"]},
            {"title": t["s_cmd"], "path": to_device(grp), "text": cmd_text(grp), "data": payload_rows(grp, domain, dname)},
        ]
        scenarios.append({"id": "g_voice", "group": "gesti", "title": t["v_title"].format(name=dname),
                          "summary": t["v_summary"].format(name=dname), "offline": t["v_off"], "steps": steps})

    # notification
    if phones and gesture_count < max_g + 2:
        main = next((p for p in phones if "phone" in ((p.get("model") or "") + (p.get("name") or "")).lower()
                     and "watch" not in (p.get("model") or "").lower()), phones[0])
        notify = "notify.mobile_app_" + _slug(main.get("name") or "phone")
        steps = [
            {"title": t["n_s1"], "path": g.via("ha", "push"), "out": True, "text": t["n_t1"],
             "data": [[t["k_service"], notify]]},
            {"title": t["n_s2"], "path": g.via("push", "phones"), "out": True, "text": t["n_t2"]},
        ]
        scenarios.append({"id": "g_notify", "group": "gesti", "title": t["n_title"], "summary": t["n_summary"],
                          "offline": t["n_off"], "steps": steps})

    # a sensor event on the zigbee mesh
    for tech in ("zigbee2mqtt", "zha", "deconz", "zwave"):
        grp = groups.get(tech)
        if not grp:
            continue
        ex = example_entity(grp, "binary_sensor") or example_entity(grp, "sensor")
        if not ex:
            continue
        eid, dname = ex
        rows = [[t["k_entity"], eid]]
        if tech == "zigbee2mqtt":
            rows += [[t["k_topic"], f"zigbee2mqtt/{dname}"], [t["k_note"], t["k_example"]]]
        scenarios.append({"id": "g_sensor", "group": "gesti",
                          "title": t["e_title"].format(tech=TECH_NAMES.get(tech, tech)),
                          "summary": t["e_summary"].format(name=dname), "offline": t["off_local"],
                          "steps": [
                              {"title": t["e_s1"].format(name=dname), "path": g.via(grp["node"], zig_hub[tech]), "text": t["e_t1"]},
                              {"title": t["e_s2"], "path": g.via(zig_hub[tech], *(["z2m", "mqtt"] if tech == "zigbee2mqtt" else []), "ha"),
                               "text": t["e_t2"], "data": rows}]})
        break

    # ---------------- automations ----------------
    max_a = int(opts.get(CONF_MAX_AUTOMATIONS, DEFAULT_MAX_AUTOMATIONS))
    chosen = set(opts.get(CONF_AUTOMATIONS) or [])
    autos = []
    for a in snap.get("automations", []):
        if chosen and a["entity_id"] not in chosen:
            continue
        if not chosen and not a.get("enabled", True):
            continue
        res = _analyze(a.get("config") or {})
        trig_groups = []
        for eid in res["trigger_entities"]:
            gp = ent_group(eid)
            if gp and gp not in [x[0] for x in trig_groups]:
                trig_groups.append((gp, eid))
        for did in res["trigger_devices"]:
            d = devices.get(did)
            if d:
                gp = group_of(d)
                if gp and gp not in [x[0] for x in trig_groups]:
                    trig_groups.append((gp, next((e["entity_id"] for e in ents_by_dev.get(did, [])), did)))
        act_groups = []
        helpers = []
        notifies = []
        for svc, eids, dids in res["actions"]:
            if svc.startswith("notify.mobile_app") or svc == "notify.notify":
                notifies.append(svc)
            for eid in eids:
                gp = ent_group(eid)
                if gp:
                    if gp not in [x[0] for x in act_groups]:
                        act_groups.append((gp, eid, svc))
                elif eid.split(".")[0] in HELPER_DOMAINS and len(helpers) < 2:
                    helpers.append((eid, svc))
            for did in dids:
                gp = group_of(devices.get(did))
                if gp and gp not in [x[0] for x in act_groups]:
                    act_groups.append((gp, next((e["entity_id"] for e in ents_by_dev.get(did, [])), did), svc))
        score = (2 if trig_groups else 0) + (3 if act_groups else 0) + (1 if notifies else 0)
        if chosen or trig_groups or act_groups or notifies:
            autos.append((score, a, res, trig_groups, act_groups, helpers, notifies))
    if not chosen:
        autos.sort(key=lambda x: (-x[0], x[1].get("name") or ""))
        autos = autos[:max_a]
    for score, a, res, trig_groups, act_groups, helpers, notifies in autos:
        steps = []
        out_clouds: list[str] = []
        n_more = len(res["trigger_entities"]) - 1
        for gp, eid in trig_groups[:2]:
            name = _short(ent_label(eid), 30)
            title = (t["a_s_trig_more"].format(name=name, n=n_more) if n_more > 0 and len(trig_groups) == 1
                     else t["a_s_trig"].format(name=name))
            st = {"title": title, "path": from_device(gp),
                  "text": t["a_t_trig"], "data": [[t["k_trigger"], res["trigger_types"][0] if res["trigger_types"] else "state"], [t["k_entity"], eid]]}
            if gp.get("cloud"):
                st["out"] = True
                out_clouds.append(cloud_name(gp))
            steps.append(st)
        if not trig_groups:
            ttype = res["trigger_types"][0] if res["trigger_types"] else ""
            if ttype == "time":
                at = ", ".join(res["times"][:3])
                steps.append({"title": t["a_s_time"], "path": ["ha"], "text": t["a_t_internal"],
                              "data": [[t["k_trigger"], t["time_at"].format(at=at) if at else "time"]]})
            elif res.get("ha_event"):
                steps.append({"title": t["a_s_start"] if res["ha_event"] == "start" else t["a_s_stop"],
                              "path": ["ha"], "text": t["a_t_internal"], "data": [[t["k_trigger"], "homeassistant." + res["ha_event"]]]})
            elif ttype == "sun":
                steps.append({"title": t["a_s_sun"], "path": ["ha"], "text": t["a_t_internal"], "data": [[t["k_trigger"], "sun"]]})
            else:
                steps.append({"title": t["a_s_other"], "path": ["ha"], "text": t["a_t_internal"],
                              "data": [[t["k_trigger"], ttype or "—"]] + ([[t["k_entity"], res["trigger_entities"][0]]] if res["trigger_entities"] else [])})
        cfg = a.get("config") or {}
        steps.append({"title": t["a_s_eval"], "path": ["ha"], "text": t["a_t_eval"],
                      "data": [[t["k_automation"], a.get("name") or a["entity_id"]],
                               [t["k_conditions"], str(res["n_conditions"])], [t["k_mode"], str(cfg.get("mode", "single"))]]})
        for gp, eid, svc in act_groups[:3]:
            name = ent_label(eid)
            st = {"title": t["a_s_act"].format(name=_short(name, 30)), "path": to_device(gp),
                  "text": t["a_t_act_cloud"].format(cloud=cloud_name(gp)) if gp.get("cloud") else t["a_t_act_local"],
                  "data": [[t["k_service"], svc], [t["k_entity"], eid]]}
            if gp.get("cloud"):
                st["out"] = True
                out_clouds.append(cloud_name(gp))
            steps.append(st)
        if not act_groups:
            for eid, svc in helpers[:1]:
                steps.append({"title": t["a_s_helper"].format(name=_short(ent_label(eid), 30)), "path": ["ha"],
                              "text": t["a_t_helper"], "data": [[t["k_service"], svc], [t["k_entity"], eid]]})
        if notifies and "push" in g.nodes:
            steps.append({"title": t["a_s_notify"], "path": g.via("ha", "push", "phones"), "out": True,
                          "text": t["n_t1"], "data": [[t["k_service"], notifies[0]]]})
            out_clouds.append(t["push"])
        trig_txt = ((t["a_trigger_dev_more"] if n_more > 0 else t["a_trigger_dev"]).format(name=ent_label(trig_groups[0][1]), n=n_more) if trig_groups
                    else (t["a_trigger_start"] if res["ha_event"] == "start" else t["a_trigger_stop"]) if res.get("ha_event")
                    else t["a_trigger_time"] if res["trigger_types"][:1] == ["time"]
                    else t["a_trigger_sun"] if res["trigger_types"][:1] == ["sun"] else t["a_trigger_other"])
        act_txt = (t["a_action_dev"].format(name=ent_label(act_groups[0][1])) if act_groups else t["a_action_notify"] if notifies else t["a_action_other"])
        desc = (cfg.get("description") or "").strip()
        summary = desc.split("\n")[0]
        if len(summary) > 200:
            summary = summary[:197].rsplit(" ", 1)[0] + "…"
        out_clouds = list(dict.fromkeys(out_clouds))
        scenarios.append({"id": "a_" + _slug(a["entity_id"].split(".", 1)[-1]), "group": "automazioni",
                          "title": a.get("name") or a["entity_id"],
                          "summary": summary or t["a_summary"].format(trigger=trig_txt, action=act_txt),
                          "offline": t["a_off_cloud"].format(cloud=", ".join(out_clouds)) if out_clouds else t["a_off_local"],
                          "steps": steps})

    # keep only the nodes that matter: every group stays, unused clouds go
    used = {x for s in scenarios for st in s["steps"] for x in st["path"]}
    for nid in list(g.nodes):
        if g.nodes[nid]["zone"] == "cloud" and nid not in used and nid not in ("nabu", "push"):
            # a vendor cloud with no flow still tells the story: keep it if a group depends on it
            if not any(gp.get("cloud") == nid for gp in groups.values()):
                del g.nodes[nid]
    edges = [e for e in g.edges if e[0] in g.nodes and e[1] in g.nodes]
    node_list = list(g.nodes.values())
    # order: cloud, net (router first), server, device
    zone_rank = {"cloud": 0, "net": 1, "server": 2, "device": 3}
    node_list.sort(key=lambda n: (zone_rank.get(n["zone"], 4), 0 if n["id"] == router_id else 1))
    server_order = ["ha", "mqtt", "z2m", "coord", "matter_srv", "zw"]
    node_list.sort(key=lambda n: (zone_rank.get(n["zone"], 4), 0 if n["id"] == router_id else 1,
                                  server_order.index(n["id"]) if n["id"] in server_order else 99))
    used_boxes = {n.get("box") for n in node_list}
    return {
        "title": t["title"],
        "note": t["note"],
        "language": lang,
        "boxes": [b for b in boxes if b["id"] in used_boxes],
        "nodes": node_list,
        "edges": edges,
        "scenarios": scenarios,
    }


def _analyze(cfg: dict) -> dict:
    """Pull trigger entities/devices and action targets out of an automation config."""
    triggers = _as_list(cfg.get("triggers", cfg.get("trigger")))
    res = {"trigger_entities": [], "trigger_devices": [], "trigger_types": [], "times": [],
           "actions": [], "n_conditions": len(_as_list(cfg.get("conditions", cfg.get("condition"))))}
    for tr in triggers:
        if not isinstance(tr, dict):
            continue
        ttype = str(tr.get("trigger") or tr.get("platform") or "")
        res["trigger_types"].append(ttype.split(".")[-1] if ttype.startswith("time") else ttype)
        for key in ("entity_id",):
            for eid in _as_list(tr.get(key)):
                if isinstance(eid, str) and not _is_template(eid) and "." in eid and eid not in res["trigger_entities"]:
                    res["trigger_entities"].append(eid)
        tgt = tr.get("target") or {}
        if isinstance(tgt, dict):
            for eid in _as_list(tgt.get("entity_id")):
                if isinstance(eid, str) and not _is_template(eid) and eid not in res["trigger_entities"]:
                    res["trigger_entities"].append(eid)
        if tr.get("device_id") and not _is_template(tr.get("device_id")):
            res["trigger_devices"].append(tr["device_id"])
        if ttype == "homeassistant" and tr.get("event") in ("start", "shutdown"):
            res.setdefault("ha_event", tr["event"])
        if ttype == "time":
            for at in _as_list(tr.get("at")):
                if isinstance(at, str) and not _is_template(at):
                    res["times"].append(at[:5])
    # normalise trigger type names
    res["trigger_types"] = [("time" if x in ("time", "time_pattern") else x) for x in res["trigger_types"]]

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for x in node:
                walk(x)
            return
        if not isinstance(node, dict):
            return
        svc = node.get("action") if isinstance(node.get("action"), str) else node.get("service")
        if isinstance(svc, str) and "." in svc and not _is_template(svc):
            eids: list[str] = []
            dids: list[str] = []
            for src in (node.get("target") or {}, node.get("data") or {}, node):
                if not isinstance(src, dict):
                    continue
                for eid in _as_list(src.get("entity_id")):
                    if isinstance(eid, str) and not _is_template(eid):
                        eids.extend(x.strip() for x in eid.split(",") if "." in x)
                for did in _as_list(src.get("device_id")):
                    if isinstance(did, str) and not _is_template(did):
                        dids.append(did)
            res["actions"].append((svc, list(dict.fromkeys(eids)), list(dict.fromkeys(dids))))
        if node.get("type") in ("turn_on", "turn_off", "toggle") and node.get("device_id") and node.get("domain"):
            res["actions"].append((f"{node['domain']}.{node['type']}", [], [node["device_id"]]))
        for key, val in node.items():
            if key in ("target", "data", "entity_id", "device_id", "variables", "conditions", "condition"):
                continue
            if isinstance(val, (list, dict)):
                walk(val)

    walk(_as_list(cfg.get("actions", cfg.get("action"))))
    return res
