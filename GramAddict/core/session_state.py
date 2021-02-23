import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum, auto
from json import JSONEncoder
from GramAddict.core.utils import get_value

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
    totalComments = 0
    totalWatched = 0
    totalUnfollowed = 0
    removedMassFollowers = []
    totalScraped = 0
    startTime = None
    finishTime = None

    def __init__(self, configs):
        self.id = str(uuid.uuid4())
        self.args = configs.args
        self.my_username = None
        self.my_followers_count = None
        self.my_following_count = None
        self.totalInteractions = {}
        self.successfulInteractions = {}
        self.totalFollowed = {}
        self.totalLikes = 0
        self.totalComments = 0
        self.totalWatched = 0
        self.totalUnfollowed = 0
        self.removedMassFollowers = []
        self.totalScraped = {}
        self.startTime = datetime.now()
        self.finishTime = None

    def add_interaction(self, source, succeed, followed, scraped):
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
        if self.totalScraped.get(source) is None:
            self.totalScraped[source] = 1 if scraped else 0
        else:
            if scraped:
                self.totalScraped[source] += 1

    def check_limit(self, args, limit_type=None, output=False):
        """Returns True if limit reached - else False"""
        limit_type = SessionState.Limit.ALL if limit_type is None else limit_type
        likes_limit = get_value(args.total_likes_limit, None, 300)
        total_likes = self.totalLikes >= int(likes_limit)
        follow_limit = get_value(args.total_follows_limit, None, 50)
        total_followed = sum(self.totalFollowed.values()) >= int(follow_limit)
        comments_limit = get_value(args.total_comments_limit, None, 10)
        total_comments = self.totalComments >= int(comments_limit)
        watch_limit = get_value(args.total_watches_limit, None, 50)
        total_watched = self.totalWatched >= int(watch_limit)
        success_limit = get_value(args.total_successful_interactions_limit, None, 100)
        total_successful = sum(self.successfulInteractions.values()) >= int(
            success_limit
        )
        total_limit = get_value(args.total_interactions_limit, None, 1000)
        total_interactions = sum(self.totalInteractions.values()) >= int(total_limit)
        total_scraped = sum(self.totalScraped.values()) >= int(total_limit)

        session_info = [
            "Checking session limits:",
            f"- Total Likes:\t\t\t\t{'Limit Reached' if total_likes else 'OK'} ({self.totalLikes}/{likes_limit})",
            f"- Total Comments:\t\t\t\t{'Limit Reached' if total_likes else 'OK'} ({self.totalComments}/{comments_limit})",
            f"- Total Followed:\t\t\t\t{'Limit Reached' if total_followed else 'OK'} ({sum(self.totalFollowed.values())}/{follow_limit})",
            f"- Total Watched:\t\t\t\t{'Limit Reached' if total_watched else 'OK'} ({self.totalWatched}/{watch_limit})",
            f"- Total Successful Interactions:\t\t{'Limit Reached' if total_successful else 'OK'} ({sum(self.successfulInteractions.values())}/{success_limit})",
            f"- Total Interactions:\t\t\t{'Limit Reached' if total_interactions else 'OK'} ({sum(self.totalInteractions.values())}/{total_limit})",
            f"- Total Successful Scraped Users:\t\t{'Limit Reached' if total_scraped else 'OK'} ({sum(self.totalScraped.values())}/{total_limit})",
        ]

        if limit_type == SessionState.Limit.ALL:
            if output:
                for line in session_info:
                    logger.info(line)
            else:
                for line in session_info:
                    logger.debug(line)

            return (total_likes and total_followed) or (
                total_interactions or total_successful
            )

        elif limit_type == SessionState.Limit.LIKES:
            if output:
                logger.info(session_info[1])
            else:
                logger.debug(session_info[1])
            return total_likes or (total_interactions or total_successful)

        elif limit_type == SessionState.Limit.COMMENTS:
            if output:
                logger.info(session_info[2])
            else:
                logger.debug(session_info[2])
            return total_comments or (total_interactions or total_successful)

        elif limit_type == SessionState.Limit.FOLLOWS:
            if output:
                logger.info(session_info[3])
            else:
                logger.debug(session_info[3])
            return total_followed or (total_interactions or total_successful)

        elif limit_type == SessionState.Limit.WATCHES:
            if output:
                logger.info(session_info[4])
            else:
                logger.debug(session_info[4])
            return total_watched or (total_interactions or total_successful)

        elif limit_type == SessionState.Limit.SUCCESS:
            if output:
                logger.info(session_info[5])
            else:
                logger.debug(session_info[5])
            return total_successful or total_interactions

        elif limit_type == SessionState.Limit.TOTAL:
            if output:
                logger.info(session_info[6])
            else:
                logger.debug(session_info[6])
            return total_interactions or total_successful

        elif limit_type == SessionState.Limit.SCRAPED:
            if output:
                logger.info(session_info[6])
            else:
                logger.debug(session_info[6])
            return total_scraped

    @staticmethod
    def inside_working_hours(working_hours, delta_min):
        def time_in_range(start, end, x):
            if start <= end:
                return start <= x <= end
            else:
                return start <= x or x <= end

        in_range = False
        time_left_list = []
        current_time = datetime.now()
        delta = timedelta(minutes=delta_min)
        for n in working_hours:
            today = current_time.strftime("%Y-%m-%d")
            inf_value = f"{n.split('-')[0]} {today}"
            inf = datetime.strptime(inf_value, "%H.%M %Y-%m-%d") + delta
            sup_value = f"{n.split('-')[1]} {today}"
            sup = datetime.strptime(sup_value, "%H.%M %Y-%m-%d") + delta
            if time_in_range(inf.time(), sup.time(), current_time.time()):
                in_range = True
                return in_range, 0
            else:
                time_left = inf - current_time
                if time_left >= timedelta(0):
                    time_left_list.append(time_left)
                else:
                    time_left_list.append(time_left + timedelta(days=1))

        return (
            in_range,
            min(time_left_list) if len(time_left_list) > 1 else time_left_list[0],
        )

    def is_finished(self):
        return self.finishTime is not None

    class Limit(Enum):
        ALL = auto()
        LIKES = auto()
        COMMENTS = auto()
        FOLLOWS = auto()
        WATCHES = auto()
        SUCCESS = auto()
        TOTAL = auto()
        SCRAPED = auto()


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
            "total_comments": session_state.totalComments,
            "total_watched": session_state.totalWatched,
            "total_unfollowed": session_state.totalUnfollowed,
            "total_scraped": session_state.totalScraped,
            "start_time": str(session_state.startTime),
            "finish_time": str(session_state.finishTime),
            "args": session_state.args.__dict__,
            "profile": {"followers": str(session_state.my_followers_count)},
        }


# %%
