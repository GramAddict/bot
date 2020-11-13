import logging
from functools import partial
from random import seed, shuffle

from colorama import Fore
from GramAddict.core.decorators import run_safely
from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.filter import Filter
from GramAddict.core.interaction import (
    _on_interaction,
    _on_like,
    _on_likes_limit_reached,
    _on_watch,
    interact_with_user,
    is_follow_limit_reached_for_source,
)
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.scroll_end_detector import ScrollEndDetector
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import get_value, random_sleep

logger = logging.getLogger(__name__)

from GramAddict.core.views import TabBarView

FOLLOWERS_BUTTON_ID_REGEX = (
    "com.instagram.android:id/row_profile_header_followers_container"
    "|com.instagram.android:id/row_profile_header_container_followers"
)

# Script Initialization
seed()


class InteractBloggerFollowers(Plugin):
    """This plugin handles the functionality of interacting with a bloggers followers"""

    def __init__(self):
        super().__init__()
        self.description = "This plugin handles the functionality of interacting with a bloggers followers"
        self.arguments = [
            {
                "arg": "--blogger-followers",
                "nargs": "+",
                "help": "list of usernames with whose followers you want to interact",
                "metavar": ("username1", "username2"),
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, device_id, args, enabled, storage, sessions):
        class State:
            def __init__(self):
                pass

            is_job_completed = False
            is_likes_limit_reached = False

        self.device_id = device_id
        self.state = None
        self.sessions = sessions
        self.session_state = sessions[-1]
        profile_filter = Filter()

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        sources = [source for source in args.blogger_followers]
        shuffle(sources)

        for source in sources:
            self.state = State()
            is_myself = source[1:] == self.session_state.my_username
            its_you = is_myself and " (it's you)" or ""
            logger.info(f"Handle {source} {its_you}")

            on_likes_limit_reached = partial(_on_likes_limit_reached, state=self.state)

            on_interaction = partial(
                _on_interaction,
                on_likes_limit_reached=on_likes_limit_reached,
                likes_limit=int(args.total_likes_limit),
                source=source,
                interactions_limit=get_value(
                    args.interactions_count, "Interactions count: {}", 70
                ),
                sessions=self.sessions,
                session_state=self.session_state,
            )

            on_like = partial(
                _on_like, sessions=self.sessions, session_state=self.session_state
            )
            on_watch = partial(
                _on_watch, sessions=self.sessions, session_state=self.session_state
            )

            @run_safely(
                device=device,
                device_id=self.device_id,
                sessions=self.sessions,
                session_state=self.session_state,
            )
            def job():
                self.handle_blogger(
                    device,
                    source[1:] if "@" in source else source,
                    args.likes_count,
                    args.stories_count,
                    int(args.follow_percentage),
                    int(args.follow_limit) if args.follow_limit else None,
                    storage,
                    profile_filter,
                    on_like,
                    on_watch,
                    on_interaction,
                )
                self.state.is_job_completed = True

            while (
                not self.state.is_job_completed
                and not self.state.is_likes_limit_reached
            ):
                job()

            if self.state.is_likes_limit_reached:
                break

    def handle_blogger(
        self,
        device,
        username,
        likes_count,
        stories_count,
        follow_percentage,
        follow_limit,
        storage,
        profile_filter,
        on_like,
        on_watch,
        on_interaction,
    ):
        is_myself = username == self.session_state.my_username
        interaction = partial(
            interact_with_user,
            my_username=self.session_state.my_username,
            likes_count=likes_count,
            stories_count=stories_count,
            follow_percentage=follow_percentage,
            on_like=on_like,
            on_watch=on_watch,
            profile_filter=profile_filter,
        )
        is_follow_limit_reached = partial(
            is_follow_limit_reached_for_source,
            follow_limit=follow_limit,
            source=username,
            session_state=self.session_state,
        )

        if not self.open_user_followers(device, username):
            return
        if is_myself:
            self.scroll_to_bottom(device)
        self.iterate_over_followers(
            device,
            interaction,
            is_follow_limit_reached,
            storage,
            on_interaction,
            is_myself,
        )

    def open_user_followers(self, device, username):
        if username is None:
            logger.info("Open your followers")
            profile_view = TabBarView(device).navigateToProfile()
            profile_view.navigateToFollowers()
        else:
            search_view = TabBarView(device).navigateToSearch()
            profile_view = search_view.navigateToUsername(username)
            random_sleep()
            if not profile_view:
                return False

            logger.info(f"Open @{username} followers")
            profile_view.navigateToFollowers()

        return True

    def scroll_to_bottom(self, device):
        logger.info("Scroll to bottom")

        def is_end_reached():
            see_all_button = device.find(
                resourceId="com.instagram.android:id/see_all_button",
                className="android.widget.TextView",
            )
            return see_all_button.exists()

        list_view = device.find(
            resourceId="android:id/list", className="android.widget.ListView"
        )
        while not is_end_reached():
            list_view.swipe(DeviceFacade.Direction.BOTTOM)

        logger.info("Scroll back to the first follower")

        def is_at_least_one_follower():
            follower = device.find(
                resourceId="com.instagram.android:id/follow_list_container",
                className="android.widget.LinearLayout",
            )
            return follower.exists()

        while not is_at_least_one_follower():
            list_view.scroll(DeviceFacade.Direction.TOP)

    def iterate_over_followers(
        self,
        device,
        interaction,
        is_follow_limit_reached,
        storage,
        on_interaction,
        is_myself,
    ):
        # Wait until list is rendered
        device.find(
            resourceId="com.instagram.android:id/follow_list_container",
            className="android.widget.LinearLayout",
        ).wait()

        def scrolled_to_top():
            row_search = device.find(
                resourceId="com.instagram.android:id/row_search_edit_text",
                className="android.widget.EditText",
            )
            return row_search.exists()

        scroll_end_detector = ScrollEndDetector()
        while True:
            logger.info("Iterate over visible followers")
            random_sleep()
            screen_iterated_followers = []
            screen_skipped_followers_count = 0
            scroll_end_detector.notify_new_page()

            try:
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
                    screen_iterated_followers.append(username)
                    scroll_end_detector.notify_username_iterated(username)

                    if storage.is_user_in_blacklist(username):
                        logger.info(f"@{username} is in blacklist. Skip.")
                    elif not is_myself and storage.check_user_was_interacted(username):
                        logger.info(f"@{username}: already interacted. Skip.")
                        screen_skipped_followers_count += 1
                    elif is_myself and storage.check_user_was_interacted_recently(
                        username
                    ):
                        logger.info(
                            f"@{username}: already interacted in the last week. Skip."
                        )
                        screen_skipped_followers_count += 1
                    else:
                        logger.info(f"@{username}: interact")
                        user_name_view.click()

                        can_follow = (
                            not is_myself
                            and not is_follow_limit_reached()
                            and storage.get_following_status(username)
                            == FollowingStatus.NONE
                        )

                        interaction_succeed, followed = interaction(
                            device, username=username, can_follow=can_follow
                        )
                        storage.add_interacted_user(username, followed=followed)
                        can_continue = on_interaction(
                            succeed=interaction_succeed, followed=followed
                        )

                        if not can_continue:
                            return

                        logger.info("Back to followers list")
                        device.back()
                        random_sleep()
            except IndexError:
                logger.error(
                    "Cannot get next item: probably reached end of the screen."
                )

            if is_myself and scrolled_to_top():
                logger.info(
                    "Scrolled to top, finish.", extra={"color": f"{Fore.GREEN}"}
                )
                return
            elif len(screen_iterated_followers) > 0:
                load_more_button = device.find(
                    resourceId="com.instagram.android:id/row_load_more_button"
                )
                load_more_button_exists = load_more_button.exists(quick=True)

                if scroll_end_detector.is_the_end():
                    return

                need_swipe = screen_skipped_followers_count == len(
                    screen_iterated_followers
                )
                list_view = device.find(
                    resourceId="android:id/list", className="android.widget.ListView"
                )
                if not list_view.exists():
                    logger.error(
                        "Cannot find the list of followers. Trying to press back again."
                    )
                    device.back()
                    list_view = device.find(
                        resourceId="android:id/list",
                        className="android.widget.ListView",
                    )

                if is_myself:
                    logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                    list_view.scroll(DeviceFacade.Direction.TOP)
                else:
                    pressed_retry = False
                    if load_more_button_exists:
                        retry_button = load_more_button.child(
                            className="android.widget.ImageView"
                        )
                        if retry_button.exists():
                            logger.info('Press "Load" button')
                            retry_button.click()
                            random_sleep()
                            pressed_retry = True

                    if need_swipe and not pressed_retry:
                        logger.info(
                            "All followers skipped, let's do a swipe",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        list_view.swipe(DeviceFacade.Direction.BOTTOM)
                    else:
                        logger.info(
                            "Need to scroll now", extra={"color": f"{Fore.GREEN}"}
                        )
                        list_view.scroll(DeviceFacade.Direction.BOTTOM)
            else:
                logger.info(
                    "No followers were iterated, finish.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return
