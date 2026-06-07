from datetime import datetime, timezone

from vnl_schedule.models import Match, ScheduleData
from vnl_schedule.update_wikipedia import changed_fields, diff_schedules


def make_match(**overrides):
    data = {
        "competition": "women",
        "phase": "Preliminary",
        "round": "Week 1 P1",
        "match_no": "W001",
        "starts_at_utc": datetime(2026, 6, 3, 15, 0, tzinfo=timezone.utc),
        "team_a": "Ukraine",
        "team_b": "United States",
        "venue": "Centre Videotron",
        "city": "Quebec City",
        "country": "Canada",
        "status": "scheduled",
    }
    data.update(overrides)
    return Match.model_validate(data)


def test_diff_schedules_detects_changed_time():
    existing = ScheduleData(matches=[make_match()])
    latest = ScheduleData(matches=[make_match(starts_at_utc=datetime(2026, 6, 3, 16, 0, tzinfo=timezone.utc))])

    diff = diff_schedules(existing, latest)

    assert not diff.added
    assert not diff.removed
    assert len(diff.changed) == 1


def test_diff_schedules_detects_added_and_removed_matches():
    existing = ScheduleData(matches=[make_match(team_a="A", team_b="B")])
    latest = ScheduleData(matches=[make_match(team_a="C", team_b="D")])

    diff = diff_schedules(existing, latest)

    assert len(diff.added) == 1
    assert len(diff.removed) == 1


def test_changed_fields_describes_field_values():
    before = make_match(status="scheduled")
    after = make_match(status="completed")

    assert changed_fields(before, after) == "status: scheduled -> completed"


def test_diff_schedules_detects_changed_score():
    existing = ScheduleData(matches=[make_match(score=None, status="scheduled")])
    latest = ScheduleData(matches=[make_match(score="3-0", status="completed")])

    diff = diff_schedules(existing, latest)

    assert len(diff.changed) == 1
    assert "score:  -> 3-0" in changed_fields(*diff.changed[0])
