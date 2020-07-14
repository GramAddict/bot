import uuid
from datetime import datetime
from json import JSONEncoder


class SessionState:
    id = None
    args = {}
    my_username = None
    my_followers_count = None
    totalInteractions = {}
    successfulInteractions = {}
    totalLikes = 0
    totalFollowed = 0
    totalUnfollowed = 0
    startTime = None
    finishTime = None

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.args = {}
        self.my_username = None
        self.my_followers_count = None
        self.totalInteractions = {}
        self.successfulInteractions = {}
        self.totalLikes = 0
        self.totalFollowed = 0
        self.totalUnfollowed = 0
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

        if followed:
            self.totalFollowed += 1

    def is_finished(self):
        return self.finishTime is not None


class SessionStateEncoder(JSONEncoder):

    def default(self, session_state: SessionState):
        return {
            "id": session_state.id,
            "total_interactions": sum(session_state.totalInteractions.values()),
            "successful_interactions": sum(session_state.successfulInteractions.values()),
            "total_likes": session_state.totalLikes,
            "total_followed": session_state.totalFollowed,
            "total_unfollowed": session_state.totalUnfollowed,
            "start_time": str(session_state.startTime),
            "finish_time": str(session_state.finishTime),
            "args": session_state.args,
            "profile": {
                "followers": str(session_state.my_followers_count)
            }
        }
