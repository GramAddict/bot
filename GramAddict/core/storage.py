import json
import logging
import os
from datetime import datetime, timedelta
from enum import Enum, unique

logger = logging.getLogger(__name__)

FILENAME_HISTORY_FILTER_USERS = "history_filters_users.json"
FILENAME_INTERACTED_USERS = "interacted_users.json"
USER_LAST_INTERACTION = "last_interaction"
USER_FOLLOWING_STATUS = "following_status"

FILENAME_WHITELIST = "whitelist.txt"
FILENAME_BLACKLIST = "blacklist.txt"


class Storage:
    interacted_users_path = None
    interacted_users = {}

    history_filter_users_path = None
    history_filter_users = {}

    whitelist = []
    blacklist = []

    def __init__(self, my_username):
        if my_username is None:
            logger.error(
                "No username, thus the script won't get access to interacted users and sessions data"
            )
            return

        if not os.path.exists(my_username):
            os.makedirs(my_username)

        self.interacted_users_path = my_username + "/" + FILENAME_INTERACTED_USERS
        if os.path.exists(self.interacted_users_path):
            with open(self.interacted_users_path) as json_file:
                self.interacted_users = json.load(json_file)

        self.history_filter_users_path = (
            my_username + "/" + FILENAME_HISTORY_FILTER_USERS
        )
        if os.path.exists(self.history_filter_users_path):
            with open(self.history_filter_users_path) as json_file:
                self.history_filter_users = json.load(json_file)

        whitelist_path = my_username + "/" + FILENAME_WHITELIST
        if os.path.exists(whitelist_path):
            with open(whitelist_path) as file:
                self.whitelist = [line.rstrip() for line in file]

        blacklist_path = my_username + "/" + FILENAME_BLACKLIST
        if os.path.exists(blacklist_path):
            with open(blacklist_path) as file:
                self.blacklist = [line.rstrip() for line in file]

    def check_user_was_interacted(self, username):
        return not self.interacted_users.get(username) is None

    def check_user_was_interacted_recently(self, username):
        user = self.interacted_users.get(username)
        if user is None:
            return False

        last_interaction = datetime.strptime(
            user[USER_LAST_INTERACTION], "%Y-%m-%d %H:%M:%S.%f"
        )
        return datetime.now() - last_interaction <= timedelta(days=3)

    def get_following_status(self, username):
        user = self.interacted_users.get(username)
        if user is None:
            return FollowingStatus.NOT_IN_LIST
        else:
            return FollowingStatus[user[USER_FOLLOWING_STATUS].upper()]

    def add_filter_user(self, username, profile_data, skip_reason=None):
        # user = self.history_filter_users.get(username, {})
        user = profile_data.__dict__
        user["follow_button_text"] = profile_data.follow_button_text.name
        user["skip_reason"] = None if skip_reason is None else skip_reason.name
        self.history_filter_users[username] = user
        # self._update_file()
        if self.history_filter_users_path is not None:
            with open(self.history_filter_users_path, "w") as outfile:
                json.dump(self.history_filter_users, outfile, indent=4, sort_keys=False)

    def add_interacted_user(
        self,
        username,
        session_id,
        followed=False,
        unfollowed=False,
        liked=0,
        watched=0,
        job_name=None,
        target=None,
    ):
        user = self.interacted_users.get(username, {})
        user[USER_LAST_INTERACTION] = str(datetime.now())

        if followed:
            user[USER_FOLLOWING_STATUS] = FollowingStatus.FOLLOWED.name.lower()
        elif unfollowed:
            user[USER_FOLLOWING_STATUS] = FollowingStatus.UNFOLLOWED.name.lower()
        else:
            user[USER_FOLLOWING_STATUS] = FollowingStatus.NONE.name.lower()

        # Save only the last session_id
        user["session_id"] = session_id

        # Save only the last job_name and target
        user["job_name"] = job_name
        user["target"] = target

        # Increase the value of liked or watched if we have already a value
        user["liked"] = liked if "liked" not in user else (user["liked"] + liked)
        user["watched"] = (
            watched if "watched" not in user else (user["watched"] + watched)
        )

        # Update the followed or unfollowed boolean only if we have a real update
        user["followed"] = (
            followed
            if "followed" not in user or user["followed"] != followed
            else user["followed"]
        )
        user["unfollowed"] = (
            unfollowed
            if "unfollowed" not in user or user["unfollowed"] != unfollowed
            else user["unfollowed"]
        )

        self.interacted_users[username] = user
        self._update_file()

    def is_user_in_whitelist(self, username):
        return username in self.whitelist

    def is_user_in_blacklist(self, username):
        return username in self.blacklist

    def _get_last_day_interactions_count(self):
        count = 0
        users_list = list(self.interacted_users.values())
        for user in users_list:
            last_interaction = datetime.strptime(
                user[USER_LAST_INTERACTION], "%Y-%m-%d %H:%M:%S.%f"
            )
            is_last_day = datetime.now() - last_interaction <= timedelta(days=1)
            if is_last_day:
                count += 1
        return count

    def _update_file(self):
        if self.interacted_users_path is not None:
            with open(self.interacted_users_path, "w") as outfile:
                json.dump(self.interacted_users, outfile, indent=4, sort_keys=False)


@unique
class FollowingStatus(Enum):
    NONE = 0
    FOLLOWED = 1
    UNFOLLOWED = 2
    NOT_IN_LIST = 3
