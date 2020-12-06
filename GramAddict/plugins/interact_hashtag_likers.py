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
    _on_watch,
    interact_with_user,
    is_follow_limit_reached_for_source,
)
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.scroll_end_detector import ScrollEndDetector
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import get_value, random_sleep
from GramAddict.core.views import (
    TabBarView,
    HashTagView,
    OpenedPostView,
    PostsViewList,
    Swipe_to,
)

logger = logging.getLogger(__name__)

# Script Initialization
seed()


class InteractHashtagLikers(Plugin):
    """Handles the functionality of interacting with a hashtags likers"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Handles the functionality of interacting with a hashtags likers"
        )
        self.arguments = [
            {
                "arg": "--hashtag-likers-top",
                "nargs": "+",
                "help": "list of hashtags in top results with whose likers you want to interact",
                "metavar": ("hashtag1", "hashtag2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--hashtag-likers-recent",
                "nargs": "+",
                "help": "list of hashtags in recent results with whose likers you want to interact",
                "metavar": ("hashtag1", "hashtag2"),
                "default": None,
                "operation": True,
            },
        ]

    def run(self, device, device_id, args, enabled, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.device_id = device_id
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.args = args
        profile_filter = Filter()
        self.current_mode = plugin[2:]

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        sources = [
            source for source in (args.hashtag_likers_top or args.hashtag_likers_recent)
        ]
        shuffle(sources)

        for source in sources:
            limit_reached = self.session_state.check_limit(
                args, limit_type=self.session_state.Limit.LIKES
            ) and self.session_state.check_limit(
                args, limit_type=self.session_state.Limit.FOLLOWS
            )

            self.state = State()
            if source[0] != "#":
                source = "#" + source
            logger.info(f"Handle {source}", extra={"color": f"{Style.BRIGHT}"})

            on_interaction = partial(
                _on_interaction,
                likes_limit=int(args.total_likes_limit),
                source=source,
                interactions_limit=get_value(
                    args.interactions_count, "Interactions count: {}", 70
                ),
                sessions=self.sessions,
                session_state=self.session_state,
                args=self.args,
            )

            on_like = partial(
                _on_like, sessions=self.sessions, session_state=self.session_state
            )

            on_watch = partial(
                _on_watch, sessions=self.sessions, session_state=self.session_state
            )

            if args.stories_count != "0":
                stories_percentage = get_value(
                    args.stories_percentage, "Chance of watching stories: {}%", 40
                )
            else:
                stories_percentage = 0

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
                    args.stories_count,
                    stories_percentage,
                    int(args.follow_percentage),
                    int(args.follow_limit) if args.follow_limit else None,
                    args.hashtag_likers_recent,
                    storage,
                    profile_filter,
                    on_like,
                    on_watch,
                    on_interaction,
                )
                self.state.is_job_completed = True

            while not self.state.is_job_completed and not limit_reached:
                job()

            if limit_reached:
                logger.info("Likes and follows limit reached.")
                self.session_state.check_limit(
                    args, limit_type=self.session_state.Limit.ALL, output=True
                )
                break

    def handle_hashtag(
        self,
        device,
        hashtag,
        likes_count,
        stories_count,
        stories_percentage,
        follow_percentage,
        follow_limit,
        hashtag_likers_recent,
        storage,
        profile_filter,
        on_like,
        on_watch,
        on_interaction,
    ):
        interaction = partial(
            interact_with_user,
            my_username=self.session_state.my_username,
            likes_count=likes_count,
            stories_count=stories_count,
            stories_percentage=stories_percentage,
            follow_percentage=follow_percentage,
            on_like=on_like,
            on_watch=on_watch,
            profile_filter=profile_filter,
            args=self.args,
            session_state=self.session_state,
            current_mode=self.current_mode,
        )

        is_follow_limit_reached = partial(
            is_follow_limit_reached_for_source,
            follow_limit=follow_limit,
            source=hashtag,
            session_state=self.session_state,
        )
        search_view = TabBarView(device).navigateToSearch()
        if not search_view.navigateToHashtag(hashtag):
            return

        if hashtag_likers_recent != None:
            logger.info("Switching to Recent tab")
            HashTagView(device)._getRecentTab().click()
            random_sleep(5, 10)
            if HashTagView(device)._check_if_no_posts():
                HashTagView(device)._reload_page()
                random_sleep(4, 8)

        logger.info("Opening the first result")

        result_view = HashTagView(device)._getRecyclerView()
        HashTagView(device)._getFistImageView(result_view).click()
        random_sleep()

        skipped_list_limit = get_value(self.args.skipped_list_limit, None, 15)
        posts_end_detector = ScrollEndDetector(
            repeats_to_end=2, skipped_list_limit=skipped_list_limit
        )
        first_post = True
        post_description = ""
        while True:

            PostsViewList(device).swipe_to_fit_posts(Swipe_to.HALF_PHOTO)
            if not OpenedPostView(device).open_likers():
                logger.info(
                    "No likes, let's scroll down.", extra={"color": f"{Fore.GREEN}"}
                )

                flag, post_description = PostsViewList(device).check_if_last_post(
                    post_description
                )
                if not flag:
                    PostsViewList(device).swipe_to_fit_posts(Swipe_to.NEXT_POST)
                    continue
                else:
                    break

            logger.info("Open list of likers.")
            posts_end_detector.notify_new_page()
            random_sleep()

            likes_list_view = OpenedPostView(device)._getListViewLikers()
            prev_screen_iterated_likers = []
            while True:
                logger.info("Iterate over visible likers.")
                screen_iterated_likers = []
                opened = False

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
                        profile_interact = profile_filter.check_profile_from_list(
                            device, item, username
                        )
                        screen_iterated_likers.append(username)
                        posts_end_detector.notify_username_iterated(username)
                        if not profile_interact:
                            continue
                        elif storage.is_user_in_blacklist(username):
                            logger.info(f"@{username} is in blacklist. Skip.")
                            continue
                        elif storage.check_user_was_interacted(username):
                            logger.info(f"@{username}: already interacted. Skip.")
                            continue
                        else:
                            logger.info(f"@{username}: interact")
                            username_view.click()

                        can_follow = not is_follow_limit_reached() and (
                            storage.get_following_status(username)
                            == FollowingStatus.NONE
                            or storage.get_following_status(username)
                            == FollowingStatus.NOT_IN_LIST
                        )

                        interaction_succeed, followed = interaction(
                            device, username=username, can_follow=can_follow
                        )
                        storage.add_interacted_user(username, followed=followed)
                        opened = True
                        can_continue = on_interaction(
                            succeed=interaction_succeed, followed=followed
                        )
                        if not can_continue:
                            return

                        logger.info("Back to likers list.")
                        device.back()
                        random_sleep()
                except IndexError:
                    logger.info(
                        "Cannot get next item: probably reached end of the screen.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    break

                if not opened:
                    logger.info(
                        "All followers skipped.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    posts_end_detector.notify_skipped_all()
                    if posts_end_detector.is_skipped_limit_reached():
                        posts_end_detector.reset_skipped_all()
                        device.back()
                        PostsViewList(device).swipe_to_fit_posts(False)
                        break

                if screen_iterated_likers == prev_screen_iterated_likers:
                    logger.info(
                        "Iterated exactly the same likers twice.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    logger.info(f"Back to {hashtag}'s posts list.")
                    device.back()
                    logger.info("Going to the next post.")
                    PostsViewList(device).swipe_to_fit_posts(Swipe_to.NEXT_POST)

                    break

                prev_screen_iterated_likers.clear()
                prev_screen_iterated_likers += screen_iterated_likers

                logger.info(
                    "Scroll to see other likers", extra={"color": f"{Fore.GREEN}"}
                )
                likes_list_view.scroll(DeviceFacade.Direction.BOTTOM)

            if posts_end_detector.is_the_end():
                break
