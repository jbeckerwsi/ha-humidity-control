"""Constants for Humidity Control integration.

This integration is derived from the Home Assistant Generic Hygrostat component.
Original source: https://github.com/home-assistant/core
Licensed under Apache License 2.0
"""

DOMAIN = "humidity_control"

# Configuration keys
CONF_SENSOR = "target_sensor"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_MAX_HUMIDITY = "max_humidity"
CONF_TARGET_HUMIDITY = "target_humidity"
CONF_DRY_TOLERANCE = "dry_tolerance"
CONF_WET_TOLERANCE = "wet_tolerance"
CONF_KEEP_ALIVE = "keep_alive"
CONF_INITIAL_STATE = "initial_state"
CONF_AWAY_HUMIDITY = "away_humidity"
CONF_AWAY_FIXED = "away_fixed"
CONF_STALE_DURATION = "sensor_stale_duration"
CONF_MIN_DUR = "min_cycle_duration"

# Output entity configuration
CONF_WET_ENTITY = "wet_entity"
CONF_DRY_ENTITY = "dry_entity"

# Default values
DEFAULT_TOLERANCE = 3.0
DEFAULT_NAME = "Humidity Control"

# Modes
MODE_IDLE = "idle"
MODE_WET = "wet"
MODE_DRY = "dry"
MODE_AWAY = "away"
MODE_NORMAL = "normal"

# Attributes
ATTR_SAVED_HUMIDITY = "saved_humidity"
ATTR_OPERATING_MODE = "operating_mode"
