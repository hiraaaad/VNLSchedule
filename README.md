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

Use the `Show results` toggle to display completed match scores. `Hide completed` is on by default; turn it off to include finished matches.

## Static GitHub Pages Version

This repo also includes a static `index.html` that can run on GitHub Pages without Python. It loads `data/vnl_2026.json`, converts times in the browser, and uses the browser's Print dialog for PDF export.

To test locally:

```bash
python3 -m http.server 8080
```

Open `http://127.0.0.1:8080`.

For GitHub Pages, commit `index.html` and `data/vnl_2026.json`, then enable Pages for the repository root branch in GitHub settings.

## Data

The app loads schedule data in this order:

1. `data/cache/vnl_2026.json`
2. `data/seed_schedule.json`

The seed file contains starter matches cited from the official FIVB/Volleyball World 2026 announcement so the app works immediately. Replace or extend the cache JSON with the full official schedule when available.

The printed PDF intentionally shows only the selected local time. Source/original times may exist in JSON for conversion, but they are not rendered in the printable schedule.

## Import Wikipedia Schedule And Results

```bash
python -m vnl_schedule.import_wikipedia
```

This writes `data/cache/vnl_2026.json`, which the app uses automatically on the next refresh.

## Check For Wikipedia Schedule Updates

Dry-run check:

```bash
python -m vnl_schedule.update_wikipedia
```

Apply changes to both the FastAPI cache and GitHub Pages JSON:

```bash
python -m vnl_schedule.update_wikipedia --update
```

The FastAPI app reads `data/cache/vnl_2026.json` first. The static GitHub Pages app reads `data/vnl_2026.json`.

The repository also includes a GitHub Actions workflow that can update the schedule JSON automatically from Wikipedia. It runs every two hours and can also be started manually from the Actions tab. When Wikipedia has new results or fixture changes, the workflow commits updated JSON files back to the repository.

## Import Manual Data

```bash
python -m vnl_schedule.import_schedule path/to/schedule.csv --out data/cache/vnl_2026.json
```

CSV columns:

```text
competition,phase,round,match_no,starts_at_utc,team_a,team_b,venue,city,country,status
```

Optional score column:

```text
competition,phase,round,match_no,starts_at_utc,team_a,team_b,score,venue,city,country,status
```

## Acknowledgements

This project was inspired by the excellent work in the `Kingdoggydog/worldcup2026` repository, which provides a simple, printable, and user-friendly platform for viewing the 2026 FIFA World Cup group stages, including features such as timezone adjustment and team highlighting.

I used that project as a reference point when designing a similar experience for the VNL 2026 platform. The goal was not only to build a functional schedule viewer, but also to preserve the same spirit of simplicity, accessibility, and usefulness for fans who want a clean way to follow fixtures.

Full credit and appreciation go to the original creator of `worldcup2026` for the idea, structure, and inspiration that helped shape this project.
