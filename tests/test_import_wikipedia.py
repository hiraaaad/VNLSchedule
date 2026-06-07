from bs4 import BeautifulSoup

from vnl_schedule.import_wikipedia import normalize_score, parse_pool_matches, parse_utc_offset


def test_parse_utc_offset_handles_unicode_minus():
    tz = parse_utc_offset("All times are Eastern Daylight Time ( UTC\u221204:00 ).")

    assert tz.utcoffset(None).total_seconds() == -4 * 60 * 60


def test_parse_pool_matches_from_wikipedia_shape():
    html = """
    <h4 id="Pool_1">Pool 1</h4>
    <ul><li>All times are Eastern Daylight Time ( UTC\u221204:00 ).</li></ul>
    <table>
      <tr><th>Date</th><th>Time</th><th></th><th>Score</th><th></th></tr>
      <tr><td>3 Jun</td><td>11:00</td><td>Ukraine</td><td>0\u20133</td><td>United States</td></tr>
      <tr><td>5 Jun</td><td>20:30</td><td>France</td><td>\u2013</td><td>United States</td></tr>
    </table>
    """

    matches = parse_pool_matches(BeautifulSoup(html, "html.parser"), "women")

    assert len(matches) == 2
    assert matches[0].team_a == "Ukraine"
    assert matches[0].team_b == "United States"
    assert matches[0].starts_at_utc.isoformat() == "2026-06-03T15:00:00+00:00"
    assert matches[0].status == "completed"
    assert matches[0].score == "0-3"
    assert matches[1].status == "scheduled"
    assert matches[1].score is None


def test_normalize_score_handles_results_and_empty_scores():
    assert normalize_score("3\u20131") == "3-1"
    assert normalize_score(" 2 - 3 ") == "2-3"
    assert normalize_score("\u2013") is None
    assert normalize_score("") is None
