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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Residency Tracker from a config entry (UI install)."""
    hass.data.setdefault(DOMAIN, {})

    db = ResidencyDB(hass.config.config_dir)
    await hass.async_add_executor_job(db.connect)

    unsub_list = []

    async def _handle_poll(now) -> None:
        _LOGGER.debug("Residency poll triggered at %s", now)
        await poll_all_persons(hass, db)

    for time_str in POLL_TIMES:
        hour, minute = (int(p) for p in time_str.split(":"))
        unsub = async_track_time(hass, _handle_poll, time(hour, minute))
        unsub_list.append(unsub)
        _LOGGER.info("Residency poll scheduled at %s local time", time_str)

    hass.data[DOMAIN][entry.entry_id] = {
        "db": db,
        "unsub_list": unsub_list,
    }

    # Run an immediate poll on startup so we don't wait until the first window
    hass.async_create_task(poll_all_persons(hass, db))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].pop(entry.entry_id, {})

    for unsub in data.get("unsub_list", []):
        unsub()

    db = data.get("db")
    if db:
        await hass.async_add_executor_job(db.close)

    return True
