from datetime import datetime, timezone

from vnl_schedule.models import Match, ScheduleData
from vnl_schedule.update_volleystation import changed_fields, diff_schedules, update_from_volleystation


def make_match(**overrides):
    data = {
        "competition": "women",
        "phase": "Preliminary",
        "round": "Week 1 P3",
        "match_no": "W001",
        "starts_at_utc": datetime(2026, 6, 3, 3, 30, tzinfo=timezone.utc),
        "team_a": "Belgium",
        "team_b": "Poland",
        "venue": "Nanjing Youth Olympic Games Sports Park Gymnasium",
        "city": "Nanjing",
        "country": "China",
        "status": "scheduled",
    }
    data.update(overrides)
    return Match.model_validate(data)


def test_diff_schedules_detects_changed_score():
    existing = ScheduleData(matches=[make_match(score=None, status="scheduled")])
    latest = ScheduleData(matches=[make_match(score="2-3", status="completed")])

    diff = diff_schedules(existing, latest)

    assert len(diff.changed) == 1
    assert "score:  -> 2-3" in changed_fields(*diff.changed[0])


def test_update_from_volleystation_writes_both_json_files(tmp_path, monkeypatch):
    static_path = tmp_path / "vnl_2026.json"
    cache_path = tmp_path / "cache" / "vnl_2026.json"
    existing = ScheduleData(matches=[make_match()])
    latest = ScheduleData(matches=[make_match(score="2-3", status="completed")])
    static_path.write_text(existing.model_dump_json(), encoding="utf-8")

    monkeypatch.setattr("vnl_schedule.update_volleystation.import_volleystation", lambda existing: latest)

    diff = update_from_volleystation(static_path=static_path, cache_path=cache_path, write=True)

    assert diff.has_changes
    assert ScheduleData.model_validate_json(static_path.read_text(encoding="utf-8")).matches[0].score == "2-3"
    assert ScheduleData.model_validate_json(cache_path.read_text(encoding="utf-8")).matches[0].score == "2-3"
