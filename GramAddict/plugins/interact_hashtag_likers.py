from genericpath import exists
import logging
from functools import partial
from random import seed, shuffle

from colorama import Fore, Style
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
from GramAddict.core.utils import get_value, random_sleep
from GramAddict.core.views import TabBarView, HashTagView, ProfileView, OpenedPostView

logger = logging.getLogger(__name__)

# Script Initialization
seed()


class InteractHashtagLikers(Plugin):
    """This plugin handles the functionality of interacting with a bloggers followers"""

    def __init__(self):
        super().__init__()
        self.description = "This plugin handles the functionality of interacting with a bloggers followers"
        self.arguments = [
            {
                "arg": "--hashtag-likers",
                "nargs": "+",
                "help": "list of hashtags with whose likers you want to interact",
                "metavar": ("hashtag1", "hashtag2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--recent-tab",
                "help": "interact with likers of 'Recent' tab instead of 'Top'",
                "action": "store_true",
            },
        ]

    def run(self, device, device_id, args, enabled, storage, sessions):
        class State:
            def __init__(self):
                pass

            is_job_completed = False
            is_likes_limit_reached = False

        self.device_id = device_id
        self.sessions = sessions
        self.session_state = sessions[-1]
        profile_filter = Filter()

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        sources = [source for source in args.hashtag_likers]
        shuffle(sources)

        for source in sources:
            self.state = State()
            if source[0] != "#":
                source = "#" + source
            logger.info(f"Handle {source}", extra={"color": f"{Style.BRIGHT}"})

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
                self.handle_hashtag(
                    device,
                    source,
                    args.likes_count,
                    int(args.follow_percentage),
                    int(args.follow_limit) if args.follow_limit else None,
                    args.recent_tab,
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

    def handle_hashtag(
        self,
        device,
        hashtag,
        likes_count,
        follow_percentage,
        follow_limit,
        recent_tab,
        storage,
        profile_filter,
        on_like,
        on_interaction,
    ):
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
            source=hashtag,
            session_state=self.session_state,
        )
        search_view = TabBarView(device).navigateToSearch()
        random_sleep()
        if not search_view.navigateToHashtag(hashtag):
            return

        if recent_tab:
            logger.info("Switching to Recent tab")
            HashTagView(device)._getRecentTab().click()
            random_sleep()

        logger.info("Opening the first result")
        random_sleep()

        result_view = HashTagView(device)._getRecyclerView()
        HashTagView(device)._getFistImageView(result_view).click()
        random_sleep()

        posts_list_view = ProfileView(device)._getRecyclerView()
        posts_end_detector = ScrollEndDetector(repeats_to_end=2)

        while True:
            if not OpenedPostView(device).open_likers():
                logger.info(
                    "No likes, let's scroll down.", extra={"color": f"{Fore.GREEN}"}
                )
                posts_list_view.scroll(DeviceFacade.Direction.BOTTOM)
                continue

            logger.info("List of likers is opened.")
            posts_end_detector.notify_new_page()
            random_sleep()

            likes_list_view = OpenedPostView(device)._getListViewLikers()
            prev_screen_iterated_likers = []

            while True:
                logger.info("Iterate over visible likers.")
                screen_iterated_likers = []

                try:
                    for item in OpenedPostView(device)._getUserCountainer():
                        username_view = OpenedPostView(device)._getUserName(item)

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
                    logger.info(f"Back to {hashtag}")
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
