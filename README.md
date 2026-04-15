# ha-residency-tracker

A Home Assistant custom component that tracks where your people are — US state or country — and builds a historical record in a local SQLite database.

Useful for anyone who needs to log physical presence across jurisdictions (tax residency, legal domicile, travel records, etc.).

## How it works

- Polls all `person.*` entities **twice daily** (08:00 and 20:00 in your HA timezone)
- Reverse-geocodes each person's GPS coordinates to a **US state name** or **country name** using fully offline libraries — no external API calls
- Writes each observation to a SQLite database at `<config_dir>/residency_tracker.db`
- Runs an immediate poll on startup so you don't wait for the first scheduled window
- New person entities are automatically picked up on the next poll — no restart required

## Installation

### HACS (recommended)

1. Add this repo as a custom repository in HACS (type: Integration)
2. Install **Residency Tracker**
3. Restart Home Assistant

### Manual

Copy `custom_components/residency_tracker/` into your HA `custom_components/` directory and restart.

## Configuration

Add to `configuration.yaml`:

```yaml
residency_tracker:
```

That's it — no options required. The component discovers all `person.*` entities automatically.

## Database

Observations are stored in `<config_dir>/residency_tracker.db` (same directory as your `configuration.yaml`).

Schema:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `person_id` | TEXT | HA object ID (e.g. `george_schlossnagle`) |
| `observed_at` | TEXT | ISO 8601 UTC timestamp |
| `jurisdiction` | TEXT | US state name or country name |
| `in_us` | INTEGER | `1` if in the US, `0` if international |
| `latitude` | REAL | GPS latitude at observation time |
| `longitude` | REAL | GPS longitude at observation time |
| `gps_accuracy` | REAL | GPS accuracy in meters (if available) |

You can query it directly with any SQLite client, or use a HA SQLite integration to expose it to dashboards.

### Example queries

Days per US state in 2025 for a given person:
```sql
SELECT jurisdiction, COUNT(*) AS observations
FROM residency_observations
WHERE person_id = 'george_schlossnagle'
  AND in_us = 1
  AND observed_at >= '2025-01-01'
  AND observed_at <  '2026-01-01'
GROUP BY jurisdiction
ORDER BY observations DESC;
```

Days outside the US:
```sql
SELECT COUNT(*) AS observations_outside_us
FROM residency_observations
WHERE person_id = 'george_schlossnagle'
  AND in_us = 0;
```

## Requirements

- Home Assistant 2023.1+
- Python packages (installed automatically): `reverse_geocoder==1.5.1`, `pycountry==22.3.5`

All geocoding is done locally — no API keys, no network calls for location resolution.

## Limitations

- Poll-based (not event-driven): location is sampled at 08:00 and 20:00, not continuously
- GPS coordinates must be present on the `person.*` entity — persons without location data are skipped
- Reverse geocoding rounds coordinates to ~1 km precision for cache efficiency

## License

MIT
