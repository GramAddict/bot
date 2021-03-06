from GramAddict.core.handle_sources import handle_likers
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
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.scroll_end_detector import ScrollEndDetector
from GramAddict.core.utils import (
    get_value,
    random_sleep,
    sample_sources,
    init_on_things,
)

logger = logging.getLogger(__name__)

# Script Initialization
seed()


class InteractBloggerPostLikers(Plugin):
    """Handles the functionality of interacting with a  blogger post likers"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Handles the functionality of interacting with a blogger post likers"
        )
        self.arguments = [
            {
                "arg": "--blogger-post-likers",
                "nargs": "+",
                "help": "interact with likers of post for a specified blogger",
                "metavar": ("blogger1", "blogger2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--blogger-post-limits",
                "nargs": None,
                "help": "limit the posts you're looking for likers",
                "metavar": "2",
                "default": 0,
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
        sources = [source for source in self.args.blogger_post_likers]
        for source in sample_sources(sources, self.args.truncate_sources):
            limit_reached = self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.ALL
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

            ##
            def job():
                self.handle_blogger(
                    device,
                    source[1:] if "@" in source else source,
                    self.args.likes_count,
                    self.args.stories_count,
                    stories_percentage,
                    follow_percentage,
                    int(self.args.follow_limit) if self.args.follow_limit else None,
                    comment_percentage,
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

    ##
    def handle_blogger(
        self,
        device,
        username,
        likes_count,
        stories_count,
        stories_percentage,
        follow_percentage,
        follow_limit,
        comment_percentage,
        scraping_file,
        current_job,
        storage,
        profile_filter,
        on_like,
        on_watch,
        on_interaction,
    ):
        # is_myself = username == self.session_state.my_username

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
            source=username,
            session_state=self.session_state,
        )
        add_interacted_user = partial(
            storage.add_interacted_user,
            session_id=self.session_state.id,
            job_name=current_job,
            target=username,
        )

        # if not nav_to_post_likers(device, username, self.session_state.my_username):
        #     return

        skipped_list_limit = get_value(self.args.skipped_list_limit, None, 15)
        skipped_fling_limit = get_value(self.args.fling_when_skipped, None, 0)
        posts_end_detector = ScrollEndDetector(
            repeats_to_end=2,
            skipped_list_limit=skipped_list_limit,
            skipped_fling_limit=skipped_fling_limit,
        )

        handle_likers(
            device,
            self.session_state,
            username,
            follow_limit,
            current_job,
            storage,
            profile_filter,
            posts_end_detector,
            on_interaction,
            interaction,
            is_follow_limit_reached,
            True,
        )
