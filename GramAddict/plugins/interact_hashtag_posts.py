import logging
from functools import partial
from random import seed, shuffle

from colorama import Style
from GramAddict.core.decorators import run_safely
from GramAddict.core.filter import Filter
from GramAddict.core.interaction import (
    _on_interaction,
    _on_like,
    _on_watch,
    interact_with_user,
    is_follow_limit_reached_for_source,
)
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import get_value, random_sleep, detect_block
from GramAddict.core.views import (
    TabBarView,
    HashTagView,
    PostsViewList,
    SwipeTo,
    LikeMode,
    Owner,
    UniversalActions,
)

logger = logging.getLogger(__name__)

# Script Initialization
seed()


class InteractHashtagPosts(Plugin):
    """Handles the functionality of interacting with a hashtags post owners"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Handles the functionality of interacting with a hashtags post owners"
        )
        self.arguments = [
            {
                "arg": "--hashtag-posts-recent",
                "nargs": "+",
                "help": "interact to hashtag post owners in recent tab",
                "metavar": ("hashtag1", "hashtag2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--hashtag-posts-top",
                "nargs": "+",
                "help": "interact to hashtag post owners in top tab",
                "metavar": ("hashtag1", "hashtag2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--interact-percentage",
                "nargs": None,
                "help": "chance to interact with user/hashtag when applicable (currently in hashtag-posts-recent/top)",
                "metavar": "50",
                "default": "50",
            },
        ]

    def run(self, device, configs, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.device_id = configs.args.device
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.args = configs.args
        profile_filter = Filter()
        self.current_mode = plugin

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        sources = [
            source
            for source in (
                self.args.hashtag_posts_top
                if self.current_mode == "hashtag-posts-top"
                else self.args.hashtag_posts_recent
            )
        ]
        shuffle(sources)

        for source in sources:
            limit_reached = self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.LIKES
            ) and self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.FOLLOWS
            )

            self.state = State()
            if source[0] != "#":
                source = "#" + source
            logger.info(f"Handle {source}", extra={"color": f"{Style.BRIGHT}"})

            on_interaction = partial(
                _on_interaction,
                likes_limit=int(self.args.total_likes_limit),
                source=source,
                interactions_limit=get_value(
                    self.args.interactions_count, "Interactions count: {}", 70
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

            if self.args.stories_count != "0":
                stories_percentage = get_value(
                    self.args.stories_percentage, "Chance of watching stories: {}%", 40
                )
            else:
                stories_percentage = 0

            @run_safely(
                device=device,
                device_id=self.device_id,
                sessions=self.sessions,
                session_state=self.session_state,
                screen_record=self.args.screen_record,
            )
            def job():
                self.handle_hashtag(
                    device,
                    source,
                    self.args.likes_count,
                    self.args.stories_count,
                    stories_percentage,
                    int(self.args.follow_percentage),
                    int(self.args.follow_limit) if self.args.follow_limit else None,
                    int(self.args.interact_percentage),
                    plugin,
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
                    self.args, limit_type=self.session_state.Limit.ALL, output=True
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
        interact_percentage,
        current_job,
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
        if current_job == "hashtag-posts-recent":
            logger.info("Switching to Recent tab")
            HashTagView(device)._getRecentTab().click()
            random_sleep(5, 10)
        if HashTagView(device)._check_if_no_posts():
            UniversalActions(device)._reload_page()
            random_sleep(4, 8)

        logger.info("Opening the first result")

        result_view = HashTagView(device)._getRecyclerView()
        HashTagView(device)._getFistImageView(result_view).click()
        random_sleep()

        def interact():
            can_follow = not is_follow_limit_reached() and (
                storage.get_following_status(username) == FollowingStatus.NONE
                or storage.get_following_status(username) == FollowingStatus.NOT_IN_LIST
            )

            interaction_succeed, followed = interaction(
                device, username=username, can_follow=can_follow
            )
            storage.add_interacted_user(username, followed=followed)
            can_continue = on_interaction(
                succeed=interaction_succeed, followed=followed
            )
            if not can_continue:
                return False
            else:
                return True

        def random_choice():
            from random import randint

            random_number = randint(1, 100)
            if interact_percentage > random_number:
                return True
            else:
                return False

        post_description = ""
        nr_same_post = 0
        nr_same_posts_max = 3
        while True:
            flag, post_description = PostsViewList(device)._check_if_last_post(
                post_description
            )
            if flag:
                nr_same_post += 1
                logger.info(
                    f"Warning: {nr_same_post}/{nr_same_posts_max} repeated posts."
                )
                if nr_same_post == nr_same_posts_max:
                    logger.info(
                        f"Scrolled through {nr_same_posts_max} posts with same description and author. Finish."
                    )
                    break
            else:
                nr_same_post = 0
            if random_choice():
                username = PostsViewList(device)._post_owner(Owner.GET_NAME)[:-3]
                if storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip.")
                elif storage.check_user_was_interacted(username):
                    logger.info(f"@{username}: already interacted. Skip.")
                else:
                    logger.info(f"@{username}: interact")
                    PostsViewList(device)._like_in_post_view(LikeMode.DOUBLE_CLICK)
                    detect_block(device)
                    if not PostsViewList(device)._check_if_liked():
                        PostsViewList(device)._like_in_post_view(LikeMode.SINGLE_CLICK)
                        detect_block(device)
                    random_sleep(1, 2)
                    if PostsViewList(device)._post_owner(Owner.OPEN):
                        if not interact():
                            break
                        device.back()

            PostsViewList(device).swipe_to_fit_posts(SwipeTo.HALF_PHOTO)
            random_sleep(0, 1)
            PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
            random_sleep()
            continue
