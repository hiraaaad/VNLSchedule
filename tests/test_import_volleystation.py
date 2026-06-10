from datetime import datetime, timezone

from vnl_schedule.import_volleystation import (
    page_represents_2026,
    page_diagnostics,
    parse_home_upcoming_page,
    parse_results_page,
)


def test_parse_women_completed_result_from_volleystation_shape():
    html = """
    <main>
      <h1>VNL 2026 Women</h1>
      <div>3 June 2026, Wednesday</div>
      <a href="/en/matches/1/">
        Round 1 • No. 1 Nanjing Youth Olympic Games Sports Park Gymnasium
        Belgium BEL Poland POL 2 3 25 20 21 25 25 20 22 25 10 15 View details
      </a>
    </main>
    """

    matches = parse_results_page(html, "women")

    assert len(matches) == 1
    assert matches[0].competition == "women"
    assert matches[0].match_no == "W001"
    assert matches[0].team_a == "Belgium"
    assert matches[0].team_b == "Poland"
    assert matches[0].score == "2-3"
    assert matches[0].venue == "Nanjing Youth Olympic Games Sports Park Gymnasium"
    assert matches[0].city == "Nanjing"
    assert matches[0].pool == 3


def test_parse_upcoming_result_row_keeps_score_empty_and_converts_time():
    html = """
    <main>
      <h1>VNL 2026 Women</h1>
      <div>17 June 2026, Wednesday</div>
      <a href="/en/matches/37/">
        Round 37 • No. 37 PhilSports Arena Dominican Republic DOM USA USA 06:00 View details
      </a>
    </main>
    """

    matches = parse_results_page(html, "women")

    assert len(matches) == 1
    assert matches[0].score is None
    assert matches[0].starts_at_utc == datetime(2026, 6, 17, 4, 0, tzinfo=timezone.utc)
    assert matches[0].team_a == "Dominican Republic"
    assert matches[0].team_b == "United States"


def test_parse_men_home_upcoming_row():
    html = """
    <main>
      <h1>VNL 2026 Men</h1>
      <a href="/en/matches/2491290/">10 Jun CUB 07:00 POL</a>
    </main>
    """

    matches = parse_home_upcoming_page(html, "men")

    assert len(matches) == 1
    assert matches[0].competition == "men"
    assert matches[0].team_a == "Cuba"
    assert matches[0].team_b == "Poland"
    assert matches[0].score is None
    assert matches[0].starts_at_utc == datetime(2026, 6, 10, 5, 0, tzinfo=timezone.utc)


def test_rejects_stale_2025_men_results_page_for_2026():
    html = "<main><h1>VNL 2025 Men</h1><a>Round 1 • No. 1 Cuba CUB Poland POL 3 0 View details</a></main>"

    assert page_represents_2026(html, "men") is False


def test_page_diagnostics_summarizes_skipped_page():
    html = "<html><head><title>Denied</title></head><body>Access denied. Please enable JavaScript.</body></html>"

    diagnostics = page_diagnostics(html, url="https://example.test/results/")

    assert "url=https://example.test/results/" in diagnostics
    assert "title=Denied" in diagnostics
    assert "has_access_denied=True" in diagnostics
    assert "has_enable_javascript=True" in diagnostics
