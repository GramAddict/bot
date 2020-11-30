import json
import matplotlib.pyplot as plt
import os

from datetime import timedelta, datetime
from enum import Enum, unique
from matplotlib import ticker
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.dates import DateFormatter

from GramAddict.core.plugin_loader import Plugin

A4_WIDTH_INCHES = 8.27
A4_HEIGHT_INCHES = 11.69


class DataAnalytics(Plugin):
    """Generates a PDF analytics report of specified username session data"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Generates a PDF analytics report of specified username session data"
        )
        self.arguments = [
            {
                "arg": "--analytics",
                "nargs": 1,
                "help": "generates a PDF analytics report of specified username session data",
                "metavar": "username1",
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, device_id, args, enabled, storage, sessions, plugin):
        self.username = args.analytics[0]
        sessions = self.load_sessions()
        if not sessions:
            return

        filename = (
            "report_"
            + self.username
            + "_"
            + datetime.now().strftime("%Y-%m-%d")
            + ".pdf"
        )
        with PdfPages(filename) as pdf:
            sessions_week = self.filter_sessions(sessions, Period.LAST_WEEK)
            sessions_month = self.filter_sessions(sessions, Period.LAST_MONTH)

            self.plot_followers_growth(
                sessions_week, pdf, self.username, Period.LAST_WEEK
            )
            self.plot_followers_growth(
                sessions_month, pdf, self.username, Period.LAST_MONTH
            )
            self.plot_followers_growth(sessions, pdf, self.username, Period.ALL_TIME)

            self.plot_duration_statistics(
                sessions_week, pdf, self.username, Period.LAST_WEEK
            )
            self.plot_duration_statistics(
                sessions_month, pdf, self.username, Period.LAST_MONTH
            )
            self.plot_duration_statistics(sessions, pdf, self.username, Period.ALL_TIME)

        print("Report saved as " + filename)

    def load_sessions(self):
        path = self.username + "/sessions.json"
        if os.path.exists(path):
            with open(path) as json_file:
                json_array = json.load(json_file)
            return json_array
        else:
            print("No sessions.json file found for @" + self.username)
            return None

    def plot_followers_growth(self, sessions, pdf, username, period):
        followers_count = [
            int(session.get("profile", {}).get("followers", 0)) for session in sessions
        ]
        dates = [self.get_start_time(session) for session in sessions]
        total_followed = [int(session.get("total_followed", 0)) for session in sessions]
        total_unfollowed = [
            -int(session.get("total_unfollowed", 0)) for session in sessions
        ]
        total_likes = [int(session.get("total_likes", 0)) for session in sessions]

        fig, (axes1, axes2, axes3) = plt.subplots(
            ncols=1,
            nrows=3,
            sharex="row",
            figsize=(A4_WIDTH_INCHES, A4_HEIGHT_INCHES),
            gridspec_kw={"height_ratios": [4, 1, 1]},
        )

        fig.subplots_adjust(top=0.8, hspace=0.05)

        formatter = DateFormatter("%B %dth")
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(formatter)

        axes1.plot(dates, followers_count, marker=".")
        axes1.set_ylabel("Followers")
        axes1.xaxis.grid(True, linestyle="--")
        axes1.set_title(
            f'Followers growth for account "@{self.username}".\nThis page shows correlation between followers count and GramAddict actions:\nfollows, unfollows, and likes.\n\nPeriod: {period.value}.\n',
            fontsize=12,
            x=0,
            horizontalalignment="left",
        )

        axes2.fill_between(dates, total_followed, 0, color="#00CCFF", alpha=0.4)
        axes2.fill_between(dates, total_unfollowed, 0, color="#F94949", alpha=0.4)
        axes2.set_ylabel("Follows / unfollows")
        axes2.xaxis.grid(True, linestyle="--")

        axes3.fill_between(dates, total_likes, 0, color="#78EF7B", alpha=0.4)
        axes3.set_ylabel("Likes")
        axes3.set_xlabel("Date")
        axes3.xaxis.grid(True, linestyle="--")

        pdf.savefig()
        plt.close()

    def filter_sessions(self, sessions, period):
        if period == Period.LAST_WEEK:
            week_ago = datetime.now() - timedelta(weeks=1)
            return list(
                filter(
                    lambda session: self.get_start_time(session) > week_ago, sessions
                )
            )
        if period == Period.LAST_MONTH:
            month_ago = datetime.now() - timedelta(days=30)
            return list(
                filter(
                    lambda session: self.get_start_time(session) > month_ago, sessions
                )
            )
        if period == Period.ALL_TIME:
            return sessions

    def get_start_time(self, session):
        return datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S.%f")

    def get_finish_time(self, session):
        finish_time = session["finish_time"]
        if finish_time == "None":
            return None
        return datetime.strptime(finish_time, "%Y-%m-%d %H:%M:%S.%f")

    def plot_duration_statistics(self, sessions, pdf, username, period):
        setups_map = {}

        for session in sessions:
            successful_interactions = session.get("successful_interactions")
            if successful_interactions is None or successful_interactions == 0:
                continue

            args = session["args"]

            likes_count = args.get("likes_count")
            if likes_count is None:
                continue

            follow_percentage = args.get("follow_percentage")
            if follow_percentage is None:
                continue

            finish_time = self.get_finish_time(session)
            if finish_time is None:
                continue

            setup = f"--likes-count {str(likes_count)}\n--follow-percentage {str(follow_percentage)}"
            start_time = self.get_start_time(session)
            time_per_interaction = (finish_time - start_time) / successful_interactions
            setups_map[setup] = time_per_interaction.total_seconds()

        def time_formatter(x, _):
            minutes = int(x // 60)
            seconds = int(x % 60)
            return (str(minutes) + "m " if minutes > 0 else "") + str(seconds) + "s"

        fig, ax = plt.subplots(
            ncols=1, nrows=1, figsize=(A4_WIDTH_INCHES, A4_HEIGHT_INCHES)
        )
        fig.subplots_adjust(top=0.8, bottom=0.2)
        plt.yticks(rotation=45, fontsize=6)
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(time_formatter))
        ax.xaxis.grid(True, linestyle="--")

        setups_map_sorted = {
            key: value
            for key, value in sorted(setups_map.items(), key=lambda item: -item[1])
        }
        setups_list = list(setups_map_sorted.keys())
        times_list = list(setups_map_sorted.values())
        ax.barh(setups_list, times_list)

        ax.set_title(
            f'Sessions duration for account "@{self.username}".\nThis page shows average time of script working per successful interaction.\nYou can obtain approximate session length by multiplying one of the\nfollowing times and your --interactions-count value.\n\nPeriod: {period.value}.\n',
            fontsize=12,
            x=0,
            horizontalalignment="left",
        )

        pdf.savefig(fig)
        plt.close()


@unique
class Period(Enum):
    LAST_WEEK = "last week"
    LAST_MONTH = "last month"
    ALL_TIME = "all time"
