import json
import logging
from datetime import datetime
from typing import Optional

import requests
import yaml
from colorama import Fore, Style

from GramAddict.core.plugin_loader import Plugin

logger = logging.getLogger(__name__)


def load_sessions(username) -> Optional[dict]:
    try:
        with open(f"accounts/{username}/sessions.json") as json_data:
            return json.load(json_data)
    except FileNotFoundError:
        logger.error("No session data found. Skipping report generation.")
        return None


def load_telegram_config(username) -> Optional[dict]:
    try:
        with open(f"accounts/{username}/telegram.yml", "r", encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        return None


def telegram_bot_send_text(bot_api_token, bot_chat_ID, text):
    try:
        method = "sendMessage"
        parse_mode = "markdown"
        params = {"text": text, "chat_id": bot_chat_ID, "parse_mode": parse_mode}
        url = f"https://api.telegram.org/bot{bot_api_token}/{method}"
        return requests.get(url, params=params).json()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return None


def _initialize_aggregated_data():
    return {
        "total_likes": 0,
        "total_watched": 0,
        "total_reel_likes": 0,
        "total_reel_watched": 0,
        "total_followed": 0,
        "total_unfollowed": 0,
        "total_comments": 0,
        "total_pm": 0,
        "total_scraped": 0,
        "total_interactions": 0,
        "successful_interactions": 0,
        "duration": 0,
        "followers": float("inf"),
        "following": float("inf"),
        "followers_gained": 0,
    }


def _calculate_session_duration(session):
    try:
        start_datetime = datetime.strptime(
            session["start_time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        finish_datetime = datetime.strptime(
            session["finish_time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        return int((finish_datetime - start_datetime).total_seconds() / 60)
    except ValueError:
        logger.debug(
            f"{session['id']} has no finish_time. Skipping duration calculation."
        )
        return 0


def daily_summary(sessions):
    def _session_value(session, key):
        value = session.get(key, 0)
        if isinstance(value, dict):
            return sum(v for v in value.values() if isinstance(v, (int, float)))
        if isinstance(value, (list, tuple)):
            return sum(v for v in value if isinstance(v, (int, float)))
        if value is None:
            return 0
        return value

    daily_aggregated_data = {}
    for session in sessions:
        date = session["start_time"][:10]
        daily_aggregated_data.setdefault(date, _initialize_aggregated_data())
        duration = _calculate_session_duration(session)
        daily_aggregated_data[date]["duration"] += duration

        for key in [
            "total_likes",
            "total_watched",
            "total_reel_likes",
            "total_reel_watched",
            "total_followed",
            "total_unfollowed",
            "total_comments",
            "total_pm",
            "total_scraped",
            "total_interactions",
            "successful_interactions",
        ]:
            daily_aggregated_data[date][key] += _session_value(session, key)

        daily_aggregated_data[date]["followers"] = min(
            session.get("profile", {}).get("followers", 0),
            daily_aggregated_data[date]["followers"],
        )
        daily_aggregated_data[date]["following"] = min(
            session.get("profile", {}).get("following", 0),
            daily_aggregated_data[date]["following"],
        )
    return _calculate_followers_gained(daily_aggregated_data)


def _calculate_followers_gained(aggregated_data):
    dates_sorted = sorted(aggregated_data.keys())
    previous_followers = None
    for date in dates_sorted:
        current_followers = aggregated_data[date]["followers"]
        if previous_followers is not None:
            followers_gained = current_followers - previous_followers
            aggregated_data[date]["followers_gained"] = followers_gained
        previous_followers = current_followers
    return aggregated_data


def generate_report(
    username,
    last_session,
    daily_aggregated_data,
    weekly_average_data,
    followers_now,
    following_now,
):
    def _session_value(session, key):
        value = session.get(key, 0)
        if isinstance(value, dict):
            return sum(v for v in value.values() if isinstance(v, (int, float)))
        if isinstance(value, (list, tuple)):
            return sum(v for v in value if isinstance(v, (int, float)))
        if value is None:
            return 0
        return value

    last_total_reel_likes = _session_value(last_session, "total_reel_likes")
    last_total_reel_watched = _session_value(last_session, "total_reel_watched")
    last_total_scraped = _session_value(last_session, "total_scraped")
    last_total_interactions = _session_value(last_session, "total_interactions")
    last_successful_interactions = _session_value(
        last_session, "successful_interactions"
    )

    return f"""
            *Stats for {username}*:

            *✨Overview after last activity*
            • {followers_now} followers ({followers_now - last_session.get("profile", {}).get("followers", 0):+})
            • {following_now} following ({following_now - last_session.get("profile", {}).get("following", 0):+})

            *🤖 Last session actions*
            • {last_session["duration"]} minutes of botting
            • {last_session["total_likes"]} likes
            • {last_total_reel_likes} reel likes
            • {last_session["total_followed"]} follows
            • {last_session["total_unfollowed"]} unfollows
            • {last_session["total_watched"]} stories watched
            • {last_total_reel_watched} reels watched
            • {last_session["total_comments"]} comments done
            • {last_session["total_pm"]} PM sent
            • {last_total_scraped} users scraped
            • {last_total_interactions} total interactions
            • {last_successful_interactions} successful interactions

            *📅 Today's total actions*
            • {daily_aggregated_data["duration"]} minutes of botting
            • {daily_aggregated_data["total_likes"]} likes
            • {daily_aggregated_data["total_reel_likes"]} reel likes
            • {daily_aggregated_data["total_followed"]} follows
            • {daily_aggregated_data["total_unfollowed"]} unfollows
            • {daily_aggregated_data["total_watched"]} stories watched
            • {daily_aggregated_data["total_reel_watched"]} reels watched
            • {daily_aggregated_data["total_comments"]} comments done
            • {daily_aggregated_data["total_pm"]} PM sent
            • {daily_aggregated_data["total_scraped"]} users scraped
            • {daily_aggregated_data["total_interactions"]} total interactions
            • {daily_aggregated_data["successful_interactions"]} successful interactions

            *📈 Trends*
            • {daily_aggregated_data["followers_gained"]} new followers today
            • {weekly_average_data["followers_gained"]} new followers this week

            *🗓 7-Day Average*
            • {weekly_average_data["duration"] / 7:.0f} minutes of botting
            • {weekly_average_data["total_likes"] / 7:.0f} likes
            • {weekly_average_data["total_reel_likes"] / 7:.0f} reel likes
            • {weekly_average_data["total_followed"] / 7:.0f} follows
            • {weekly_average_data["total_unfollowed"] / 7:.0f} unfollows
            • {weekly_average_data["total_watched"] / 7:.0f} stories watched
            • {weekly_average_data["total_reel_watched"] / 7:.0f} reels watched
            • {weekly_average_data["total_comments"] / 7:.0f} comments done
            • {weekly_average_data["total_pm"] / 7:.0f} PM sent
            • {weekly_average_data["total_scraped"] / 7:.0f} users scraped
            • {weekly_average_data["total_interactions"] / 7:.0f} total interactions
            • {weekly_average_data["successful_interactions"] / 7:.0f} successful interactions
        """


def weekly_average(daily_aggregated_data, today) -> dict:
    weekly_average_data = _initialize_aggregated_data()

    for date in daily_aggregated_data:
        if (today - datetime.strptime(date, "%Y-%m-%d")).days > 7:
            continue
        for key in [
            "total_likes",
            "total_watched",
            "total_reel_likes",
            "total_reel_watched",
            "total_followed",
            "total_unfollowed",
            "total_comments",
            "total_pm",
            "total_scraped",
            "total_interactions",
            "successful_interactions",
            "duration",
            "followers_gained",
        ]:
            weekly_average_data[key] += daily_aggregated_data[date][key]
    return weekly_average_data


class TelegramReports(Plugin):
    """Generate reports at the end of the session and send them using telegram"""

    def __init__(self):
        super().__init__()
        self.description = "Generate reports at the end of the session and send them using telegram. You have to configure 'telegram.yml' in your account folder"
        self.arguments = [
            {
                "arg": "--telegram-reports",
                "help": "at the end of every session send a report to your telegram account",
                "action": "store_true",
                "operation": True,
            }
        ]

    def run(self, config, plugin, followers_now, following_now, time_left):
        username = config.args.username
        if username is None:
            logger.error("You have to specify a username for getting reports!")
            return

        sessions = load_sessions(username)
        if not sessions:
            logger.error(
                f"No session data found for {username}. Skipping report generation."
            )
            return

        last_session = sessions[-1]
        last_session["duration"] = _calculate_session_duration(last_session)

        telegram_config = load_telegram_config(username)
        if not telegram_config:
            logger.error(
                f"No telegram configuration found for {username}. Skipping report generation."
            )
            return

        daily_aggregated_data = daily_summary(sessions)
        today_data = daily_aggregated_data.get(last_session["start_time"][:10], {})
        today = datetime.now()
        weekly_average_data = weekly_average(daily_aggregated_data, today)
        report = generate_report(
            username,
            last_session,
            today_data,
            weekly_average_data,
            followers_now,
            following_now,
        )
        response = telegram_bot_send_text(
            telegram_config.get("telegram-api-token"),
            telegram_config.get("telegram-chat-id"),
            report,
        )
        if response and response.get("ok"):
            logger.info(
                "Telegram message sent successfully.",
                extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
            )
        else:
            error = response.get("description") if response else "Unknown error"
            logger.error(f"Failed to send Telegram message: {error}")
