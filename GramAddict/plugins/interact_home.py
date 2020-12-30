import logging
from functools import partial
from colorama import Style
from datetime import datetime, timedelta
from GramAddict.core.decorators import run_safely
from GramAddict.core.interaction import _on_like
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.utils import random_sleep, open_instagram, detect_block, get_value

logger = logging.getLogger(__name__)

from GramAddict.core.views import (
    TabBarView,
    PostsViewList,
    SwipeTo,
    LikeMode,
    Owner,
    UniversalActions,
)


class LikesFromHome(Plugin):
    """Interact with posts from home screen. Uncomment to use."""

    def __init__(self):
        super().__init__()
        self.description = "Interact with posts from home feed."
        self.arguments = [
            {
                "arg": "--like-from-home",
                "nargs": None,  # see argparse docs for usage - if not needed use None
                "help": "Set the number of minutes to scroll and like. Default: 5.",
                "metavar": 5,  # see argparse docs for usage - if not needed use None
                "default": 5,  # see argparse docs for usage - if not needed use None
                "operation": True,  # If the argument is an operation, set to true. Otherwise do not include
            }
        ]

    def run(self, device, configs, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.source = "home"
        self.start_time = datetime.now()
        self.device_id = configs.args.device
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.args = configs.args
        self.current_mode = plugin
        if self.args.like_from_home:
            self.time_at_home = get_value(
                self.args.like_from_home, "Time browsing home: {} minutes", 5
            )
        else:
            self.time_at_home = 0

        limit_reached = self.session_state.check_limit(
            self.args, limit_type=self.session_state.Limit.LIKES
        )
        on_like = partial(
            _on_like, sessions=self.sessions, session_state=self.session_state
        )
        self.state = State()

        logger.info(
            f"Handle {self.source}",
            extra={
                "color": f"{Style.BRIGHT}. Scrolling and liking for {self.time_at_home} minutes"
            },
        )

        @run_safely(
            device=device,
            device_id=self.device_id,
            sessions=self.sessions,
            session_state=self.session_state,
        )
        def job():
            logger.info(
                f"Started liking home at: {self.start_time.strftime('%H:%M:%S')}. Will browse for { self.time_at_home } minutes."
            )

            self.handle_home(
                device,
                self.source,
                self.args.likes_count,
                int(self.args.interact_percentage),
                plugin,
                storage,
                on_like,
            )
            self.state.is_job_completed = True
            logger.info(
                f"Finished liking from home at {datetime.now().strftime('%H:%M:%S')}"
            )
            ran_for = datetime.now() - self.start_time
            logger.info(f"Liked home for {ran_for}")

        while not self.state.is_job_completed and not limit_reached:
            job()
            if limit_reached:
                logger.info("Likes limit reached.")
                self.session_state.check_limit(
                    self.args, limit_type=self.session_state.Limit.ALL, output=True
                )
                break

    def handle_home(
        self,
        device,
        source,
        likes_count,
        interact_percentage,
        current_job,
        storage,
        on_like,
    ):

        if open_instagram() is not True:
            # Navigate to home
            open_instagram()

        logger.info("Go to Home")
        TabBarView(device).navigateToHome()
        random_sleep(1, 2)
        logger.info("Refresh to get latest posts")
        UniversalActions(device)._reload_page()
        random_sleep(2, 4)
        nr_same_post = 0
        post_description = ""
        nr_same_posts_max = 3

        # check limit and check time left
        while not self.session_state.check_limit(
            self.args, limit_type=self.session_state.Limit.LIKES
        ) and not datetime.now() - self.start_time >= timedelta(
            minutes=self.time_at_home
        ):

            post_description = PostsViewList(device)._check_if_last_post(
                post_description
            )
            ad = PostsViewList(device)._check_if_ad()
            liked = PostsViewList(device)._check_if_liked()
            nr_same_post += 1
            if nr_same_post == nr_same_posts_max:
                logger.info(
                    f"Scrolled through {nr_same_posts_max} posts with same description and author. Finish."
                )
                break

            else:
                nr_same_post = 0
                if True:
                    username = PostsViewList(device)._post_owner(Owner.GET_NAME)[:-3]
                    if storage.is_user_in_blacklist(username):
                        logger.info(f"@{username} is in blacklist. Skip.")
                    elif liked:
                        logger.info("Already liked it. Skip.")
                    elif ad:
                        logger.info("Looks like an ad. Skip.")
                    else:
                        logger.info(f"Liking post by: {username}")
                        PostsViewList(device)._like_in_post_view(LikeMode.DOUBLE_CLICK)
                        on_like()
                        detect_block(device)
                        if not PostsViewList(device)._check_if_liked():
                            PostsViewList(device)._like_in_post_view(
                                LikeMode.SINGLE_CLICK
                            )
                            on_like()
                            detect_block(device)
                        random_sleep(1, 2)
                PostsViewList(device).swipe_to_fit_posts(SwipeTo.HALF_PHOTO)
                random_sleep(0, 1)
                PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
