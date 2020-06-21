from datetime import datetime


class SessionState:
    my_username = None
    totalInteractions = {}
    successfulInteractions = {}
    totalLikes = 0
    totalFollowed = 0
    totalUnfollowed = 0
    startTime = None
    finishTime = None

    def __init__(self):
        self.my_username = None
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
