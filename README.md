# Humidity Control - Combined Humidifier/Dehumidifier for Home Assistant

A custom Home Assistant integration that provides combined humidity control with both humidifying and dehumidifying capabilities in a single entity.

## License

This integration is licensed under the **Apache License 2.0**.

This is a derivative work based on the [Generic Hygrostat](https://github.com/home-assistant/core/tree/dev/homeassistant/components/generic_hygrostat) component from Home Assistant Core.

**Original work:**
- Home Assistant Core - Generic Hygrostat Integration
- Copyright Home Assistant Contributors
- Licensed under the Apache License, Version 2.0
- https://github.com/home-assistant/core

See the [NOTICE](custom_components/humidity_control/NOTICE) file for details on changes made.

## Features

- **Combined Control**: Single entity controls both humidifier and dehumidifier
- **Three Operating Modes**: 
  - `idle` - Within target humidity range, no action needed
  - `wet` - Humidifying to increase humidity
  - `dry` - Dehumidifying to decrease humidity
- **Flexible Output Entities**: Supports both `switch` and `input_boolean` entities as outputs
- **Tolerance Settings**: Configurable dry and wet tolerances to prevent rapid cycling
- **Away Mode**: Optional away humidity setting for when you're not home
- **Sensor Stale Detection**: Safety feature to turn off when sensor stops responding
- **Keep-Alive**: Periodic signals for devices that need regular commands
- **Min Cycle Duration**: Prevents rapid on/off cycling

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
4. Follow the setup wizard:
   - Enter a name
   - Select your humidity sensor
   - Select humidifier entity (optional)
   - Select dehumidifier entity (optional)
   - Configure tolerances and other options

### YAML Configuration

Alternatively, add to your `configuration.yaml`:

```yaml
humidity_control:
  - name: "Living Room Humidity"
    target_sensor: sensor.living_room_humidity
    wet_entity: switch.humidifier
    dry_entity: switch.dehumidifier
    target_humidity: 50
    min_humidity: 30
    max_humidity: 70
    dry_tolerance: 3
    wet_tolerance: 3
```

### Configuration Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `name` | No | "Humidity Control" | Name of the entity |
| `target_sensor` | **Yes** | - | Entity ID of the humidity sensor |
| `wet_entity` | No | - | Entity ID of the humidifier switch/input_boolean |
| `dry_entity` | No | - | Entity ID of the dehumidifier switch/input_boolean |
| `target_humidity` | No | - | Initial target humidity |
| `min_humidity` | No | 0 | Minimum settable humidity |
| `max_humidity` | No | 100 | Maximum settable humidity |
| `dry_tolerance` | No | 3 | How far below target before humidifying starts |
| `wet_tolerance` | No | 3 | How far above target before dehumidifying starts |
| `min_cycle_duration` | No | - | Minimum time between switching (e.g., `00:05:00`) |
| `keep_alive` | No | - | Interval to resend commands (e.g., `00:03:00`) |
| `initial_state` | No | false | Whether to start enabled |
| `away_humidity` | No | - | Target humidity when in away mode |
| `away_fixed` | No | false | If true, away humidity cannot be changed |
| `sensor_stale_duration` | No | - | Turn off if sensor doesn't update (e.g., `00:15:00`) |
| `unique_id` | No | - | Unique ID for the entity |

## Examples

### Basic Setup with Both Humidifier and Dehumidifier

```yaml
humidity_control:
  - name: "Bedroom Humidity"
    target_sensor: sensor.bedroom_humidity
    wet_entity: switch.bedroom_humidifier
    dry_entity: switch.bedroom_dehumidifier
    target_humidity: 50
    dry_tolerance: 5
    wet_tolerance: 5
    initial_state: true
```

### Humidifier Only

```yaml
humidity_control:
  - name: "Nursery Humidity"
    target_sensor: sensor.nursery_humidity
    wet_entity: switch.nursery_humidifier
    target_humidity: 55
    min_humidity: 40
    max_humidity: 60
```

### Dehumidifier Only (Basement)

```yaml
humidity_control:
  - name: "Basement Humidity"
    target_sensor: sensor.basement_humidity
    dry_entity: switch.basement_dehumidifier
    target_humidity: 50
    max_humidity: 60
```

### With Input Boolean Entities

```yaml
input_boolean:
  humidifier_control:
    name: Humidifier Control
  dehumidifier_control:
    name: Dehumidifier Control

humidity_control:
  - name: "Smart Humidity"
    target_sensor: sensor.room_humidity
    wet_entity: input_boolean.humidifier_control
    dry_entity: input_boolean.dehumidifier_control
    target_humidity: 50
```

### With Away Mode and Safety Features

```yaml
humidity_control:
  - name: "Home Humidity"
    target_sensor: sensor.home_humidity
    wet_entity: switch.whole_house_humidifier
    dry_entity: switch.whole_house_dehumidifier
    target_humidity: 50
    away_humidity: 40
    min_cycle_duration: "00:05:00"
    keep_alive: "00:10:00"
    sensor_stale_duration: "00:30:00"
    initial_state: true
```

## How It Works

1. The integration monitors the humidity sensor
2. When humidity drops below `target - dry_tolerance`:
   - Turns on the wet entity (humidifier)
   - Turns off the dry entity (if active)
   - Operating mode: `wet`
3. When humidity rises above `target + wet_tolerance`:
   - Turns on the dry entity (dehumidifier)
   - Turns off the wet entity (if active)
   - Operating mode: `dry`
4. When humidity is within tolerance range:
   - Turns off both entities
   - Operating mode: `idle`

## State Attributes

The entity exposes these attributes:

- `humidity`: Current target humidity
- `current_humidity`: Current measured humidity
- `operating_mode`: Current mode (`idle`, `wet`, or `dry`)
- `saved_humidity`: Saved humidity when in away mode
- `mode`: Current preset mode (`normal` or `away`)

## Services

The entity supports standard humidifier services:

- `humidifier.turn_on` - Enable humidity control
- `humidifier.turn_off` - Disable humidity control (turns off all outputs)
- `humidifier.toggle` - Toggle on/off
- `humidifier.set_humidity` - Set target humidity
- `humidifier.set_mode` - Set mode (`normal` or `away`)

## Troubleshooting

### Entity shows as unavailable
- Check that your humidity sensor is reporting values
- Verify the sensor entity ID is correct

### Devices not turning on/off
- Verify the switch/input_boolean entity IDs are correct
- Check that the entities can be controlled manually
- Review Home Assistant logs for errors

### Rapid cycling
- Increase `dry_tolerance` and `wet_tolerance` values
- Add `min_cycle_duration` to prevent rapid switching

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Acknowledgments

This integration is based on the excellent [Generic Hygrostat](https://www.home-assistant.io/integrations/generic_hygrostat/) integration from Home Assistant Core, maintained by [@Shulyaka](https://github.com/Shulyaka).
