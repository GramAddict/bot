import argparse
import json
import os
from datetime import timedelta, datetime
from enum import Enum, unique

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.dates import DateFormatter

A4_WIDTH_INCHES = 8.27
A4_HEIGHT_INCHES = 11.69


def generate_analytics(username):

    sessions = _load_sessions(username)
    if not sessions:
        return

    filename = "report_" + username + "_" + datetime.now().strftime("%Y-%m-%d") + ".pdf"
    with PdfPages(filename) as pdf:
        sessions_week = filter_sessions(sessions, Period.LAST_WEEK)
        sessions_month = filter_sessions(sessions, Period.LAST_MONTH)

        plot_followers_growth(sessions_week, pdf, username, Period.LAST_WEEK)
        plot_followers_growth(sessions_month, pdf, username, Period.LAST_MONTH)
        plot_followers_growth(sessions, pdf, username, Period.ALL_TIME)

        plot_duration_statistics(sessions_week, pdf, username, Period.LAST_WEEK)
        plot_duration_statistics(sessions_month, pdf, username, Period.LAST_MONTH)
        plot_duration_statistics(sessions, pdf, username, Period.ALL_TIME)

    print("Report saved as " + filename)


def _load_sessions(username):
    path = username + "/sessions.json"
    if os.path.exists(path):
        with open(path) as json_file:
            json_array = json.load(json_file)
        return json_array
    else:
        print("No sessions.json file found for @" + username)
        return None


def plot_followers_growth(sessions, pdf, username, period):
    followers_count = [int(session["profile"]["followers"]) for session in sessions]
    dates = [get_start_time(session) for session in sessions]
    total_followed = [int(session["total_followed"]) for session in sessions]
    total_unfollowed = [-int(session["total_unfollowed"]) for session in sessions]
    total_likes = [int(session["total_likes"]) for session in sessions]

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
        'Followers growth for account "@'
        + username
        + '".\nThis page shows correlation between '
        "followers count and GramAddict actions:\n"
        "follows, unfollows, and likes.\n\n"
        "Period: " + period.value + ".\n",
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


def filter_sessions(sessions, period):
    if period == Period.LAST_WEEK:
        week_ago = datetime.now() - timedelta(weeks=1)
        return list(
            filter(lambda session: get_start_time(session) > week_ago, sessions)
        )
    if period == Period.LAST_MONTH:
        month_ago = datetime.now() - timedelta(days=30)
        return list(
            filter(lambda session: get_start_time(session) > month_ago, sessions)
        )
    if period == Period.ALL_TIME:
        return sessions


def get_start_time(session):
    return datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S.%f")


def get_finish_time(session):
    finish_time = session["finish_time"]
    if finish_time == "None":
        return None
    return datetime.strptime(finish_time, "%Y-%m-%d %H:%M:%S.%f")


def plot_duration_statistics(sessions, pdf, username, period):
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

        finish_time = get_finish_time(session)
        if finish_time is None:
            continue

        setup = (
            "--likes-count "
            + likes_count
            + "\n--follow-percentage "
            + follow_percentage
        )
        start_time = get_start_time(session)
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
        'Sessions duration for account "@'
        + username
        + '".\nThis page shows average time of script working '
        "per successful interaction.\nYou can obtain "
        "approximate session length by multiplying one of the"
        "\nfollowing times and your --interactions-count "
        "value.\n\nPeriod: " + period.value + ".\n",
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
