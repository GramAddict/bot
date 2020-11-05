from random import shuffle

from src.device_facade import DeviceFacade
from src.navigation import switch_to_english, LanguageChangedException
from src.utils import *


TEXTVIEW_OR_BUTTON_REGEX = "android.widget.TextView|android.widget.Button"
FOLLOW_REGEX = "Follow|Follow Back"
UNFOLLOW_REGEX = "Following|Requested"

_action_bar_bottom = None
_tab_bar_top = None


def update_interaction_rect(device):
    action_bar = device.find(
        resourceId="com.instagram.android:id/action_bar_container",
        className="android.widget.FrameLayout",
    )
    if action_bar.exists():
        global _action_bar_bottom
        _action_bar_bottom = action_bar.get_bounds()["bottom"]

    tab_bar = device.find(
        resourceId="com.instagram.android:id/tab_bar",
        className="android.widget.LinearLayout",
    )
    if tab_bar.exists():
        global _tab_bar_top
        _tab_bar_top = tab_bar.get_bounds()["top"]


def is_in_interaction_rect(view):
    if _action_bar_bottom is None or _tab_bar_top is None:
        print(COLOR_FAIL + "Interaction rect is not specified." + COLOR_ENDC)
        return False

    view_top = view.get_bounds()["top"]
    view_bottom = view.get_bounds()["bottom"]
    return _action_bar_bottom <= view_top and view_bottom <= _tab_bar_top


def interact_with_user(
    device,
    username,
    my_username,
    likes_count,
    on_like,
    can_follow,
    follow_percentage,
    profile_filter,
) -> (bool, bool):
    """
    :return: (whether interaction succeed, whether @username was followed during the interaction)
    """
    if username == my_username:
        print("It's you, skip.")
        return False, False

    random_sleep()

    if not profile_filter.check_profile(device, username):
        return False, False

    likes_value = get_value(likes_count, "Likes count: {}", 2)
    if likes_value > 12:
        print(COLOR_FAIL + "Max number of likes per user is 12" + COLOR_ENDC)
        likes_value = 12

    coordinator_layout = device.find(
        resourceId="com.instagram.android:id/coordinator_root_layout"
    )
    if coordinator_layout.exists():
        print("Scroll down to see more photos.")
        coordinator_layout.scroll(DeviceFacade.Direction.BOTTOM)

    recycler_view = device.find(resourceId="android:id/list")
    if not recycler_view.exists():
        print(COLOR_OKGREEN + "Private / empty account." + COLOR_ENDC)
        if can_follow and profile_filter.can_follow_private_or_empty():
            followed = _follow(device, username, follow_percentage)
        else:
            followed = False
            print(COLOR_OKGREEN + "Skip user." + COLOR_ENDC)
        return False, followed

    number_of_rows_to_use = min((likes_value * 2) // 3 + 1, 4)
    photos_indices = list(range(0, number_of_rows_to_use * 3))
    shuffle(photos_indices)
    photos_indices = photos_indices[:likes_value]
    photos_indices = sorted(photos_indices)
    for i in range(0, likes_value):
        photo_index = photos_indices[i]
        row = photo_index // 3
        column = photo_index - row * 3

        random_sleep()
        print(
            "Open and like photo #"
            + str(i + 1)
            + " ("
            + str(row + 1)
            + " row, "
            + str(column + 1)
            + " column)"
        )
        if not _open_photo_and_like(device, row, column, on_like):
            print(
                COLOR_OKGREEN
                + "Less than "
                + str(number_of_rows_to_use * 3)
                + " photos."
                + COLOR_ENDC
            )
            if can_follow and profile_filter.can_follow_private_or_empty():
                followed = _follow(device, username, follow_percentage)
            else:
                followed = False

            if not followed:
                print(COLOR_OKGREEN + "Skip user." + COLOR_ENDC)
            return False, followed

    if can_follow:
        return True, _follow(device, username, follow_percentage)

    return True, False


def is_follow_limit_reached_for_source(session_state, follow_limit, source):
    if follow_limit is None:
        return False

    followed_count = session_state.totalFollowed.get(source)
    return followed_count is not None and followed_count >= follow_limit


def _open_photo_and_like(device, row, column, on_like):
    def open_photo():
        # recycler_view has a className 'androidx.recyclerview.widget.RecyclerView' on modern Android versions and
        # 'android.view.View' on Android 5.0.1 and probably earlier versions
        recycler_view = device.find(resourceId="android:id/list")
        row_view = recycler_view.child(index=row + 1)
        if not row_view.exists():
            return False
        item_view = row_view.child(index=column)
        if not item_view.exists():
            return False
        item_view.click()
        return True

    if not open_photo():
        return False

    random_sleep()
    print("Double click!")
    photo_view = device.find(
        resourceId="com.instagram.android:id/layout_container_main",
        className="android.widget.FrameLayout",
    )
    photo_view.double_click()
    random_sleep()

    # If double click didn't work, set like by icon click
    try:
        # Click only button which is under the action bar and above the tab bar.
        # It fixes bugs with accidental back / home clicks.
        for like_button in device.find(
            resourceId="com.instagram.android:id/row_feed_button_like",
            className="android.widget.ImageView",
            selected=False,
        ):
            if is_in_interaction_rect(like_button):
                print("Double click didn't work, click on icon.")
                like_button.click()
                random_sleep()
                break
    except DeviceFacade.JsonRpcError:
        print("Double click worked successfully.")

    detect_block(device)
    on_like()
    print("Back to profile")
    device.back()
    return True


def _follow(device, username, follow_percentage):
    follow_chance = randint(1, 100)
    if follow_chance > follow_percentage:
        return False

    print("Following...")
    coordinator_layout = device.find(
        resourceId="com.instagram.android:id/coordinator_root_layout"
    )
    if coordinator_layout.exists():
        coordinator_layout.scroll(DeviceFacade.Direction.TOP)

    random_sleep()

    profile_header_actions_layout = device.find(
        resourceId="com.instagram.android:id/profile_header_actions_top_row",
        className="android.widget.LinearLayout",
    )
    if not profile_header_actions_layout.exists():
        print(COLOR_FAIL + "Cannot find profile actions." + COLOR_ENDC)
        return False

    follow_button = profile_header_actions_layout.child(
        classNameMatches=TEXTVIEW_OR_BUTTON_REGEX,
        clickable=True,
        textMatches=FOLLOW_REGEX,
    )
    if not follow_button.exists():
        unfollow_button = profile_header_actions_layout.child(
            classNameMatches=TEXTVIEW_OR_BUTTON_REGEX,
            clickable=True,
            textMatches=UNFOLLOW_REGEX,
        )
        if unfollow_button.exists():
            print(COLOR_OKGREEN + "You already follow @" + username + "." + COLOR_ENDC)
            return False
        else:
            print(
                COLOR_FAIL
                + "Cannot find neither Follow button, nor Unfollow button. Maybe not "
                "English language is set?" + COLOR_ENDC
            )
            save_crash(device)
            switch_to_english(device)
            raise LanguageChangedException()

    follow_button.click()
    detect_block(device)
    print(COLOR_OKGREEN + "Followed @" + username + COLOR_ENDC)
    random_sleep()
    return True
