import logging
import uuid
from datetime import datetime
from json import JSONEncoder

logger = logging.getLogger(__name__)


class SessionState:
    id = None
    args = {}
    my_username = None
    my_followers_count = None
    my_following_count = None
    totalInteractions = {}
    successfulInteractions = {}
    totalFollowed = {}
    totalLikes = 0
    totalWatched = 0
    totalUnfollowed = 0
    removedMassFollowers = []
    startTime = None
    finishTime = None

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.args = {}
        self.my_username = None
        self.my_followers_count = None
        self.my_following_count = None
        self.totalInteractions = {}
        self.successfulInteractions = {}
        self.totalFollowed = {}
        self.totalLikes = 0
        self.totalWatched = 0
        self.totalUnfollowed = 0
        self.removedMassFollowers = []
        self.startTime = datetime.now()
        self.finishTime = None

    def add_interaction(self, source, succeed, followed):
        if self.totalInteractions.get(source) is None:
            self.totalInteractions[source] = 1
        else:
            self.totalInteractions[source] += 1

        if self.successfulInteractions.get(source) is None:
            self.successfulInteractions[source] = 1 if succeed else 0
        else:
            if succeed:
                self.successfulInteractions[source] += 1

        if self.totalFollowed.get(source) is None:
            self.totalFollowed[source] = 1 if followed else 0
        else:
            if followed:
                self.totalFollowed[source] += 1

    def check_limit(self, args, limit_type="ALL", output=False):
        """Returns True if limit reached - else False"""

        total_likes = self.totalLikes >= int(args.total_likes_limit)
        total_followed = sum(self.totalFollowed.values()) >= int(
            args.total_follows_limit
        )
        total_watched = self.totalWatched >= int(args.total_watch_limit)
        total_successful = sum(self.successfulInteractions.values()) >= int(
            args.total_successful_interactions_limit
        )
        total_interactions = sum(self.totalInteractions.values()) >= int(
            args.total_interactions_limit
        )

        session_info = [
            "Checking session limits:",
            f"- Total Likes:\t\t\t\t{'Limit Reached' if total_likes else 'OK'} ({self.totalLikes}/{args.total_likes_limit})",
            f"- Total Followed:\t\t\t\t{'Limit Reached' if total_followed else 'OK'} ({sum(self.totalFollowed.values())}/{args.total_follows_limit})",
            f"- Total Watched:\t\t\t\t{'Limit Reached' if total_watched else 'OK'} ({self.totalWatched}/{args.total_watch_limit})",
            f"- Total Successful Interactions:\t\t{'Limit Reached' if total_successful else 'OK'} ({sum(self.successfulInteractions.values())}/{args.total_successful_interactions_limit})",
            f"- Total Interactions:\t\t\t{'Limit Reached' if total_interactions else 'OK'} ({sum(self.totalInteractions.values())}/{args.total_interactions_limit})",
        ]

        if limit_type == "ALL":
            if output:
                for line in session_info:
                    logger.info(line)
            else:
                for line in session_info:
                    logger.debug(line)

            return (
                total_likes
                and total_followed
                and total_unfollowed
                and (total_interactions or total_successful)
            )

        elif limit_type == "LIKES":
            if output:
                logger.info(session_info[1])
            else:
                logger.debug(session_info[1])
            return total_likes or (total_interactions or total_successful)

        elif limit_type == "FOLLOWs":
            if output:
                logger.info(session_info[2])
            else:
                logger.debug(session_info[2])
            return total_followed or (total_interactions or total_successful)

        elif limit_type == "WATCHES":
            if output:
                logger.info(session_info[3])
            else:
                logger.debug(session_info[3])
            return total_unfollowed or (total_interactions or total_successful)

        elif limit_type == "SUCCESS":
            if output:
                logger.info(session_info[4])
            else:
                logger.debug(session_info[4])
            return total_successful or total_interactions

        elif limit_type == "TOTAL":
            if output:
                logger.info(session_info[5])
            else:
                logger.debug(session_info[5])
            return total_interactions or total_successful

    def is_finished(self):
        return self.finishTime is not None


class SessionStateEncoder(JSONEncoder):
    def default(self, session_state: SessionState):
        return {
            "id": session_state.id,
            "total_interactions": sum(session_state.totalInteractions.values()),
            "successful_interactions": sum(
                session_state.successfulInteractions.values()
            ),
            "total_followed": sum(session_state.totalFollowed.values()),
            "total_likes": session_state.totalLikes,
            "total_watched": session_state.totalWatched,
            "total_unfollowed": session_state.totalUnfollowed,
            "start_time": str(session_state.startTime),
            "finish_time": str(session_state.finishTime),
            "args": session_state.args,
            "profile": {"followers": str(session_state.my_followers_count)},
        }
