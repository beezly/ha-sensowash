# ha-sensowash

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for **Duravit SensoWash** smart toilets.

Connects over Bluetooth Low Energy — works with direct BLE adapters **and**
[Home Assistant Bluetooth proxies](https://esphome.io/components/bluetooth_proxy.html)
(ESPHome, etc.), so you don't need a Bluetooth dongle on your HA server.

Uses the [sensowash-ble](https://github.com/beezly/sensowash-ble) Python library.

---

## Supported Devices

| Model | BLE Name |
|---|---|
| SensoWash Classic (EU & Non-EU) | `SensoWash c` |
| SensoWash U | `SensoWash u` |
| SensoWash Starck F Pro | `SensoWash s` |
| SensoWash i Pro | `SensoWash i` |
| DuraSystem | `DuraSystem` |

> Older serial-protocol models (Starck Plus/Lite, i Plus/Lite for China/USA) are not
> currently supported.

---

## Installation via HACS

1. In HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/beezly/ha-sensowash` as category **Integration**
3. Install **Duravit SensoWash**
4. Restart Home Assistant

### Manual installation

Copy `custom_components/sensowash/` into your HA `config/custom_components/` directory
and restart.

---

## Setup

### Automatic (recommended)

If HA can see the toilet over Bluetooth (directly or via a proxy), it will appear
automatically in **Settings → Devices & Services** as a discovered device.
Click **Configure** and confirm.

### Manual

1. **Settings → Devices & Services → Add Integration**
2. Search for **SensoWash**
3. Enter the Bluetooth MAC address (Linux/Windows) or CoreBluetooth UUID (macOS)

### Bluetooth Proxy

For best results, place an
[ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html) near the
toilet. HA will automatically use it — no additional config needed. A cheap ESP32 board
is all that's required.

---

## Entities

### Binary Sensors
| Entity | Description |
|---|---|
| **Wash active** | True while a wash cycle is running |
| **Dryer active** | True while the dryer is running |
| **Lid** | Open / Closed |
| **Occupied** | True when someone is seated (proximity sensor) |
| **Deodorizing** | True while deodorizer is running |

### Sensors
| Entity | Description |
|---|---|
| **Seat temperature** | Measured seat surface temperature (°C) |
| **Status** | `ok` or active error code list; attributes contain full error detail |

### Switches
| Entity | Description |
|---|---|
| **Ambient light** | Night/ambient LED |
| **HygieneUV light** | UVC disinfection light |
| **HygieneUV automatic** | Automatic UVC cycle after each use |
| **Deodorization** | Deodorizer on/off |
| **Automatic deodorization** | Auto-trigger after use |
| **Automatic flush** | Auto-flush on seat exit |
| **Pre-flush** | Pre-flush before use |
| **Proximity sensor** | Presence detection |
| **Mute** | Silence beep tones |
| **Automatic seat** | Auto lower the seat |

### Selects
| Entity | Options |
|---|---|
| **Water flow** | Low / Medium / High |
| **Water temperature** | Off / Warm / Warmer / Hot |
| **Nozzle position** | 1 (forward) … 5 (rear) |
| **Seat heating** | Off / Warm / Warmer / Hot |
| **Dryer temperature** | Off / Warm / Warmer / Hot |
| **Dryer speed** | Normal / Turbo |
| **Water hardness** | Soft / Medium-soft / Medium / Medium-hard / Hard |

### Buttons
| Entity | Action |
|---|---|
| **Start rear wash** | Starts rear wash with current settings |
| **Start lady wash** | Starts lady wash with current settings |
| **Stop** | Stops any active function |
| **Flush** | Manual flush |
| **Open lid** | Opens the lid |
| **Close lid** | Closes the lid |
| **Start dryer** | Starts the dryer |
| **Stop dryer** | Stops the dryer |

---

## Example Automations

### Auto-wash on motion
```yaml
automation:
  - alias: "Toilet: start rear wash when occupied"
    trigger:
      - platform: state
        entity_id: binary_sensor.sensowash_occupied
        to: "on"
    action:
      - delay: "00:00:05"   # brief settle
      - service: button.press
        target:
          entity_id: button.sensowash_start_rear_wash
```

### Nighttime ambient light
```yaml
automation:
  - alias: "Toilet: ambient light on at night"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.sensowash_ambient_light
  - alias: "Toilet: ambient light off in morning"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.sensowash_ambient_light
```

### Alert on fault
```yaml
automation:
  - alias: "Toilet: notify on error"
    trigger:
      - platform: state
        entity_id: sensor.sensowash_status
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state != 'ok' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "SensoWash fault"
          message: >
            Error {{ states('sensor.sensowash_status') }}.
            {{ state_attr('sensor.sensowash_status', 'active_errors')[0]['action'] }}
```

---

## Bluetooth Proxy Setup (ESPHome)

Minimal ESPHome config for a BT proxy near the toilet:

```yaml
esphome:
  name: toilet-bt-proxy

esp32:
  board: esp32dev

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

bluetooth_proxy:
  active: true

logger:
api:
ota:
```

Flash to an ESP32, add to HA, and the toilet will appear automatically.

---

## Technical Notes

- **Protocol:** BLE GATT over Bluetooth LE (custom Duravit services)
- **Connectivity:** `local_push` — state updates arrive via BLE notifications in real time
- **Polling:** Full state refresh every 30 seconds as a fallback
- **Bonding:** Required — pair the toilet to your BT adapter/proxy before adding to HA
- **Library:** [sensowash-ble](https://github.com/beezly/sensowash-ble) — see that repo for
  full protocol documentation

---

## License

MIT. Not affiliated with or endorsed by Duravit AG.
