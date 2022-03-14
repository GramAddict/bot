import json
import logging
import sys
from datetime import datetime, timedelta
from textwrap import dedent

import requests
import yaml
from colorama import Fore, Style

from GramAddict.core.plugin_loader import Plugin

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    logger.warning(
        "If you want to use telegram_reports, please type in console: 'pip3 install gramaddict[telegram-reports]'"
    )


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
        modulename = "pandas"
        if modulename not in sys.modules:
            logger.error(
                f"You can't use {plugin} without installing {modulename}. Type that in console: 'pip3 install gramaddict[telegram-reports]'"
            )
            return

        def telegram_bot_sendtext(text):
            with open(
                f"accounts/{username}/telegram.yml", "r", encoding="utf-8"
            ) as stream:
                try:
                    config = yaml.safe_load(stream)
                    bot_api_token = config.get("telegram-api-token")
                    bot_chat_ID = config.get("telegram-chat-id")
                except yaml.YAMLError as e:
                    logger.error(e)
            if bot_api_token is not None and bot_chat_ID is not None:
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

        if username is None:
            logger.error("You have to specify an username for getting reports!")
            return None
        with open(f"accounts/{username}/sessions.json") as json_data:
            activity = json.load(json_data)

        aggActivity = []
        for session in activity:
            try:
                id = session["id"]
                start = session["start_time"]
                finish = session["finish_time"]
                followed = session.get("total_followed", 0)
                unfollowed = session.get("total_unfollowed", 0)
                likes = session.get("total_likes", 0)
                watched = session.get("total_watched", 0)
                comments = session.get("total_comments", 0)
                pm_sent = session.get("total_pm", 0)
                followers = int(session.get("profile", 0).get("followers", 0))
                following = int(session.get("profile", 0).get("following", 0))
                aggActivity.append(
                    [
                        start,
                        finish,
                        likes,
                        watched,
                        followed,
                        unfollowed,
                        comments,
                        pm_sent,
                        followers,
                        following,
                    ]
                )
            except TypeError:
                logger.error(f"The session {id} has malformed data, skip.")
                continue

        df = pd.DataFrame(
            aggActivity,
            columns=[
                "start",
                "finish",
                "likes",
                "watched",
                "followed",
                "unfollowed",
                "comments",
                "pm_sent",
                "followers",
                "following",
            ],
        )
        df["date"] = df.loc[:, "start"].str[:10]
        df["duration"] = pd.to_datetime(df["finish"], errors="coerce") - pd.to_datetime(
            df["start"], errors="coerce"
        )
        df["duration"] = df["duration"].dt.total_seconds() / 60

        if time_left is not None:
            timeString = f'Next session will start at: {(datetime.now()+ timedelta(seconds=time_left)).strftime("%H:%M:%S (%Y/%m/%d)")}.'
        else:
            timeString = "There is no new session planned!"

        dailySummary = df.groupby(by="date").agg(
            {
                "likes": "sum",
                "watched": "sum",
                "followed": "sum",
                "unfollowed": "sum",
                "comments": "sum",
                "pm_sent": "sum",
                "followers": "max",
                "following": "max",
                "duration": "sum",
            }
        )
        if len(dailySummary.index) > 1:
            dailySummary["followers_gained"] = dailySummary["followers"].astype(
                int
            ) - dailySummary["followers"].astype(int).shift(1)
        else:
            logger.info(
                "First day of botting eh? Stats for the first day are meh because we don't have enough data to track how many followers you earned today from the bot activity."
            )
            dailySummary["followers_gained"] = dailySummary["followers"].astype(int)
        dailySummary.dropna(inplace=True)
        dailySummary["followers_gained"] = dailySummary["followers_gained"].astype(int)
        dailySummary["duration"] = dailySummary["duration"].astype(int)
        numFollowers = int(dailySummary["followers"].iloc[-1])
        n = 1
        milestone = ""
        try:
            for x in range(10):
                if numFollowers in range(x * 1000, n * 1000):
                    milestone = f"• {str(int(((n * 1000 - numFollowers)/dailySummary['followers_gained'].tail(7).mean())))} days until {n}k!"
                    break
                n += 1
        except OverflowError:
            logger.info("Not able to get milestone ETA..")

        def undentString(string):
            return dedent(string[1:])[:-1]

        followers_before = int(df["followers"].iloc[-1])
        following_before = int(df["following"].iloc[-1])
        statString = f"""
                *Stats for {username}*:

                *✨Overview after last activity*
                • {followers_now} followers ({followers_now - followers_before:+})
                • {following_now} following ({following_now - following_before:+})

                *🤖 Last session actions*
                • {str(df["duration"].iloc[-1].astype(int))} minutes of botting
                • {str(df["likes"].iloc[-1])} likes
                • {str(df["followed"].iloc[-1])} follows
                • {str(df["unfollowed"].iloc[-1])} unfollows
                • {str(df["watched"].iloc[-1])} stories watched
                • {str(df["comments"].iloc[-1])} comments done
                • {str(df["pm_sent"].iloc[-1])} PM sent

                *📅 Today's total actions*
                • {str(dailySummary["duration"].iloc[-1])} minutes of botting
                • {str(dailySummary["likes"].iloc[-1])} likes
                • {str(dailySummary["followed"].iloc[-1])} follows
                • {str(dailySummary["unfollowed"].iloc[-1])} unfollows
                • {str(dailySummary["watched"].iloc[-1])} stories watched
                • {str(dailySummary["comments"].iloc[-1])} comments done
                • {str(dailySummary["pm_sent"].iloc[-1])} PM sent

                *📈 Trends*
                • {str(dailySummary["followers_gained"].iloc[-1])} new followers today
                • {str(dailySummary["followers_gained"].tail(3).sum())} new followers past 3 days
                • {str(dailySummary["followers_gained"].tail(7).sum())} new followers past week
                {milestone if not "" else ""}

                *🗓 7-Day Average*
                • {str(round(dailySummary["followers_gained"].tail(7).mean(), 1))} followers / day
                • {str(int(dailySummary["likes"].tail(7).mean()))} likes
                • {str(int(dailySummary["followed"].tail(7).mean()))} follows
                • {str(int(dailySummary["unfollowed"].tail(7).mean()))} unfollows
                • {str(int(dailySummary["watched"].tail(7).mean()))} stories watched
                • {str(int(dailySummary["comments"].tail(7).mean()))} comments done
                • {str(int(dailySummary["pm_sent"].tail(7).mean()))} PM sent
                • {str(int(dailySummary["duration"].tail(7).mean()))} minutes of botting
            """
        try:
            r = telegram_bot_sendtext(f"{undentString(statString)}\n\n{timeString}")
            if r.get("ok"):
                logger.info(
                    "Telegram message sent successfully.",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
            else:
                logger.error(
                    f"Unable to send telegram report. Error code: {r.get('error_code')} - {r.get('description')}"
                )
        except Exception as e:
            logger.error(f"Telegram message failed to send. Error: {e}")
