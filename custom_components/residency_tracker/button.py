"""Poll Now button for Residency Tracker."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import poll_all_persons


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([PollNowButton(hass, entry.entry_id)])


class PollNowButton(ButtonEntity):
    """Button that triggers an immediate residency poll."""

    _attr_name = "Residency Tracker Poll Now"
    _attr_icon = "mdi:refresh"

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._attr_unique_id = f"residency_tracker_{entry_id}_poll_now"

    async def async_press(self) -> None:
        db = self._hass.data[DOMAIN][self._entry_id]["db"]
        await poll_all_persons(self._hass, db)
