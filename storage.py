import json
import os
from datetime import datetime
from enum import Enum, unique

FILENAME_INTERACTED_USERS = "interacted_users.json"
USER_LAST_INTERACTION = "last_interaction"
USER_FOLLOWING_STATUS = "following_status"


class Storage:
    interacted_users = {}

    def __init__(self):
        if os.path.exists(FILENAME_INTERACTED_USERS):
            with open(FILENAME_INTERACTED_USERS) as json_file:
                self.interacted_users = json.load(json_file)

    def check_user_was_interacted(self, username):
        return not self.interacted_users.get(username) is None

    def add_interacted_user(self, username):
        user = self.interacted_users.get(username, {})
        user[USER_LAST_INTERACTION] = str(datetime.now())
        user[USER_FOLLOWING_STATUS] = FollowingStatus.NONE.name.lower()
        self.interacted_users[username] = user
        self._update_file()

    def _update_file(self):
        with open(FILENAME_INTERACTED_USERS, 'w') as outfile:
            json.dump(self.interacted_users, outfile, indent=4, sort_keys=False)


@unique
class FollowingStatus(Enum):
    NONE = 0
    FOLLOWED = 1
    UNFOLLOWED = 2
