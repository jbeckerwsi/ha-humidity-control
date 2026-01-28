"""Constants for Humidity Control integration.

This integration is derived from the Home Assistant Generic Hygrostat component.
Original source: https://github.com/home-assistant/core
Licensed under Apache License 2.0
"""

DOMAIN = "humidity_control"

# Configuration keys - Humidity
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

# Configuration keys - Multi-level humidifier
CONF_HUMIDIFIER_POWER_ENTITY = "humidifier_power_entity"
CONF_HUMIDIFIER_LEVEL_ENTITY = "humidifier_level_entity"
CONF_HUMIDIFIER_LEVELS = "humidifier_levels"

# Configuration keys - Air quality sensors
CONF_CO2_SENSOR = "co2_sensor"
CONF_CO2_TARGET = "co2_target"
CONF_CO2_CRITICAL = "co2_critical"
CONF_VOC_SENSOR = "voc_sensor"
CONF_VOC_TARGET = "voc_target"
CONF_VOC_CRITICAL = "voc_critical"

# Configuration keys - Ventilation
CONF_VENTILATION_ENTITY = "ventilation_entity"
CONF_VENTILATION_LEVELS = "ventilation_levels"
CONF_HUMIDITY_DEHUMIDIFY_THRESHOLD = "humidity_dehumidify_threshold"
CONF_HUMIDITY_DEHUMIDIFY_CRITICAL = "humidity_dehumidify_critical"

# Configuration keys - Timing
CONF_MIN_HUMIDIFY_DURATION = "min_humidify_duration"
CONF_MIN_VENTILATE_DURATION = "min_ventilate_duration"

# Configuration keys - Boost mode
CONF_BOOST_HELPER = "boost_helper"

# Default values
DEFAULT_TOLERANCE = 3.0
DEFAULT_NAME = "Humidity Control"
DEFAULT_CO2_TARGET = 600
DEFAULT_CO2_CRITICAL = 900
DEFAULT_VOC_TARGET = 100
DEFAULT_VOC_CRITICAL = 350
DEFAULT_HUMIDITY_DEHUMIDIFY_THRESHOLD = 48
DEFAULT_HUMIDITY_DEHUMIDIFY_CRITICAL = 55
DEFAULT_HUMIDIFIER_LEVELS = ["Auto", "Low", "Medium", "High"]
DEFAULT_VENTILATION_LEVELS = ["0", "1", "2", "3", "4"]
DEFAULT_MIN_HUMIDIFY_DURATION = 300  # 5 minutes in seconds
DEFAULT_MIN_VENTILATE_DURATION = 180  # 3 minutes in seconds
DEFAULT_BOOST_DURATION = 1200  # 20 minutes in seconds

# Modes
MODE_IDLE = "idle"
MODE_WET = "wet"
MODE_DRY = "dry"
MODE_AWAY = "away"
MODE_NORMAL = "normal"

# Operating modes (extended)
OP_MODE_IDLE = "idle"
OP_MODE_HUMIDIFYING = "humidifying"
OP_MODE_DEHUMIDIFYING = "dehumidifying"
OP_MODE_VENTILATING = "ventilating"
OP_MODE_VENTILATING_AND_HUMIDIFYING = "ventilating_and_humidifying"
OP_MODE_BOOST = "boost"

# Air quality status
AQ_STATUS_GOOD = "good"
AQ_STATUS_ELEVATED = "elevated"
AQ_STATUS_POOR = "poor"
AQ_STATUS_CRITICAL = "critical"

# Ventilation reasons
VENT_REASON_NONE = "none"
VENT_REASON_CO2 = "co2"
VENT_REASON_VOC = "voc"
VENT_REASON_HUMIDITY = "humidity"
VENT_REASON_BOOST = "boost"

# Attributes
ATTR_SAVED_HUMIDITY = "saved_humidity"
ATTR_OPERATING_MODE = "operating_mode"
ATTR_CURRENT_CO2 = "current_co2"
ATTR_CURRENT_VOC = "current_voc"
ATTR_AIR_QUALITY_STATUS = "air_quality_status"
ATTR_VENTILATION_LEVEL = "ventilation_level"
ATTR_VENTILATION_REASON = "ventilation_reason"
ATTR_HUMIDIFIER_LEVEL = "humidifier_level"
ATTR_HUMIDIFIER_POWER = "humidifier_power"
ATTR_BOOST_ACTIVE = "boost_active"
ATTR_BOOST_END_TIME = "boost_end_time"
ATTR_BOOST_LEVEL = "boost_level"
ATTR_HUMIDITY_ACTION = "humidity_action"
ATTR_CO2_ACTION = "co2_action"
ATTR_VOC_ACTION = "voc_action"

# Services
SERVICE_BOOST = "boost"
SERVICE_STOP_BOOST = "stop_boost"
