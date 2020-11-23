import logging
from enum import Enum, unique
from functools import partial
from random import randint, seed, shuffle
from time import sleep

from colorama import Fore
from GramAddict.core.decorators import run_safely
from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.filter import Filter
from GramAddict.core.interaction import (
    _on_interaction,
    _on_like,
    _on_likes_limit_reached,
    interact_with_user,
    is_follow_limit_reached_for_source,
)
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.scroll_end_detector import ScrollEndDetector
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import get_value, random_sleep, save_crash
from GramAddict.core.views import LanguageNotEnglishException, ProfileView

logger = logging.getLogger(__name__)

from GramAddict.core.views import TabBarView

from GramAddict.core.navigation import open_user, open_likers

BUTTON_REGEX = "android.widget.Button"
BUTTON_OR_TEXTVIEW_REGEX = "android.widget.Button|android.widget.TextView"
FOLLOWING_REGEX = "^Following|^Requested"
UNFOLLOW_REGEX = "^Unfollow"


# Script Initialization
seed()


class InteractPostLikers(Plugin):
    """Interact someones posts likers"""

    def __init__(self):
        super().__init__()
        self.description = "Interact someones posts likers"
        self.arguments = [
            {
                "arg": "--interact-post-likers",
                "nargs": "+",
                "help": "Interact someones posts likers",
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
        sources = [source for source in args.interact_post_likers]
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
                    int(args.follow_percentage),
                    int(args.follow_limit) if args.follow_limit else None,
                    storage,
                    profile_filter,
                    on_like,
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
        follow_percentage,
        follow_limit,
        storage,
        profile_filter,
        on_like,
        on_interaction,
    ):
        is_myself = username == self.session_state.my_username
        interaction = partial(
            interact_with_user,
            my_username=self.session_state.my_username,
            likes_count=likes_count,
            follow_percentage=follow_percentage,
            on_like=on_like,
            profile_filter=profile_filter,
        )
        is_follow_limit_reached = partial(
            is_follow_limit_reached_for_source,
            follow_limit=follow_limit,
            source=username,
            session_state=self.session_state,
        )

        if not open_user(device, username):
            return

        profile_view = ProfileView(device)
        is_private = profile_view.isPrivateAccount()
        posts_count = profile_view.getPostsCount()
        posts_tab_view = profile_view.navigateToPostsTab()
        if posts_tab_view.scrollDown():  # scroll down to view all maximum 12 posts
            logger.info("Scrolled down to see more posts.")
        random_sleep()
        number_of_rows_to_use = 4
        photos_indices = list(range(0, number_of_rows_to_use * 3))
        shuffle(photos_indices)
        photos_indices = sorted(photos_indices)
        print(photos_indices)
        x = randint(0, len(photos_indices) - 1)
        photo_index = photos_indices[x]
        opened_post_view = None
        row = 0
        column = 0
        while opened_post_view == None:
            x = randint(0, 1)
            photo_index = photos_indices[x]
            row = photo_index // 3
            column = photo_index - row * 3
            opened_post_view = posts_tab_view.navigateToPost(row, column)
        logger.info(f"Open post  ({row + 1} row, {column + 1} column)")
        random_sleep()
        posts_list_view = device.find(
            resourceId="android:id/list",
            className="androidx.recyclerview.widget.RecyclerView",
        )

        posts_end_detector = ScrollEndDetector(repeats_to_end=2)

        while True:
            if not open_likers(device):
                logger.info(
                    "No likes, let's scroll down.", extra={"color": f"{Fore.GREEN}"}
                )
                posts_list_view.scroll(DeviceFacade.Direction.BOTTOM)
                continue

            logger.info("List of likers is opened.")
            posts_end_detector.notify_new_page()
            random_sleep()

            likes_list_view = device.find(
                resourceId="android:id/list", className="android.widget.ListView"
            )
            prev_screen_iterated_likers = []
            while True:
                logger.info("Iterate over visible likers.")
                screen_iterated_likers = []

                try:
                    for item in device.find(
                        resourceId="com.instagram.android:id/row_user_container_base",
                        className="android.widget.LinearLayout",
                    ):
                        username_view = item.child(
                            resourceId="com.instagram.android:id/row_user_primary_name",
                            className="android.widget.TextView",
                        )
                        if not username_view.exists(quick=True):
                            logger.info(
                                "Next item not found: probably reached end of the screen.",
                                extra={"color": f"{Fore.GREEN}"},
                            )
                            break

                        username = username_view.get_text()
                        screen_iterated_likers.append(username)
                        posts_end_detector.notify_username_iterated(username)

                        if storage.is_user_in_blacklist(username):
                            logger.info(f"@{username} is in blacklist. Skip.")
                            continue
                        elif storage.check_user_was_interacted(username):
                            logger.info(f"@{username}: already interacted. Skip.")
                            continue
                        else:
                            logger.info(f"@{username}: interact")
                            username_view.click()

                        can_follow = (
                            not is_follow_limit_reached()
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

                        logger.info("Back to likers list")
                        device.back()
                        random_sleep()
                except IndexError:
                    logger.info(
                        "Cannot get next item: probably reached end of the screen.",
                        extra={"color": f"{Fore.GREEN}"},
                    )

                if screen_iterated_likers == prev_screen_iterated_likers:
                    logger.info(
                        "Iterated exactly the same likers twice, finish.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    logger.info(f"Back to #{username}")
                    device.back()
                    break

                prev_screen_iterated_likers.clear()
                prev_screen_iterated_likers += screen_iterated_likers

                logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                likes_list_view.scroll(DeviceFacade.Direction.BOTTOM)

            if posts_end_detector.is_the_end():
                break
            else:
                posts_list_view.scroll(DeviceFacade.Direction.BOTTOM)
