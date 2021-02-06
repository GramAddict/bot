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
    handle_posts,
)
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.utils import get_value

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
        profile_filter = Filter(storage)
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
                    int(self.args.comment_percentage),
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
        comment_percentage,
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
            comment_percentage=comment_percentage,
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

        handle_posts(
            device,
            hashtag,
            follow_limit,
            current_job,
            storage,
            interaction,
            interact_percentage,
            on_interaction,
            is_follow_limit_reached,
        )
