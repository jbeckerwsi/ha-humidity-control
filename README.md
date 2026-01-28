# Humidity Control - Unified Indoor Air Quality Controller for Home Assistant

A custom Home Assistant integration that provides unified indoor air quality control, managing humidity, CO2, and VOC levels through coordinated humidifier and ventilation control.

## Features

### Humidity Control
- **Multi-level Humidifier Support**: Control humidifiers with multiple fan speeds (e.g., Robby with power switch + level selector)
- **Dehumidification via Ventilation**: Use HVAC/ventilation systems to reduce humidity
- **Target Range**: Maintain humidity between configurable thresholds (default: 40-46%)
- **Critical Protection**: Cap ventilation when humidity drops critically low (<35%)

### Air Quality Control
- **CO2 Monitoring**: Target 600ppm, critical threshold 900ppm
- **VOC Monitoring**: Target 100, critical threshold 350
- **Proportional Control**: Fan speeds scale based on how far readings are from targets
- **Simultaneous Operation**: Humidifier and ventilation can run together (e.g., high CO2 but low humidity)

### Boost Mode
- **Rapid Air Exchange**: Maximum ventilation for configurable duration (5-60 minutes)
- **Multiple Triggers**: Activate via service call or input_boolean helper
- **Auto-Restore**: Returns to normal operation after boost ends

### Safety Features
- **Minimum Action Durations**: Prevent rapid cycling of humidifier and ventilation
- **Sensor Stale Detection**: Turn off when sensors stop responding
- **Conflict Resolution**: Automatically balance competing needs (humidity vs air quality)

## Operating Modes

| Mode | Description |
|------|-------------|
| `idle` | All readings within target range |
| `humidifying` | Humidity below target, humidifier active |
| `dehumidifying` | Humidity above threshold, ventilation active |
| `ventilating` | CO2/VOC elevated, ventilation active |
| `ventilating_and_humidifying` | Air quality needs ventilation, but humidity also low |
| `boost` | Manual boost mode active |

## Installation

### Manual Installation

1. Copy the `custom_components/humidity_control` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant
3. Set up via UI or YAML (see Configuration below)

### HACS (Manual Repository)

1. In HACS, go to "Integrations"
2. Click the three dots menu and select "Custom repositories"
3. Add this repository URL with category "Integration"
4. Install "Humidity Control"
5. Restart Home Assistant

## Configuration

### UI Setup (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Humidity Control"
4. Follow the multi-step setup wizard:
   - **Basic**: Name and humidity sensor
   - **Humidifier**: Power entity, level entity, available levels
   - **Air Quality**: CO2/VOC sensors and thresholds
   - **Ventilation**: Climate entity, fan levels, dehumidification thresholds
   - **Timing**: Minimum action durations, boost helper

### YAML Configuration

```yaml
humidity_control:
  - name: "Living Room Air Quality"
    # Required - Humidity sensor
    target_sensor: sensor.bme680_humidity
    target_humidity: 43
    min_humidity: 30
    max_humidity: 60
    
    # Multi-level humidifier (Robby)
    humidifier_power_entity: switch.robby_power
    humidifier_level_entity: select.robby_fan_level
    humidifier_levels:
      - "1"
      - "2"
      - "3"
    
    # Air quality sensors
    co2_sensor: sensor.mh_z19_co2_value
    co2_target: 600
    co2_critical: 900
    voc_sensor: sensor.voc
    voc_target: 100
    voc_critical: 350
    
    # Ventilation control (Nilan HVAC)
    ventilation_entity: climate.nilan_hvac
    ventilation_levels:
      - "0"
      - "1"
      - "2"
      - "3"
      - "4"
    humidity_dehumidify_threshold: 48
    humidity_dehumidify_critical: 35
    
    # Timing
    min_humidify_duration: 300  # 5 minutes
    min_ventilate_duration: 180  # 3 minutes
    
    # Boost mode helper (optional)
    boost_helper: input_boolean.air_quality_boost
```

### Configuration Variables

#### Required
| Variable | Description |
|----------|-------------|
| `target_sensor` | Entity ID of the humidity sensor |

#### Humidity Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `name` | "Humidity Control" | Name of the entity |
| `target_humidity` | - | Initial target humidity |
| `min_humidity` | 0 | Minimum settable humidity |
| `max_humidity` | 100 | Maximum settable humidity |
| `dry_tolerance` | 3 | How far below target before humidifying starts |
| `wet_tolerance` | 3 | How far above target before dehumidifying starts |

#### Multi-Level Humidifier
| Variable | Default | Description |
|----------|---------|-------------|
| `humidifier_power_entity` | - | Power switch entity (e.g., `switch.robby_power`) |
| `humidifier_level_entity` | - | Level selector entity (e.g., `select.robby_fan_level`) |
| `humidifier_levels` | ["1","2","3"] | Available fan level options |

#### Legacy Humidifier/Dehumidifier (simple on/off)
| Variable | Description |
|----------|-------------|
| `wet_entity` | Entity ID of simple humidifier switch |
| `dry_entity` | Entity ID of simple dehumidifier switch |

#### Air Quality
| Variable | Default | Description |
|----------|---------|-------------|
| `co2_sensor` | - | CO2 sensor entity ID |
| `co2_target` | 600 | Target CO2 level (ppm) |
| `co2_critical` | 900 | Critical CO2 level (ppm) |
| `voc_sensor` | - | VOC sensor entity ID |
| `voc_target` | 100 | Target VOC level |
| `voc_critical` | 350 | Critical VOC level |

#### Ventilation
| Variable | Default | Description |
|----------|---------|-------------|
| `ventilation_entity` | - | Climate entity for ventilation (e.g., `climate.nilan_hvac`) |
| `ventilation_levels` | ["0","1","2","3","4"] | Available fan mode levels |
| `humidity_dehumidify_threshold` | 48 | Humidity % to start dehumidifying via ventilation |
| `humidity_dehumidify_critical` | 35 | Humidity % to cap ventilation (protect from over-drying) |

#### Timing
| Variable | Default | Description |
|----------|---------|-------------|
| `min_humidify_duration` | 300 | Minimum seconds to run humidifier |
| `min_ventilate_duration` | 180 | Minimum seconds to run ventilation |
| `min_cycle_duration` | - | Legacy: minimum time between switching |
| `keep_alive` | - | Interval to resend commands |
| `sensor_stale_duration` | - | Turn off if sensor doesn't update |

#### Boost Mode
| Variable | Default | Description |
|----------|---------|-------------|
| `boost_helper` | - | Input boolean to trigger boost mode |

## Services

### Standard Humidifier Services
- `humidifier.turn_on` - Enable humidity control
- `humidifier.turn_off` - Disable humidity control
- `humidifier.toggle` - Toggle on/off
- `humidifier.set_humidity` - Set target humidity
- `humidifier.set_mode` - Set mode (`normal` or `away`)

### Custom Services

#### `humidity_control.boost`
Activate boost mode for rapid air exchange.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `duration` | No | 1200 | Duration in seconds (60-3600) |

```yaml
service: humidity_control.boost
target:
  entity_id: humidifier.living_room_air_quality
data:
  duration: 1800  # 30 minutes
```

#### `humidity_control.stop_boost`
Immediately deactivate boost mode.

```yaml
service: humidity_control.stop_boost
target:
  entity_id: humidifier.living_room_air_quality
```

## State Attributes

| Attribute | Description |
|-----------|-------------|
| `humidity` | Target humidity |
| `current_humidity` | Current measured humidity |
| `operating_mode` | Current operating mode |
| `air_quality_status` | Air quality status (good/elevated/poor/critical) |
| `current_co2` | Current CO2 reading |
| `current_voc` | Current VOC reading |
| `humidifier_power` | Humidifier power state |
| `humidifier_level` | Current humidifier level |
| `ventilation_level` | Current ventilation level |
| `ventilation_reason` | Why ventilation is active (co2/voc/humidity/boost/none) |
| `boost_active` | Whether boost mode is active |
| `boost_end_time` | When boost mode will end |

## How It Works

### Humidity Control
1. When humidity drops below `target - dry_tolerance`:
   - Multi-level humidifier: Activates power, sets proportional level
   - Legacy humidifier: Turns on wet entity
2. When humidity rises above `humidity_dehumidify_threshold`:
   - Activates ventilation to reduce humidity
3. Humidity level determines humidifier fan speed (proportional control)

### Air Quality Control
1. CO2/VOC sensors are monitored continuously
2. Ventilation level scales proportionally:
   - At target: Level 0-1
   - Approaching critical: Level 3-4
3. Multiple triggers combine (highest need wins)

### Conflict Resolution
- If humidity drops below `humidity_dehumidify_critical` (35%), ventilation is capped at level 2
- Humidifier and ventilation can run simultaneously when air quality needs ventilation but humidity is low

### Boost Mode
1. Triggered via service call or input_boolean helper
2. Sets ventilation to maximum level
3. Automatically ends after duration expires
4. Returns to normal proportional control

## Development

### Prerequisites

This project uses [Nix](https://nixos.org/) for reproducible development environments.

### Setup

```bash
# Enter development shell
nix develop

# Or if you don't have flakes enabled
nix-shell -p python312 python312Packages.pyyaml python312Packages.pytest ruff
```

### Available Tools

Inside the development shell:

```bash
# Linting
ruff check custom_components/

# Auto-fix linting issues
ruff check custom_components/ --fix

# Format code
ruff format custom_components/

# Check formatting without changes
ruff format --check custom_components/

# Type checking (expects errors without HA installed)
mypy custom_components/

# Validate YAML
python3 -c "import yaml; yaml.safe_load(open('custom_components/humidity_control/services.yaml'))"

# Validate JSON
python3 -c "import json; json.load(open('custom_components/humidity_control/strings.json'))"
```

### Project Structure

```
custom_components/humidity_control/
├── __init__.py          # Component setup, YAML schema
├── config_flow.py       # UI configuration flow
├── const.py             # Constants and defaults
├── humidifier.py        # Main entity logic
├── manifest.json        # Integration manifest
├── services.yaml        # Service definitions
├── strings.json         # Translatable strings
└── translations/
    ├── en.json          # English translations
    └── de.json          # German translations
```

### Code Style

- Python 3.12+
- Formatted with `ruff format`
- Linted with `ruff check`
- Line length: 100 characters

## Troubleshooting

### Entity shows as unavailable
- Check that your humidity sensor is reporting values
- Verify all sensor entity IDs are correct

### Humidifier not turning on
- Verify power and level entity IDs are correct
- Check that the entities can be controlled manually
- Review Home Assistant logs for errors

### Ventilation not activating for air quality
- Ensure CO2/VOC sensors are configured
- Check sensor readings are within expected ranges
- Verify ventilation entity supports `climate.set_fan_mode`

### Boost mode not working
- If using helper: ensure input_boolean entity exists
- Check service call syntax
- Review entity attributes for `boost_active` status

## License

This integration is licensed under the **Apache License 2.0**.

This is a derivative work based on the [Generic Hygrostat](https://github.com/home-assistant/core/tree/dev/homeassistant/components/generic_hygrostat) component from Home Assistant Core.

**Original work:**
- Home Assistant Core - Generic Hygrostat Integration
- Copyright Home Assistant Contributors
- Licensed under the Apache License, Version 2.0
- https://github.com/home-assistant/core

See the [NOTICE](custom_components/humidity_control/NOTICE) file for details on changes made.

## Contributing

Contributions are welcome! Please:

1. Run `ruff check` and `ruff format` before submitting
2. Ensure all JSON/YAML files are valid
3. Update translations if adding new strings
4. Test in a Home Assistant environment

## Acknowledgments

This integration is based on the excellent [Generic Hygrostat](https://www.home-assistant.io/integrations/generic_hygrostat/) integration from Home Assistant Core, maintained by [@Shulyaka](https://github.com/Shulyaka).
