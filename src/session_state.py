import uuid
from datetime import datetime
from json import JSONEncoder


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
    totalUnfollowed = 0
    totalRemovedMassFollowers = 0
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
        self.totalUnfollowed = 0
        self.totalRemovedMassFollowers = 0
        self.startTime = datetime.now()
        self.finishTime = None

    def add_interaction(self, blogger, succeed, followed):
        if self.totalInteractions.get(blogger) is None:
            self.totalInteractions[blogger] = 1
        else:
            self.totalInteractions[blogger] += 1

        if self.successfulInteractions.get(blogger) is None:
            self.successfulInteractions[blogger] = 1 if succeed else 0
        else:
            if succeed:
                self.successfulInteractions[blogger] += 1

        if self.totalFollowed.get(blogger) is None:
            self.totalFollowed[blogger] = 1 if followed else 0
        else:
            if followed:
                self.totalFollowed[blogger] += 1

    def is_finished(self):
        return self.finishTime is not None


class SessionStateEncoder(JSONEncoder):

    def default(self, session_state: SessionState):
        return {
            "id": session_state.id,
            "total_interactions": sum(session_state.totalInteractions.values()),
            "successful_interactions": sum(session_state.successfulInteractions.values()),
            "total_followed": sum(session_state.totalFollowed.values()),
            "total_likes": session_state.totalLikes,
            "total_unfollowed": session_state.totalUnfollowed,
            "total_removed_mass_followers": session_state.totalRemovedMassFollowers,
            "start_time": str(session_state.startTime),
            "finish_time": str(session_state.finishTime),
            "args": session_state.args,
            "profile": {
                "followers": str(session_state.my_followers_count)
            }
        }
