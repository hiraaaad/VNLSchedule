from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, NavigableString

from .models import Competition, Match, ScheduleData

WOMEN_RESULTS_URL = "https://vnlw.volleystation.com/en/results/"
MEN_RESULTS_URL = "https://vnlm.volleystation.com/en/results/"
MEN_HOME_URL = "https://vnlm.volleystation.com/en/"
DISPLAY_TIMEZONE = ZoneInfo("Europe/Warsaw")
DEBUG_DIR_ENV = "VNL_DEBUG_DIR"

TEAM_BY_ABBR = {
    "ARG": "Argentina",
    "BEL": "Belgium",
    "BRA": "Brazil",
    "BUL": "Bulgaria",
    "CAN": "Canada",
    "CHN": "China",
    "CUB": "Cuba",
    "CZE": "Czech Republic",
    "DOM": "Dominican Republic",
    "FRA": "France",
    "GER": "Germany",
    "IRI": "Iran",
    "ITA": "Italy",
    "JPN": "Japan",
    "NED": "Netherlands",
    "POL": "Poland",
    "SRB": "Serbia",
    "SLO": "Slovenia",
    "THA": "Thailand",
    "TUR": "Turkey",
    "UKR": "Ukraine",
    "USA": "United States",
}

VENUE_META: dict[str, tuple[str, str, str, int | None]] = {
    "Ankara Sports Hall": ("Ankara Sports Hall", "Ankara", "Turkey", 4),
    "Arena Nilson Nelson": ("Arena Nilson Nelson", "Brasilia", "Brazil", 2),
    "Arena Stožice Ljubljana": ("Arena Stozice Ljubljana", "Ljubljana", "Slovenia", 6),
    "Asue Arena": ("Asue Arena Osaka", "Osaka", "Japan", 9),
    "Belgrade Arena": ("Belgrade Arena", "Belgrade", "Serbia", 7),
    "Centre Vidéotron": ("Centre Videotron", "Quebec City", "Canada", 1),
    "Co'met Arena": ("Co'met Arena", "Orleans", "France", 4),
    "Gliwice Arena": ("Gliwice Arena", "Gliwice", "Poland", 5),
    "Indoor Stadium Huamark": ("Indoor Stadium Huamark", "Bangkok", "Thailand", 6),
    "Kai Tak Sports Park": ("Kai Tak Sports Park", "Hong Kong", "China", 8),
    "Linyi": ("Linyi Olympic Sports Park Gymnasium", "Linyi", "China", 3),
    "Nanjing Youth Olympic Games Sports Park Gymnasium": (
        "Nanjing Youth Olympic Games Sports Park Gymnasium",
        "Nanjing",
        "China",
        3,
    ),
    "Now Arena": ("NOW Arena", "Chicago", "United States", 8),
    "PhilSports Arena": ("PhilSports Arena", "Pasig", "Philippines", 5),
    "TD Place": ("TD Place", "Ottawa", "Canada", 1),
}


@dataclass(frozen=True)
class VolleyStationMatch:
    competition: Competition
    match_no: str
    source_no: int | None
    source_date: datetime | None
    starts_at_utc: datetime | None
    team_a: str
    team_b: str
    score: str | None
    venue: str = ""
    city: str = ""
    country: str = ""
    pool: int | None = None


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8")
            write_debug_artifacts(url=url, html=html, method="urllib")
            return html
    except HTTPError as error:
        if error.code != 403:
            raise
        return fetch_html_with_browser(url)


def fetch_html_with_browser(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            )
        )
        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_timeout(3_000)
        html = page.content()
        write_debug_artifacts(
            url=url,
            html=html,
            method="playwright",
            final_url=page.url,
            title=page.title(),
            visible_text=page.locator("body").inner_text(timeout=5_000) if page.locator("body").count() else "",
            screenshot=page.screenshot(full_page=True),
        )
        browser.close()
        return html


def debug_slug(url: str) -> str:
    slug = re.sub(r"^https?://", "", url).strip("/")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    return slug or "volleystation"


def debug_dir() -> Path | None:
    value = os.environ.get(DEBUG_DIR_ENV)
    if not value:
        return None
    path = Path(value)
    path.mkdir(parents=True, exist_ok=True)
    return path


def page_text(html: str) -> str:
    return normalize_text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))


def page_diagnostics(html: str, *, url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = page_text(html)
    title = normalize_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    flags = [
        f"url={url}",
        f"title={title or '(none)'}",
        f"html_chars={len(html)}",
        f"text_chars={len(text)}",
        f"has_vnl_2026={'VNL 2026' in text}",
        f"has_vnl_2026_women={'VNL 2026 Women' in text}",
        f"has_vnl_2026_men={'VNL 2026 Men' in text}",
        f"has_cloudflare={'cloudflare' in html.casefold() or 'cloudflare' in text.casefold()}",
        f"has_access_denied={'access denied' in text.casefold()}",
        f"has_enable_javascript={'enable javascript' in text.casefold()}",
        f"text_preview={text[:500]}",
    ]
    return " | ".join(flags)


def write_debug_artifacts(
    *,
    url: str,
    html: str,
    method: str,
    final_url: str = "",
    title: str = "",
    visible_text: str = "",
    screenshot: bytes | None = None,
) -> None:
    path = debug_dir()
    if path is None:
        return
    slug = debug_slug(url)
    text = normalize_text(visible_text) if visible_text else page_text(html)
    metadata = {
        "url": url,
        "final_url": final_url or url,
        "method": method,
        "title": title,
        "html_chars": len(html),
        "text_chars": len(text),
        "has_vnl_2026": "VNL 2026" in text,
        "has_vnl_2026_women": "VNL 2026 Women" in text,
        "has_vnl_2026_men": "VNL 2026 Men" in text,
        "has_cloudflare": "cloudflare" in html.casefold() or "cloudflare" in text.casefold(),
        "has_access_denied": "access denied" in text.casefold(),
        "has_enable_javascript": "enable javascript" in text.casefold(),
    }
    (path / f"{slug}.html").write_text(html, encoding="utf-8")
    (path / f"{slug}.txt").write_text(text, encoding="utf-8")
    (path / f"{slug}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if screenshot:
        (path / f"{slug}.png").write_bytes(screenshot)


def write_schedule(schedule: ScheduleData, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(schedule.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_score_parts(left: str, right: str) -> str | None:
    if left.isdigit() and right.isdigit() and 0 <= int(left) <= 3 and 0 <= int(right) <= 3:
        if int(left) == 3 or int(right) == 3:
            return f"{int(left)}-{int(right)}"
    return None


def parse_date_line(value: str) -> datetime | None:
    match = re.search(r"\b(\d{1,2})\s+([A-Z][a-z]+)\s+2026\b", value)
    if not match:
        return None
    return datetime.strptime(f"{match.group(1)} {match.group(2)} 2026", "%d %B %Y").replace(
        tzinfo=DISPLAY_TIMEZONE
    )


def parse_short_date_time(day: str, month: str, time_text: str) -> datetime:
    local_dt = datetime.strptime(f"{day} {month} 2026 {time_text}", "%d %b %Y %H:%M").replace(
        tzinfo=DISPLAY_TIMEZONE
    )
    return local_dt.astimezone(timezone.utc)


def prefixed_match_no(competition: Competition, source_no: int | None) -> str:
    if source_no is None:
        return ""
    return f"{competition[0].upper()}{source_no:03d}"


def week_label(source_no: int | None) -> str:
    if source_no is None:
        return "Week 1"
    if source_no <= 36:
        return "Week 1"
    if source_no <= 72:
        return "Week 2"
    return "Week 3"


def venue_metadata(raw_venue: str) -> tuple[str, str, str, int | None]:
    for needle, meta in VENUE_META.items():
        if needle.casefold() in raw_venue.casefold():
            return meta
    return raw_venue, "", "", None


def round_label(source_no: int | None, pool: int | None) -> str:
    week = week_label(source_no)
    return f"{week} P{pool}" if pool else week


def page_represents_2026(html: str, competition: Competition, *, allow_home: bool = False) -> bool:
    text = normalize_text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    label = "Women" if competition == "women" else "Men"
    if f"VNL 2026 {label}" in text:
        return True
    if allow_home and competition == "men" and "Upcoming" in text and "Copyright © 2026" in text:
        return True
    return False


def parse_round_link(text: str, competition: Competition, current_date: datetime | None) -> VolleyStationMatch | None:
    match = re.search(r"Round\s+(\d+)\s*•\s*No\.\s*(\d+)\s+(.+?)\s+View details\b", text)
    if not match:
        return None

    source_no = int(match.group(2))
    tokens = match.group(3).split()
    abbr_positions = [index for index, token in enumerate(tokens) if token in TEAM_BY_ABBR]
    if len(abbr_positions) < 2:
        return None

    first_abbr_index = abbr_positions[0]
    second_abbr_index = abbr_positions[1]
    for candidate in abbr_positions[1:]:
        next_token = tokens[candidate + 1] if candidate + 1 < len(tokens) else ""
        following_token = tokens[candidate + 2] if candidate + 2 < len(tokens) else ""
        if re.fullmatch(r"\d{1,2}:\d{2}", next_token) or normalize_score_parts(next_token, following_token):
            second_abbr_index = candidate
            break
    abbr_a = tokens[first_abbr_index]
    abbr_b = tokens[second_abbr_index]
    team_a = TEAM_BY_ABBR[abbr_a]
    team_b = TEAM_BY_ABBR[abbr_b]

    team_a_start = max(first_abbr_index - len(team_a.split()), 0)
    raw_venue = normalize_text(" ".join(tokens[:team_a_start]))
    venue, city, country, pool = venue_metadata(raw_venue)

    after_teams = tokens[second_abbr_index + 1 :]
    score = None
    starts_at_utc = None
    if len(after_teams) >= 2:
        score = normalize_score_parts(after_teams[0], after_teams[1])
    if not score and after_teams and re.fullmatch(r"\d{1,2}:\d{2}", after_teams[0]) and current_date:
        local_dt = current_date.replace(
            hour=int(after_teams[0].split(":")[0]),
            minute=int(after_teams[0].split(":")[1]),
        )
        starts_at_utc = local_dt.astimezone(timezone.utc)

    return VolleyStationMatch(
        competition=competition,
        match_no=prefixed_match_no(competition, source_no),
        source_no=source_no,
        source_date=current_date,
        starts_at_utc=starts_at_utc,
        team_a=team_a,
        team_b=team_b,
        score=score,
        venue=venue,
        city=city,
        country=country,
        pool=pool,
    )


def parse_home_upcoming_link(text: str, competition: Competition, sequence: int) -> VolleyStationMatch | None:
    match = re.search(r"\b(\d{1,2})\s+([A-Z][a-z]{2})\s+([A-Z]{3})\s+(\d{1,2}:\d{2})\s+([A-Z]{3})\b", text)
    if not match:
        return None
    abbr_a = match.group(3)
    abbr_b = match.group(5)
    if abbr_a not in TEAM_BY_ABBR or abbr_b not in TEAM_BY_ABBR:
        return None
    starts_at_utc = parse_short_date_time(match.group(1), match.group(2), match.group(4))
    return VolleyStationMatch(
        competition=competition,
        match_no=prefixed_match_no(competition, sequence),
        source_no=sequence,
        source_date=starts_at_utc.astimezone(DISPLAY_TIMEZONE),
        starts_at_utc=starts_at_utc,
        team_a=TEAM_BY_ABBR[abbr_a],
        team_b=TEAM_BY_ABBR[abbr_b],
        score=None,
    )


def parse_results_page(html: str, competition: Competition) -> list[VolleyStationMatch]:
    soup = BeautifulSoup(html, "html.parser")
    current_date: datetime | None = None
    matches: list[VolleyStationMatch] = []
    seen: set[tuple[str, str, str]] = set()

    for node in soup.descendants:
        if isinstance(node, NavigableString):
            if getattr(node.parent, "name", None) == "a":
                continue
            parsed_date = parse_date_line(str(node))
            if parsed_date is not None:
                current_date = parsed_date
            continue
        if getattr(node, "name", None) != "a":
            continue
        parsed = parse_round_link(normalize_text(node.get_text(" ", strip=True)), competition, current_date)
        if parsed is None:
            continue
        key = (parsed.match_no, parsed.team_a, parsed.team_b)
        if key in seen:
            continue
        seen.add(key)
        matches.append(parsed)
    return matches


def parse_home_upcoming_page(html: str, competition: Competition) -> list[VolleyStationMatch]:
    soup = BeautifulSoup(html, "html.parser")
    matches: list[VolleyStationMatch] = []
    for sequence, link in enumerate(soup.find_all("a"), start=1):
        parsed = parse_home_upcoming_link(normalize_text(link.get_text(" ", strip=True)), competition, sequence)
        if parsed is not None:
            matches.append(parsed)
    return matches


def team_key(value: str) -> str:
    return value.casefold().replace("türkiye", "turkey").replace("czechia", "czech republic")


def existing_match_key(match: Match) -> tuple[str, str, str, str]:
    local_date = match.starts_at_utc.astimezone(DISPLAY_TIMEZONE).date().isoformat()
    return (match.competition, local_date, team_key(match.team_a), team_key(match.team_b))


def parsed_match_key(match: VolleyStationMatch) -> tuple[str, str, str, str] | None:
    source_date = match.source_date or (match.starts_at_utc.astimezone(DISPLAY_TIMEZONE) if match.starts_at_utc else None)
    if source_date is None:
        return None
    return (match.competition, source_date.date().isoformat(), team_key(match.team_a), team_key(match.team_b))


def merge_matches(existing: ScheduleData | None, parsed_matches: list[VolleyStationMatch]) -> list[Match]:
    existing_matches = existing.matches if existing else []
    existing_by_key = {existing_match_key(match): match for match in existing_matches}
    used_existing_keys: set[tuple[str, str, str, str]] = set()
    output: list[Match] = []

    for parsed in parsed_matches:
        key = parsed_match_key(parsed)
        existing_match = existing_by_key.get(key) if key else None
        if key and existing_match:
            used_existing_keys.add(key)

        starts_at_utc = parsed.starts_at_utc or (existing_match.starts_at_utc if existing_match else None)
        if starts_at_utc is None:
            continue

        venue = parsed.venue or (existing_match.venue if existing_match else "")
        city = parsed.city or (existing_match.city if existing_match else "")
        country = parsed.country or (existing_match.country if existing_match else "")
        round_value = round_label(parsed.source_no, parsed.pool) if parsed.pool else (existing_match.round if existing_match else round_label(parsed.source_no, None))
        status = "completed" if parsed.score else "scheduled"

        output.append(
            Match(
                competition=parsed.competition,
                phase=existing_match.phase if existing_match else "Preliminary",
                round=round_value,
                match_no=parsed.match_no or (existing_match.match_no if existing_match else ""),
                starts_at_utc=starts_at_utc,
                team_a=parsed.team_a,
                team_b=parsed.team_b,
                score=parsed.score,
                venue=venue,
                city=city,
                country=country,
                status=status,
            )
        )

    parsed_competitions = {match.competition for match in parsed_matches}
    parsed_counts = {competition: sum(1 for match in parsed_matches if match.competition == competition) for competition in ("women", "men")}
    existing_counts = {competition: sum(1 for match in existing_matches if match.competition == competition) for competition in ("women", "men")}
    for existing_match in existing_matches:
        key = existing_match_key(existing_match)
        if key in used_existing_keys:
            continue
        if existing_match.competition in parsed_competitions and parsed_counts[existing_match.competition] >= existing_counts[existing_match.competition]:
            continue
        output.append(existing_match)

    output.sort(key=lambda match: (match.competition != "women", match.starts_at_utc, match.match_no))
    return output


def import_volleystation(existing: ScheduleData | None = None) -> ScheduleData:
    sources: list[str] = []
    parsed_matches: list[VolleyStationMatch] = []

    women_html = fetch_html(WOMEN_RESULTS_URL)
    if page_represents_2026(women_html, "women"):
        women_matches = parse_results_page(women_html, "women")
        parsed_matches.extend(women_matches)
        sources.append(f"Women VolleyStation results ({len(women_matches)} matches)")
    else:
        sources.append("Women VolleyStation results skipped: page is not VNL 2026 Women")
        sources.append(f"  Diagnostics: {page_diagnostics(women_html, url=WOMEN_RESULTS_URL)}")

    men_results_html = fetch_html(MEN_RESULTS_URL)
    if page_represents_2026(men_results_html, "men"):
        men_matches = parse_results_page(men_results_html, "men")
        parsed_matches.extend(men_matches)
        sources.append(f"Men VolleyStation results ({len(men_matches)} matches)")
    else:
        sources.append("Men VolleyStation results skipped: page is not VNL 2026 Men")
        sources.append(f"  Diagnostics: {page_diagnostics(men_results_html, url=MEN_RESULTS_URL)}")
        men_home_html = fetch_html(MEN_HOME_URL)
        if page_represents_2026(men_home_html, "men", allow_home=True):
            men_home_matches = parse_home_upcoming_page(men_home_html, "men")
            parsed_matches.extend(men_home_matches)
            sources.append(f"Men VolleyStation upcoming home ({len(men_home_matches)} matches)")
        else:
            sources.append("Men VolleyStation home skipped: page is not current VNL 2026")
            sources.append(f"  Diagnostics: {page_diagnostics(men_home_html, url=MEN_HOME_URL)}")

    matches = merge_matches(existing, parsed_matches)
    print("VolleyStation source summary:")
    for source in sources:
        print(f"- {source}")
    print(
        "VolleyStation parsed matches: "
        f"{sum(1 for match in parsed_matches if match.competition == 'women')} women, "
        f"{sum(1 for match in parsed_matches if match.competition == 'men')} men"
    )
    print(
        "Schedule output matches: "
        f"{sum(1 for match in matches if match.competition == 'women')} women, "
        f"{sum(1 for match in matches if match.competition == 'men')} men"
    )
    return ScheduleData(
        version=f"volleystation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        source_name="VolleyStation VNL 2026 schedule and results",
        source_url=f"{WOMEN_RESULTS_URL} | {MEN_RESULTS_URL} | {MEN_HOME_URL}",
        generated_at=datetime.now(timezone.utc),
        matches=matches,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the VNL 2026 schedule and results from VolleyStation.")
    parser.add_argument("--out", type=Path, default=Path("data/cache/vnl_2026.json"))
    args = parser.parse_args()
    schedule = import_volleystation()
    write_schedule(schedule, args.out)
    counts = {"women": 0, "men": 0}
    for match in schedule.matches:
        counts[match.competition] += 1
    print(f"Wrote {args.out} with {counts['women']} women matches and {counts['men']} men matches")


if __name__ == "__main__":
    main()
