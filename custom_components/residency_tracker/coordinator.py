"""Polls all person entities twice daily and records their jurisdiction."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_UPDATE
from .db import ResidencyDB
from .geocoder import resolve_jurisdiction

_LOGGER = logging.getLogger(__name__)


async def poll_all_persons(hass: HomeAssistant, db: ResidencyDB) -> None:
    """
    Iterate every person.* entity currently registered in HA,
    reverse-geocode their location, and persist an observation.

    New persons added to HA are automatically picked up on the next poll
    because we query hass.states at call time rather than caching the list.
    """
    person_states = hass.states.async_all("person")

    if not person_states:
        _LOGGER.debug("No person entities found; skipping poll")
        return

    observed_at = datetime.now(timezone.utc)

    for state in person_states:
        person_id: str = state.object_id  # e.g. 'george_schlossnagle'
        attrs = state.attributes

        lat = attrs.get("latitude")
        lon = attrs.get("longitude")
        gps_accuracy = attrs.get("gps_accuracy")

        if lat is None or lon is None:
            _LOGGER.warning(
                "Person %s has no GPS coordinates — skipping observation", person_id
            )
            continue

        jurisdiction, in_us = await resolve_jurisdiction(hass, lat, lon)

        _LOGGER.debug(
            "Observed %s at (%.4f, %.4f) → %s (in_us=%s)",
            person_id, lat, lon, jurisdiction, in_us,
        )

        await hass.async_add_executor_job(
            db.insert_observation,
            person_id,
            observed_at,
            jurisdiction,
            in_us,
            lat,
            lon,
            gps_accuracy,
        )

    async_dispatcher_send(hass, SIGNAL_UPDATE)
