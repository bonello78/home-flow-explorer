"""Constants for Home Flow Explorer."""

DOMAIN = "home_flow_explorer"
VERSION = "2.0.0"

URL_BASE = "/home_flow_explorer_static"
CARD_FILE = "home-flow-explorer.js"

CONF_LANGUAGE = "language"
CONF_OBJECTS = "objects"
CONF_HA_LINK = "ha_link"
CONF_WIFI = "wifi"
CONF_HOST_LABEL = "host_label"
CONF_EXCLUDED = "excluded_integrations"
CONF_MAX_AUTOMATIONS = "max_automations"
CONF_MAX_GESTURES = "max_gestures"
CONF_AUTOMATIONS = "automations"

DEFAULT_MAX_AUTOMATIONS = 6
DEFAULT_MAX_GESTURES = 5

# Kinds of objects the user can add by hand, and the map zone each one lands in.
OBJECT_KINDS = {
    "router": "net",
    "access_point": "net",
    "switch": "net",
    "nas": "server",
    "server": "server",
    "cloud": "cloud",
    "device": "device",
    "other": "device",
}

MEDIA = ["cable", "wifi", "zigbee", "internet", "internal"]
