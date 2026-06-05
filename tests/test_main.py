from vnl_schedule.main import assert_timezone, timezone_choices


def test_timezone_aliases_resolve_to_iana_names():
    assert assert_timezone("Indonesia") == "Asia/Jakarta"
    assert assert_timezone("Philippines") == "Asia/Manila"
    assert assert_timezone("Western Australia") == "Australia/Perth"


def test_timezone_choices_include_global_options():
    choices = timezone_choices()

    assert "Australia/Perth" in choices
    assert "Asia/Jakarta" in choices
    assert "America/New_York" in choices
