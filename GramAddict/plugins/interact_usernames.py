from GramAddict.core.filter import Filter
import logging
import os
from functools import partial
from colorama import Style
from random import seed, shuffle
from GramAddict.core.decorators import run_safely
from GramAddict.core.interaction import _on_interaction, _on_like, interact_with_user
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import get_value, random_sleep, detect_block
from GramAddict.core.interaction import (
    _on_interaction,
    _on_like,
    _on_watch,
    interact_with_user,
    is_follow_limit_reached_for_source,
)

logger = logging.getLogger(__name__)

from GramAddict.core.views import TabBarView


class IntreractUsernames(Plugin):
    """Interact with users that are given from a file"""

    def __init__(self):
        super().__init__()
        self.description = "Interact with users that are given from a file"
        self.arguments = [
            {
                "arg": "--interact-usernames",
                "nargs": "+",
                "help": "filenames of the list of users [*.txt]",
                "metavar": ("filename1", "filename2"),
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
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.args = args
        profile_filter = Filter()
        self.current_mode = plugin[2:]

        file_list = [file for file in (args.interact_usernames)]
        shuffle(file_list)

        for file in file_list:
            limit_reached = self.session_state.check_limit(
                args, limit_type=self.session_state.Limit.LIKES
            ) and self.session_state.check_limit(
                args, limit_type=self.session_state.Limit.FOLLOWS
            )

            self.state = State()
            logger.info(f"Handle {file}", extra={"color": f"{Style.BRIGHT}"})

            on_interaction = partial(
                _on_interaction,
                likes_limit=int(args.total_likes_limit),
                source=file,
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
                self.handle_username_file(
                    device,
                    file,
                    args.likes_count,
                    args.stories_count,
                    stories_percentage,
                    int(args.follow_percentage),
                    int(args.follow_limit) if args.follow_limit else None,
                    # int(args.interact_chance),
                    plugin[2:],
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

    def handle_username_file(
        self,
        device,
        current_file,
        likes_count,
        stories_count,
        stories_percentage,
        follow_percentage,
        follow_limit,
        # interact_chance,
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
            source=current_file,
            session_state=self.session_state,
        )

        # start
        if os.path.isfile(current_file):
            with open(current_file, "r") as f:
                user_list = f.readlines()
        else:
            logger.warning(f"File {current_file} not found.")
            return

        for username in user_list:
            if username[-1:] == "\n":
                username = username[:-1]
            search_view = TabBarView(device).navigateToSearch()
            random_sleep()
            profile_view = search_view.navigateToUsername(username)
            random_sleep()

            def interact():
                can_follow = not is_follow_limit_reached() and (
                    storage.get_following_status(username) == FollowingStatus.NONE
                    or storage.get_following_status(username)
                    == FollowingStatus.NOT_IN_LIST
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

            if storage.is_user_in_blacklist(username):
                logger.info(f"@{username} is in blacklist. Skip.")
            elif storage.check_user_was_interacted(username):
                logger.info(f"@{username}: already interacted. Skip.")
            else:
                logger.info(f"@{username}: interact")
                if not interact():
                    break
                device.back()

            continue
        logger.info(f"Interact with users in {current_file} complete.")
        device.back()
