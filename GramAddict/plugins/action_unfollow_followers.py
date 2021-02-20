import logging
from enum import Enum, unique

from colorama import Fore
from GramAddict.core.decorators import run_safely
from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.resources import ClassName, ResourceID as resources
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import detect_block, random_sleep, save_crash, get_value
from GramAddict.core.views import (
    UniversalActions,
    Direction,
)

logger = logging.getLogger(__name__)

FOLLOWING_REGEX = "^Following|^Requested"
UNFOLLOW_REGEX = "^Unfollow"


class ActionUnfollowFollowers(Plugin):
    """Handles the functionality of unfollowing your followers"""

    def __init__(self):
        super().__init__()
        self.description = "Handles the functionality of unfollowing your followers"
        self.arguments = [
            {
                "arg": "--unfollow",
                "nargs": None,
                "help": "unfollow at most given number of users. Only users followed by this script will be unfollowed. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-non-followers",
                "nargs": None,
                "help": "unfollow at most given number of users, that don't follow you back. Only users followed by this script will be unfollowed. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-any-non-followers",
                "nargs": None,
                "help": "unfollow at most given number of users, that don't follow you back. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--unfollow-any",
                "nargs": None,
                "help": "unfollow at most given number of users. The order is from oldest to newest followings. It can be a number (e.g. 10) or a range (e.g. 10-20)",
                "metavar": "10-20",
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

    def run(self, device, configs, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            unfollowed_count = 0
            is_job_completed = False

        self.args = configs.args
        self.device_id = configs.args.device
        self.state = State()
        self.session_state = sessions[-1]
        self.sessions = sessions
        self.unfollow_type = plugin
        self.ResourceID = resources(self.args.app_id)

        count_arg = get_value(
            getattr(self.args, self.unfollow_type.replace("-", "_")),
            "Unfollow count: {}",
            10,
        )

        count = min(
            count_arg,
            self.session_state.my_following_count - int(self.args.min_following),
        )

        if self.unfollow_type == "unfollow":
            self.unfollow_type = UnfollowRestriction.FOLLOWED_BY_SCRIPT
        elif self.unfollow_type == "unfollow-non-followers":
            self.unfollow_type = UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS
        elif self.unfollow_type == "unfollow-any-non-followers":
            self.unfollow_type = UnfollowRestriction.ANY_NON_FOLLOWERS
        else:
            self.unfollow_type = UnfollowRestriction.ANY

        if count <= 0:
            logger.info(
                "You want to unfollow "
                + str(count)
                + ", you have "
                + str(self.session_state.my_following_count)
                + " followings, min following is "
                + str(self.args.min_following)
                + ". Finish."
            )
            return

        @run_safely(
            device=device,
            device_id=self.device_id,
            sessions=self.sessions,
            session_state=self.session_state,
            screen_record=self.args.screen_record,
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
            device.back()

        while not self.state.is_job_completed and (self.state.unfollowed_count < count):
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
        followings_button = device.find(
            resourceIdMatches=self.ResourceID.ROW_PROFILE_HEADER_FOLLOWING_CONTAINER
        )
        followings_button.click()

    def sort_followings_by_date(self, device):
        logger.info("Sort followings by date: from oldest to newest.")
        UniversalActions(device)._swipe_points(
            direction=Direction.DOWN,
        )

        sort_button = device.find(
            resourceId=self.ResourceID.SORTING_ENTRY_ROW_ICON,
            className=ClassName.IMAGE_VIEW,
        )
        if not sort_button.exists():
            logger.error(
                "Cannot find button to sort followings. Continue without sorting."
            )
            return
        sort_button.click()
        random_sleep()

        sort_options_recycler_view = device.find(
            resourceId=self.ResourceID.FOLLOW_LIST_SORTING_OPTIONS_RECYCLER_VIEW
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
            resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
            className=ClassName.LINEAR_LAYOUT,
        ).wait()
        sort_container_obj = device.find(
            resourceId=self.ResourceID.SORTING_ENTRY_ROW_ICON
        )
        top_tab_obj = device.find(
            resourceId=self.ResourceID.UNIFIED_FOLLOW_LIST_TAB_LAYOUT
        )
        if sort_container_obj.exists() and top_tab_obj.exists():
            sort_container_bounds = sort_container_obj.get_bounds()["top"]
            list_tab_bounds = top_tab_obj.get_bounds()["bottom"]
            delta = sort_container_bounds - list_tab_bounds
            UniversalActions(device)._swipe_points(
                direction=Direction.DOWN,
                start_point_y=sort_container_bounds,
                delta_y=delta - 50,
            )
        else:
            UniversalActions(device)._swipe_points(
                direction=Direction.DOWN,
            )
        checked = {}
        unfollowed_count = 0
        while True:
            logger.info("Iterate over visible followings")
            random_sleep()
            screen_iterated_followings = 0
            for item in device.find(
                resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
                className=ClassName.LINEAR_LAYOUT,
            ):
                user_info_view = item.child(index=1)
                user_name_view = user_info_view.child(index=0).child()
                if not user_name_view.exists():
                    logger.info(
                        "Next item not found: probably reached end of the screen.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    break

                username = user_name_view.get_text()
                if username not in checked:
                    checked[username] = None
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
                        if following_status == FollowingStatus.NOT_IN_LIST:
                            logger.info(
                                f"@{username} has not been followed by this bot. Skip."
                            )
                            continue
                        elif not following_status == FollowingStatus.FOLLOWED:
                            logger.info(
                                f"Skip @{username}. Following status: {following_status.name}."
                            )
                            continue

                    if (
                        unfollow_restriction == UnfollowRestriction.ANY
                        or unfollow_restriction == UnfollowRestriction.ANY_NON_FOLLOWERS
                    ):
                        following_status = storage.get_following_status(username)
                        if following_status == FollowingStatus.UNFOLLOWED:
                            logger.info(
                                f"Skip @{username}. Following status: {following_status.name}."
                            )
                            continue

                    unfollowed = self.do_unfollow(
                        device,
                        username,
                        my_username,
                        unfollow_restriction
                        == UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS
                        or unfollow_restriction
                        == UnfollowRestriction.ANY_NON_FOLLOWERS,
                    )
                    if unfollowed:
                        storage.add_interacted_user(
                            username, self.session_state.id, unfollowed=True
                        )
                        on_unfollow()
                        unfollowed_count += 1

                    random_sleep()
                    if unfollowed_count >= count:
                        return
                else:
                    logger.debug(f"Already checked {username}")

            if screen_iterated_followings > 0:
                logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                list_view = device.find(
                    resourceId=self.ResourceID.LIST, className=ClassName.LIST_VIEW
                )
                list_view.scroll(DeviceFacade.Direction.BOTTOM)
            else:
                logger.info(
                    "No followings were iterated, finish.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return

    def do_unfollow(
        self, device: DeviceFacade, username, my_username, check_if_is_follower
    ):
        """
        :return: whether unfollow was successful
        """
        username_view = device.find(
            resourceId=self.ResourceID.FOLLOW_LIST_USERNAME,
            className=ClassName.TEXT_VIEW,
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

        unfollow_button = device.find(
            classNameMatches=ClassName.BUTTON,
            clickable=True,
            textMatches=FOLLOWING_REGEX,
        )
        # I don't know/remember the origin of this, if someone does - let's document it
        attempts = 2
        for _ in range(attempts):
            if unfollow_button.exists():
                break

            scrollable = device.find(classNameMatches=ClassName.VIEW_PAGER)
            if scrollable.exists():
                scrollable.scroll(DeviceFacade.Direction.TOP)
            device.find(
                classNameMatches=ClassName.BUTTON,
                clickable=True,
                textMatches=FOLLOWING_REGEX,
            ).wait()
            unfollow_button = device.find(
                classNameMatches=ClassName.BUTTON,
                clickable=True,
                textMatches=FOLLOWING_REGEX,
            )

        if not unfollow_button.exists():
            logger.error("Cannot find Following button.")
            save_crash(device)
        random_sleep()
        logger.debug("Unfollow button click.")
        unfollow_button.click()
        logger.info(f"Unfollow @{username}.", extra={"color": f"{Fore.YELLOW}"})

        # Weirdly enough, this is a fix for after you unfollow someone that follows
        # you back - the next person you unfollow the button is missing on first find
        # additional find - finds it. :shrug:
        confirm_unfollow_button = None
        attempts = 2
        for _ in range(attempts):
            confirm_unfollow_button = device.find(
                resourceId=self.ResourceID.FOLLOW_SHEET_UNFOLLOW_ROW
            )
            confirm_unfollow_button.wait()
            if confirm_unfollow_button.exists():
                break

        if not confirm_unfollow_button or not confirm_unfollow_button.exists():
            logger.error("Cannot confirm unfollow.")
            save_crash(device)
            device.back()
            return False
        logger.debug("Confirm unfollow")
        confirm_unfollow_button.click()

        random_sleep(0, 1)

        # Check if private account confirmation
        private_unfollow_button = device.find(
            classNameMatches=ClassName.BUTTON_OR_TEXTVIEW_REGEX,
            textMatches=UNFOLLOW_REGEX,
        )

        if private_unfollow_button.exists():
            logger.debug("Confirm unfollow private account")
            private_unfollow_button.click()

        detect_block(device)

        logger.info("Back to the followings list.")
        device.back()
        return True

    def check_is_follower(self, device, username, my_username):
        random_sleep()
        logger.info(
            f"Check if @{username} is following you.", extra={"color": f"{Fore.GREEN}"}
        )
        following_container = device.find(
            resourceIdMatches=self.ResourceID.ROW_PROFILE_HEADER_FOLLOWING_CONTAINER
        )
        following_container.click()

        random_sleep()
        device.find(
            resourceId=self.ResourceID.FOLLOW_LIST_USERNAME,
            className=ClassName.TEXT_VIEW,
        ).wait()
        my_username_view = device.find(
            resourceId=self.ResourceID.FOLLOW_LIST_USERNAME,
            className=ClassName.TEXT_VIEW,
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
    ANY_NON_FOLLOWERS = 3
