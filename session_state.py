from datetime import datetime


class SessionState:
    totalInteractions = 0
    successfulInteractions = 0
    totalLikes = 0
    startTime = datetime.now()

    def __init__(self):
        pass

    def reset(self):
        self.totalInteractions = 0
        self.successfulInteractions = 0
        self.totalLikes = 0
        self.startTime = datetime.now()
