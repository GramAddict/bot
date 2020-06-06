from datetime import datetime


class SessionState:
    totalInteractions = {}
    successfulInteractions = {}
    totalLikes = 0
    startTime = None
    finishTime = None

    def __init__(self):
        self.startTime = datetime.now()

    def add_interaction(self, blogger, succeed):
        if self.totalInteractions.get(blogger) is None:
            self.totalInteractions[blogger] = 1
        else:
            self.totalInteractions[blogger] += 1

        if self.successfulInteractions.get(blogger) is None:
            self.successfulInteractions[blogger] = 1 if succeed else 0
        else:
            if succeed:
                self.successfulInteractions[blogger] += 1

    def is_finished(self):
        return self.finishTime is not None
