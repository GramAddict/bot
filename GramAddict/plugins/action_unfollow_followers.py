import logging
from enum import Enum, unique
from random import seed, randint

from colorama import Fore
from GramAddict.core.decorators import run_safely
from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.navigation import switch_to_english
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import detect_block, random_sleep, save_crash
from GramAddict.core.views import LanguageNotEnglishException

logger = logging.getLogger(__name__)

FOLLOWING_BUTTON_ID_REGEX = (
    "com.instagram.android:id/row_profile_header_following_container"
    "|com.instagram.android:id/row_profile_header_container_following"
)
BUTTON_REGEX = "android.widget.Button"
BUTTON_OR_TEXTVIEW_REGEX = "android.widget.Button|android.widget.TextView"
FOLLOWING_REGEX = "^Following|^Requested"
UNFOLLOW_REGEX = "^Unfollow"

# Script Initialization
seed()


class ActionUnfollowFollowers(Plugin):
    """This plugin handles the functionality of unfollowing your followers"""

    def __init__(self):
        super().__init__()
        self.description = (
            "This plugin handles the functionality of unfollowing your followers"
        )
        self.arguments = [
            {
                "arg": "--unfollow",
                "nargs": None,
                "help": "unfollow at most given number of users. Only users followed by this script will be unfollowed. The order is from oldest to newest followings. It can be a number (e.g. 100) or a range (e.g. 100-200)",
                "metavar": "100-200",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-non-followers",
                "nargs": None,
                "help": "unfollow at most given number of users, that don't follow you back. Only users followed by this script will be unfollowed. The order is from oldest to newest followings. It can be a number (e.g. 100) or a range (e.g. 100-200)",
                "metavar": "100-200",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-any",
                "nargs": None,
                "help": "unfollow at most given number of users. The order is from oldest to newest followings. It can be a number (e.g. 100) or a range (e.g. 100-200)",
                "metavar": "100-200",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--min-following",
                "nargs": None,
                "help": "minimum amount of followings, after reaching this amount unfollow stops",
                "metavar": "100",
                "default": 0,
            },
        ]

    def run(self, device, device_id, args, enabled, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            unfollowed_count = 0
            is_job_completed = False

        self.device_id = device_id
        self.state = State()
        self.session_state = sessions[-1]
        self.sessions = sessions
        self.unfollow_type = plugin[2:]

        limit_reached = self.session_state.check_limit(args, limit_type="UNFOLLOWS")

        count_arg = get_value(
                    getattr(args, self.unfollow_type, "Unfollow count: {}", 70
                ),

        count = min(
            count_arg,
            self.session_state.my_following_count - int(args.min_following),
        )

        if self.unfollow_type == "unfollow":
            self.unfollow_type = UnfollowRestriction.FOLLOWED_BY_SCRIPT
        elif self.unfollow_type == "unfollow-non-followers":
            self.unfollow_type = UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS
        else:
            self.unfollow_type = UnfollowRestriction.ANY

        if count <= 0:
            logger.info(
                "You want to unfollow "
                + str(count)
                + ", you have "
                + str(self.session_state.my_following_count)
                + " followings, min following is "
                + str(args.min_following)
                + ". Finish."
            )
            return

        @run_safely(
            device=device,
            device_id=self.device_id,
            sessions=self.sessions,
            session_state=self.session_state,
        )
        def job():
            self.unfollow(
                device,
                count - self.state.unfollowed_count,
                self.on_unfollow,
                storage,
                self.unfollow_type,
                self.session_state.my_username,
            )
            logger.info(f"Unfollowed {self.state.unfollowed_count}, finish.")
            self.state.is_job_completed = True

        while not self.state.is_job_completed and (
            self.state.unfollowed_count < count or not limit_reached
        ):
            job()

    def unfollow(
        self, device, count, on_unfollow, storage, unfollow_restriction, my_username
    ):
        self.open_my_followings(device)
        random_sleep()
        self.sort_followings_by_date(device)
        random_sleep()
        self.iterate_over_followings(
            device, count, on_unfollow, storage, unfollow_restriction, my_username
        )

    def on_unfollow(self):
        self.state.unfollowed_count += 1
        self.session_state.totalUnfollowed += 1

    def open_my_followings(self, device):
        logger.info("Open my followings")
        followings_button = device.find(resourceIdMatches=FOLLOWING_BUTTON_ID_REGEX)
        followings_button.click()

    def sort_followings_by_date(self, device):
        logger.info("Sort followings by date: from oldest to newest.")
        sort_button = device.find(
            resourceId="com.instagram.android:id/sorting_entry_row_icon",
            className="android.widget.ImageView",
        )
        if not sort_button.exists():
            logger.error(
                "Cannot find button to sort followings. Continue without sorting."
            )
            return
        sort_button.click()

        sort_options_recycler_view = device.find(
            resourceId="com.instagram.android:id/follow_list_sorting_options_recycler_view"
        )
        if not sort_options_recycler_view.exists():
            logger.error(
                "Cannot find options to sort followings. Continue without sorting."
            )
            return

        sort_options_recycler_view.child(index=2).click()

    def iterate_over_followings(
        self, device, count, on_unfollow, storage, unfollow_restriction, my_username
    ):
        # Wait until list is rendered
        device.find(
            resourceId="com.instagram.android:id/follow_list_container",
            className="android.widget.LinearLayout",
        ).wait()

        unfollowed_count = 0
        while True:
            logger.info("Iterate over visible followings")
            random_sleep()
            screen_iterated_followings = 0

            for item in device.find(
                resourceId="com.instagram.android:id/follow_list_container",
                className="android.widget.LinearLayout",
            ):
                user_info_view = item.child(index=1)
                user_name_view = user_info_view.child(index=0).child()
                if not user_name_view.exists(quick=True):
                    logger.info(
                        "Next item not found: probably reached end of the screen.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    break

                username = user_name_view.get_text()
                screen_iterated_followings += 1

                if storage.is_user_in_whitelist(username):
                    logger.info(f"@{username} is in whitelist. Skip.")
                    continue

                if (
                    unfollow_restriction == UnfollowRestriction.FOLLOWED_BY_SCRIPT
                    or unfollow_restriction
                    == UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS
                ):
                    following_status = storage.get_following_status(username)
                    if not following_status == FollowingStatus.FOLLOWED:
                        logger.info(
                            f"Skip @{username}. Following status: {following_status.name}."
                        )
                        continue

                if unfollow_restriction == UnfollowRestriction.ANY:
                    following_status = storage.get_following_status(username)
                    if following_status == FollowingStatus.UNFOLLOWED:
                        logger.info(
                            f"Skip @{username}. Following status: {following_status.name}."
                        )
                        continue

                logger.info("Unfollow @" + username)
                unfollowed = self.do_unfollow(
                    device,
                    username,
                    my_username,
                    unfollow_restriction
                    == UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS,
                )
                if unfollowed:
                    storage.add_interacted_user(username, unfollowed=True)
                    on_unfollow()
                    unfollowed_count += 1

                random_sleep()
                if unfollowed_count >= count:
                    return

            if screen_iterated_followings > 0:
                logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                list_view = device.find(
                    resourceId="android:id/list", className="android.widget.ListView"
                )
                list_view.scroll(DeviceFacade.Direction.BOTTOM)
            else:
                logger.info(
                    "No followings were iterated, finish.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return

    def do_unfollow(self, device, username, my_username, check_if_is_follower):
        """
        :return: whether unfollow was successful
        """
        username_view = device.find(
            resourceId="com.instagram.android:id/follow_list_username",
            className="android.widget.TextView",
            text=username,
        )
        if not username_view.exists():
            logger.error("Cannot find @" + username + ", skip.")
            return False
        username_view.click()

        if check_if_is_follower and self.check_is_follower(
            device, username, my_username
        ):
            logger.info(f"Skip @{username}. This user is following you.")
            logger.info("Back to the followings list.")
            device.back()
            return False

        attempts = 0

        while True:
            unfollow_button = device.find(
                classNameMatches=BUTTON_REGEX,
                clickable=True,
                textMatches=FOLLOWING_REGEX,
            )
            if not unfollow_button.exists() and attempts <= 1:
                scrollable = device.find(
                    classNameMatches="androidx.viewpager.widget.ViewPager"
                )
                scrollable.scroll(DeviceFacade.Direction.TOP)
                attempts += 1
            else:
                break

        if not unfollow_button.exists():
            logger.error(
                "Cannot find Following button. Maybe not English language is set?"
            )
            save_crash(device)
            switch_to_english(device)
            raise LanguageNotEnglishException()
        unfollow_button.click()

        confirm_unfollow_button = device.find(
            resourceId="com.instagram.android:id/follow_sheet_unfollow_row",
            className="android.widget.TextView",
        )
        if not confirm_unfollow_button.exists():
            logger.error("Cannot confirm unfollow.")
            save_crash(device)
            device.back()
            return False
        confirm_unfollow_button.click()

        random_sleep()

        # Check if private account confirmation
        private_unfollow_button = device.find(
            classNameMatches=BUTTON_OR_TEXTVIEW_REGEX,
            textMatches=UNFOLLOW_REGEX,
        )

        if private_unfollow_button.exists():
            private_unfollow_button.click()

        detect_block(device)

        logger.info("Back to the followings list.")
        device.back()
        return True

    def check_is_follower(self, device, username, my_username):
        logger.info(
            f"Check if @{username} is following you.", extra={"color": f"{Fore.GREEN}"}
        )
        following_container = device.find(resourceIdMatches=FOLLOWING_BUTTON_ID_REGEX)
        following_container.click()

        random_sleep()

        my_username_view = device.find(
            resourceId="com.instagram.android:id/follow_list_username",
            className="android.widget.TextView",
            text=my_username,
        )
        result = my_username_view.exists()
        logger.info("Back to the profile.")
        device.back()
        return result


@unique
class UnfollowRestriction(Enum):
    ANY = 0
    FOLLOWED_BY_SCRIPT = 1
    FOLLOWED_BY_SCRIPT_NON_FOLLOWERS = 2
