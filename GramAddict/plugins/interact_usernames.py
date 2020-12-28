from GramAddict.core.filter import Filter
import logging
from functools import partial
from colorama import Style
from os import path
from random import shuffle
from GramAddict.core.decorators import run_safely
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.views import TabBarView
from GramAddict.core.utils import (
    get_value,
    random_sleep,
)
from GramAddict.core.interaction import (
    _on_interaction,
    _on_like,
    _on_watch,
    interact_with_user,
    is_follow_limit_reached_for_source,
)

logger = logging.getLogger(__name__)


class InteractUsernames(Plugin):
    """Interact with users that are given from a file"""

    def __init__(self):
        super().__init__()
        self.description = "Interact with users that are given from a file"
        self.arguments = [
            {
                "arg": "--interact-from-file",
                "nargs": "+",
                "help": "filenames of the list of users [*.txt]",
                "metavar": ("filename1", "filename2"),
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, configs, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.args = configs.args
        self.device_id = configs.args.device
        self.sessions = sessions
        self.session_state = sessions[-1]
        profile_filter = Filter()
        self.current_mode = plugin

        file_list = [file for file in (self.args.interact_from_file)]
        shuffle(file_list)

        for file in file_list:
            limit_reached = self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.LIKES
            ) and self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.FOLLOWS
            )

            self.state = State()
            logger.info(f"Handle {file}", extra={"color": f"{Style.BRIGHT}"})

            on_interaction = partial(
                _on_interaction,
                likes_limit=int(self.args.total_likes_limit),
                source=file,
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
                self.handle_username_file(
                    device,
                    file,
                    self.args.likes_count,
                    self.args.stories_count,
                    stories_percentage,
                    int(self.args.follow_percentage),
                    int(self.args.follow_limit) if self.args.follow_limit else None,
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

    def handle_username_file(
        self,
        device,
        current_file,
        likes_count,
        stories_count,
        stories_percentage,
        follow_percentage,
        follow_limit,
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
        need_to_refresh = True
        if path.isfile(current_file):
            with open(current_file, "r") as f:
                for line in f:
                    username = line.strip()
                    if username != "":
                        if storage.is_user_in_blacklist(username):
                            logger.info(f"@{username} is in blacklist. Skip.")
                            continue
                        elif storage.check_user_was_interacted(username):
                            logger.info(f"@{username}: already interacted. Skip.")
                            continue
                        if need_to_refresh:
                            search_view = TabBarView(device).navigateToSearch()
                            random_sleep()
                        profile_view = search_view.navigateToUsername(
                            username, True, need_to_refresh
                        )
                        need_to_refresh = False
                        if not profile_view:
                            continue
                        random_sleep()

                        def interact():
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
                            can_continue = on_interaction(
                                succeed=interaction_succeed, followed=followed
                            )
                            if not can_continue:
                                return False
                            else:
                                return True

                        logger.info(f"@{username}: interact")
                        if not interact():
                            break
                        device.back()
                    else:
                        logger.info("Line in file is blank, skip.")
                remaining = f.readlines()
            if self.args.delete_interacted_users:
                with open(current_file, "w") as f:
                    f.writelines(remaining)
        else:
            logger.warning(f"File {current_file} not found.")
            return

        logger.info(f"Interact with users in {current_file} complete.")
        device.back()
