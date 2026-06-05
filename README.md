# VNLSchedule

A local Python/FastAPI app for building a compact printable Volleyball Nations League 2026 schedule PDF in your selected local timezone.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Run

```bash
uvicorn vnl_schedule.main:app --reload
```

Open `http://127.0.0.1:8000`.

The timezone field accepts IANA timezone names such as `Asia/Jakarta`, `Asia/Manila`, `Europe/Paris`, and `America/New_York`. It also accepts common country or city aliases such as `Indonesia`, `Philippines`, `Singapore`, `Japan`, `Perth`, and `Western Australia`.

## Data

The app loads schedule data in this order:

1. `data/cache/vnl_2026.json`
2. `data/seed_schedule.json`

The seed file contains starter matches cited from the official FIVB/Volleyball World 2026 announcement so the app works immediately. Replace or extend the cache JSON with the full official schedule when available.

The printed PDF intentionally shows only the selected local time. Source/original times may exist in JSON for conversion, but they are not rendered in the printable schedule.

## Import Full Wikipedia Schedule

```bash
python -m vnl_schedule.import_wikipedia
```

This writes `data/cache/vnl_2026.json`, which the app uses automatically on the next refresh.

## Import Manual Data

```bash
python -m vnl_schedule.import_schedule path/to/schedule.csv --out data/cache/vnl_2026.json
```

CSV columns:

```text
competition,phase,round,match_no,starts_at_utc,team_a,team_b,venue,city,country,status
```
