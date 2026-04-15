"""Offline reverse geocoding: returns US state name or country name."""
from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

_LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=512)
def _resolve(lat: float, lon: float) -> tuple[str, bool]:
    """Return (jurisdiction, in_us). Runs synchronously — call via executor."""
    import reverse_geocoder as rg  # lazy import; ~200ms on first call to load data
    import pycountry

    results = rg.search((lat, lon), verbose=False)
    if not results:
        return ("Unknown", False)

    result = results[0]
    cc: str = result.get("cc", "")
    admin1: str = result.get("admin1", "")

    if cc == "US":
        jurisdiction = admin1 if admin1 else "Unknown"
        return (jurisdiction, True)

    country = pycountry.countries.get(alpha_2=cc)
    jurisdiction = country.name if country else cc or "Unknown"
    return (jurisdiction, False)


async def resolve_jurisdiction(
    hass,
    lat: float,
    lon: float,
) -> tuple[str, bool]:
    """Async wrapper — offloads blocking work to the executor."""
    # Round to ~1km precision before hitting cache to improve hit rate
    lat_r = round(lat, 2)
    lon_r = round(lon, 2)
    try:
        return await hass.async_add_executor_job(_resolve, lat_r, lon_r)
    except Exception:
        _LOGGER.exception("Reverse geocoding failed for (%s, %s)", lat, lon)
        return ("Unknown", False)
