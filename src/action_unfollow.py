from enum import unique, Enum

from src.device_facade import DeviceFacade
from src.navigation import switch_to_english, LanguageChangedException
from src.storage import FollowingStatus
from src.utils import *

FOLLOWING_BUTTON_ID_REGEX = 'com.instagram.android:id/row_profile_header_following_container' \
                            '|com.instagram.android:id/row_profile_header_container_following'
TEXTVIEW_OR_BUTTON_REGEX = 'android.widget.TextView|android.widget.Button'


def unfollow(device, count, on_unfollow, storage, unfollow_restriction, my_username):
    _open_my_followings(device)
    _sort_followings_by_date(device)
    random_sleep()
    _iterate_over_followings(device, count, on_unfollow, storage, unfollow_restriction, my_username)


def _open_my_followings(device):
    print("Open my followings")
    followings_button = device.find(resourceIdMatches=FOLLOWING_BUTTON_ID_REGEX)
    followings_button.click()


def _sort_followings_by_date(device):
    print("Sort followings by date: from oldest to newest.")
    sort_button = device.find(resourceId='com.instagram.android:id/sorting_entry_row_icon',
                              className='android.widget.ImageView')
    if not sort_button.exists():
        print(COLOR_FAIL + "Cannot find button to sort followings. Continue without sorting.")
        return
    sort_button.click()

    sort_options_recycler_view = device.find(
        resourceId='com.instagram.android:id/follow_list_sorting_options_recycler_view')
    if not sort_options_recycler_view.exists():
        print(COLOR_FAIL + "Cannot find options to sort followings. Continue without sorting." + COLOR_ENDC)
        return

    sort_options_recycler_view.child(index=2).click()


def _iterate_over_followings(device, count, on_unfollow, storage, unfollow_restriction, my_username):
    # Wait until list is rendered
    device.find(resourceId='com.instagram.android:id/follow_list_container',
                className='android.widget.LinearLayout').wait()

    unfollowed_count = 0
    while True:
        print("Iterate over visible followings")
        random_sleep()
        screen_iterated_followings = 0

        for item in device.find(resourceId='com.instagram.android:id/follow_list_container',
                                className='android.widget.LinearLayout'):
            user_info_view = item.child(index=1)
            user_name_view = user_info_view.child(index=0).child()
            if not user_name_view.exists(quick=True):
                print(COLOR_OKGREEN + "Next item not found: probably reached end of the screen." + COLOR_ENDC)
                break

            username = user_name_view.get_text()
            screen_iterated_followings += 1

            if unfollow_restriction == UnfollowRestriction.FOLLOWED_BY_SCRIPT or \
                    unfollow_restriction == UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS:
                following_status = storage.get_following_status(username)
                if not following_status == FollowingStatus.FOLLOWED:
                    print("Skip @" + username + ". Following status: " + following_status.name + ".")
                    continue

            if unfollow_restriction == UnfollowRestriction.ANY:
                following_status = storage.get_following_status(username)
                if following_status == FollowingStatus.UNFOLLOWED:
                    print("Skip @" + username + ". Following status: " + following_status.name + ".")
                    continue

            print("Unfollow @" + username)
            unfollowed = _do_unfollow(device,
                                      username,
                                      my_username,
                                      unfollow_restriction == UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS)
            if unfollowed:
                storage.add_interacted_user(username, unfollowed=True)
                on_unfollow()
                unfollowed_count += 1

            random_sleep()
            if unfollowed_count >= count:
                return

        if screen_iterated_followings > 0:
            print(COLOR_OKGREEN + "Need to scroll now" + COLOR_ENDC)
            list_view = device.find(resourceId='android:id/list',
                                    className='android.widget.ListView')
            list_view.scroll(DeviceFacade.Direction.BOTTOM)
        else:
            print(COLOR_OKGREEN + "No followings were iterated, finish." + COLOR_ENDC)
            return


def _do_unfollow(device, username, my_username, check_if_is_follower):
    """
    :return: whether unfollow was successful
    """
    username_view = device.find(resourceId='com.instagram.android:id/follow_list_username',
                                className='android.widget.TextView',
                                text=username)
    if not username_view.exists():
        print(COLOR_FAIL + "Cannot find @" + username + ", skip." + COLOR_ENDC)
        return False
    username_view.click()

    if check_if_is_follower and _check_is_follower(device, username, my_username):
        print("Skip @" + username + ". This user is following you.")
        print("Back to the followings list.")
        device.back()
        return False

    unfollow_button = device.find(classNameMatches=TEXTVIEW_OR_BUTTON_REGEX,
                                  clickable=True,
                                  text='Following')
    if not unfollow_button.exists():
        print(COLOR_FAIL + "Cannot find Following button. Maybe not English language is set?" + COLOR_ENDC)
        save_crash(device)
        switch_to_english(device)
        raise LanguageChangedException()
    unfollow_button.click()

    confirm_unfollow_button = device.find(resourceId='com.instagram.android:id/follow_sheet_unfollow_row',
                                          className='android.widget.TextView')
    if not confirm_unfollow_button.exists():
        print(COLOR_FAIL + "Cannot confirm unfollow." + COLOR_ENDC)
        save_crash(device)
        device.back()
        return False
    confirm_unfollow_button.click()

    random_sleep()
    _close_confirm_dialog_if_shown(device)
    detect_block(device)

    print("Back to the followings list.")
    device.back()
    return True


def _check_is_follower(device, username, my_username):
    print(COLOR_OKGREEN + "Check if @" + username + " is following you." + COLOR_ENDC)
    following_container = device.find(resourceIdMatches=FOLLOWING_BUTTON_ID_REGEX)
    following_container.click()

    random_sleep()

    my_username_view = device.find(resourceId='com.instagram.android:id/follow_list_username',
                                   className='android.widget.TextView',
                                   text=my_username)
    result = my_username_view.exists()
    print("Back to the profile.")
    device.back()
    return result


def _close_confirm_dialog_if_shown(device):
    dialog_root_view = device.find(resourceId='com.instagram.android:id/dialog_root_view',
                                   className='android.widget.FrameLayout')
    if not dialog_root_view.exists():
        return

    # Avatar existence is the way to distinguish confirm dialog from block dialog
    user_avatar_view = device.find(resourceId='com.instagram.android:id/circular_image',
                                   className='android.widget.ImageView')
    if not user_avatar_view.exists():
        return

    print(COLOR_OKGREEN + "Dialog shown, confirm unfollowing." + COLOR_ENDC)
    random_sleep()
    unfollow_button = dialog_root_view.child(resourceId='com.instagram.android:id/primary_button',
                                             className='android.widget.TextView')
    unfollow_button.click()


@unique
class UnfollowRestriction(Enum):
    ANY = 0
    FOLLOWED_BY_SCRIPT = 1
    FOLLOWED_BY_SCRIPT_NON_FOLLOWERS = 2
