# hevy2garmin

[![CI](https://github.com/drkostas/hevy2garmin/actions/workflows/ci.yml/badge.svg)](https://github.com/drkostas/hevy2garmin/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/hevy2garmin)](https://pypi.org/project/hevy2garmin/)
[![Python](https://img.shields.io/pypi/pyversions/hevy2garmin)](https://pypi.org/project/hevy2garmin/)

Sync your [Hevy](https://hevyapp.com) gym workouts to [Garmin Connect](https://connect.garmin.com) — with correct exercise names, sets/reps/weights, and optional HR overlay.

## Why?

Hevy is great for tracking gym workouts but doesn't sync to Garmin. This tool:

- **Maps 438 Hevy exercises** to Garmin's FIT SDK categories (bench press shows as bench press, not "Other")
- **Generates proper FIT files** with exercise structure, sets, reps, weights, and timing
- **Uploads to Garmin Connect** with correct activity name and a detailed description
- **Tracks synced workouts** locally so it never duplicates

## Install

```bash
pip install hevy2garmin
```

## Quick Start

```bash
# First time — syncs your 10 most recent workouts
export HEVY_API_KEY=your-hevy-api-key
hevy2garmin sync

# List recent workouts (✓ = already synced)
hevy2garmin list

# Check sync status
hevy2garmin status

# Sync with Garmin credentials
hevy2garmin --garmin-email you@example.com sync

# Dry run (generate FIT files without uploading)
hevy2garmin sync --dry-run

# Sync last 5 workouts only
hevy2garmin sync -n 5
```

## Getting Your Hevy API Key

1. Go to [Hevy Settings](https://hevyapp.com/settings) → Developer → API Key
2. Copy the key
3. Set as environment variable: `export HEVY_API_KEY=your-key`

## How It Works

1. Pulls workouts from Hevy API
2. Maps each exercise to Garmin's FIT SDK category/subcategory (438 mappings)
3. Generates a structured FIT file with timing, sets, reps, weights
4. Authenticates with Garmin via [garmin-auth](https://pypi.org/project/garmin-auth/) (self-healing OAuth)
5. Uploads FIT file, renames activity, sets description
6. Tracks synced workouts in local SQLite to avoid duplicates

## Python API

```python
from hevy2garmin.sync import sync

result = sync(hevy_api_key="...", garmin_email="...", garmin_password="...")
print(f"Synced: {result['synced']}, Skipped: {result['skipped']}")
```

```python
# Just the exercise mapper
from hevy2garmin.mapper import lookup_exercise

cat, subcat, name = lookup_exercise("Bench Press (Barbell)")
# (0, 1, "Bench Press (Barbell)")

# Just FIT generation
from hevy2garmin.fit import generate_fit

result = generate_fit(hevy_workout_dict, hr_samples=None, output_path="workout.fit")
```

## Docker

```bash
docker build -t hevy2garmin .
docker run -e HEVY_API_KEY=... -e GARMIN_EMAIL=... -e GARMIN_PASSWORD=... hevy2garmin sync
```

## Exercise Mapping

438 Hevy exercises are mapped to Garmin FIT SDK categories. If an exercise isn't mapped, it falls back to "Unknown" (category 65534). Unmapped exercises are logged so you can report them.

## Development

```bash
git clone https://github.com/drkostas/hevy2garmin.git
cd hevy2garmin
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
