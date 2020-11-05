from functools import partial

from src.device_facade import DeviceFacade
from src.interaction import (
    is_follow_limit_reached_for_source,
    interact_with_user,
    is_in_interaction_rect,
)
from src.navigation import search_for
from src.scroll_end_detector import ScrollEndDetector
from src.storage import FollowingStatus
from src.utils import *


def handle_hashtag(
    device,
    hashtag,
    session_state,
    likes_count,
    follow_percentage,
    follow_limit,
    storage,
    profile_filter,
    on_like,
    on_interaction,
):
    interaction = partial(
        interact_with_user,
        my_username=session_state.my_username,
        likes_count=likes_count,
        follow_percentage=follow_percentage,
        on_like=on_like,
        profile_filter=profile_filter,
    )

    is_follow_limit_reached = partial(
        is_follow_limit_reached_for_source,
        session_state=session_state,
        follow_limit=follow_limit,
        source=hashtag,
    )

    if not search_for(device, hashtag=hashtag):
        return

    # Switch to Recent tab
    print("Switching to Recent tab")
    tab_layout = device.find(
        resourceId="com.instagram.android:id/tab_layout",
        className="android.widget.LinearLayout",
    )
    tab_layout.child(index=1).click()
    random_sleep()

    # Open first post
    print("Opening the first post")
    first_post_view = device.find(
        resourceId="com.instagram.android:id/image_button",
        className="android.widget.ImageView",
        index=1,
    )
    first_post_view.click()
    random_sleep()

    posts_list_view = device.find(
        resourceId="android:id/list",
        className="androidx.recyclerview.widget.RecyclerView",
        # className="android.widget.ListView",
    )
    posts_end_detector = ScrollEndDetector(repeats_to_end=2)

    while True:
        if not _open_likers(device):
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


def _open_likers(device):
    likes_view = device.find(
        resourceId="com.instagram.android:id/row_feed_textview_likes",
        className="android.widget.TextView",
    )
    if likes_view.exists(quick=True) and is_in_interaction_rect(likes_view):
        print("Opening post likers")
        random_sleep()
        likes_view.click()
        return True
    else:
        return False
