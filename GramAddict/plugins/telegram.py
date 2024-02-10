import json
import logging
from datetime import datetime
import requests
import yaml
from colorama import Fore, Style

from GramAddict.core.plugin_loader import Plugin

logger = logging.getLogger(__name__)


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

        def telegram_bot_sendtext(text):
            try:
                with open(
                    f"accounts/{username}/telegram.yml", "r", encoding="utf-8"
                ) as stream:
                    config = yaml.safe_load(stream)
                bot_api_token = config.get("telegram-api-token")
                bot_chat_ID = config.get("telegram-chat-id")
                if bot_api_token and bot_chat_ID:
                    method = "sendMessage"
                    parse_mode = "markdown"
                    params = {
                        "text": text,
                        "chat_id": bot_chat_ID,
                        "parse_mode": parse_mode,
                    }
                    url = f"https://api.telegram.org/bot{bot_api_token}/{method}"
                    response = requests.get(url, params=params)
                    return response.json()
            except Exception as e:
                logger.error(f"Error sending Telegram message: {e}")
                return None

        try:
            with open(f"accounts/{username}/sessions.json") as json_data:
                sessions = json.load(json_data)
        except FileNotFoundError:
            logger.error("No session data found. Skipping report generation.")
            return

        aggregated_data = {}

        for session in sessions:
            date = session["start_time"][:10]
            if date not in aggregated_data:
                aggregated_data[date] = {
                    "total_likes": 0,
                    "total_watched": 0,
                    "total_followed": 0,
                    "total_unfollowed": 0,
                    "total_comments": 0,
                    "total_pm": 0,
                    "duration": 0,
                    "followers": 0,
                }
            try:
                start_datetime = datetime.strptime(
                    session["start_time"], "%Y-%m-%d %H:%M:%S.%f"
                )
                finish_datetime = datetime.strptime(
                    session["finish_time"], "%Y-%m-%d %H:%M:%S.%f"
                )
                duration = int((finish_datetime - start_datetime).total_seconds() / 60)
            except ValueError:
                logger.error(f"Failed to calculate session duration for {date}.")
                duration = 0
            aggregated_data[date]["duration"] += duration

            for key in [
                "total_likes",
                "total_watched",
                "total_followed",
                "total_unfollowed",
                "total_comments",
                "total_pm",
            ]:
                aggregated_data[date][key] += session.get(key, 0)
            aggregated_data[date]["followers"] = session.get("profile", {}).get(
                "followers", 0
            )

        # Calculate followers gained
        dates_sorted = list(sorted(aggregated_data.keys()))[-2:]
        previous_followers = None
        for date in dates_sorted:
            current_followers = aggregated_data[date]["followers"]
            if previous_followers is not None:
                aggregated_data[date]["followers_gained"] = (
                    current_followers - previous_followers
                )
            else:
                aggregated_data[date][
                    "followers_gained"
                ] = 0  # No data to compare for the first entry
            previous_followers = current_followers

        # TODO: Add more stats
        report = f"Stats for {username}:\n\n"
        for date, data in list(aggregated_data.items())[-2:]:
            report += f"Date: {date}\n"
            report += f"Duration (min): {data['duration']:.2f}\n"
            report += f"Likes: {data['total_likes']}, Watched: {data['total_watched']}, Followed: {data['total_followed']}, Unfollowed: {data['total_unfollowed']}\n"
            report += (
                f"Comments: {data['total_comments']}, PM Sent: {data['total_pm']}\n"
            )
            report += f"Followers Gained: {data['followers_gained']}\n\n"

        # Send the report via Telegram
        response = telegram_bot_sendtext(report)
        if response and response.get("ok"):
            logger.info(
                "Telegram message sent successfully.",
                extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
            )
        else:
            error = response.get("description") if response else "Unknown error"
            logger.error(f"Failed to send Telegram message: {error}")
