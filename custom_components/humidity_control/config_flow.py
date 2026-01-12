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

from homeassistant.components.humidifier import HumidifierDeviceClass
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import CONF_NAME, PERCENTAGE
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
    SchemaOptionsFlowHandler,
)

from .const import (
    CONF_AWAY_FIXED,
    CONF_AWAY_HUMIDITY,
    CONF_DRY_ENTITY,
    CONF_DRY_TOLERANCE,
    CONF_INITIAL_STATE,
    CONF_KEEP_ALIVE,
    CONF_MAX_HUMIDITY,
    CONF_MIN_DUR,
    CONF_MIN_HUMIDITY,
    CONF_SENSOR,
    CONF_STALE_DURATION,
    CONF_TARGET_HUMIDITY,
    CONF_WET_ENTITY,
    CONF_WET_TOLERANCE,
    DEFAULT_NAME,
    DEFAULT_TOLERANCE,
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
        vol.Optional(CONF_WET_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["switch", "input_boolean"],
            )
        ),
        vol.Optional(CONF_DRY_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["switch", "input_boolean"],
            )
        ),
    }
)

# Schema for options (editable after setup)
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_WET_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["switch", "input_boolean"],
            )
        ),
        vol.Optional(CONF_DRY_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["switch", "input_boolean"],
            )
        ),
        vol.Required(
            CONF_DRY_TOLERANCE, default=DEFAULT_TOLERANCE
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=10,
                step=0.1,
                unit_of_measurement=PERCENTAGE,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_WET_TOLERANCE, default=DEFAULT_TOLERANCE
        ): selector.NumberSelector(
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

CONFIG_FLOW = {
    "user": SchemaFlowFormStep(CONFIG_SCHEMA, next_step="options"),
    "options": SchemaFlowFormStep(OPTIONS_SCHEMA),
}

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(OPTIONS_SCHEMA),
}


class HumidityControlConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Humidity Control."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options[CONF_NAME])
