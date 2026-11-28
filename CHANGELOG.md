# Changelog

## Unreleased

- Icon and logo: shown in Settings → Integrations (Home Assistant 2026.3 or later) and at the top of the README
- Automations started by Home Assistant itself (start or shutdown), automations that only send a notification and triggers on many entities read better
- Device registry read without the calls Home Assistant marks as deprecated

## 2.0.0

Home Flow Explorer is now an integration that builds the map by itself.

- Guided setup: router, how Home Assistant is connected, where Wi-Fi comes from
- Reads devices, integrations, add-ons and automations and generates nodes, links and flows
- Local or cloud comes from each integration's declared IoT class; push or polling decides how state comes back
- Zigbee2MQTT, ZHA, deCONZ, Z-Wave, MQTT and Matter get their own chain inside the Home Assistant box
- Network gear and NAS found by their integrations show up on their own; anything else (access points, switches, servers, cloud services) can be added and classified from Configure
- Everyday flows generated from real devices, plus voice, notifications and a sensor event when they apply
- Automations: triggers and targets read from their configuration, with the physical path of every hop
- The integration serves the card itself: no dashboard resource to add
- `source: auto` on the card; anything written in the card config adds to or overrides the generated map; `hide` removes nodes or flows
- `home_flow_explorer.export` action returns the generated configuration
- Fix: label backgrounds no longer stretch to the corner when a node has no second line

## 1.0.0

First public release: a card configured by hand.
