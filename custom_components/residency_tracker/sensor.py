"""Residency Tracker sensors."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_UPDATE
from .db import ResidencyDB


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    db: ResidencyDB = hass.data[DOMAIN][entry.entry_id]["db"]

    entities = []
    for state in hass.states.async_all("person"):
        person_id = state.object_id
        friendly_name = state.name
        entities.extend([
            ResidencyCurrentLocationSensor(hass, db, person_id, friendly_name),
            ResidencyDaysSensor(hass, db, person_id, friendly_name),
        ])

    async_add_entities(entities, update_before_add=True)


class ResidencyCurrentLocationSensor(SensorEntity):
    """Current jurisdiction for a person based on their most recent observation.

    Entity ID: sensor.residency_tracker_current_location_{person_id}
    """

    _attr_icon = "mdi:map-marker-account"

    def __init__(
        self, hass: HomeAssistant, db: ResidencyDB, person_id: str, friendly_name: str
    ) -> None:
        self._hass = hass
        self._db = db
        self._person_id = person_id
        # Name slugifies to: residency_tracker_current_location_{person_id}
        self._attr_name = f"Residency Tracker Current Location {friendly_name}"
        self._attr_unique_id = f"residency_tracker_{person_id}_current_location"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self._hass, SIGNAL_UPDATE, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_schedule_update_ha_state(True)

    def update(self) -> None:
        row = self._db.get_latest_observation(self._person_id)
        if row:
            self._attr_native_value = row["jurisdiction"]
            self._attr_extra_state_attributes = {
                "last_observed": row["observed_at"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
            }
        else:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}


class ResidencyDaysSensor(SensorEntity):
    """Days per jurisdiction for a person, grouped by year.

    Entity ID: sensor.residency_tracker_residency_days_{person_id}

    State: total days recorded in the current calendar year.
    Attributes: {year: {jurisdiction: days}} for all years with observations.
      New years are included automatically as observations are added.
    """

    _attr_icon = "mdi:calendar-account"
    _attr_native_unit_of_measurement = "days"

    def __init__(
        self,
        hass: HomeAssistant,
        db: ResidencyDB,
        person_id: str,
        friendly_name: str,
    ) -> None:
        self._hass = hass
        self._db = db
        self._person_id = person_id
        # Name slugifies to: residency_tracker_residency_days_{person_id}
        self._attr_name = f"Residency Tracker Residency Days {friendly_name}"
        self._attr_unique_id = f"residency_tracker_{person_id}_days"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self._hass, SIGNAL_UPDATE, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_schedule_update_ha_state(True)

    def update(self) -> None:
        all_years = self._db.get_all_years_days_by_jurisdiction(self._person_id)
        current_year = str(datetime.now(timezone.utc).year)
        current_year_data = all_years.get(current_year, {})
        self._attr_native_value = sum(current_year_data.values())
        self._attr_extra_state_attributes = all_years
