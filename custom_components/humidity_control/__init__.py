"""The Humidity Control component.

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

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.typing import ConfigType

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
    DEFAULT_MIN_HUMIDIFY_DURATION,
    DEFAULT_MIN_VENTILATE_DURATION,
    DEFAULT_NAME,
    DEFAULT_TOLERANCE,
    DEFAULT_VENTILATION_LEVELS,
    DEFAULT_VOC_CRITICAL,
    DEFAULT_VOC_TARGET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.HUMIDIFIER]

HUMIDITY_CONTROL_SCHEMA = vol.Schema(
    {
        # Required - Humidity sensor
        vol.Required(CONF_SENSOR): cv.entity_id,
        # Multi-level humidifier (Robby)
        vol.Optional(CONF_HUMIDIFIER_POWER_ENTITY): cv.entity_id,
        vol.Optional(CONF_HUMIDIFIER_LEVEL_ENTITY): cv.entity_id,
        vol.Optional(CONF_HUMIDIFIER_LEVELS, default=DEFAULT_HUMIDIFIER_LEVELS): vol.All(
            cv.ensure_list, [cv.string]
        ),
        # Air quality sensors
        vol.Optional(CONF_CO2_SENSOR): cv.entity_id,
        vol.Optional(CONF_CO2_TARGET, default=DEFAULT_CO2_TARGET): vol.Coerce(int),
        vol.Optional(CONF_CO2_CRITICAL, default=DEFAULT_CO2_CRITICAL): vol.Coerce(int),
        vol.Optional(CONF_VOC_SENSOR): cv.entity_id,
        vol.Optional(CONF_VOC_TARGET, default=DEFAULT_VOC_TARGET): vol.Coerce(int),
        vol.Optional(CONF_VOC_CRITICAL, default=DEFAULT_VOC_CRITICAL): vol.Coerce(int),
        # Ventilation control (Nilan)
        vol.Optional(CONF_VENTILATION_ENTITY): cv.entity_id,
        vol.Optional(CONF_VENTILATION_LEVELS, default=DEFAULT_VENTILATION_LEVELS): vol.All(
            cv.ensure_list, [cv.string]
        ),
        vol.Optional(
            CONF_HUMIDITY_DEHUMIDIFY_CRITICAL,
            default=DEFAULT_HUMIDITY_DEHUMIDIFY_CRITICAL,
        ): vol.Coerce(float),
        # Humidity settings
        vol.Optional(CONF_MAX_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_MIN_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_TARGET_HUMIDITY): vol.Coerce(float),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DRY_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_WET_TOLERANCE, default=DEFAULT_TOLERANCE): vol.Coerce(float),
        vol.Optional(CONF_KEEP_ALIVE): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_INITIAL_STATE): cv.boolean,
        vol.Optional(CONF_AWAY_HUMIDITY): vol.Coerce(int),
        vol.Optional(CONF_AWAY_FIXED): cv.boolean,
        vol.Optional(CONF_MIN_DUR): vol.All(cv.time_period, cv.positive_timedelta),
        vol.Optional(CONF_STALE_DURATION): vol.All(cv.time_period, cv.positive_timedelta),
        # Timing for new features
        vol.Optional(CONF_MIN_HUMIDIFY_DURATION, default=DEFAULT_MIN_HUMIDIFY_DURATION): vol.Coerce(
            int
        ),
        vol.Optional(
            CONF_MIN_VENTILATE_DURATION, default=DEFAULT_MIN_VENTILATE_DURATION
        ): vol.Coerce(int),
        # Boost mode
        vol.Optional(CONF_BOOST_HELPER): cv.entity_id,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [HUMIDITY_CONTROL_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Humidity Control component."""
    if DOMAIN not in config:
        return True

    for humidity_control_conf in config[DOMAIN]:
        hass.async_create_task(
            discovery.async_load_platform(
                hass, Platform.HUMIDIFIER, DOMAIN, humidity_control_conf, config
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Humidity Control from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
