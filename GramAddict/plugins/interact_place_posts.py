import logging
from functools import partial
from random import seed
from colorama import Style
from GramAddict.core.decorators import run_safely
from GramAddict.core.filter import Filter
from GramAddict.core.interaction import (
    interact_with_user,
    is_follow_limit_reached_for_source,
)
from GramAddict.core.handle_sources import handle_posts
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.utils import sample_sources, init_on_things

logger = logging.getLogger(__name__)

# Script Initialization
seed()


class InteractPlacePosts(Plugin):
    """Handles the functionality of interacting with a places post owners"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Handles the functionality of interacting with a places post owners"
        )
        self.arguments = [
            {
                "arg": "--place-posts-recent",
                "nargs": "+",
                "help": "interact to place post owners in recent tab",
                "metavar": ("place1", "place2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--place-posts-top",
                "nargs": "+",
                "help": "interact to place post owners in top tab",
                "metavar": ("place1", "place2"),
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

        # Handle sources
        sources = [
            source
            for source in (
                self.args.place_posts_top
                if self.current_mode == "place-posts-top"
                else self.args.place_posts_recent
            )
        ]

        for source in sample_sources(sources, self.args.truncate_sources):
            limit_reached = self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.LIKES
            ) and self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.FOLLOWS
            )

            self.state = State()
            logger.info(f"Handle {source}", extra={"color": f"{Style.BRIGHT}"})

            # Init common things
            (
                on_interaction,
                on_like,
                on_watch,
                stories_percentage,
                follow_percentage,
                comment_percentage,
                interact_percentage,
            ) = init_on_things(source, self.args, self.sessions, self.session_state)

            @run_safely(
                device=device,
                device_id=self.device_id,
                sessions=self.sessions,
                session_state=self.session_state,
                screen_record=self.args.screen_record,
            )
            def job():
                self.handle_place(
                    device,
                    source,
                    self.args.likes_count,
                    self.args.stories_count,
                    stories_percentage,
                    follow_percentage,
                    int(self.args.follow_limit) if self.args.follow_limit else None,
                    comment_percentage,
                    interact_percentage,
                    self.args.scrape_to_file,
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

    def handle_place(
        self,
        device,
        place,
        likes_count,
        stories_count,
        stories_percentage,
        follow_percentage,
        follow_limit,
        comment_percentage,
        interact_percentage,
        scraping_file,
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
            scraping_file=scraping_file,
            current_mode=self.current_mode,
        )

        is_follow_limit_reached = partial(
            is_follow_limit_reached_for_source,
            follow_limit=follow_limit,
            source=place,
            session_state=self.session_state,
        )

        handle_posts(
            device,
            self.session_state,
            place,
            follow_limit,
            current_job,
            storage,
            scraping_file,
            profile_filter,
            on_interaction,
            interaction,
            is_follow_limit_reached,
            interact_percentage,
        )
