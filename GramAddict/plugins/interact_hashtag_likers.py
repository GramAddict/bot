from functools import partial
from random import seed, shuffle
from GramAddict.core.decorators import run_safely
from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.filter import Filter
from GramAddict.core.interaction import (
    is_follow_limit_reached_for_source,
    interact_with_user,
    _on_interaction,
    _on_like,
    _on_likes_limit_reached,
    _on_watch,
)
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.scroll_end_detector import ScrollEndDetector
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import (
    COLOR_OKGREEN,
    COLOR_FAIL,
    COLOR_ENDC,
    COLOR_BOLD,
    random_sleep,
    get_value,
    print_timeless,
    print,
)
from GramAddict.core.views import TabBarView

# Script Initialization
seed()


class InteractHashtagLikers(Plugin):
    """This plugin handles the functionality of interacting with hashtags likers"""

    def __init__(self):
        super().__init__()
        self.description = "This plugin handles the functionality of interacting with hashtags likers"
        self.arguments = [
            {
                "arg": "--hashtag-likers",
                "nargs": "+",
                "help": "list of hashtags with whose likers you want to interact",
                "metavar": ("hashtag1", "hashtag2"),
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, device_id, args, enabled, storage, sessions):
        class State:
            def __init__(self):
                pass

            is_job_completed = False
            is_likes_limit_reached = False

        self.device_id = device_id
        self.sessions = sessions
        self.session_state = sessions[-1]
        profile_filter = Filter()

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        sources = [source for source in args.hashtag_likers]
        shuffle(sources)

        for source in sources:
            self.state = State()
            print_timeless("")
            print(COLOR_BOLD + "Handle " + source + COLOR_ENDC)

            on_likes_limit_reached = partial(_on_likes_limit_reached, state=self.state)

            on_interaction = partial(
                _on_interaction,
                on_likes_limit_reached=on_likes_limit_reached,
                likes_limit=int(args.total_likes_limit),
                source=source,
                interactions_limit=get_value(
                    args.interactions_count, "Interactions count: {}", 70
                ),
                sessions=self.sessions,
                session_state=self.session_state,
            )

            on_like = partial(
                _on_like, sessions=self.sessions, session_state=self.session_state
            )
            on_watch = partial(
                _on_watch, sessions=self.sessions, session_state=self.session_state
            )

            @run_safely(
                device=device,
                device_id=self.device_id,
                sessions=self.sessions,
                session_state=self.session_state,
            )
            def job():
                self.handle_hashtag(
                    device,
                    source[1:] if "#" in source else source,
                    args.likes_count,
                    args.stories_count,
                    int(args.follow_percentage),
                    int(args.follow_limit) if args.follow_limit else None,
                    storage,
                    profile_filter,
                    on_like,
                    on_watch,
                    on_interaction,
                )
                self.state.is_job_completed = True

            while (
                not self.state.is_job_completed
                and not self.state.is_likes_limit_reached
            ):
                job()

            if self.state.is_likes_limit_reached:
                break

    def handle_hashtag(
        self,
        device,
        hashtag,
        likes_count,
        stories_count,
        follow_percentage,
        follow_limit,
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
            follow_percentage=follow_percentage,
            on_like=on_like,
            on_watch=on_watch,
            profile_filter=profile_filter,
        )

        is_follow_limit_reached = partial(
            is_follow_limit_reached_for_source,
            follow_limit=follow_limit,
            source=hashtag,
            session_state=self.session_state,
        )
        search_view = TabBarView(device).navigateToSearch()
        random_sleep()
        if not search_view.navigateToHashtag(hashtag):
            return

        print("Opening the first result")

        first_result_view = device.find(
            resourceId="com.instagram.android:id/recycler_view",
            className="androidx.recyclerview.widget.RecyclerView",
        )

        first_result_view.child(index=3).click()
        random_sleep()

        posts_list_view = device.find(
            resourceId="android:id/list",
            className="androidx.recyclerview.widget.RecyclerView",
        )
        posts_end_detector = ScrollEndDetector(repeats_to_end=2)

        while True:
            if not self.open_likers(device):
                print(COLOR_OKGREEN + "No likes, let's scroll down." + COLOR_ENDC)
                posts_list_view.scroll(DeviceFacade.Direction.BOTTOM)
                continue

            print("List of likers is opened.")
            posts_end_detector.notify_new_page()
            random_sleep()
            likes_list_view = device.find(
                resourceId="android:id/list", className="android.widget.ListView"
            )
            prev_screen_iterated_likers = []
            while True:
                print("Iterate over visible likers.")
                screen_iterated_likers = []

                try:
                    for item in device.find(
                        resourceId="com.instagram.android:id/row_user_container_base",
                        className="android.widget.LinearLayout",
                    ):
                        username_view = item.child(
                            resourceId="com.instagram.android:id/row_user_primary_name",
                            className="android.widget.TextView",
                        )
                        if not username_view.exists(quick=True):
                            print(
                                COLOR_OKGREEN
                                + "Next item not found: probably reached end of the screen."
                                + COLOR_ENDC
                            )
                            break

                        username = username_view.get_text()
                        screen_iterated_likers.append(username)
                        posts_end_detector.notify_username_iterated(username)

                        if storage.is_user_in_blacklist(username):
                            print("@" + username + " is in blacklist. Skip.")
                            continue
                        elif storage.check_user_was_interacted(username):
                            print("@" + username + ": already interacted. Skip.")
                            continue
                        else:
                            print("@" + username + ": interact")
                            username_view.click()

                        can_follow = (
                            not is_follow_limit_reached()
                            and storage.get_following_status(username)
                            == FollowingStatus.NONE
                        )

                        interaction_succeed, followed = interaction(
                            device, username=username, can_follow=can_follow
                        )
                        storage.add_interacted_user(username, followed=followed)
                        can_continue = on_interaction(
                            succeed=interaction_succeed, followed=followed
                        )
                        if not can_continue:
                            return

                        print("Back to likers list")
                        device.back()
                        random_sleep()
                except IndexError:
                    print(
                        COLOR_FAIL
                        + "Cannot get next item: probably reached end of the screen."
                        + COLOR_ENDC
                    )

                if screen_iterated_likers == prev_screen_iterated_likers:
                    print(
                        COLOR_OKGREEN
                        + "Iterated exactly the same likers twice, finish."
                        + COLOR_ENDC
                    )
                    print(f"Back to #{hashtag}")
                    device.back()
                    break

                prev_screen_iterated_likers.clear()
                prev_screen_iterated_likers += screen_iterated_likers

                print(COLOR_OKGREEN + "Need to scroll now" + COLOR_ENDC)
                likes_list_view.scroll(DeviceFacade.Direction.BOTTOM)

            if posts_end_detector.is_the_end():
                break
            else:
                posts_list_view.scroll(DeviceFacade.Direction.BOTTOM)

    def open_likers(self, device):
        likes_view = device.find(
            resourceId="com.instagram.android:id/row_feed_textview_likes",
            className="android.widget.TextView",
        )
        if likes_view.exists():
            print("Opening post likers")
            random_sleep()
            likes_view.click("right")
            return True
        else:
            return False
