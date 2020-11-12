from datetime import timedelta, datetime
from GramAddict.core.utils import (
    COLOR_WARNING,
    COLOR_ENDC,
    print_timeless,
    print,
)


def print_full_report(sessions):
    if len(sessions) > 1:
        for index, session in enumerate(sessions):
            finish_time = session.finishTime or datetime.now()
            print_timeless("\n")
            print_timeless(COLOR_WARNING + "SESSION #" + str(index + 1) + COLOR_ENDC)
            print_timeless(
                COLOR_WARNING + "Start time: " + str(session.startTime) + COLOR_ENDC
            )
            print_timeless(
                COLOR_WARNING + "Finish time: " + str(finish_time) + COLOR_ENDC
            )
            print_timeless(
                COLOR_WARNING
                + "Duration: "
                + str(finish_time - session.startTime)
                + COLOR_ENDC
            )
            print_timeless(
                COLOR_WARNING
                + "Total interactions: "
                + _stringify_interactions(session.totalInteractions)
                + COLOR_ENDC
            )
            print_timeless(
                COLOR_WARNING
                + "Successful interactions: "
                + _stringify_interactions(session.successfulInteractions)
                + COLOR_ENDC
            )
            print_timeless(
                COLOR_WARNING
                + "Total followed: "
                + _stringify_interactions(session.totalFollowed)
                + COLOR_ENDC
            )
            print_timeless(
                COLOR_WARNING + "Total likes: " + str(session.totalLikes) + COLOR_ENDC
            )
            print_timeless(
                COLOR_WARNING
                + "Total unfollowed: "
                + str(session.totalUnfollowed)
                + COLOR_ENDC
            )
            print_timeless(
                COLOR_WARNING
                + "Removed mass followers: "
                + _stringify_removed_mass_followers(session.removedMassFollowers)
                + COLOR_ENDC
            )

    print_timeless("\n")
    print_timeless(COLOR_WARNING + "TOTAL" + COLOR_ENDC)

    completed_sessions = [session for session in sessions if session.is_finished()]
    print_timeless(
        COLOR_WARNING
        + "Completed sessions: "
        + str(len(completed_sessions))
        + COLOR_ENDC
    )

    duration = timedelta(0)
    for session in sessions:
        finish_time = session.finishTime or datetime.now()
        duration += finish_time - session.startTime
    print_timeless(COLOR_WARNING + "Total duration: " + str(duration) + COLOR_ENDC)

    total_interactions = {}
    successful_interactions = {}
    total_followed = {}
    total_removed_mass_followers = []
    for session in sessions:
        for source, count in session.totalInteractions.items():
            if total_interactions.get(source) is None:
                total_interactions[source] = count
            else:
                total_interactions[source] += count

        for source, count in session.successfulInteractions.items():
            if successful_interactions.get(source) is None:
                successful_interactions[source] = count
            else:
                successful_interactions[source] += count

        for source, count in session.totalFollowed.items():
            if total_followed.get(source) is None:
                total_followed[source] = count
            else:
                total_followed[source] += count

        for username in session.removedMassFollowers:
            total_removed_mass_followers.append(username)

    print_timeless(
        COLOR_WARNING
        + "Total interactions: "
        + _stringify_interactions(total_interactions)
        + COLOR_ENDC
    )
    print_timeless(
        COLOR_WARNING
        + "Successful interactions: "
        + _stringify_interactions(successful_interactions)
        + COLOR_ENDC
    )
    print_timeless(
        COLOR_WARNING
        + "Total followed : "
        + _stringify_interactions(total_followed)
        + COLOR_ENDC
    )

    total_likes = sum(session.totalLikes for session in sessions)
    print_timeless(COLOR_WARNING + "Total likes: " + str(total_likes) + COLOR_ENDC)

    total_unfollowed = sum(session.totalUnfollowed for session in sessions)
    print_timeless(
        COLOR_WARNING + "Total unfollowed: " + str(total_unfollowed) + COLOR_ENDC
    )

    print_timeless(
        COLOR_WARNING
        + "Removed mass followers: "
        + _stringify_removed_mass_followers(total_removed_mass_followers)
        + COLOR_ENDC
    )


def print_short_report(source, session_state):
    total_likes = session_state.totalLikes
    total_followed = sum(session_state.totalFollowed.values())
    interactions = session_state.successfulInteractions.get(source, 0)
    print(
        COLOR_WARNING
        + "Session progress: "
        + str(total_likes)
        + " likes, "
        + str(total_followed)
        + " followed, "
        + str(interactions)
        + " successful "
        + ("interaction" if interactions == 1 else "interactions")
        + " for "
        + source
        + COLOR_ENDC
    )


def _stringify_interactions(interactions):
    if len(interactions) == 0:
        return "0"

    result = ""
    for source, count in interactions.items():
        result += str(count) + " for " + source + ", "
    result = result[:-2]
    return result


def _stringify_removed_mass_followers(removed_mass_followers):
    if len(removed_mass_followers) == 0:
        return "none"
    else:
        return "@" + ", @".join(removed_mass_followers)
