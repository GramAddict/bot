from unittest.mock import mock_open
import GramAddict.plugins.telegram as TelegramReports
import json

# LOAD SESSIONS EXAMPLE
with open(r"mock_data\sessions.json", "r") as file:
    sessions_txt = file.read()
    sessions_json = json.loads(sessions_txt)


def test_load_sessions(mocker):
    """Test if the function returns a list of dictionaries"""
    mock_file_content = sessions_txt
    mocker.patch("builtins.open", mock_open(read_data=mock_file_content))
    result = TelegramReports.load_sessions("test_user")
    assert isinstance(result, list), "Expected a list"
    assert isinstance(result[0], dict), "Expected a dictionary"


def test_calculate_duration():
    """Test if the function returns a number"""
    result = TelegramReports._calculate_session_duration(sessions_json[0])
    assert isinstance(result, int), "Expected an integer"


def test_calculate_duration_not_finisched():
    """Test if the function returns 0 if the session is not finished"""
    result = TelegramReports._calculate_session_duration(sessions_json[1])
    assert result == 0


def test_daily_summary():
    """Test if the function returns a dictionary and the values are correct"""
    results = TelegramReports.daily_summary(sessions_json)
    assert isinstance(results, dict), "Expected a dictionary"
    assert results.get("2024-01-01", {}).get("total_likes") == 16, "Expected 16"
    assert results.get("2024-01-01", {}).get("total_watched") == 16, "Expected 16"
    assert results.get("2024-01-01", {}).get("total_followed") == 16, "Expected 16"
    assert results.get("2024-01-01", {}).get("total_unfollowed") == 16, "Expected 16"
    assert results.get("2024-01-01", {}).get("total_comments") == 16, "Expected 16"
    assert results.get("2024-01-01", {}).get("total_pm") == 16, "Expected 16"
    assert results.get("2024-01-01", {}).get("followers_gained") == 0, "Expected 16"


def test_daily_summary_no_sessions():
    """Test if the function returns an empty dictionary if no sessions are provided"""
    results = TelegramReports.daily_summary([])
    assert results == {}, "Expected an empty dictionary"


def test_generate_report():
    """Test if the function returns a string"""
    daily_aggregated_data = TelegramReports.daily_summary(sessions_json)
    today_data = daily_aggregated_data.get("2024-01-02", {})
    last_session = sessions_json[-1]
    last_session["duration"] = TelegramReports._calculate_session_duration(last_session)
    results = TelegramReports.generate_report(
        "test_user", last_session, today_data, 400, 400
    )
    assert isinstance(results, str), "Expected a string"
