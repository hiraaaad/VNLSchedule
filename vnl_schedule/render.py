from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schedule import ROOT, DEFAULT_TIMEZONE, RenderSection

TEMPLATE_DIR = ROOT / "vnl_schedule" / "templates"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def timezone_label(timezone_name: str) -> str:
    now = datetime.now(ZoneInfo(timezone_name))
    offset = now.strftime("%z")
    offset_label = f"UTC{offset[:3]}:{offset[3:]}"
    return f"{timezone_name} ({now.tzname()}, {offset_label})"


def render_schedule_html(
    *,
    sections: list[RenderSection],
    timezone_name: str = DEFAULT_TIMEZONE,
    highlight: str = "",
    source_name: str,
    source_url: str,
    version: str,
    generated_at: datetime | None = None,
    print_mode: bool = False,
) -> str:
    template = env.get_template("schedule.html")
    generated = generated_at or datetime.now(ZoneInfo(timezone_name))
    return template.render(
        sections=sections,
        timezone_name=timezone_name,
        timezone_label=timezone_label(timezone_name),
        highlight=highlight,
        source_name=source_name,
        source_url=source_url,
        version=version,
        generated_at=generated.astimezone(ZoneInfo(timezone_name)),
        print_mode=print_mode,
    )
