"""Humidity Control - Combined Humidifier/Dehumidifier support.

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

import asyncio
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any, cast

from homeassistant.components.humidifier import (
    ATTR_HUMIDITY,
    PLATFORM_SCHEMA as HUMIDIFIER_PLATFORM_SCHEMA,
    HumidifierAction,
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
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
    Event,
    EventStateChangedData,
    EventStateReportedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers import condition, config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
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
    ATTR_OPERATING_MODE,
    ATTR_SAVED_HUMIDITY,
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
    MODE_AWAY,
    MODE_DRY,
    MODE_IDLE,
    MODE_NORMAL,
    MODE_WET,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = HUMIDIFIER_PLATFORM_SCHEMA.extend(HUMIDITY_CONTROL_SCHEMA.schema)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the humidity control platform."""
    if discovery_info:
        config = discovery_info
    await _async_setup_config(
        hass, config, config.get(CONF_UNIQUE_ID), async_add_entities
    )


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
    wet_entity_id: str | None = config.get(CONF_WET_ENTITY)
    dry_entity_id: str | None = config.get(CONF_DRY_ENTITY)
    min_humidity: float | None = config.get(CONF_MIN_HUMIDITY)
    max_humidity: float | None = config.get(CONF_MAX_HUMIDITY)
    target_humidity: float | None = config.get(CONF_TARGET_HUMIDITY)
    min_cycle_duration: timedelta | None = _time_period_or_none(
        config.get(CONF_MIN_DUR)
    )
    sensor_stale_duration: timedelta | None = _time_period_or_none(
        config.get(CONF_STALE_DURATION)
    )
    dry_tolerance: float = config.get(CONF_DRY_TOLERANCE, 3.0)
    wet_tolerance: float = config.get(CONF_WET_TOLERANCE, 3.0)
    keep_alive: timedelta | None = _time_period_or_none(config.get(CONF_KEEP_ALIVE))
    initial_state: bool | None = config.get(CONF_INITIAL_STATE)
    away_humidity: int | None = config.get(CONF_AWAY_HUMIDITY)
    away_fixed: bool | None = config.get(CONF_AWAY_FIXED)

    async_add_entities(
        [
            HumidityControl(
                hass,
                name=name,
                sensor_entity_id=sensor_entity_id,
                wet_entity_id=wet_entity_id,
                dry_entity_id=dry_entity_id,
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
            )
        ]
    )


class HumidityControl(HumidifierEntity, RestoreEntity):
    """Representation of a combined Humidity Control device."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        name: str,
        sensor_entity_id: str,
        wet_entity_id: str | None,
        dry_entity_id: str | None,
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
    ) -> None:
        """Initialize the humidity control."""
        self._name = name
        self._sensor_entity_id = sensor_entity_id
        self._wet_entity_id = wet_entity_id
        self._dry_entity_id = dry_entity_id
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
        
        # Track operating mode: idle, wet, or dry
        self._operating_mode = MODE_IDLE

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()

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
        
        # Track wet entity state changes
        if self._wet_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._wet_entity_id, self._async_output_event
                )
            )
        
        # Track dry entity state changes
        if self._dry_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._dry_entity_id, self._async_output_event
                )
            )
        
        if self._keep_alive:
            self.async_on_remove(
                async_track_time_interval(
                    self.hass, self._async_operate, self._keep_alive
                )
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

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

        if (old_state := await self.async_get_last_state()) is not None:
            if old_state.attributes.get(ATTR_MODE) == MODE_AWAY:
                self._is_away = True
                self._saved_target_humidity = self._target_humidity
                self._target_humidity = self._away_humidity or self._target_humidity
            if old_state.attributes.get(ATTR_HUMIDITY):
                self._target_humidity = int(old_state.attributes[ATTR_HUMIDITY])
            if old_state.attributes.get(ATTR_SAVED_HUMIDITY):
                self._saved_target_humidity = int(
                    old_state.attributes[ATTR_SAVED_HUMIDITY]
                )
            if old_state.attributes.get(ATTR_OPERATING_MODE):
                self._operating_mode = old_state.attributes[ATTR_OPERATING_MODE]
            if old_state.state:
                self._state = old_state.state == STATE_ON
        if self._target_humidity is None:
            self._target_humidity = self.min_humidity
            _LOGGER.warning(
                "No previously saved humidity, setting to %s", self._target_humidity
            )
        if self._state is None:
            self._state = False

        await _async_startup(None)  # init the sensor

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        if self._remove_stale_tracking:
            self._remove_stale_tracking()
        return await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._active

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the optional state attributes."""
        attrs: dict[str, Any] = {ATTR_OPERATING_MODE: self._operating_mode}
        if self._saved_target_humidity:
            attrs[ATTR_SAVED_HUMIDITY] = self._saved_target_humidity
        return attrs

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
        self._operating_mode = MODE_IDLE
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

        # Determine operating mode based on output states
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

        self.async_write_ha_state()

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

    async def _async_operate(
        self, time: datetime | None = None, force: bool = False
    ) -> None:
        """Check if we need to turn humidifying/dehumidifying on or off."""
        async with self._humidity_lock:
            if not self._active and None not in (
                self._cur_humidity,
                self._target_humidity,
            ):
                self._active = True
                force = True
                _LOGGER.debug(
                    "Obtained current and target humidity. Humidity control active. %s, %s",
                    self._cur_humidity,
                    self._target_humidity,
                )

            if not self._active or not self._state:
                return

            if not force and time is None:
                # Check min_cycle_duration for both output entities
                if self._min_cycle_duration:
                    if not self._check_min_cycle():
                        return

            # Always use configured tolerances
            # (force only bypasses min_cycle_duration, not tolerance)
            dry_tolerance = self._dry_tolerance
            wet_tolerance = self._wet_tolerance

            if TYPE_CHECKING:
                assert self._target_humidity is not None
                assert self._cur_humidity is not None

            too_dry = self._target_humidity - self._cur_humidity >= dry_tolerance
            too_wet = self._cur_humidity - self._target_humidity >= wet_tolerance

            wet_active = self._is_wet_active
            dry_active = self._is_dry_active

            # Logic:
            # - If too dry and we have a wet entity -> turn on wet, turn off dry
            # - If too wet and we have a dry entity -> turn on dry, turn off wet
            # - If neither -> turn off both (idle)
            
            if too_dry and not too_wet:
                # Need to humidify
                if self._wet_entity_id:
                    if dry_active:
                        _LOGGER.debug("Turning off dry entity %s", self._dry_entity_id)
                        await self._async_entity_turn_off(self._dry_entity_id)
                    if not wet_active:
                        _LOGGER.debug("Turning on wet entity %s", self._wet_entity_id)
                        await self._async_entity_turn_on(self._wet_entity_id)
                    elif time is not None:
                        # Keep-alive
                        await self._async_entity_turn_on(self._wet_entity_id)
                else:
                    _LOGGER.debug("Too dry but no wet entity configured")
                    
            elif too_wet and not too_dry:
                # Need to dehumidify
                if self._dry_entity_id:
                    if wet_active:
                        _LOGGER.debug("Turning off wet entity %s", self._wet_entity_id)
                        await self._async_entity_turn_off(self._wet_entity_id)
                    if not dry_active:
                        _LOGGER.debug("Turning on dry entity %s", self._dry_entity_id)
                        await self._async_entity_turn_on(self._dry_entity_id)
                    elif time is not None:
                        # Keep-alive
                        await self._async_entity_turn_on(self._dry_entity_id)
                else:
                    _LOGGER.debug("Too wet but no dry entity configured")
                    
            else:
                # Within tolerance - turn everything off (idle)
                if wet_active:
                    _LOGGER.debug("Turning off wet entity %s", self._wet_entity_id)
                    await self._async_entity_turn_off(self._wet_entity_id)
                if dry_active:
                    _LOGGER.debug("Turning off dry entity %s", self._dry_entity_id)
                    await self._async_entity_turn_off(self._dry_entity_id)
                if time is not None:
                    # Keep-alive - maintain current off state
                    if self._wet_entity_id:
                        await self._async_entity_turn_off(self._wet_entity_id)
                    if self._dry_entity_id:
                        await self._async_entity_turn_off(self._dry_entity_id)

    def _check_min_cycle(self) -> bool:
        """Check if min_cycle_duration has elapsed for active entities."""
        # Check wet entity
        if self._wet_entity_id and self._is_wet_active:
            current_state = STATE_ON
            if not condition.state(
                self.hass,
                self._wet_entity_id,
                current_state,
                self._min_cycle_duration,
            ):
                return False
        
        # Check dry entity
        if self._dry_entity_id and self._is_dry_active:
            current_state = STATE_ON
            if not condition.state(
                self.hass,
                self._dry_entity_id,
                current_state,
                self._min_cycle_duration,
            ):
                return False
        
        return True

    @property
    def _is_wet_active(self) -> bool:
        """Check if the wet entity is currently active."""
        if not self._wet_entity_id:
            return False
        return self.hass.states.is_state(self._wet_entity_id, STATE_ON)

    @property
    def _is_dry_active(self) -> bool:
        """Check if the dry entity is currently active."""
        if not self._dry_entity_id:
            return False
        return self.hass.states.is_state(self._dry_entity_id, STATE_ON)

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
        if self._is_wet_active:
            await self._async_entity_turn_off(self._wet_entity_id)
        if self._is_dry_active:
            await self._async_entity_turn_off(self._dry_entity_id)

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
