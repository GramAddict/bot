import logging
from functools import partial
from random import seed, shuffle

from colorama import Fore
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
from GramAddict.core.resources import ClassName, ResourceID as resources
from GramAddict.core.scroll_end_detector import ScrollEndDetector
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import get_value, random_sleep

logger = logging.getLogger(__name__)

from GramAddict.core.views import TabBarView

# Script Initialization
seed()


class InteractBloggerFollowers(Plugin):
    """Handles the functionality of interacting with a bloggers followers"""

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
        sources = [source for source in self.args.blogger_followers]
        shuffle(sources)

        for source in sources:
            limit_reached = self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.LIKES
            ) and self.session_state.check_limit(
                self.args, limit_type=self.session_state.Limit.FOLLOWS
            )

            self.state = State()
            is_myself = source[1:] == self.session_state.my_username
            its_you = is_myself and " (it's you)" or ""
            logger.info(f"Handle {source} {its_you}")

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
                self.handle_blogger(
                    device,
                    source[1:] if "@" in source else source,
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

    def handle_blogger(
        self,
        device,
        username,
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

        if not self.open_user_followers(device, username):
            return
        if is_myself:
            self.scroll_to_bottom(device)
        self.iterate_over_followers(
            device,
            interaction,
            is_follow_limit_reached,
            storage,
            add_interacted_user,
            on_interaction,
            is_myself,
            skipped_list_limit=get_value(self.args.skipped_list_limit, None, 15),
            skipped_fling_limit=get_value(self.args.fling_when_skipped, None, 0),
        )

    def open_user_followers(self, device, username):
        if username is None:
            logger.info("Open your followers")
            profile_view = TabBarView(device).navigateToProfile()
            profile_view.navigateToFollowers()
        else:
            search_view = TabBarView(device).navigateToSearch()
            profile_view = search_view.navigateToUsername(username)
            random_sleep()
            if not profile_view:
                return False

            logger.info(f"Open @{username} followers")
            profile_view.navigateToFollowers()

        return True

    def scroll_to_bottom(self, device):
        logger.info("Scroll to bottom")

        def is_end_reached():
            see_all_button = device.find(
                resourceId=self.ResourceID.SEE_ALL_BUTTON,
                className=ClassName.TEXT_VIEW,
            )
            return see_all_button.exists()

        list_view = device.find(
            resourceId=self.ResourceID.LIST, className=ClassName.LIST_VIEW
        )
        while not is_end_reached():
            list_view.fling(DeviceFacade.Direction.BOTTOM)

        logger.info("Scroll back to the first follower")

        def is_at_least_one_follower():
            follower = device.find(
                resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
                className=ClassName.LINEAR_LAYOUT,
            )
            return follower.exists()

        while not is_at_least_one_follower():
            list_view.scroll(DeviceFacade.Direction.TOP)

    def iterate_over_followers(
        self,
        device,
        interaction,
        is_follow_limit_reached,
        storage,
        add_interacted_user,
        on_interaction,
        is_myself,
        skipped_list_limit,
        skipped_fling_limit,
    ):
        # Wait until list is rendered
        device.find(
            resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
            className=ClassName.LINEAR_LAYOUT,
        ).wait()

        def scrolled_to_top():
            row_search = device.find(
                resourceId=self.ResourceID.ROW_SEARCH_EDIT_TEXT,
                className=ClassName.EDIT_TEXT,
            )
            return row_search.exists()

        scroll_end_detector = ScrollEndDetector(
            skipped_list_limit=skipped_list_limit,
            skipped_fling_limit=skipped_fling_limit,
        )
        while True:
            logger.info("Iterate over visible followers")
            random_sleep()
            screen_iterated_followers = []
            screen_skipped_followers_count = 0
            scroll_end_detector.notify_new_page()

            try:
                for item in device.find(
                    resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
                    className=ClassName.LINEAR_LAYOUT,
                ):
                    user_info_view = item.child(index=1)
                    user_name_view = user_info_view.child(index=0).child()
                    if not user_name_view.exists(quick=True):
                        logger.info(
                            "Next item not found: probably reached end of the screen.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        break

                    username = user_name_view.get_text()
                    screen_iterated_followers.append(username)
                    scroll_end_detector.notify_username_iterated(username)

                    if storage.is_user_in_blacklist(username):
                        logger.info(f"@{username} is in blacklist. Skip.")
                    elif not is_myself and storage.check_user_was_interacted(username):
                        logger.info(f"@{username}: already interacted. Skip.")
                        screen_skipped_followers_count += 1
                    elif is_myself and storage.check_user_was_interacted_recently(
                        username
                    ):
                        logger.info(
                            f"@{username}: already interacted in the last week. Skip."
                        )
                        screen_skipped_followers_count += 1
                    else:
                        logger.info(f"@{username}: interact")
                        user_name_view.click()

                        can_follow = (
                            not is_myself
                            and not is_follow_limit_reached()
                            and (
                                storage.get_following_status(username)
                                == FollowingStatus.NONE
                                or storage.get_following_status(username)
                                == FollowingStatus.NOT_IN_LIST
                            )
                        )

                        (
                            interaction_succeed,
                            followed,
                            number_of_liked,
                            number_of_watched,
                        ) = interaction(
                            device, username=username, can_follow=can_follow
                        )
                        add_interacted_user(
                            username,
                            followed=followed,
                            liked=number_of_liked,
                            watched=number_of_watched,
                        )
                        can_continue = on_interaction(
                            succeed=interaction_succeed,
                            followed=followed,
                        )

                        if not can_continue:
                            return

                        logger.info("Back to followers list")
                        device.back()
                        random_sleep()
            except IndexError:
                logger.error(
                    "Cannot get next item: probably reached end of the screen."
                )

            if is_myself and scrolled_to_top():
                logger.info(
                    "Scrolled to top, finish.", extra={"color": f"{Fore.GREEN}"}
                )
                return
            elif len(screen_iterated_followers) > 0:
                load_more_button = device.find(
                    resourceId=self.ResourceID.ROW_LOAD_MORE_BUTTON
                )
                load_more_button_exists = load_more_button.exists(quick=True)

                if scroll_end_detector.is_the_end():
                    return

                need_swipe = screen_skipped_followers_count == len(
                    screen_iterated_followers
                )
                list_view = device.find(
                    resourceId=self.ResourceID.LIST, className=ClassName.LIST_VIEW
                )
                if not list_view.exists():
                    logger.error(
                        "Cannot find the list of followers. Trying to press back again."
                    )
                    device.back()
                    list_view = device.find(
                        resourceId=self.ResourceID.LIST,
                        className=ClassName.LIST_VIEW,
                    )

                if is_myself:
                    logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                    list_view.scroll(DeviceFacade.Direction.TOP)
                else:
                    pressed_retry = False
                    if load_more_button_exists:
                        retry_button = load_more_button.child(
                            className=ClassName.IMAGE_VIEW
                        )
                        if retry_button.exists():
                            logger.info('Press "Load" button')
                            retry_button.click()
                            random_sleep()
                            pressed_retry = True

                    if need_swipe and not pressed_retry:
                        scroll_end_detector.notify_skipped_all()
                        if scroll_end_detector.is_skipped_limit_reached():
                            return
                        if scroll_end_detector.is_fling_limit_reached():
                            logger.info(
                                "Limit of all followers skipped reached, let's fling.",
                                extra={"color": f"{Fore.GREEN}"},
                            )
                            list_view.fling(DeviceFacade.Direction.BOTTOM)
                        else:
                            logger.info(
                                "All followers skipped, let's scroll.",
                                extra={"color": f"{Fore.GREEN}"},
                            )
                            list_view.scroll(DeviceFacade.Direction.BOTTOM)
                    else:
                        logger.info(
                            "Need to scroll now", extra={"color": f"{Fore.GREEN}"}
                        )
                        list_view.scroll(DeviceFacade.Direction.BOTTOM)
            else:
                logger.info(
                    "No followers were iterated, finish.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return
