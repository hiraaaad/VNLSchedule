from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from .models import Competition, Match, ScheduleData

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_PATH = ROOT / "data" / "cache" / "vnl_2026.json"
SEED_PATH = ROOT / "data" / "seed_schedule.json"
DEFAULT_TIMEZONE = "Australia/Perth"

TEAM_COUNTRY_CODES = {
    "Argentina": "AR",
    "Belgium": "BE",
    "Brazil": "BR",
    "Bulgaria": "BG",
    "Canada": "CA",
    "China": "CN",
    "Cuba": "CU",
    "Czech Republic": "CZ",
    "Czechia": "CZ",
    "Dominican Republic": "DO",
    "France": "FR",
    "Germany": "DE",
    "Iran": "IR",
    "Italy": "IT",
    "Japan": "JP",
    "Netherlands": "NL",
    "Poland": "PL",
    "Serbia": "RS",
    "Slovenia": "SI",
    "Thailand": "TH",
    "Turkey": "TR",
    "Turkiye": "TR",
    "Ukraine": "UA",
    "United States": "US",
    "USA": "US",
}


@dataclass(frozen=True)
class RenderedMatch:
    match: Match
    local_datetime: datetime
    is_highlighted: bool

    @property
    def day_key(self) -> str:
        return self.local_datetime.strftime("%Y-%m-%d")

    @property
    def day_label(self) -> str:
        return self.local_datetime.strftime("%a %-d %b")

    @property
    def time_label(self) -> str:
        return self.local_datetime.strftime("%H:%M")

    @property
    def venue_label(self) -> str:
        parts = [self.match.city, self.match.country]
        return ", ".join(part for part in parts if part)

    @property
    def team_a_label(self) -> str:
        return team_label(self.match.team_a)

    @property
    def team_b_label(self) -> str:
        return team_label(self.match.team_b)

    @property
    def matchup_label(self) -> str:
        return f"{self.team_a_label} v {self.team_b_label}"

    @property
    def result_label(self) -> str:
        if self.match.score:
            return f"{self.team_a_label} {self.match.score} {self.team_b_label}"
        return self.matchup_label

    @property
    def round_label(self) -> str:
        label = self.match.round or self.match.phase
        pool = re.search(r"\bP(\d+)\b", label)
        if pool:
            return f"P{pool.group(1)}"
        return label.replace("Pool ", "P").replace("Week ", "WK")


@dataclass(frozen=True)
class RenderSection:
    competition: Competition
    title: str
    days: OrderedDict[str, list[RenderedMatch]]


def week_number(label: str) -> int | None:
    match = re.search(r"\bWeek\s+(\d+)\b", label)
    return int(match.group(1)) if match else None


def load_schedule(path: Path = DEFAULT_CACHE_PATH) -> ScheduleData:
    data_path = path if path.exists() else SEED_PATH
    return ScheduleData.model_validate_json(data_path.read_text(encoding="utf-8"))


def country_flag(country_code: str) -> str:
    base = 0x1F1E6
    return "".join(chr(base + ord(char) - ord("A")) for char in country_code.upper())


def team_label(team_name: str) -> str:
    country_code = TEAM_COUNTRY_CODES.get(team_name)
    if not country_code:
        return team_name
    return f"{country_flag(country_code)} {team_name}"


def convert_match(match: Match, timezone_name: str, highlight: str = "") -> RenderedMatch:
    local_datetime = match.starts_at_utc.astimezone(ZoneInfo(timezone_name))
    normalized_highlight = highlight.casefold().strip()
    is_highlighted = bool(
        normalized_highlight
        and normalized_highlight in {match.team_a.casefold(), match.team_b.casefold()}
    )
    return RenderedMatch(match=match, local_datetime=local_datetime, is_highlighted=is_highlighted)


def build_sections(
    schedule: ScheduleData,
    timezone_name: str,
    competitions: list[Competition],
    highlight: str = "",
    hide_completed: bool = False,
) -> list[RenderSection]:
    sections: list[RenderSection] = []
    section_keys: list[tuple[int | None, Competition]] = []
    for week in (1, 2, 3):
        for competition in competitions:
            section_keys.append((week, competition))
    for competition in competitions:
        section_keys.append((None, competition))

    seen: set[tuple[int | None, Competition]] = set()
    for week, competition in section_keys:
        if (week, competition) in seen:
            continue
        seen.add((week, competition))
        rendered = [
            convert_match(match, timezone_name, highlight)
            for match in schedule.matches
            if match.competition == competition and week_number(match.round) == week
            and not (hide_completed and match.status == "completed")
        ]
        if not rendered:
            continue
        rendered.sort(key=lambda item: item.local_datetime)
        days: OrderedDict[str, list[RenderedMatch]] = OrderedDict()
        for item in rendered:
            days.setdefault(item.day_key, []).append(item)
        title = f"VNL 2026 {competition.title()}"
        if week is not None:
            title = f"WK{week} {competition.title()}"
        sections.append(
            RenderSection(
                competition=competition,
                title=title,
                days=days,
            )
        )
    return sections


def available_teams(schedule: ScheduleData) -> list[str]:
    teams = {match.team_a for match in schedule.matches} | {match.team_b for match in schedule.matches}
    return sorted(teams)
