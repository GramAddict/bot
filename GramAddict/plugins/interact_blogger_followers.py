from GramAddict.core.handle_sources import handle_followers
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
from GramAddict.core.resources import ResourceID as resources
from GramAddict.core.scroll_end_detector import ScrollEndDetector
from GramAddict.core.utils import get_value, init_on_things, sample_sources

logger = logging.getLogger(__name__)


# Script Initialization
seed()


class InteractBloggerFollowers(Plugin):
    """Handles the functionality of interacting with a bloggers followers/following"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Handles the functionality of interacting with a bloggers followers"
        )
        self.arguments = [
            {
                "arg": "--blogger-followers",
                "nargs": "+",
                "help": "list of usernames with whose followers you want to interact",
                "metavar": ("username1", "username2"),
                "default": None,
                "operation": True,
            },
            {
                "arg": "--blogger-following",
                "nargs": "+",
                "help": "list of usernames with whose following you want to interact",
                "metavar": ("username1", "username2"),
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, configs, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.device_id = configs.args.device
        self.state = None
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.args = configs.args
        self.ResourceID = resources(self.args.app_id)
        profile_filter = Filter(storage)
        self.current_mode = plugin

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        if self.args.blogger_followers is not None:
            sources = [source for source in self.args.blogger_followers]
        else:
            sources = [source for source in self.args.blogger_following]

        # Start
        for source in sample_sources(sources, self.args.truncate_sources):
            limit_reached = self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.ALL
            )

            self.state = State()
            is_myself = source[1:] == self.session_state.my_username
            its_you = is_myself and " (it's you)" or ""
            logger.info(
                f"Handle {source} {its_you}", extra={"color": f"{Style.BRIGHT}"}
            )

            # Init common things
            (
                on_interaction,
                stories_percentage,
                follow_percentage,
                comment_percentage,
                pm_percentage,
                interact_percentage,
            ) = init_on_things(source, self.args, self.sessions, self.session_state)

            @run_safely(
                device=device,
                device_id=self.device_id,
                sessions=self.sessions,
                session_state=self.session_state,
                screen_record=self.args.screen_record,
                configs=configs,
            )
            def job():
                self.handle_blogger(
                    device,
                    source,
                    plugin,
                    storage,
                    profile_filter,
                    on_interaction,
                    stories_percentage,
                    follow_percentage,
                    comment_percentage,
                    pm_percentage,
                    interact_percentage,
                )
                self.state.is_job_completed = True

            while not self.state.is_job_completed and not limit_reached:
                job()

            if limit_reached:
                logger.info("Ending session.")
                self.session_state.check_limit(
                    self.args, limit_type=self.session_state.Limit.ALL, output=True
                )
                break

    def handle_blogger(
        self,
        device,
        username,
        current_job,
        storage,
        profile_filter,
        on_interaction,
        stories_percentage,
        follow_percentage,
        comment_percentage,
        pm_percentage,
        interact_percentage,
    ):
        interaction = partial(
            interact_with_user,
            my_username=self.session_state.my_username,
            likes_count=self.args.likes_count,
            stories_percentage=stories_percentage,
            follow_percentage=follow_percentage,
            comment_percentage=comment_percentage,
            pm_percentage=pm_percentage,
            profile_filter=profile_filter,
            args=self.args,
            session_state=self.session_state,
            scraping_file=self.args.scrape_to_file,
            current_mode=self.current_mode,
        )
        is_follow_limit_reached = partial(
            is_follow_limit_reached_for_source,
            session_state=self.session_state,
            follow_limit=self.args.follow_limit,
            source=username,
        )

        skipped_list_limit = get_value(self.args.skipped_list_limit, None, 15)
        skipped_fling_limit = get_value(self.args.fling_when_skipped, None, 0)

        posts_end_detector = ScrollEndDetector(
            repeats_to_end=2,
            skipped_list_limit=skipped_list_limit,
            skipped_fling_limit=skipped_fling_limit,
        )
        handle_followers(
            self,
            device,
            self.session_state,
            username,
            current_job,
            storage,
            on_interaction,
            interaction,
            is_follow_limit_reached,
            posts_end_detector,
        )
