from src.action_get_my_profile_info import get_following_count
from src.device_facade import DeviceFacade
from src.utils import *


FOLLOWERS_BUTTON_ID_REGEX = (
    "com.instagram.android:id/row_profile_header_followers_container"
    "|com.instagram.android:id/row_profile_header_container_followers"
)


def remove_mass_followers(device, max_followings, on_remove, storage):

    print("Open your followers")
    followers_button = device.find(resourceIdMatches=FOLLOWERS_BUTTON_ID_REGEX)
    followers_button.click()
    _scroll_to_bottom(device)

    _iterate_over_followers(device, max_followings, on_remove, storage)


def _iterate_over_followers(device, max_followings, on_remove, storage):
    # Wait until list is rendered
    device.find(
        resourceId="com.instagram.android:id/follow_list_container",
        className="android.widget.LinearLayout",
    ).wait()

    def scrolled_to_top():
        row_search = device.find(
            resourceId="com.instagram.android:id/row_search_edit_text",
            className="android.widget.EditText",
        )
        return row_search.exists()

    need_to_restart = (
        False  # after removing a user we need to start the screen from the beginning
    )
    while True:
        print("Iterate over visible followers")
        random_sleep()
        screen_iterated_followers = 0

        try:
            for item in device.find(
                resourceId="com.instagram.android:id/follow_list_container",
                className="android.widget.LinearLayout",
            ):
                user_info_view = item.child(index=1)
                if not user_info_view.exists(quick=True):
                    print(
                        COLOR_OKGREEN
                        + "Next item not found: probably reached end of the screen."
                        + COLOR_ENDC
                    )
                    break

                user_name_view = user_info_view.child(index=0).child()
                if not user_name_view.exists():
                    print(
                        COLOR_OKGREEN
                        + "Next item not found: probably reached end of the screen."
                        + COLOR_ENDC
                    )
                    break

                username = user_name_view.get_text()
                screen_iterated_followers += 1

                if storage.is_user_in_whitelist(username):
                    print("@" + username + " is in whitelist, skip.")
                    continue

                print("Open @" + username)
                user_name_view.click()
                random_sleep()
                is_mass_follower = _is_mass_follower(device, username, max_followings)
                device.back()
                if is_mass_follower:
                    print(
                        COLOR_OKGREEN
                        + "@"
                        + username
                        + " is mass follower, remove."
                        + COLOR_ENDC
                    )
                    remove_button = user_info_view.right(
                        resourceId="com.instagram.android:id/button",
                        className="android.widget.TextView",
                    )
                    if not remove_button.exists():
                        print(
                            COLOR_OKGREEN
                            + "Next item not found: probably reached end of the screen."
                            + COLOR_ENDC
                        )
                        break
                    remove_button.click()
                    random_sleep()
                    _close_dialog_if_shown(device)
                    _close_bottom_sheet_if_shown(device)
                    can_continue = on_remove(username)

                    if not can_continue:
                        return

                    need_to_restart = True
                    break
        except IndexError:
            print(
                COLOR_FAIL
                + "Cannot get next item: probably reached end of the screen."
                + COLOR_ENDC
            )

        if need_to_restart:
            need_to_restart = False
            continue

        if scrolled_to_top():
            print(COLOR_OKGREEN + "Scrolled to top, finish." + COLOR_ENDC)
            return
        elif screen_iterated_followers > 0:
            print(COLOR_OKGREEN + "Need to scroll now" + COLOR_ENDC)
            list_view = device.find(
                resourceId="android:id/list", className="android.widget.ListView"
            )
            list_view.scroll(DeviceFacade.Direction.TOP)
        else:
            print(COLOR_OKGREEN + "No followers were iterated, finish." + COLOR_ENDC)
            return


def _is_mass_follower(device, username, max_followings):
    followings = get_following_count(device)
    print("@" + username + " has " + str(followings) + " followings")
    return followings is not None and followings > max_followings


def _close_dialog_if_shown(device):
    dialog_root_view = device.find(
        resourceId="com.instagram.android:id/dialog_root_view",
        className="android.widget.FrameLayout",
    )
    if not dialog_root_view.exists():
        return

    print(COLOR_OKGREEN + "Dialog shown, confirm removing..." + COLOR_ENDC)
    random_sleep()
    remove_button = dialog_root_view.child(index=0).child(
        resourceId="com.instagram.android:id/primary_button",
        className="android.widget.TextView",
    )
    remove_button.click()
    print("Removing confirmed!")
    random_sleep()


def _close_bottom_sheet_if_shown(device):
    bottom_sheet_view = device.find(
        resourceId="com.instagram.android:id/bottom_sheet_container",
        className="android.view.ViewGroup",
    )
    if not bottom_sheet_view.exists():
        return

    print(COLOR_OKGREEN + "Bottom sheet shown, confirm removing..." + COLOR_ENDC)
    random_sleep()
    remove_button = bottom_sheet_view.child(
        resourceId="com.instagram.android:id/action_sheet_row_text_view",
        className="android.widget.TextView",
    )
    remove_button.click()
    print("Removing confirmed!")
    random_sleep()


def _scroll_to_bottom(device):
    print("Scroll to bottom")

    def is_end_reached():
        see_all_button = device.find(
            resourceId="com.instagram.android:id/see_all_button",
            className="android.widget.TextView",
        )
        return see_all_button.exists()

    list_view = device.find(
        resourceId="android:id/list", className="android.widget.ListView"
    )
    while not is_end_reached():
        list_view.swipe(DeviceFacade.Direction.BOTTOM)

    print("Scroll back to the first follower")

    def is_at_least_one_follower():
        follower = device.find(
            resourceId="com.instagram.android:id/follow_list_container",
            className="android.widget.LinearLayout",
        )
        return follower.exists()

    while not is_at_least_one_follower():
        list_view.scroll(DeviceFacade.Direction.TOP)
