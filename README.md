<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo-dark.png">
    <img src="docs/logo.png" alt="Home Flow Explorer" height="96">
  </picture>
</p>

# Home Flow Explorer

A map of how messages actually travel through your smart home. Pick something that happens ("I turn on the floor lamp from the app", "the irrigation automation runs at 7") and a packet walks the path hop by hop: phone, Wi-Fi, Home Assistant, MQTT, Zigbee2MQTT, coordinator, device, or out to a vendor cloud and back. Each hop shows what is sent and whether it stays local or leaves the house.

![Home Flow Explorer](docs/screenshot.png)

It answers questions like "what stops working if the internet goes down?" or "why does this thermostat need the cloud?".

## How it works

Home Flow Explorer is an integration with a card:

1. **Add the integration.** It reads your devices, integrations, add-ons and automations.
2. **Answer the guided setup.** Home Assistant cannot see your router, your access points or how its own machine is wired, so it asks.
3. **Add the card wherever you like.** `type: custom:home-flow-explorer` with `source: auto`. The integration serves the card file, there is no resource to register.

The map rebuilds every time the card loads, so new devices and automations show up on their own.

## Install

### Marketplace / HACS

1. **Settings → Marketplace** (HACS on 2026.10 and older) → add `https://github.com/bonello78/home-flow-explorer` as a custom repository of type **Integration**.
2. Install **Home Flow Explorer** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Home Flow Explorer.**

If you installed version 1 as a dashboard card, remove it first: the integration now ships the card.

### Manual

Copy `custom_components/home_flow_explorer` into your `config/custom_components` folder and restart.

## Setup

The guided setup asks four things:

- **Router name and address**, shown on the map.
- **How Home Assistant is connected**: straight to the router or through a switch.
- **Where Wi-Fi comes from**: the router, an access point found by an integration (TP-Link Deco, UniFi, Fritz!Box…) or one you add now.
- **What to show**: integrations to hide, how many everyday flows and automations.

Everything else is read from Home Assistant.

### Things Home Assistant cannot see

Open the integration and press **Configure**:

- **Add an object**: access points, switches, a NAS, a server, a cloud service or any other device. Pick its type (it decides where it sits on the map), what it is connected to and how (cable, Wi-Fi, radio, internet).
- **Edit** or **remove** objects.
- **Map settings**: language, links, hidden integrations, which automations to show.

## The card

```yaml
type: custom:home-flow-explorer
source: auto
```

Put it in a **panel** view so it gets the full width. The map describes your whole network, so only administrators can load it.

You can add to the generated map or change it from the card configuration. Anything with the same `id` replaces the generated item, anything new is added:

```yaml
type: custom:home-flow-explorer
source: auto
title: Our home
hide: [grp_vesync]            # node or flow ids to drop
nodes:
  - {id: router, sub: 192.168.1.1}
scenarios:
  - id: my-flow
    group: automazioni
    title: Something Home Assistant cannot see
    steps:
      - {title: First hop, path: [ha, mqtt], text: What happens here.}
```

To see the generated configuration, run the action `home_flow_explorer.export` from **Developer tools → Actions** with "return response" on.

### What gets generated

- **Nodes.** Vendor clouds (from each integration's IoT class), Nabu Casa, the push service, your router and objects, the Home Assistant machine with MQTT, Zigbee2MQTT, the Zigbee or Z-Wave coordinator and the Matter server, and one node per integration that has devices. Small local integrations with a single device are grouped under "Others".
- **Everyday flows.** One per kind of connection (Zigbee, local Wi-Fi, cloud, Matter…), using a real device as the example. Plus "Alexa turns on a light" when Alexa and Nabu Casa are there, "a notification reaches the phone" when the companion app is installed, and a Zigbee sensor event.
- **Automations.** Triggers and targets are read from the configuration. Each automation becomes a flow: the trigger device reaching Home Assistant, the decision, and every action reaching its device, through the cloud when the integration needs one.

Not covered: logic inside Node-RED or AppDaemon, and anything behind templates. Add those by hand in the card.

## Manual mode

Without `source: auto` the card takes the whole map from its configuration: `nodes`, `edges`, `scenarios`, optional `boxes` and `layout`. A complete example is in [`examples/demo.yaml`](examples/demo.yaml), and [`examples/demo.html`](examples/demo.html) runs it in a browser without Home Assistant.

| Key | Description |
|---|---|
| `nodes` | `{id, name, sub, zone: cloud\|net\|server\|device, box, info}` |
| `edges` | `[from, to, cable\|wifi\|zigbee\|internet\|internal]` |
| `scenarios` | `{id, group, title, summary, offline, steps: [{title, path, out, text, data}]}` |
| `boxes` | `{id, label}`: containers for server nodes |
| `layout` | Hand-placed coordinates for `desktop` (1200 wide) and `mobile` (400 wide) |
| `language` | `it` or `en`, default the Home Assistant language |
| `start`, `autoplay`, `title`, `intro`, `note`, `group_labels` | Optional |

Every consecutive pair in a step `path` must be an edge.

## Troubleshooting

- **"Configuration error" in the phone app after installing**: the companion app loads its resources only when it starts. Reset the frontend cache (Settings → Companion app → Debugging) and restart the app.
- **The card asks to set up the integration**: add it from Devices & services.
- **Blank map**: set `debug: true` on the card; it then writes its size and any drawing error to the Home Assistant log (logger `home_flow_explorer`).

## Development

The map builder (`custom_components/home_flow_explorer/graph.py`) does not import Home Assistant and can be tested on plain data. Integration tests use `pytest-homeassistant-custom-component`:

```
pip install pytest-homeassistant-custom-component
pytest tests
```

## License

MIT
