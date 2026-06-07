from datetime import datetime, timezone

from vnl_schedule.models import Match, ScheduleData
from vnl_schedule.render import render_schedule_html
from vnl_schedule.schedule import build_sections, convert_match, team_label


def make_match(**overrides):
    data = {
        "competition": "women",
        "phase": "Preliminary",
        "round": "Week 1",
        "match_no": "",
        "starts_at_utc": datetime(2026, 6, 3, 23, 0, tzinfo=timezone.utc),
        "team_a": "Brazil",
        "team_b": "Netherlands",
        "venue": "Arena BRB",
        "city": "Brasilia",
        "country": "Brazil",
        "status": "scheduled",
    }
    data.update(overrides)
    return Match.model_validate(data)


def test_timezone_conversion_rolls_into_perth_next_day():
    rendered = convert_match(make_match(), "Australia/Perth")

    assert rendered.local_datetime.day == 4
    assert rendered.time_label == "07:00"


def test_sections_keep_women_before_men():
    schedule = ScheduleData(
        matches=[
            make_match(competition="men", team_a="Poland", team_b="Cuba", round="Week 1 P1"),
            make_match(competition="women", team_a="Brazil", team_b="Netherlands", round="Week 1 P1"),
        ]
    )

    sections = build_sections(schedule, "Australia/Perth", ["women", "men"])

    assert [section.competition for section in sections] == ["women", "men"]
    assert [section.title for section in sections] == ["WK1 Women", "WK1 Men"]


def test_printed_html_uses_local_time_without_source_time():
    schedule = ScheduleData(
        version="test",
        source_name="Test source",
        matches=[make_match()],
    )
    sections = build_sections(schedule, "Australia/Perth", ["women"])

    html = render_schedule_html(
        sections=sections,
        timezone_name="Australia/Perth",
        source_name=schedule.source_name,
        source_url=schedule.source_url,
        version=schedule.version,
        print_mode=True,
    )

    assert "07:00" in html
    assert "23:00" not in html
    assert "UTC" in html


def test_show_results_controls_score_rendering():
    schedule = ScheduleData(
        version="test",
        source_name="Test source",
        matches=[make_match(score="3-1", status="completed")],
    )
    sections = build_sections(schedule, "Australia/Perth", ["women"])

    without_results = render_schedule_html(
        sections=sections,
        timezone_name="Australia/Perth",
        source_name=schedule.source_name,
        source_url=schedule.source_url,
        version=schedule.version,
        show_results=False,
    )
    with_results = render_schedule_html(
        sections=sections,
        timezone_name="Australia/Perth",
        source_name=schedule.source_name,
        source_url=schedule.source_url,
        version=schedule.version,
        show_results=True,
    )

    assert "Brazil v" in without_results
    assert "3-1" not in without_results
    assert "Brazil 3-1" in with_results


def test_team_label_adds_country_flag():
    assert team_label("Brazil").endswith(" Brazil")
    assert team_label("Brazil") != "Brazil"
    assert team_label("Unknown Team") == "Unknown Team"


def test_round_label_compacts_week_text():
    rendered = convert_match(make_match(round="Week 2 P4"), "Australia/Perth")

    assert rendered.round_label == "P4"


def test_result_label_uses_score_when_present():
    rendered = convert_match(make_match(score="3-2"), "Australia/Perth")

    assert "3-2" in rendered.result_label
