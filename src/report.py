from datetime import timedelta

from src.utils import *


def print_full_report(sessions):
    if len(sessions) > 1:
        for index, session in enumerate(sessions):
            finish_time = session.finishTime or datetime.now()
            print_timeless("\n")
            print_timeless(COLOR_WARNING + "SESSION #" + str(index + 1) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Start time: " + str(session.startTime) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Finish time: " + str(finish_time) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Duration: " + str(finish_time - session.startTime) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total interactions: " + stringify_interactions(session.totalInteractions)
                           + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Successful interactions: "
                           + stringify_interactions(session.successfulInteractions) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total followed: "
                           + stringify_interactions(session.totalFollowed) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total likes: " + str(session.totalLikes) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total unfollowed: " + str(session.totalUnfollowed) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total removed mass followers: "
                           + str(session.totalRemovedMassFollowers) + COLOR_ENDC)

    print_timeless("\n")
    print_timeless(COLOR_WARNING + "TOTAL" + COLOR_ENDC)

    completed_sessions = [session for session in sessions if session.is_finished()]
    print_timeless(COLOR_WARNING + "Completed sessions: " + str(len(completed_sessions)) + COLOR_ENDC)

    duration = timedelta(0)
    for session in sessions:
        finish_time = session.finishTime or datetime.now()
        duration += finish_time - session.startTime
    print_timeless(COLOR_WARNING + "Total duration: " + str(duration) + COLOR_ENDC)

    total_interactions = {}
    successful_interactions = {}
    total_followed = {}
    for session in sessions:
        for blogger, count in session.totalInteractions.items():
            if total_interactions.get(blogger) is None:
                total_interactions[blogger] = count
            else:
                total_interactions[blogger] += count

        for blogger, count in session.successfulInteractions.items():
            if successful_interactions.get(blogger) is None:
                successful_interactions[blogger] = count
            else:
                successful_interactions[blogger] += count

        for blogger, count in session.totalFollowed.items():
            if total_followed.get(blogger) is None:
                total_followed[blogger] = count
            else:
                total_followed[blogger] += count

    print_timeless(COLOR_WARNING + "Total interactions: " + stringify_interactions(total_interactions) + COLOR_ENDC)
    print_timeless(COLOR_WARNING + "Successful interactions: " + stringify_interactions(successful_interactions)
                   + COLOR_ENDC)
    print_timeless(COLOR_WARNING + "Total followed : " + stringify_interactions(total_followed)
                   + COLOR_ENDC)

    total_likes = sum(session.totalLikes for session in sessions)
    print_timeless(COLOR_WARNING + "Total likes: " + str(total_likes) + COLOR_ENDC)

    total_unfollowed = sum(session.totalUnfollowed for session in sessions)
    print_timeless(COLOR_WARNING + "Total unfollowed: " + str(total_unfollowed) + COLOR_ENDC)

    total_removed_mass_followers = sum(session.totalRemovedMassFollowers for session in sessions)
    print_timeless(COLOR_WARNING + "Total removed mass followers: " + str(total_removed_mass_followers) + COLOR_ENDC)


def print_short_report(blogger, session_state):
    total_likes = session_state.totalLikes
    total_followed = sum(session_state.totalFollowed.values())
    interactions = session_state.successfulInteractions.get(blogger, 0)
    print(COLOR_WARNING + "Session progress: " + str(total_likes) + " likes, " + str(total_followed) + " followed, " +
          str(interactions) + " successful " + ("interaction" if interactions == 1 else "interactions") +
          " for @" + blogger + COLOR_ENDC)
