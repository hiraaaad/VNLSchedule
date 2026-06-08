from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .import_volleystation import import_volleystation, write_schedule
from .models import Match, ScheduleData

STATIC_DATA_PATH = Path("data/vnl_2026.json")
CACHE_DATA_PATH = Path("data/cache/vnl_2026.json")


@dataclass(frozen=True)
class ScheduleDiff:
    added: list[Match]
    removed: list[Match]
    changed: list[tuple[Match, Match]]

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)


def load_existing(path: Path) -> ScheduleData | None:
    if not path.exists():
        return None
    return ScheduleData.model_validate_json(path.read_text(encoding="utf-8"))


def match_identity(match: Match) -> tuple[str, str, str, str]:
    return (
        match.competition,
        match.round,
        match.team_a.casefold(),
        match.team_b.casefold(),
    )


def comparable_match(match: Match) -> dict[str, str]:
    return {
        "competition": match.competition,
        "round": match.round,
        "starts_at_utc": match.starts_at_utc.isoformat(),
        "team_a": match.team_a,
        "team_b": match.team_b,
        "score": match.score or "",
        "venue": match.venue,
        "city": match.city,
        "country": match.country,
        "status": match.status,
    }


def diff_schedules(existing: ScheduleData | None, latest: ScheduleData) -> ScheduleDiff:
    if existing is None:
        return ScheduleDiff(added=latest.matches, removed=[], changed=[])

    existing_by_key = {match_identity(match): match for match in existing.matches}
    latest_by_key = {match_identity(match): match for match in latest.matches}

    added = [match for key, match in latest_by_key.items() if key not in existing_by_key]
    removed = [match for key, match in existing_by_key.items() if key not in latest_by_key]
    changed = [
        (existing_by_key[key], latest_by_key[key])
        for key in sorted(existing_by_key.keys() & latest_by_key.keys())
        if comparable_match(existing_by_key[key]) != comparable_match(latest_by_key[key])
    ]
    return ScheduleDiff(added=added, removed=removed, changed=changed)


def describe_match(match: Match) -> str:
    return (
        f"{match.competition} {match.round} "
        f"{match.starts_at_utc.isoformat()} {match.team_a} v {match.team_b} "
        f"({match.city}, {match.country})"
    )


def changed_fields(before: Match, after: Match) -> str:
    before_data = comparable_match(before)
    after_data = comparable_match(after)
    fields = [
        f"{key}: {before_data[key]} -> {after_data[key]}"
        for key in before_data
        if before_data[key] != after_data[key]
    ]
    return "; ".join(fields)


def print_diff(diff: ScheduleDiff) -> None:
    if not diff.has_changes:
        print("No schedule changes found.")
        return

    print(
        "Schedule changes found: "
        f"{len(diff.added)} added, {len(diff.removed)} removed, {len(diff.changed)} changed"
    )
    for match in diff.added[:10]:
        print(f"+ {describe_match(match)}")
    for match in diff.removed[:10]:
        print(f"- {describe_match(match)}")
    for before, after in diff.changed[:10]:
        print(f"* {describe_match(before)}")
        print(f"  -> {changed_fields(before, after)}")
    omitted = max(len(diff.added) - 10, 0) + max(len(diff.removed) - 10, 0) + max(len(diff.changed) - 10, 0)
    if omitted:
        print(f"... {omitted} more changes omitted")


def update_from_volleystation(
    *,
    static_path: Path = STATIC_DATA_PATH,
    cache_path: Path = CACHE_DATA_PATH,
    write: bool = False,
) -> ScheduleDiff:
    existing = load_existing(static_path)
    latest = import_volleystation(existing=existing)
    diff = diff_schedules(existing, latest)
    print_diff(diff)
    if write and diff.has_changes:
        write_schedule(latest, static_path)
        write_schedule(latest, cache_path)
        print(f"Updated {static_path} and {cache_path}")
    elif write:
        print("Files left unchanged.")
    else:
        print("Dry run only. Re-run with --update to write changes.")
    return diff


def main() -> None:
    parser = argparse.ArgumentParser(description="Check VolleyStation for VNL schedule and result changes.")
    parser.add_argument("--update", action="store_true", help="Write changed schedule JSON files.")
    parser.add_argument("--static-out", type=Path, default=STATIC_DATA_PATH)
    parser.add_argument("--cache-out", type=Path, default=CACHE_DATA_PATH)
    args = parser.parse_args()
    update_from_volleystation(
        static_path=args.static_out,
        cache_path=args.cache_out,
        write=args.update,
    )


if __name__ == "__main__":
    main()
