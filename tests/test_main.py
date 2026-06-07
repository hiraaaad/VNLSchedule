from vnl_schedule.main import all_timezone_aliases, assert_timezone, timezone_choices


def test_timezone_aliases_resolve_to_iana_names():
    assert assert_timezone("Indonesia") == "Asia/Jakarta"
    assert assert_timezone("Philippines") == "Asia/Manila"
    assert assert_timezone("Western Australia") == "Australia/Perth"
    assert assert_timezone("Krakow") == "Europe/Warsaw"
    assert assert_timezone("Krak\u00f3w") == "Europe/Warsaw"
    assert assert_timezone("Gliwice") == "Europe/Warsaw"
    assert assert_timezone("Kansas City") == "America/Chicago"
    assert assert_timezone("Quebec City") == "America/Toronto"


def test_timezone_choices_include_global_options():
    choices = timezone_choices()

    assert "Australia/Perth" in choices
    assert "Asia/Jakarta" in choices
    assert "America/New_York" in choices


def test_generated_timezone_aliases_include_city_names():
    aliases = all_timezone_aliases()

    assert aliases["warsaw"] == "Europe/Warsaw"
    assert aliases["new york"] == "America/New_York"
    assert aliases["kansas city"] == "America/Chicago"
