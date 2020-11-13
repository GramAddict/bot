import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def print_full_report(sessions):
    if len(sessions) > 1:
        for index, session in enumerate(sessions):
            finish_time = session.finishTime or datetime.now()
            logger.warn("")
            logger.warn(f"SESSION #{index + 1}")
            logger.warn(f"Start time: {session.startTime}")
            logger.warn(f"Finish time: {finish_time}")
            logger.warn(f"Duration: {finish_time - session.startTime}")
            logger.warn(
                f"Total interactions: {_stringify_interactions(session.totalInteractions)}"
            )
            logger.warn(
                f"Successful interactions: {_stringify_interactions(session.successfulInteractions)}"
            )
            logger.warn(
                f"Total followed: {_stringify_interactions(session.totalFollowed)}"
            )
            logger.warn(f"Total likes: {session.totalLikes}")
            logger.warn(f"Total unfollowed: {session.totalUnfollowed}")
            logger.warn(
                f"Removed mass followers: {_stringify_removed_mass_followers(session.removedMassFollowers)}"
            )

    logger.warn("")
    logger.warn("TOTAL")

    completed_sessions = [session for session in sessions if session.is_finished()]
    logger.warn(f"Completed sessions: {len(completed_sessions)}")

    duration = timedelta(0)
    for session in sessions:
        finish_time = session.finishTime or datetime.now()
        duration += finish_time - session.startTime
    logger.warn(f"Total duration: {duration}")

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

    logger.warn(f"Total interactions: {_stringify_interactions(total_interactions)}")
    logger.warn(
        f"Successful interactions: {_stringify_interactions(successful_interactions)}"
    )
    logger.warn(f"Total followed : {_stringify_interactions(total_followed)}")

    total_likes = sum(session.totalLikes for session in sessions)
    logger.warn(f"Total likes: {total_likes}")

    total_unfollowed = sum(session.totalUnfollowed for session in sessions)
    logger.warn(f"Total unfollowed: {total_unfollowed} ")

    logger.warn(
        f"Removed mass followers: {_stringify_removed_mass_followers(total_removed_mass_followers)}"
    )


def print_short_report(source, session_state):
    total_likes = session_state.totalLikes
    total_followed = sum(session_state.totalFollowed.values())
    interactions = session_state.successfulInteractions.get(source, 0)
    logger.warn(
        f"Session progress: {total_likes} likes, {total_followed} followed, {interactions} successful interaction(s) for {source}"
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
