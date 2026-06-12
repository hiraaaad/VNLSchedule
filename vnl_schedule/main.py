from __future__ import annotations

from html import escape
import re
import unicodedata
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from fastapi import FastAPI, Query, Response
from fastapi.responses import HTMLResponse

from .models import Competition
from .pdf import html_to_pdf
from .render import render_schedule_html
from .schedule import DEFAULT_TIMEZONE, available_teams, build_sections, load_schedule

app = FastAPI(title="VNL Schedule PDF")

POPULAR_TIMEZONES = [
    "Australia/Perth",
    "Australia/Sydney",
    "Pacific/Auckland",
    "Asia/Bangkok",
    "Asia/Ho_Chi_Minh",
    "Asia/Jakarta",
    "Asia/Kuala_Lumpur",
    "Asia/Manila",
    "Asia/Singapore",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Asia/Dubai",
    "Europe/London",
    "Europe/Paris",
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "UTC",
]

TIMEZONE_ALIASES = {
    "awst": "Australia/Perth",
    "perth": "Australia/Perth",
    "western australia": "Australia/Perth",
    "wa": "Australia/Perth",
    "aest": "Australia/Sydney",
    "australia": "Australia/Sydney",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "adelaide": "Australia/Adelaide",
    "auckland": "Pacific/Auckland",
    "new zealand": "Pacific/Auckland",
    "indonesia": "Asia/Jakarta",
    "jakarta": "Asia/Jakarta",
    "bali": "Asia/Makassar",
    "malaysia": "Asia/Kuala_Lumpur",
    "kuala lumpur": "Asia/Kuala_Lumpur",
    "philippines": "Asia/Manila",
    "manila": "Asia/Manila",
    "singapore": "Asia/Singapore",
    "thailand": "Asia/Bangkok",
    "bangkok": "Asia/Bangkok",
    "vietnam": "Asia/Ho_Chi_Minh",
    "china": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "japan": "Asia/Tokyo",
    "tokyo": "Asia/Tokyo",
    "korea": "Asia/Seoul",
    "south korea": "Asia/Seoul",
    "uae": "Asia/Dubai",
    "dubai": "Asia/Dubai",
    "uk": "Europe/London",
    "london": "Europe/London",
    "france": "Europe/Paris",
    "paris": "Europe/Paris",
    "poland": "Europe/Warsaw",
    "warsaw": "Europe/Warsaw",
    "krakow": "Europe/Warsaw",
    "krak\u00f3w": "Europe/Warsaw",
    "gliwice": "Europe/Warsaw",
    "slovenia": "Europe/Ljubljana",
    "ljubljana": "Europe/Ljubljana",
    "serbia": "Europe/Belgrade",
    "belgrade": "Europe/Belgrade",
    "italy": "Europe/Rome",
    "rome": "Europe/Rome",
    "germany": "Europe/Berlin",
    "berlin": "Europe/Berlin",
    "bulgaria": "Europe/Sofia",
    "sofia": "Europe/Sofia",
    "czech republic": "Europe/Prague",
    "czechia": "Europe/Prague",
    "prague": "Europe/Prague",
    "netherlands": "Europe/Amsterdam",
    "amsterdam": "Europe/Amsterdam",
    "belgium": "Europe/Brussels",
    "brussels": "Europe/Brussels",
    "ukraine": "Europe/Kyiv",
    "kyiv": "Europe/Kyiv",
    "kiev": "Europe/Kyiv",
    "turkey": "Europe/Istanbul",
    "turkiye": "Europe/Istanbul",
    "istanbul": "Europe/Istanbul",
    "brazil": "America/Sao_Paulo",
    "brasilia": "America/Sao_Paulo",
    "canada eastern": "America/Toronto",
    "toronto": "America/Toronto",
    "usa eastern": "America/New_York",
    "new york": "America/New_York",
    "usa central": "America/Chicago",
    "chicago": "America/Chicago",
    "kansas city": "America/Chicago",
    "dallas": "America/Chicago",
    "houston": "America/Chicago",
    "usa pacific": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "vancouver": "America/Vancouver",
    "atlanta": "America/New_York",
    "boston": "America/New_York",
    "miami": "America/New_York",
    "philadelphia": "America/New_York",
    "toronto": "America/Toronto",
    "montreal": "America/Toronto",
    "ottawa": "America/Toronto",
    "quebec city": "America/Toronto",
    "mexico city": "America/Mexico_City",
    "guadalajara": "America/Mexico_City",
    "monterrey": "America/Monterrey",
    "utc": "UTC",
}


def normalize_timezone_query(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def generated_timezone_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for zone in sorted(available_timezones()):
        if "/" not in zone:
            continue
        city = zone.rsplit("/", 1)[1].replace("_", " ")
        normalized = normalize_timezone_query(city)
        aliases.setdefault(normalized, zone)
    return aliases


def all_timezone_aliases() -> dict[str, str]:
    aliases = generated_timezone_aliases()
    aliases.update({normalize_timezone_query(alias): zone for alias, zone in TIMEZONE_ALIASES.items()})
    return aliases


def timezone_choices() -> list[str]:
    zones = sorted(available_timezones())
    preferred = [zone for zone in POPULAR_TIMEZONES if zone in zones or zone == "UTC"]
    return preferred + [zone for zone in zones if zone not in set(preferred)]


def parse_competitions(values: list[str] | None) -> list[Competition]:
    if not values:
        return ["women", "men"]
    selected: list[Competition] = []
    for value in values:
        if value in {"women", "men"}:
            selected.append(value)  # type: ignore[arg-type]
    return selected or ["women", "men"]


def assert_timezone(timezone_name: str) -> str:
    timezone_name = timezone_name.strip()
    timezone_name = all_timezone_aliases().get(normalize_timezone_query(timezone_name), timezone_name)
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        msg = f"Unknown timezone: {timezone_name}"
        raise ValueError(msg) from exc
    return timezone_name


def page_html(
    *,
    timezone_name: str,
    competitions: list[Competition],
    highlight: str,
    show_results: bool = False,
    hide_completed: bool = True,
    print_mode: bool = False,
) -> str:
    schedule = load_schedule()
    sections = build_sections(schedule, timezone_name, competitions, highlight, hide_completed)
    schedule_html = render_schedule_html(
        sections=sections,
        timezone_name=timezone_name,
        highlight=highlight,
        source_name=schedule.source_name,
        source_url=schedule.source_url,
        version=schedule.version,
        generated_at=schedule.generated_at,
        print_mode=print_mode,
        show_results=show_results,
    )
    if print_mode:
        return schedule_html

    controls = render_controls(
        timezone_name=timezone_name,
        competitions=competitions,
        highlight=highlight,
        show_results=show_results,
        hide_completed=hide_completed,
        teams=available_teams(schedule),
    )
    return schedule_html.replace("<!-- APP_CONTROLS -->", controls)


def render_controls(
    *,
    timezone_name: str,
    competitions: list[Competition],
    highlight: str,
    show_results: bool,
    hide_completed: bool,
    teams: list[str],
) -> str:
    selected = set(competitions)
    safe_timezone_name = escape(timezone_name, quote=True)
    timezone_options = "\n".join(
        f'<option value="{escape(zone, quote=True)}" {"selected" if zone == timezone_name else ""}>{escape(zone)}</option>'
        for zone in timezone_choices()
    )
    timezone_alias_options = "\n".join(
        f'<option value="{escape(alias.title(), quote=True)}">{escape(target)}</option>'
        for alias, target in sorted(all_timezone_aliases().items())
    )
    team_options = "\n".join(
        f'<option value="{escape(team, quote=True)}" {"selected" if team == highlight else ""}>{escape(team)}</option>'
        for team in teams
    )
    women_checked = "checked" if "women" in selected else ""
    men_checked = "checked" if "men" in selected else ""
    results_checked = "checked" if show_results else ""
    hide_completed_checked = "checked" if hide_completed else ""
    return f"""
    <form class="controls" method="get" action="/">
      <label>
        <span>Timezone</span>
        <input class="timezone-input" name="timezone_name" value="{safe_timezone_name}" list="timezones" placeholder="Country, city, or timezone">
        <datalist id="timezones">{timezone_alias_options}{timezone_options}</datalist>
      </label>
      <label class="check"><input type="checkbox" name="competition" value="women" {women_checked}> Women</label>
      <label class="check"><input type="checkbox" name="competition" value="men" {men_checked}> Men</label>
      <label class="check"><input type="checkbox" name="show_results" value="1" {results_checked}> Show results</label>
      <label class="check"><input type="checkbox" name="hide_completed" value="1" {hide_completed_checked}> Hide completed</label>
      <label>
        <span>Highlight</span>
        <select name="highlight">
          <option value="">No highlight</option>
          {team_options}
        </select>
      </label>
      <button type="submit">Preview</button>
      <button type="submit" formaction="/pdf" formmethod="get">Export PDF</button>
      <a class="support-link" href="https://www.buymeacoffee.com/hiraaaad" target="_blank" rel="noopener noreferrer">Buy me a coffee</a>
    </form>
    """


@app.get("/", response_class=HTMLResponse)
async def index(
    timezone_name: str = DEFAULT_TIMEZONE,
    competition: Annotated[list[str] | None, Query()] = None,
    highlight: str = "",
    show_results: bool = False,
    hide_completed: bool = True,
) -> str:
    timezone_name = assert_timezone(timezone_name)
    return page_html(
        timezone_name=timezone_name,
        competitions=parse_competitions(competition),
        highlight=highlight,
        show_results=show_results,
        hide_completed=hide_completed,
    )


@app.get("/pdf")
async def export_pdf(
    timezone_name: str = DEFAULT_TIMEZONE,
    competition: Annotated[list[str] | None, Query()] = None,
    highlight: str = "",
    show_results: bool = False,
    hide_completed: bool = True,
) -> Response:
    timezone_name = assert_timezone(timezone_name)
    html = page_html(
        timezone_name=timezone_name,
        competitions=parse_competitions(competition),
        highlight=highlight,
        show_results=show_results,
        hide_completed=hide_completed,
        print_mode=True,
    )
    pdf = await html_to_pdf(html)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="vnl-2026-schedule.pdf"'},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/timezones")
async def timezones() -> dict[str, object]:
    return {
        "default": DEFAULT_TIMEZONE,
        "aliases": all_timezone_aliases(),
        "timezones": timezone_choices(),
    }
