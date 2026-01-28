"""Config flow for Humidity Control.

This integration is a derivative work based on the Generic Hygrostat component
from Home Assistant Core.

Original work:
  Home Assistant Core - Generic Hygrostat Integration
  Copyright Home Assistant Contributors
  Licensed under the Apache License, Version 2.0
  https://github.com/home-assistant/core

See NOTICE file for details on changes made.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_NAME, PERCENTAGE
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
)

from .const import (
    CONF_AWAY_FIXED,
    CONF_AWAY_HUMIDITY,
    CONF_BOOST_HELPER,
    CONF_CO2_CRITICAL,
    CONF_CO2_SENSOR,
    CONF_CO2_TARGET,
    CONF_DRY_TOLERANCE,
    CONF_HUMIDIFIER_LEVEL_ENTITY,
    CONF_HUMIDIFIER_LEVELS,
    CONF_HUMIDIFIER_POWER_ENTITY,
    CONF_HUMIDITY_DEHUMIDIFY_CRITICAL,
    CONF_HUMIDITY_DEHUMIDIFY_THRESHOLD,
    CONF_INITIAL_STATE,
    CONF_KEEP_ALIVE,
    CONF_MAX_HUMIDITY,
    CONF_MIN_DUR,
    CONF_MIN_HUMIDIFY_DURATION,
    CONF_MIN_HUMIDITY,
    CONF_MIN_VENTILATE_DURATION,
    CONF_SENSOR,
    CONF_STALE_DURATION,
    CONF_TARGET_HUMIDITY,
    CONF_VENTILATION_ENTITY,
    CONF_VENTILATION_LEVELS,
    CONF_VOC_CRITICAL,
    CONF_VOC_SENSOR,
    CONF_VOC_TARGET,
    CONF_WET_TOLERANCE,
    DEFAULT_CO2_CRITICAL,
    DEFAULT_CO2_TARGET,
    DEFAULT_HUMIDIFIER_LEVELS,
    DEFAULT_HUMIDITY_DEHUMIDIFY_CRITICAL,
    DEFAULT_HUMIDITY_DEHUMIDIFY_THRESHOLD,
    DEFAULT_MIN_HUMIDIFY_DURATION,
    DEFAULT_MIN_VENTILATE_DURATION,
    DEFAULT_NAME,
    DEFAULT_TOLERANCE,
    DEFAULT_VENTILATION_LEVELS,
    DEFAULT_VOC_CRITICAL,
    DEFAULT_VOC_TARGET,
    DOMAIN,
)

# Schema for basic configuration (required fields)
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(),
        vol.Required(CONF_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=SENSOR_DOMAIN,
                device_class=SensorDeviceClass.HUMIDITY,
            )
        ),
    }
)

# Schema for multi-level humidifier (Robby)
HUMIDIFIER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HUMIDIFIER_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["switch"],
            )
        ),
        vol.Optional(CONF_HUMIDIFIER_LEVEL_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["select", "input_select"],
            )
        ),
        vol.Optional(
            CONF_HUMIDIFIER_LEVELS, default=DEFAULT_HUMIDIFIER_LEVELS
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEFAULT_HUMIDIFIER_LEVELS,
                multiple=True,
                custom_value=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        ),
    }
)

# Schema for air quality sensors (CO2/VOC)
AIR_QUALITY_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CO2_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=SENSOR_DOMAIN,
                device_class=SensorDeviceClass.CO2,
            )
        ),
        vol.Optional(CONF_CO2_TARGET, default=DEFAULT_CO2_TARGET): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=400,
                max=2000,
                step=50,
                unit_of_measurement="ppm",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_CO2_CRITICAL, default=DEFAULT_CO2_CRITICAL): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=600,
                max=3000,
                step=50,
                unit_of_measurement="ppm",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_VOC_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=SENSOR_DOMAIN,
                device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            )
        ),
        vol.Optional(CONF_VOC_TARGET, default=DEFAULT_VOC_TARGET): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=1000,
                step=10,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_VOC_CRITICAL, default=DEFAULT_VOC_CRITICAL): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=100,
                max=2000,
                step=10,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }
)

# Schema for ventilation control (Nilan)
VENTILATION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_VENTILATION_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["climate", "fan"],
            )
        ),
        vol.Optional(
            CONF_VENTILATION_LEVELS, default=DEFAULT_VENTILATION_LEVELS
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEFAULT_VENTILATION_LEVELS,
                multiple=True,
                custom_value=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        ),
        vol.Optional(
            CONF_HUMIDITY_DEHUMIDIFY_THRESHOLD,
            default=DEFAULT_HUMIDITY_DEHUMIDIFY_THRESHOLD,
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=30,
                max=70,
                step=1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(
            CONF_HUMIDITY_DEHUMIDIFY_CRITICAL,
            default=DEFAULT_HUMIDITY_DEHUMIDIFY_CRITICAL,
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=40,
                max=80,
                step=1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }
)

# Schema for options (editable after setup)
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DRY_TOLERANCE, default=DEFAULT_TOLERANCE): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=10,
                step=0.1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(CONF_WET_TOLERANCE, default=DEFAULT_TOLERANCE): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=10,
                step=0.1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_MIN_HUMIDITY): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_MAX_HUMIDITY): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_TARGET_HUMIDITY): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_MIN_DUR): selector.DurationSelector(
            selector.DurationSelectorConfig(enable_day=False)
        ),
        vol.Optional(CONF_KEEP_ALIVE): selector.DurationSelector(
            selector.DurationSelectorConfig(enable_day=False)
        ),
        vol.Optional(CONF_STALE_DURATION): selector.DurationSelector(
            selector.DurationSelectorConfig(enable_day=False)
        ),
        vol.Optional(CONF_INITIAL_STATE): selector.BooleanSelector(),
        vol.Optional(CONF_AWAY_HUMIDITY): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_AWAY_FIXED): selector.BooleanSelector(),
    }
)

# Schema for timing and boost options
TIMING_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_MIN_HUMIDIFY_DURATION, default=DEFAULT_MIN_HUMIDIFY_DURATION
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=1800,
                step=60,
                unit_of_measurement="seconds",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(
            CONF_MIN_VENTILATE_DURATION, default=DEFAULT_MIN_VENTILATE_DURATION
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=1800,
                step=60,
                unit_of_measurement="seconds",
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(CONF_BOOST_HELPER): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["input_boolean"],
            )
        ),
    }
)

CONFIG_FLOW = {
    "user": SchemaFlowFormStep(CONFIG_SCHEMA, next_step="humidifier"),
    "humidifier": SchemaFlowFormStep(HUMIDIFIER_SCHEMA, next_step="air_quality"),
    "air_quality": SchemaFlowFormStep(AIR_QUALITY_SCHEMA, next_step="ventilation"),
    "ventilation": SchemaFlowFormStep(VENTILATION_SCHEMA, next_step="options"),
    "options": SchemaFlowFormStep(OPTIONS_SCHEMA, next_step="timing"),
    "timing": SchemaFlowFormStep(TIMING_SCHEMA),
}

OPTIONS_FLOW = {
    "init": SchemaFlowMenuStep(["humidity", "humidifier", "air_quality", "ventilation", "timing"]),
    "humidity": SchemaFlowFormStep(OPTIONS_SCHEMA),
    "humidifier": SchemaFlowFormStep(HUMIDIFIER_SCHEMA),
    "air_quality": SchemaFlowFormStep(AIR_QUALITY_SCHEMA),
    "ventilation": SchemaFlowFormStep(VENTILATION_SCHEMA),
    "timing": SchemaFlowFormStep(TIMING_SCHEMA),
}


class HumidityControlConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Humidity Control."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options[CONF_NAME])
