from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .models import Competition, Match, ScheduleData

WOMEN_URL = "https://en.wikipedia.org/wiki/2026_FIVB_Women%27s_Volleyball_Nations_League"
MEN_URL = "https://en.wikipedia.org/wiki/2026_FIVB_Men%27s_Volleyball_Nations_League"

POOL_VENUES: dict[Competition, dict[int, tuple[str, str, str]]] = {
    "women": {
        1: ("Centre Videotron", "Quebec City", "Canada"),
        2: ("Nilson Nelson Gymnasium", "Brasilia", "Brazil"),
        3: ("Nanjing Olympic Youth Sports Park Gymnasium", "Nanjing", "China"),
        4: ("Ankara Arena", "Ankara", "Turkey"),
        5: ("PhilSports Arena", "Pasig", "Philippines"),
        6: ("Indoor Stadium Huamark", "Bangkok", "Thailand"),
        7: ("Belgrade Arena", "Belgrade", "Serbia"),
        8: ("Kai Tak Arena", "Hong Kong", "China"),
        9: ("Asue Arena Osaka", "Osaka", "Japan"),
    },
    "men": {
        1: ("TD Place", "Ottawa", "Canada"),
        2: ("Nilson Nelson Gymnasium", "Brasilia", "Brazil"),
        3: ("Linyi Olympic Sports Park Gymnasium", "Linyi", "China"),
        4: ("Co'met Arena", "Orleans", "France"),
        5: ("Gliwice Arena", "Gliwice", "Poland"),
        6: ("Stozice Arena", "Ljubljana", "Slovenia"),
        7: ("Belgrade Arena", "Belgrade", "Serbia"),
        8: ("NOW Arena", "Chicago", "United States"),
        9: ("Asue Arena Osaka", "Osaka", "Japan"),
    },
}

MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "VNLSchedule local importer"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_utc_offset(text: str) -> timezone:
    normalized = text.replace("\u2212", "-").replace("\u2013", "-")
    match = re.search(r"UTC\s*([+-])\s*(\d{1,2})(?::(\d{2}))?", normalized)
    if not match:
        msg = f"Could not find UTC offset in: {text}"
        raise ValueError(msg)
    sign = 1 if match.group(1) == "+" else -1
    hours = int(match.group(2))
    minutes = int(match.group(3) or "0")
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def parse_match_datetime(date_text: str, time_text: str, tzinfo: timezone) -> datetime | None:
    date_match = re.search(r"(\d{1,2})\s+([A-Z][a-z]{2})", date_text)
    time_match = re.search(r"(\d{1,2}):(\d{2})", time_text)
    if not date_match or not time_match:
        return None
    day = int(date_match.group(1))
    month = MONTHS[date_match.group(2)]
    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    return datetime(2026, month, day, hour, minute, tzinfo=tzinfo).astimezone(timezone.utc)


def clean_team(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_score(value: str) -> str | None:
    normalized = value.strip().replace("\u2013", "-").replace("\u2212", "-")
    if normalized in {"", "-"}:
        return None
    if re.fullmatch(r"\d+\s*-\s*\d+", normalized):
        return re.sub(r"\s+", "", normalized)
    return None


def pool_number(title: str) -> int | None:
    match = re.search(r"Pool\s+(\d+)", title)
    return int(match.group(1)) if match else None


def current_week(pool: int) -> str:
    if pool <= 3:
        return "Week 1"
    if pool <= 6:
        return "Week 2"
    return "Week 3"


def parse_pool_matches(soup: BeautifulSoup, competition: Competition) -> list[Match]:
    matches: list[Match] = []
    sequence = 1
    for heading in soup.find_all("h4"):
        pool = pool_number(heading.get_text(" ", strip=True))
        if pool is None or pool not in POOL_VENUES[competition]:
            continue

        note = heading.find_next("ul")
        if note is None:
            continue
        local_tz = parse_utc_offset(note.get_text(" ", strip=True))
        table = heading.find_next("table")
        if table is None:
            continue

        venue, city, country = POOL_VENUES[competition][pool]
        for row in table.find_all("tr")[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) < 5:
                continue
            starts_at_utc = parse_match_datetime(cells[0], cells[1], local_tz)
            team_a = clean_team(cells[2])
            score = normalize_score(cells[3])
            team_b = clean_team(cells[4])
            if starts_at_utc is None or not team_a or not team_b:
                continue
            status = "completed" if score else "scheduled"
            matches.append(
                Match(
                    competition=competition,
                    phase="Preliminary",
                    round=f"{current_week(pool)} P{pool}",
                    match_no=f"{competition[0].upper()}{sequence:03d}",
                    starts_at_utc=starts_at_utc,
                    team_a=team_a,
                    team_b=team_b,
                    score=score,
                    venue=venue,
                    city=city,
                    country=country,
                    status=status,
                )
            )
            sequence += 1
    return matches


def import_wikipedia() -> ScheduleData:
    pages: list[tuple[Competition, str, str]] = [
        ("women", WOMEN_URL, fetch_html(WOMEN_URL)),
        ("men", MEN_URL, fetch_html(MEN_URL)),
    ]
    matches: list[Match] = []
    for competition, _url, html in pages:
        matches.extend(parse_pool_matches(BeautifulSoup(html, "html.parser"), competition))
    matches.sort(key=lambda match: (match.competition != "women", match.starts_at_utc, match.match_no))
    return ScheduleData(
        version=f"wikipedia-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        source_name="Wikipedia 2026 FIVB Volleyball Nations League pages",
        source_url=f"{WOMEN_URL} | {MEN_URL}",
        generated_at=datetime.now(timezone.utc),
        matches=matches,
    )


def write_schedule(schedule: ScheduleData, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(schedule.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the VNL 2026 schedule from Wikipedia.")
    parser.add_argument("--out", type=Path, default=Path("data/cache/vnl_2026.json"))
    args = parser.parse_args()
    schedule = import_wikipedia()
    write_schedule(schedule, args.out)
    counts = {"women": 0, "men": 0}
    for match in schedule.matches:
        counts[match.competition] += 1
    print(f"Wrote {args.out} with {counts['women']} women matches and {counts['men']} men matches")


if __name__ == "__main__":
    main()
