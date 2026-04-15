"""Residency Tracker integration for Home Assistant.

Polls all person.* entities twice daily, reverse-geocodes their location
to a US state (or country if outside the US), and stores observations in
a local SQLite database at <config_dir>/residency_tracker.db.

New person entities added to the HA instance are automatically tracked on
the next scheduled poll — no restart or reconfiguration required.
"""
from __future__ import annotations

import logging
from datetime import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time

from .const import DOMAIN, POLL_TIMES
from .coordinator import poll_all_persons
from .db import ResidencyDB

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up via configuration.yaml (no config entry needed)."""
    hass.data.setdefault(DOMAIN, {})

    db = ResidencyDB(hass.config.config_dir)
    await hass.async_add_executor_job(db.connect)
    hass.data[DOMAIN]["db"] = db

    async def _handle_poll(now) -> None:
        _LOGGER.debug("Residency poll triggered at %s", now)
        await poll_all_persons(hass, db)

    # Schedule polls at each configured time (local HA timezone)
    for time_str in POLL_TIMES:
        hour, minute = (int(p) for p in time_str.split(":"))
        async_track_time(hass, _handle_poll, time(hour, minute))
        _LOGGER.info("Residency poll scheduled at %s local time", time_str)

    # Run an immediate poll on startup so we don't wait until the first window
    hass.async_create_task(poll_all_persons(hass, db))

    async def _async_shutdown(event) -> None:
        await hass.async_add_executor_job(db.close)

    hass.bus.async_listen_once("homeassistant_stop", _async_shutdown)

    return True
