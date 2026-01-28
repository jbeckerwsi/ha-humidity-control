"""Humidity Control - Unified Air Quality Controller.

This integration is a derivative work based on the Generic Hygrostat component
from Home Assistant Core.

Original work:
  Home Assistant Core - Generic Hygrostat Integration
  Copyright Home Assistant Contributors
  Licensed under the Apache License, Version 2.0
  https://github.com/home-assistant/core

See NOTICE file for details on changes made.

Extended features:
- Multi-level humidifier control (power + fan level)
- CO2 and VOC air quality monitoring
- Ventilation control with proportional fan speed
- Boost mode for rapid air exchange
- Conflict resolution between humidity and air quality needs
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any, cast

import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant.components.humidifier import (
    ATTR_HUMIDITY,
    HumidifierAction,
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.components.humidifier import (
    PLATFORM_SCHEMA as HUMIDIFIER_PLATFORM_SCHEMA,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_MODE,
    CONF_NAME,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_START,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    DOMAIN as HOMEASSISTANT_DOMAIN,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    EventStateReportedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_state_report_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import HUMIDITY_CONTROL_SCHEMA
from .const import (
    AQ_STATUS_CRITICAL,
    AQ_STATUS_ELEVATED,
    AQ_STATUS_GOOD,
    AQ_STATUS_POOR,
    ATTR_AIR_QUALITY_STATUS,
    ATTR_BOOST_ACTIVE,
    ATTR_BOOST_END_TIME,
    ATTR_BOOST_LEVEL,
    ATTR_CO2_ACTION,
    ATTR_CURRENT_CO2,
    ATTR_CURRENT_VOC,
    ATTR_HUMIDIFIER_LEVEL,
    ATTR_HUMIDIFIER_POWER,
    ATTR_HUMIDITY_ACTION,
    ATTR_OPERATING_MODE,
    ATTR_SAVED_HUMIDITY,
    ATTR_VENTILATION_LEVEL,
    ATTR_VENTILATION_REASON,
    ATTR_VOC_ACTION,
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
    DEFAULT_BOOST_DURATION,
    DEFAULT_CO2_CRITICAL,
    DEFAULT_CO2_TARGET,
    DEFAULT_HUMIDIFIER_LEVELS,
    DEFAULT_HUMIDITY_DEHUMIDIFY_CRITICAL,
    DEFAULT_HUMIDITY_DEHUMIDIFY_THRESHOLD,
    DEFAULT_MIN_HUMIDIFY_DURATION,
    DEFAULT_MIN_VENTILATE_DURATION,
    DEFAULT_VENTILATION_LEVELS,
    DEFAULT_VOC_CRITICAL,
    DEFAULT_VOC_TARGET,
    MODE_AWAY,
    MODE_DRY,
    MODE_IDLE,
    MODE_NORMAL,
    MODE_WET,
    OP_MODE_BOOST,
    OP_MODE_DEHUMIDIFYING,
    OP_MODE_HUMIDIFYING,
    OP_MODE_IDLE,
    OP_MODE_VENTILATING,
    OP_MODE_VENTILATING_AND_HUMIDIFYING,
    SERVICE_BOOST,
    SERVICE_STOP_BOOST,
    VENT_REASON_BOOST,
    VENT_REASON_CO2,
    VENT_REASON_HUMIDITY,
    VENT_REASON_NONE,
    VENT_REASON_VOC,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = HUMIDIFIER_PLATFORM_SCHEMA.extend(HUMIDITY_CONTROL_SCHEMA.schema)

# Service schemas
ATTR_DURATION = "duration"

SERVICE_BOOST_SCHEMA = {
    vol.Optional(ATTR_DURATION, default=DEFAULT_BOOST_DURATION): vol.All(
        vol.Coerce(int), vol.Range(min=60, max=3600)
    ),
}


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the humidity control platform."""
    if discovery_info:
        config = discovery_info
    await _async_setup_config(hass, config, config.get(CONF_UNIQUE_ID), async_add_entities)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize config entry."""
    await _async_setup_config(
        hass,
        config_entry.options | config_entry.data,
        config_entry.entry_id,
        async_add_entities,
    )

    # Register entity services
    platform = async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_BOOST,
        SERVICE_BOOST_SCHEMA,
        "async_activate_boost",
    )

    platform.async_register_entity_service(
        SERVICE_STOP_BOOST,
        {},
        "async_deactivate_boost",
    )


def _time_period_or_none(value: Any) -> timedelta | None:
    if value is None:
        return None
    return cast(timedelta, cv.time_period(value))


async def _async_setup_config(
    hass: HomeAssistant,
    config: Mapping[str, Any],
    unique_id: str | None,
    async_add_entities: AddEntitiesCallback | AddConfigEntryEntitiesCallback,
) -> None:
    name: str = config[CONF_NAME]
    sensor_entity_id: str = config[CONF_SENSOR]
    min_humidity: float | None = config.get(CONF_MIN_HUMIDITY)
    max_humidity: float | None = config.get(CONF_MAX_HUMIDITY)
    target_humidity: float | None = config.get(CONF_TARGET_HUMIDITY)
    min_cycle_duration: timedelta | None = _time_period_or_none(config.get(CONF_MIN_DUR))
    sensor_stale_duration: timedelta | None = _time_period_or_none(config.get(CONF_STALE_DURATION))
    dry_tolerance: float = config.get(CONF_DRY_TOLERANCE, 3.0)
    wet_tolerance: float = config.get(CONF_WET_TOLERANCE, 3.0)
    keep_alive: timedelta | None = _time_period_or_none(config.get(CONF_KEEP_ALIVE))
    initial_state: bool | None = config.get(CONF_INITIAL_STATE)
    away_humidity: int | None = config.get(CONF_AWAY_HUMIDITY)
    away_fixed: bool | None = config.get(CONF_AWAY_FIXED)

    # New multi-level humidifier config
    humidifier_power_entity: str | None = config.get(CONF_HUMIDIFIER_POWER_ENTITY)
    humidifier_level_entity: str | None = config.get(CONF_HUMIDIFIER_LEVEL_ENTITY)
    humidifier_levels: list[str] = config.get(CONF_HUMIDIFIER_LEVELS, DEFAULT_HUMIDIFIER_LEVELS)

    # Air quality sensors
    co2_sensor: str | None = config.get(CONF_CO2_SENSOR)
    co2_target: int = config.get(CONF_CO2_TARGET, DEFAULT_CO2_TARGET)
    co2_critical: int = config.get(CONF_CO2_CRITICAL, DEFAULT_CO2_CRITICAL)
    voc_sensor: str | None = config.get(CONF_VOC_SENSOR)
    voc_target: int = config.get(CONF_VOC_TARGET, DEFAULT_VOC_TARGET)
    voc_critical: int = config.get(CONF_VOC_CRITICAL, DEFAULT_VOC_CRITICAL)

    # Ventilation config
    ventilation_entity: str | None = config.get(CONF_VENTILATION_ENTITY)
    ventilation_levels: list[str] = config.get(CONF_VENTILATION_LEVELS, DEFAULT_VENTILATION_LEVELS)
    humidity_dehumidify_threshold: float = config.get(
        CONF_HUMIDITY_DEHUMIDIFY_THRESHOLD, DEFAULT_HUMIDITY_DEHUMIDIFY_THRESHOLD
    )
    humidity_dehumidify_critical: float = config.get(
        CONF_HUMIDITY_DEHUMIDIFY_CRITICAL, DEFAULT_HUMIDITY_DEHUMIDIFY_CRITICAL
    )

    # Timing
    min_humidify_duration: int = config.get(
        CONF_MIN_HUMIDIFY_DURATION, DEFAULT_MIN_HUMIDIFY_DURATION
    )
    min_ventilate_duration: int = config.get(
        CONF_MIN_VENTILATE_DURATION, DEFAULT_MIN_VENTILATE_DURATION
    )

    # Boost helper
    boost_helper: str | None = config.get(CONF_BOOST_HELPER)

    async_add_entities(
        [
            HumidityControl(
                hass,
                name=name,
                sensor_entity_id=sensor_entity_id,
                min_humidity=min_humidity,
                max_humidity=max_humidity,
                target_humidity=target_humidity,
                min_cycle_duration=min_cycle_duration,
                dry_tolerance=dry_tolerance,
                wet_tolerance=wet_tolerance,
                keep_alive=keep_alive,
                initial_state=initial_state,
                away_humidity=away_humidity,
                away_fixed=away_fixed,
                sensor_stale_duration=sensor_stale_duration,
                unique_id=unique_id,
                # New parameters
                humidifier_power_entity=humidifier_power_entity,
                humidifier_level_entity=humidifier_level_entity,
                humidifier_levels=humidifier_levels,
                co2_sensor=co2_sensor,
                co2_target=co2_target,
                co2_critical=co2_critical,
                voc_sensor=voc_sensor,
                voc_target=voc_target,
                voc_critical=voc_critical,
                ventilation_entity=ventilation_entity,
                ventilation_levels=ventilation_levels,
                humidity_dehumidify_threshold=humidity_dehumidify_threshold,
                humidity_dehumidify_critical=humidity_dehumidify_critical,
                min_humidify_duration=min_humidify_duration,
                min_ventilate_duration=min_ventilate_duration,
                boost_helper=boost_helper,
            )
        ]
    )


class HumidityControl(HumidifierEntity, RestoreEntity):
    """Representation of a Unified Air Quality Controller."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        name: str,
        sensor_entity_id: str,
        min_humidity: float | None,
        max_humidity: float | None,
        target_humidity: float | None,
        min_cycle_duration: timedelta | None,
        dry_tolerance: float,
        wet_tolerance: float,
        keep_alive: timedelta | None,
        initial_state: bool | None,
        away_humidity: int | None,
        away_fixed: bool | None,
        sensor_stale_duration: timedelta | None,
        unique_id: str | None,
        # New parameters
        humidifier_power_entity: str | None,
        humidifier_level_entity: str | None,
        humidifier_levels: list[str],
        co2_sensor: str | None,
        co2_target: int,
        co2_critical: int,
        voc_sensor: str | None,
        voc_target: int,
        voc_critical: int,
        ventilation_entity: str | None,
        ventilation_levels: list[str],
        humidity_dehumidify_threshold: float,
        humidity_dehumidify_critical: float,
        min_humidify_duration: int,
        min_ventilate_duration: int,
        boost_helper: str | None,
    ) -> None:
        """Initialize the humidity control."""
        self._name = name
        self._sensor_entity_id = sensor_entity_id
        self._device_class = HumidifierDeviceClass.HUMIDIFIER
        self._min_cycle_duration = min_cycle_duration
        self._dry_tolerance = dry_tolerance
        self._wet_tolerance = wet_tolerance
        self._keep_alive = keep_alive
        self._state = initial_state
        self._saved_target_humidity = away_humidity or target_humidity
        self._active = False
        self._cur_humidity: float | None = None
        self._humidity_lock = asyncio.Lock()
        self._min_humidity = min_humidity
        self._max_humidity = max_humidity
        self._target_humidity = target_humidity

        # Always support modes: idle, wet, dry (and away if configured)
        self._attr_supported_features = HumidifierEntityFeature.MODES

        self._away_humidity = away_humidity
        self._away_fixed = away_fixed
        self._sensor_stale_duration = sensor_stale_duration
        self._remove_stale_tracking: Callable[[], None] | None = None
        self._is_away = False
        self._attr_action = HumidifierAction.IDLE
        self._attr_unique_id = unique_id

        # Track operating mode: idle, wet, or dry (legacy)
        self._operating_mode = MODE_IDLE

        # New: Multi-level humidifier (Robby)
        self._humidifier_power_entity = humidifier_power_entity
        self._humidifier_level_entity = humidifier_level_entity
        self._humidifier_levels = humidifier_levels
        self._current_humidifier_level: str | None = None

        # New: Air quality sensors
        self._co2_sensor = co2_sensor
        self._co2_target = co2_target
        self._co2_critical = co2_critical
        self._voc_sensor = voc_sensor
        self._voc_target = voc_target
        self._voc_critical = voc_critical
        self._cur_co2: float | None = None
        self._cur_voc: float | None = None

        # New: Ventilation control (Nilan)
        self._ventilation_entity = ventilation_entity
        self._ventilation_levels = ventilation_levels
        self._humidity_dehumidify_threshold = humidity_dehumidify_threshold
        self._humidity_dehumidify_critical = humidity_dehumidify_critical
        self._current_ventilation_level: int = 0
        self._ventilation_reason: str = VENT_REASON_NONE

        # New: Timing
        self._min_humidify_duration = timedelta(seconds=min_humidify_duration)
        self._min_ventilate_duration = timedelta(seconds=min_ventilate_duration)
        self._last_humidifier_change: datetime | None = None
        self._last_ventilation_change: datetime | None = None

        # New: Boost mode
        self._boost_helper = boost_helper
        self._boost_active = False
        self._boost_end_time: datetime | None = None
        self._boost_level: int = 4  # Max level during boost
        self._remove_boost_timer: Callable[[], None] | None = None

        # New: Extended operating mode
        self._extended_operating_mode = OP_MODE_IDLE
        self._air_quality_status = AQ_STATUS_GOOD

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Track humidity sensor
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._sensor_entity_id, self._async_sensor_event
            )
        )
        self.async_on_remove(
            async_track_state_report_event(
                self.hass, self._sensor_entity_id, self._async_sensor_event
            )
        )

        # Track CO2 sensor
        if self._co2_sensor:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._co2_sensor, self._async_co2_sensor_event
                )
            )

        # Track VOC sensor
        if self._voc_sensor:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._voc_sensor, self._async_voc_sensor_event
                )
            )

        # Track boost helper input_boolean
        if self._boost_helper:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._boost_helper, self._async_boost_helper_event
                )
            )

        if self._keep_alive:
            self.async_on_remove(
                async_track_time_interval(self.hass, self._async_operate, self._keep_alive)
            )

        async def _async_startup(event: Event | None) -> None:
            """Init on startup."""
            sensor_state = self.hass.states.get(self._sensor_entity_id)
            if sensor_state is None or sensor_state.state in (
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ):
                _LOGGER.debug(
                    "The sensor state is %s, initialization is delayed",
                    sensor_state.state if sensor_state is not None else "None",
                )
                return

            await self._async_sensor_update(sensor_state)

            # Also initialize CO2 and VOC readings
            if self._co2_sensor:
                co2_state = self.hass.states.get(self._co2_sensor)
                if co2_state and co2_state.state not in (
                    STATE_UNKNOWN,
                    STATE_UNAVAILABLE,
                ):
                    await self._async_update_co2(co2_state.state)

            if self._voc_sensor:
                voc_state = self.hass.states.get(self._voc_sensor)
                if voc_state and voc_state.state not in (
                    STATE_UNKNOWN,
                    STATE_UNAVAILABLE,
                ):
                    await self._async_update_voc(voc_state.state)

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

        if (old_state := await self.async_get_last_state()) is not None:
            if old_state.attributes.get(ATTR_MODE) == MODE_AWAY:
                self._is_away = True
                self._saved_target_humidity = self._target_humidity
                self._target_humidity = self._away_humidity or self._target_humidity
            if old_state.attributes.get(ATTR_HUMIDITY):
                self._target_humidity = int(old_state.attributes[ATTR_HUMIDITY])
            if old_state.attributes.get(ATTR_SAVED_HUMIDITY):
                self._saved_target_humidity = int(old_state.attributes[ATTR_SAVED_HUMIDITY])
            if old_state.attributes.get(ATTR_OPERATING_MODE):
                self._extended_operating_mode = old_state.attributes[ATTR_OPERATING_MODE]
            if old_state.state:
                self._state = old_state.state == STATE_ON
        if self._target_humidity is None:
            self._target_humidity = self.min_humidity
            _LOGGER.warning("No previously saved humidity, setting to %s", self._target_humidity)
        if self._state is None:
            self._state = False

        await _async_startup(None)  # init the sensor

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        if self._remove_stale_tracking:
            self._remove_stale_tracking()
        if self._remove_boost_timer:
            self._remove_boost_timer()
        return await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._active

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the optional state attributes."""
        attrs: dict[str, Any] = {
            ATTR_OPERATING_MODE: self._extended_operating_mode,
            ATTR_AIR_QUALITY_STATUS: self._air_quality_status,
        }

        if self._saved_target_humidity:
            attrs[ATTR_SAVED_HUMIDITY] = self._saved_target_humidity

        # Air quality readings
        if self._cur_co2 is not None:
            attrs[ATTR_CURRENT_CO2] = self._cur_co2
        if self._cur_voc is not None:
            attrs[ATTR_CURRENT_VOC] = self._cur_voc

        # Ventilation state
        if self._ventilation_entity:
            attrs[ATTR_VENTILATION_LEVEL] = self._current_ventilation_level
            attrs[ATTR_VENTILATION_REASON] = self._ventilation_reason

        # Humidifier state (multi-level)
        if self._humidifier_power_entity:
            attrs[ATTR_HUMIDIFIER_POWER] = self._is_humidifier_power_on
            attrs[ATTR_HUMIDIFIER_LEVEL] = self._current_humidifier_level

        # Boost state
        attrs[ATTR_BOOST_ACTIVE] = self._boost_active
        if self._boost_active and self._boost_end_time:
            attrs[ATTR_BOOST_END_TIME] = self._boost_end_time.isoformat()
            attrs[ATTR_BOOST_LEVEL] = self._boost_level

        # Action breakdown
        attrs[ATTR_HUMIDITY_ACTION] = self._get_humidity_action()
        attrs[ATTR_CO2_ACTION] = self._get_co2_action()
        attrs[ATTR_VOC_ACTION] = self._get_voc_action()

        return attrs

    def _get_humidity_action(self) -> str:
        """Get the current humidity action."""
        if self._extended_operating_mode in (
            OP_MODE_HUMIDIFYING,
            OP_MODE_VENTILATING_AND_HUMIDIFYING,
        ):
            return "humidifying"
        elif self._extended_operating_mode == OP_MODE_DEHUMIDIFYING:
            return "dehumidifying"
        return "idle"

    def _get_co2_action(self) -> str:
        """Get the current CO2 action level."""
        if self._cur_co2 is None:
            return "unknown"
        if self._cur_co2 >= self._co2_critical:
            return "critical"
        if self._cur_co2 >= self._co2_target:
            return "ventilating"
        return "good"

    def _get_voc_action(self) -> str:
        """Get the current VOC action level."""
        if self._cur_voc is None:
            return "unknown"
        if self._cur_voc >= self._voc_critical:
            return "critical"
        if self._cur_voc >= self._voc_target:
            return "ventilating"
        return "good"

    @property
    def name(self) -> str:
        """Return the name of the humidity control."""
        return self._name

    @property
    def is_on(self) -> bool | None:
        """Return true if the humidity control is on."""
        return self._state

    @property
    def current_humidity(self) -> float | None:
        """Return the measured humidity."""
        return self._cur_humidity

    @property
    def target_humidity(self) -> float | None:
        """Return the humidity we try to reach."""
        return self._target_humidity

    @property
    def mode(self) -> str | None:
        """Return the current mode."""
        if self._is_away:
            return MODE_AWAY
        return MODE_NORMAL

    @property
    def available_modes(self) -> list[str] | None:
        """Return a list of available modes."""
        modes = [MODE_NORMAL]
        if self._away_humidity is not None:
            modes.append(MODE_AWAY)
        return modes

    @property
    def device_class(self) -> HumidifierDeviceClass:
        """Return the device class of the humidity control."""
        return self._device_class

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn humidity control on."""
        if not self._active:
            return
        self._state = True
        await self._async_operate(force=True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn humidity control off."""
        if not self._active:
            return
        self._state = False
        await self._async_turn_off_all()
        self._extended_operating_mode = OP_MODE_IDLE
        self._attr_action = HumidifierAction.IDLE
        self.async_write_ha_state()

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        if humidity is None:
            return  # type: ignore[unreachable]

        if self._is_away and self._away_fixed:
            self._saved_target_humidity = humidity
            self.async_write_ha_state()
            return

        self._target_humidity = humidity
        await self._async_operate()
        self.async_write_ha_state()

    @property
    def min_humidity(self) -> float:
        """Return the minimum humidity."""
        if self._min_humidity:
            return self._min_humidity
        return super().min_humidity

    @property
    def max_humidity(self) -> float:
        """Return the maximum humidity."""
        if self._max_humidity:
            return self._max_humidity
        return super().max_humidity

    # =========================================================================
    # Sensor Event Handlers
    # =========================================================================

    async def _async_sensor_event(
        self, event: Event[EventStateChangedData] | Event[EventStateReportedData]
    ) -> None:
        """Handle ambient humidity changes."""
        new_state = event.data["new_state"]
        if new_state is None:
            return
        await self._async_sensor_update(new_state)

    async def _async_sensor_update(self, new_state: State) -> None:
        """Update state based on humidity sensor."""
        if self._sensor_stale_duration:
            if self._remove_stale_tracking:
                self._remove_stale_tracking()

            self._remove_stale_tracking = async_track_time_interval(
                self.hass,
                self._async_sensor_not_responding,
                self._sensor_stale_duration,
            )

        await self._async_update_humidity(new_state.state)
        await self._async_operate()
        self.async_write_ha_state()

    async def _async_co2_sensor_event(self, event: Event[EventStateChangedData]) -> None:
        """Handle CO2 sensor changes."""
        new_state = event.data["new_state"]
        if new_state is None or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        await self._async_update_co2(new_state.state)
        await self._async_operate()
        self.async_write_ha_state()

    async def _async_voc_sensor_event(self, event: Event[EventStateChangedData]) -> None:
        """Handle VOC sensor changes."""
        new_state = event.data["new_state"]
        if new_state is None or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        await self._async_update_voc(new_state.state)
        await self._async_operate()
        self.async_write_ha_state()

    async def _async_boost_helper_event(self, event: Event[EventStateChangedData]) -> None:
        """Handle boost helper input_boolean changes."""
        new_state = event.data["new_state"]
        if new_state is None:
            return

        if new_state.state == STATE_ON and not self._boost_active:
            # Boost was turned on via helper
            await self.async_activate_boost(DEFAULT_BOOST_DURATION)
        elif new_state.state == STATE_OFF and self._boost_active:
            # Boost was turned off via helper
            await self.async_deactivate_boost()

    async def _async_sensor_not_responding(self, now: datetime | None = None) -> None:
        """Handle sensor stale event."""
        state = self.hass.states.get(self._sensor_entity_id)
        _LOGGER.debug(
            "Sensor has not been updated for %s",
            now - state.last_reported if now and state else "---",
        )
        _LOGGER.warning("Sensor is stalled, call the emergency stop")
        await self._async_update_humidity("Stalled")

    @callback
    def _async_output_event(self, event: Event[EventStateChangedData]) -> None:
        """Handle output entity state changes."""
        self._async_output_changed(event.data["new_state"])

    @callback
    def _async_output_changed(self, new_state: State | None) -> None:
        """Handle output entity state changes."""
        if new_state is None:
            return

        # Update operating mode based on output states
        self._update_operating_mode_from_outputs()
        self.async_write_ha_state()

    def _update_operating_mode_from_outputs(self) -> None:
        """Update operating mode based on current output states."""
        # This is called when legacy wet/dry entities change state
        wet_active = self._is_wet_active
        dry_active = self._is_dry_active

        if wet_active and not dry_active:
            self._operating_mode = MODE_WET
            self._attr_action = HumidifierAction.HUMIDIFYING
        elif dry_active and not wet_active:
            self._operating_mode = MODE_DRY
            self._attr_action = HumidifierAction.DRYING
        else:
            self._operating_mode = MODE_IDLE
            self._attr_action = HumidifierAction.IDLE

    # =========================================================================
    # Sensor Value Updates
    # =========================================================================

    async def _async_update_humidity(self, humidity: str) -> None:
        """Update humidity control with latest state from sensor."""
        try:
            self._cur_humidity = float(humidity)
        except ValueError as ex:
            if self._active:
                _LOGGER.warning("Unable to update from sensor: %s", ex)
                self._active = False
            else:
                _LOGGER.debug("Unable to update from sensor: %s", ex)
            self._cur_humidity = None
            await self._async_turn_off_all()

    async def _async_update_co2(self, co2: str) -> None:
        """Update CO2 reading."""
        try:
            self._cur_co2 = float(co2)
        except ValueError as ex:
            _LOGGER.debug("Unable to update CO2 from sensor: %s", ex)
            self._cur_co2 = None

    async def _async_update_voc(self, voc: str) -> None:
        """Update VOC reading."""
        try:
            self._cur_voc = float(voc)
        except ValueError as ex:
            _LOGGER.debug("Unable to update VOC from sensor: %s", ex)
            self._cur_voc = None

    # =========================================================================
    # Main Control Logic
    # =========================================================================

    async def _async_operate(self, time: datetime | None = None, force: bool = False) -> None:
        """Main control loop - check all sensors and adjust outputs."""
        async with self._humidity_lock:
            if not self._active and None not in (
                self._cur_humidity,
                self._target_humidity,
            ):
                self._active = True
                force = True
                _LOGGER.debug(
                    "Obtained current and target humidity. Controller active. %s, %s",
                    self._cur_humidity,
                    self._target_humidity,
                )

            if not self._active or not self._state:
                return

            # Update air quality status
            self._update_air_quality_status()

            # Check if we're in boost mode
            if self._boost_active:
                await self._async_operate_boost()
                return

            # Calculate required ventilation level
            vent_level, vent_reason = self._calculate_ventilation_need()

            # Calculate required humidifier level
            humidifier_level, humidify_needed = self._calculate_humidifier_need()

            # Determine operating mode
            if vent_level > 0 and humidify_needed:
                new_mode = OP_MODE_VENTILATING_AND_HUMIDIFYING
            elif vent_level > 0:
                new_mode = OP_MODE_VENTILATING
            elif humidify_needed:
                new_mode = OP_MODE_HUMIDIFYING
            elif self._is_dehumidify_needed():
                new_mode = OP_MODE_DEHUMIDIFYING
                vent_level, vent_reason = self._calculate_dehumidify_ventilation()
            else:
                new_mode = OP_MODE_IDLE

            # Apply conflict resolution
            vent_level, humidifier_level = self._resolve_conflicts(vent_level, humidifier_level)

            # Check minimum durations before making changes
            if not force:
                if not self._can_change_humidifier():
                    humidifier_level = self._get_current_humidifier_level_index()
                if not self._can_change_ventilation():
                    vent_level = self._current_ventilation_level

            # Apply changes
            await self._async_set_ventilation_level(vent_level, vent_reason)
            await self._async_set_humidifier_level(humidifier_level)

            # Update operating mode
            self._extended_operating_mode = new_mode
            self._update_action_from_mode(new_mode)

    def _update_air_quality_status(self) -> None:
        """Update the overall air quality status."""
        co2_status = AQ_STATUS_GOOD
        voc_status = AQ_STATUS_GOOD

        if self._cur_co2 is not None:
            if self._cur_co2 >= self._co2_critical:
                co2_status = AQ_STATUS_CRITICAL
            elif self._cur_co2 >= self._co2_target * 1.5:
                co2_status = AQ_STATUS_POOR
            elif self._cur_co2 >= self._co2_target:
                co2_status = AQ_STATUS_ELEVATED

        if self._cur_voc is not None:
            if self._cur_voc >= self._voc_critical:
                voc_status = AQ_STATUS_CRITICAL
            elif self._cur_voc >= self._voc_target * 1.5:
                voc_status = AQ_STATUS_POOR
            elif self._cur_voc >= self._voc_target:
                voc_status = AQ_STATUS_ELEVATED

        # Use worst status
        status_order = [AQ_STATUS_GOOD, AQ_STATUS_ELEVATED, AQ_STATUS_POOR, AQ_STATUS_CRITICAL]
        co2_idx = status_order.index(co2_status)
        voc_idx = status_order.index(voc_status)
        self._air_quality_status = status_order[max(co2_idx, voc_idx)]

    def _calculate_ventilation_need(self) -> tuple[int, str]:
        """Calculate required ventilation level based on air quality.

        Returns:
            Tuple of (level 0-4, reason string)
        """
        max_levels = len(self._ventilation_levels) - 1
        co2_level = 0
        voc_level = 0
        reason = VENT_REASON_NONE

        # Calculate CO2-based level (proportional)
        if self._cur_co2 is not None and self._cur_co2 >= self._co2_target:
            co2_range = self._co2_critical - self._co2_target
            co2_excess = self._cur_co2 - self._co2_target
            co2_level = min(max_levels, int((co2_excess / co2_range) * max_levels) + 1)
            if co2_level >= self._current_ventilation_level or self._current_ventilation_level == 0:
                reason = VENT_REASON_CO2

        # Calculate VOC-based level (proportional)
        if self._cur_voc is not None and self._cur_voc >= self._voc_target:
            voc_range = self._voc_critical - self._voc_target
            voc_excess = self._cur_voc - self._voc_target
            voc_level = min(max_levels, int((voc_excess / voc_range) * max_levels) + 1)
            if voc_level > co2_level:
                reason = VENT_REASON_VOC

        return max(co2_level, voc_level), reason

    def _calculate_humidifier_need(self) -> tuple[int, bool]:
        """Calculate required humidifier level based on humidity.

        Returns:
            Tuple of (level index 0-3, humidify_needed bool)
        """
        if self._target_humidity is None or self._cur_humidity is None:
            return 0, False

        deficit = self._target_humidity - self._cur_humidity

        if deficit < self._dry_tolerance:
            return 0, False

        # Proportional control based on deficit
        # 0 = Off, 1 = Auto/Low, 2 = Medium, 3 = High
        max_level = len(self._humidifier_levels) - 1

        if deficit >= self._dry_tolerance + 10:
            level = max_level  # High
        elif deficit >= self._dry_tolerance + 5:
            level = max(1, max_level - 1)  # Medium
        else:
            level = 1  # Auto/Low

        return level, True

    def _is_dehumidify_needed(self) -> bool:
        """Check if dehumidification is needed."""
        if self._cur_humidity is None:
            return False
        return self._cur_humidity >= self._humidity_dehumidify_threshold

    def _calculate_dehumidify_ventilation(self) -> tuple[int, str]:
        """Calculate ventilation level for dehumidification.

        Returns:
            Tuple of (level 0-4, reason string)
        """
        if self._cur_humidity is None:
            return 0, VENT_REASON_NONE

        max_levels = len(self._ventilation_levels) - 1
        humidity_range = self._humidity_dehumidify_critical - self._humidity_dehumidify_threshold
        humidity_excess = self._cur_humidity - self._humidity_dehumidify_threshold

        if humidity_excess <= 0:
            return 0, VENT_REASON_NONE

        level = min(max_levels, int((humidity_excess / humidity_range) * max_levels) + 1)
        return level, VENT_REASON_HUMIDITY

    def _resolve_conflicts(self, vent_level: int, humidifier_level: int) -> tuple[int, int]:
        """Resolve conflicts between ventilation and humidification.

        If humidity drops too low during ventilation, cap ventilation level.

        Returns:
            Adjusted (vent_level, humidifier_level)
        """
        if self._cur_humidity is None or self._target_humidity is None:
            return vent_level, humidifier_level

        # If humidity is critically low and we're ventilating, cap ventilation
        critical_low_humidity = 35.0  # Below this, cap ventilation
        if self._cur_humidity < critical_low_humidity and vent_level > 2:
            _LOGGER.debug(
                "Capping ventilation to level 2 due to low humidity (%.1f%%)",
                self._cur_humidity,
            )
            vent_level = 2

        return vent_level, humidifier_level

    def _can_change_humidifier(self) -> bool:
        """Check if minimum humidifier duration has passed."""
        if self._last_humidifier_change is None:
            return True
        elapsed = dt_util.utcnow() - self._last_humidifier_change
        return elapsed >= self._min_humidify_duration

    def _can_change_ventilation(self) -> bool:
        """Check if minimum ventilation duration has passed."""
        if self._last_ventilation_change is None:
            return True
        elapsed = dt_util.utcnow() - self._last_ventilation_change
        return elapsed >= self._min_ventilate_duration

    def _get_current_humidifier_level_index(self) -> int:
        """Get the current humidifier level as an index."""
        if not self._is_humidifier_power_on:
            return 0
        if (
            self._current_humidifier_level
            and self._current_humidifier_level in self._humidifier_levels
        ):
            return self._humidifier_levels.index(self._current_humidifier_level)
        return 0

    def _update_action_from_mode(self, mode: str) -> None:
        """Update the humidifier action based on operating mode."""
        if mode == OP_MODE_HUMIDIFYING:
            self._attr_action = HumidifierAction.HUMIDIFYING
        elif mode == OP_MODE_DEHUMIDIFYING:
            self._attr_action = HumidifierAction.DRYING
        elif mode in (OP_MODE_VENTILATING, OP_MODE_VENTILATING_AND_HUMIDIFYING):
            # Ventilating could be either action depending on humidity
            if self._is_humidifier_power_on:
                self._attr_action = HumidifierAction.HUMIDIFYING
            else:
                self._attr_action = HumidifierAction.DRYING
        else:
            self._attr_action = HumidifierAction.IDLE

    # =========================================================================
    # Boost Mode
    # =========================================================================

    async def async_activate_boost(self, duration: int = DEFAULT_BOOST_DURATION) -> None:
        """Activate boost mode for rapid air exchange.

        Args:
            duration: Duration in seconds for boost mode (default: 1200 = 20 minutes).
        """
        self._boost_active = True
        self._boost_end_time = dt_util.utcnow() + timedelta(seconds=duration)

        # Cancel any existing timer
        if self._remove_boost_timer:
            self._remove_boost_timer()

        # Set up timer to end boost
        self._remove_boost_timer = async_track_time_interval(
            self.hass,
            self._async_check_boost_end,
            timedelta(seconds=10),  # Check every 10 seconds
        )

        _LOGGER.info("Boost mode activated for %d seconds", duration)
        await self._async_operate(force=True)
        self.async_write_ha_state()

    async def async_deactivate_boost(self) -> None:
        """Deactivate boost mode."""
        self._boost_active = False
        self._boost_end_time = None

        if self._remove_boost_timer:
            self._remove_boost_timer()
            self._remove_boost_timer = None

        # Turn off boost helper if it's on
        if self._boost_helper and self.hass.states.is_state(self._boost_helper, STATE_ON):
            await self.hass.services.async_call(
                HOMEASSISTANT_DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self._boost_helper},
            )

        _LOGGER.info("Boost mode deactivated")
        await self._async_operate(force=True)
        self.async_write_ha_state()

    async def _async_check_boost_end(self, now: datetime | None = None) -> None:
        """Check if boost mode should end."""
        if not self._boost_active or self._boost_end_time is None:
            return

        if dt_util.utcnow() >= self._boost_end_time:
            await self.async_deactivate_boost()

    async def _async_operate_boost(self) -> None:
        """Operate in boost mode - max ventilation."""
        max_level = len(self._ventilation_levels) - 1
        await self._async_set_ventilation_level(max_level, VENT_REASON_BOOST)

        # Keep humidifier running if humidity is low
        if self._cur_humidity is not None and self._target_humidity is not None:
            if self._cur_humidity < self._target_humidity - self._dry_tolerance:
                # Medium level during boost to maintain some humidity
                await self._async_set_humidifier_level(2)
            else:
                await self._async_set_humidifier_level(0)

        self._extended_operating_mode = OP_MODE_BOOST

    # =========================================================================
    # Output Control Methods
    # =========================================================================

    async def _async_set_ventilation_level(self, level: int, reason: str) -> None:
        """Set the ventilation level on the climate/fan entity."""
        if not self._ventilation_entity:
            return

        if level == self._current_ventilation_level and reason == self._ventilation_reason:
            return  # No change needed

        # Clamp level to valid range
        level = max(0, min(level, len(self._ventilation_levels) - 1))
        fan_mode = self._ventilation_levels[level]

        _LOGGER.debug(
            "Setting ventilation to level %d (%s) for reason: %s",
            level,
            fan_mode,
            reason,
        )

        # Determine the entity domain
        entity_domain = self._ventilation_entity.split(".")[0]

        if entity_domain == "climate":
            await self.hass.services.async_call(
                "climate",
                "set_fan_mode",
                {
                    ATTR_ENTITY_ID: self._ventilation_entity,
                    "fan_mode": fan_mode,
                },
            )
        elif entity_domain == "fan":
            if level == 0:
                await self.hass.services.async_call(
                    "fan",
                    SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: self._ventilation_entity},
                )
            else:
                # Calculate percentage based on level
                percentage = int((level / (len(self._ventilation_levels) - 1)) * 100)
                await self.hass.services.async_call(
                    "fan",
                    SERVICE_TURN_ON,
                    {
                        ATTR_ENTITY_ID: self._ventilation_entity,
                        "percentage": percentage,
                    },
                )

        self._current_ventilation_level = level
        self._ventilation_reason = reason
        self._last_ventilation_change = dt_util.utcnow()

    async def _async_set_humidifier_level(self, level_index: int) -> None:
        """Set the humidifier power and level."""
        if not self._humidifier_power_entity:
            return

        current_level_index = self._get_current_humidifier_level_index()
        if level_index == current_level_index:
            return  # No change needed

        if level_index == 0:
            # Turn off
            _LOGGER.debug("Turning off humidifier")
            await self._async_entity_turn_off(self._humidifier_power_entity)
            self._current_humidifier_level = None
        else:
            # Set level first, then turn on
            level_name = self._humidifier_levels[level_index]
            _LOGGER.debug("Setting humidifier to level: %s", level_name)

            if self._humidifier_level_entity:
                await self.hass.services.async_call(
                    "select",
                    "select_option",
                    {
                        ATTR_ENTITY_ID: self._humidifier_level_entity,
                        "option": level_name,
                    },
                )
                self._current_humidifier_level = level_name

            # Turn on if not already on
            if not self._is_humidifier_power_on:
                await self._async_entity_turn_on(self._humidifier_power_entity)

        self._last_humidifier_change = dt_util.utcnow()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _check_min_cycle(self) -> bool:
        """Check if min_cycle_duration has elapsed for active entities."""
        # Check humidifier power entity
        if not self._humidifier_power_entity or not self._is_humidifier_power_on:
            return True

        return condition.state(
            self.hass,
            self._humidifier_power_entity,
            STATE_ON,
            self._min_cycle_duration,
        )

    @property
    def _is_humidifier_power_on(self) -> bool:
        """Check if the humidifier power entity is on."""
        if not self._humidifier_power_entity:
            return False
        return self.hass.states.is_state(self._humidifier_power_entity, STATE_ON)

    async def _async_entity_turn_on(self, entity_id: str | None) -> None:
        """Turn an output entity on."""
        if not entity_id:
            return
        data = {ATTR_ENTITY_ID: entity_id}
        await self.hass.services.async_call(HOMEASSISTANT_DOMAIN, SERVICE_TURN_ON, data)

    async def _async_entity_turn_off(self, entity_id: str | None) -> None:
        """Turn an output entity off."""
        if not entity_id:
            return
        data = {ATTR_ENTITY_ID: entity_id}
        await self.hass.services.async_call(HOMEASSISTANT_DOMAIN, SERVICE_TURN_OFF, data)

    async def _async_turn_off_all(self) -> None:
        """Turn off all output entities."""
        # Multi-level humidifier
        if self._is_humidifier_power_on:
            await self._async_entity_turn_off(self._humidifier_power_entity)

        # Ventilation - set to level 0
        if self._ventilation_entity:
            await self._async_set_ventilation_level(0, VENT_REASON_NONE)

    async def async_set_mode(self, mode: str) -> None:
        """Set new mode."""
        if mode == MODE_AWAY and self._away_humidity is not None:
            self._is_away = True
            self._saved_target_humidity = self._target_humidity
            self._target_humidity = self._away_humidity
        elif mode == MODE_NORMAL:
            self._is_away = False
            if self._saved_target_humidity:
                self._target_humidity = self._saved_target_humidity

        await self._async_operate(force=True)
        self.async_write_ha_state()
