import json
from unittest.mock import mock_open

import pytest
from datetime import datetime

import GramAddict.plugins.telegram as TelegramReports


@pytest.fixture
def mock_session_data_raw():
    """Provides session data in raw format"""
    with open(r"mock_data\sessions.json", "r") as file:
        return file.read()


@pytest.fixture
def mock_session_data_json(mock_session_data_raw):
    """Provides session data in JSON format"""
    return json.loads(mock_session_data_raw)


@pytest.fixture
def mock_daily_summary():
    return {
        "2024-01-02": {
            "total_likes": 20,
            "total_watched": 20,
            "total_followed": 20,
            "total_unfollowed": 20,
            "total_comments": 20,
            "total_pm": 20,
            "duration": 120,
            "followers": 120,
            "following": 120,
            "followers_gained": 20,
        },
        "2024-01-01": {
            "total_likes": 16,
            "total_watched": 16,
            "total_followed": 16,
            "total_unfollowed": 16,
            "total_comments": 16,
            "total_pm": 16,
            "duration": 45,
            "followers": 100,
            "following": 100,
            "followers_gained": 20,
        },
        "2023-12-29": {
            "total_likes": 20,
            "total_watched": 20,
            "total_followed": 20,
            "total_unfollowed": 20,
            "total_comments": 20,
            "total_pm": 20,
            "duration": 35,
            "followers": 90,
            "following": 90,
            "followers_gained": 10,
        },
        "2023-12-01": {
            "total_likes": 100,
            "total_watched": 100,
            "total_followed": 100,
            "total_unfollowed": 100,
            "total_comments": 100,
            "total_pm": 100,
            "duration": 100,
            "followers": 80,
            "following": 80,
            "followers_gained": 30,
        },
    }


@pytest.fixture
def mock_weekly_average():
    return {
        "total_likes": 56,
        "total_watched": 56,
        "total_followed": 56,
        "total_unfollowed": 56,
        "total_comments": 56,
        "total_pm": 56,
        "followers_gained": 50,
        "duration": 200,
    }


def test_load_sessions(mocker, mock_session_data_raw):
    """Test if the function returns a list of dictionaries"""
    mocker.patch("builtins.open", mock_open(read_data=mock_session_data_raw))
    result = TelegramReports.load_sessions("test_user")
    assert isinstance(result, list), "Expected a list"
    assert isinstance(result[0], dict), "Expected a dictionary"


def test_calculate_duration(mock_session_data_json):
    """Test if the function returns a number"""
    result = TelegramReports._calculate_session_duration(mock_session_data_json[0])
    assert isinstance(result, int), "Expected an integer"


def test_calculate_duration_not_finished(mock_session_data_json):
    """Test if the function returns 0 if the session is not finished"""
    result = TelegramReports._calculate_session_duration(mock_session_data_json[2])
    assert result == 0


@pytest.mark.parametrize(
    "input_date,expected_total_likes, expected_total_watched, expected_total_followed, expected_total_unfollowed, "
    "expected_total_comments, expected_total_pm, expected_total_followers_gained",
    [
        ("2024-01-02", 20, 20, 20, 20, 20, 20, 20),
        ("2024-01-01", 16, 16, 16, 16, 16, 16, 22),
        ("2023-12-29", 10, 10, 10, 10, 10, 10, 0),
    ],
)
def test_daily_summary(
    mock_session_data_json,
    input_date,
    expected_total_likes,
    expected_total_watched,
    expected_total_followed,
    expected_total_unfollowed,
    expected_total_comments,
    expected_total_pm,
    expected_total_followers_gained,
):
    """Test if the function returns a dictionary and the values are correct"""
    results = TelegramReports.daily_summary(mock_session_data_json)
    assert isinstance(results, dict), "Expected a dictionary"
    assert results.get(input_date, {}).get("total_likes") == expected_total_likes
    assert results.get(input_date, {}).get("total_watched") == expected_total_watched
    assert results.get(input_date, {}).get("total_followed") == expected_total_followed
    assert (
        results.get(input_date, {}).get("total_unfollowed") == expected_total_unfollowed
    )
    assert results.get(input_date, {}).get("total_comments") == expected_total_comments
    assert results.get(input_date, {}).get("total_pm") == expected_total_pm
    assert (
        results.get(input_date, {}).get("followers_gained")
        == expected_total_followers_gained
    )


def test_daily_summary_no_sessions():
    """Test if the function returns an empty dictionary if no sessions are provided"""
    results = TelegramReports.daily_summary([])
    assert results == {}, "Expected an empty dictionary"


def test_weekly_average(mock_daily_summary):
    """Test if the function returns a dictionary and the values are correct"""
    results = TelegramReports.weekly_average(
        mock_daily_summary,
        datetime.strptime("2024-01-02", "%Y-%m-%d"),
    )
    assert isinstance(results, dict), "Expected a dictionary"
    assert results.get("total_likes") == 56, "Expected 56"
    assert results.get("total_watched") == 56, "Expected 56"
    assert results.get("total_followed") == 56, "Expected 56"
    assert results.get("total_unfollowed") == 56, "Expected 56"
    assert results.get("total_comments") == 56, "Expected 56"
    assert results.get("total_pm") == 56, "Expected 56"
    assert results.get("followers_gained") == 50, "Expected 50"


def test_generate_report(
    mock_session_data_json, mock_daily_summary, mock_weekly_average
):
    """Test if the function returns a string"""
    daily_aggregated_data = mock_daily_summary
    today_data = daily_aggregated_data.get("2024-01-02", {})
    last_session = mock_session_data_json[-1]
    last_session["duration"] = 120

    report = TelegramReports.generate_report(
        "test_user", last_session, today_data, mock_weekly_average, 400, 400
    )
    assert isinstance(report, str), "Expected a string"
