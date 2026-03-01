# ha-sensowash

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for **Duravit SensoWash** smart toilets.

Connects over Bluetooth Low Energy — works with direct BLE adapters **and**
[ESPHome Bluetooth proxies](https://esphome.io/components/bluetooth_proxy.html).
This means **your Home Assistant server doesn't need to be within Bluetooth range of
your toilet** — a cheap ESP32 board placed nearby is all you need.
See [Bluetooth Proxy Setup](#bluetooth-proxy-setup-esphome) for a minimal ESPHome config.

Uses the [sensowash-ble](https://github.com/beezly/sensowash-ble) Python library.

---

## Supported Devices

| Model | BLE Name |
|---|---|
| SensoWash Classic (EU & Non-EU) | `SensoWash c` |
| SensoWash U | `SensoWash u` |
| SensoWash Starck F Pro | `SensoWash s` |
| SensoWash i Pro | `SensoWash i` |
| SensoWash Starck F Plus / Starck F Lite (serial) | `DURAVIT_BT` |
| SensoWash i Plus / i Lite (serial) | `DURAVIT_BT` |
| DuraSystem | `DuraSystem` |

> **Serial-protocol models** (Starck F Plus/Lite, i Plus/Lite) require a one-time pairing
> step the first time you add the integration. See [Pairing](#pairing) below.

---

## Installation

### Via HACS (recommended)

This integration is not yet in the default HACS store, so you need to add it as a
**custom repository** first.

#### Step 1 — Add the custom repository

**Option A — one-click (HACS 2.x+):**

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=beezly&repository=ha-sensowash&category=integration)

**Option B — manually:**

1. Open HACS in your Home Assistant sidebar
2. Click **⋮ (three dots)** → **Custom repositories**
3. Enter `https://github.com/beezly/ha-sensowash` in the URL field
4. Select **Integration** as the category
5. Click **Add**

#### Step 2 — Install

1. Search for **SensoWash** in HACS → Integrations
2. Click **Download** and confirm
3. **Restart Home Assistant**

#### Step 3 — Configure

After restarting, HA will discover your toilet automatically if it's advertising via
Bluetooth. Accept the prompt in **Settings → Notifications**, or go to
**Settings → Devices & Services → Add Integration → SensoWash**.

---

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

Entities are registered based on what the toilet actually supports — not all will appear on every model. Serial-protocol devices are write-only for some settings (no readback), so selects may show **unknown** until you set them.

### Binary Sensors
| Entity | Description |
|---|---|
| **Wash active** | True while a wash cycle is running |
| **Dryer active** | True while the dryer is running |
| **Lid** | Open / Closed |
| **Seat occupied** | True when someone is seated (serial protocol only — see note below) |
| **Deodorizing** | True while deodorizer is running |

> **Seat occupied (serial protocol only):** The occupancy state is decoded from the
> toilet's status packet — the same packet used for wash/dryer state. It reflects
> whether the proximity/weight sensor detects someone seated. Because the toilet does
> not push this state unsolicited, the integration polls every **10 seconds** when
> the seat occupied entity is active (reduced from the normal 30-second interval).
> GATT-protocol models (Classic, U, Starck F Pro, i Pro) do not expose a live
> occupancy characteristic and will not have this entity.

### Sensors
| Entity | Description |
|---|---|
| **Seat temperature** | Measured seat surface temperature (°C) |
| **Status** | `ok` or active error code list; attributes contain full error detail |
| **Descaling status** | `idle` / `in_progress` / `paused` |
| **Descaling time remaining** | Minutes remaining in current descaling cycle (serial only) |

### Switches
| Entity | Description |
|---|---|
| **HygieneUV light** | UVC disinfection light |
| **HygieneUV automatic** | Automatic UVC cycle after each use |
| **Deodorization** | Deodorizer on/off |
| **Automatic deodorization** | Auto-trigger after use |
| **Automatic flush** | Auto-flush on seat exit |
| **Pre-flush** | Pre-flush before use |
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
| **Night light** | Off / On / Auto |
| **Proximity sensitivity** | Near / Medium / Far |
| **Deodorization delay** | Off (immediate) / Short / Long |

### Buttons
| Entity | Action | Protocol |
|---|---|---|
| **Start rear wash** | Starts rear wash with current settings | Both |
| **Start lady wash** | Starts lady wash with current settings | Both |
| **Stop** | Stops any active function | Both |
| **Flush** | Full manual flush | Both |
| **Eco flush** | Reduced-water flush | Serial |
| **Open lid** | Opens the lid | Both |
| **Close lid** | Closes the lid | Both |
| **Start dryer** | Starts the dryer | Both |
| **Stop dryer** | Stops the dryer | Both |
| **Start descaling** | Triggers a descaling cycle | Serial |
| **Nozzle self-clean** | Automatic nozzle cleaning cycle | Serial |
| **Extend nozzle for cleaning** | Extends nozzle for manual cleaning | Serial |
| **Drain tank** | Drains internal tank (EN 1717 / BS EN 1717) | Serial |
| **Factory reset** | Restores factory defaults ⚠️ | Serial |

---

## Pairing

Older serial-protocol models (Starck F Plus/Lite, i Plus/Lite) advertise as `DURAVIT_BT`
and require a one-time Bluetooth pairing handshake before they'll accept commands.

### How it works

When the integration detects a serial-protocol toilet during setup, it automatically
starts the pairing process. At that point the toilet's Bluetooth indicator will
**slow-flash blue** — this means it's waiting for you to confirm pairing.

**Press the Bluetooth button on the toilet** (usually on the side panel, marked with the
Bluetooth symbol). The indicator will stop flashing and the pairing will complete.

The pairing key is saved automatically — you won't need to do this again unless you
factory reset the toilet or reinstall the integration.

### Troubleshooting

- **LED not flashing?** Make sure Bluetooth is enabled on the toilet (check the app or
  side panel switch). The toilet must be powered on and within BLE range.
- **Timed out?** The pairing screen has a countdown. If it expires before you press the
  button, you can retry from the next screen.
- **Already paired to another device?** The toilet can only be paired to one controller
  at a time. If it was previously paired via the Duravit app, you may need to reset
  the Bluetooth pairing on the toilet first (hold the Bluetooth button for ~10 seconds
  until the LED flashes rapidly).

---

### Services

Scheduling features that don't map to simple entity types are exposed as HA services,
callable from **Developer Tools → Actions**, automations, and scripts.

| Service | Description |
|---|---|
| `sensowash.set_seat_heating_schedule` | Program seat heating time windows and temperature |
| `sensowash.get_seat_heating_schedule` | Read current schedule (logged to HA log) |
| `sensowash.clear_seat_heating_schedule` | Remove all seat heating windows |
| `sensowash.set_uvc_schedule` | Set UVC disinfection trigger times |
| `sensowash.set_uvc_schedule_default` | Reset UVC schedule to factory default (02:00 & 03:00) |

Example — warm seat on weekday mornings:
```yaml
action: sensowash.set_seat_heating_schedule
data:
  config_entry_id: "your_entry_id"
  enabled: true
  temperature: 2   # 0=Off 1=Warm 2=Warmer 3=Hot
  windows:
    - from_hour: 6
      from_minute: 30
      to_hour: 8
      to_minute: 0
      days: [1, 2, 3, 4, 5]   # 1=Mon … 7=Sun
```

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
  - alias: "Toilet: night light auto mode at night"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.sensowash_night_light
        data:
          option: auto
  - alias: "Toilet: night light off in morning"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.sensowash_night_light
        data:
          option: "off"
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
