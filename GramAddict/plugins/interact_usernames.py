from GramAddict.core.filter import Filter
import logging
import os
from functools import partial
from GramAddict.core.decorators import run_safely
from GramAddict.core.interaction import _on_interaction, _on_like, interact_with_user
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.utils import get_value, random_sleep
from GramAddict.core.interaction import (
    _on_interaction,
    _on_like,
    _on_watch,
    interact_with_user,
    is_follow_limit_reached_for_source,
)
logger = logging.getLogger(__name__)

from GramAddict.core.views import OpenedPostView, ProfileView, TabBarView


class IntreractUsernames(Plugin):
    """Interact with users that are given from a file"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Interact with users that are given from a file"
        )
        self.arguments = [
            {
                "arg": "--interact-usernames",
                "nargs": None,
                "help": "name of the file with extention usernames.txt",
                "metavar": None,
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, device_id, args, enabled, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.device_id = device_id
        self.state = None
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.args = args
        self.usernames = []
        profile_filter = Filter()
        

        if os.path.isfile(args.interact_usernames):
            with open(args.interact_usernames, "r") as f:
                self.usernames = f.readlines()
                

        limit_reached = self.session_state.check_limit(
                args, limit_type=self.session_state.Limit.LIKES
            ) and self.session_state.check_limit(
                args, limit_type=self.session_state.Limit.FOLLOWS
            )

        self.state = State()
        

        on_interaction = partial(
            _on_interaction,
            likes_limit=int(args.total_likes_limit),
            source=self.usernames,
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
            for name in self.usernames:
                search_view = TabBarView(device).navigateToSearch()
                random_sleep()
                if not search_view.navigateToUsername(name.strip().replace(" ", "")):
                
                    return
                random_sleep()
                self.handle_blogger(
                    device,
                    name,
                    args.likes_count,
                    args.stories_count,
                    stories_percentage,
                    int(args.follow_percentage),
                    int(args.follow_limit) if args.follow_limit else None,
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
                
        job()
                
    def handle_blogger(
        self,
        device,
        username,
        likes_count,
        stories_count,
        stories_percentage,
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
            stories_percentage=stories_percentage,
            follow_percentage=follow_percentage,
            on_like=on_like,
            on_watch=on_watch,
            profile_filter=profile_filter,
            args=self.args,
            session_state=self.session_state,
        )
        is_follow_limit_reached = partial(
            is_follow_limit_reached_for_source,
            follow_limit=follow_limit,
            source=username,
            session_state=self.session_state,
        )
                
      
            
