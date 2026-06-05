from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Match, ScheduleData


def import_csv(csv_path: Path, out_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        matches = [Match.model_validate(row) for row in reader]

    schedule = ScheduleData(
        version=f"manual-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        source_name=f"Manual CSV import: {csv_path.name}",
        source_url="",
        generated_at=datetime.now(timezone.utc),
        matches=matches,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(schedule.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import VNL schedule CSV into app JSON cache.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/cache/vnl_2026.json"))
    args = parser.parse_args()
    import_csv(args.csv_path, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
