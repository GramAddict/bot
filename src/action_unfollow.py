from enum import unique, Enum

from src.globals import UI_TIMEOUT, UI_TIMEOUT_ITERATOR
from src.storage import FollowingStatus
from src.utils import *


def unfollow(device, count, on_unfollow, storage, unfollow_restriction, my_username):
    _open_my_followings(device)
    _sort_followings_by_date(device)
    random_sleep()
    _iterate_over_followings(device, count, on_unfollow, storage, unfollow_restriction, my_username)


def _open_my_followings(device):
    print("Open my followings")
    followings_button = device(resourceId='com.instagram.android:id/row_profile_header_following_container',
                               className='android.widget.LinearLayout')
    followings_button.click(timeout=UI_TIMEOUT)


def _sort_followings_by_date(device):
    print("Sort followings by date: from oldest to newest.")
    sort_button = device(resourceId='com.instagram.android:id/sorting_entry_row_icon',
                         className='android.widget.ImageView')
    if not sort_button.exists(timeout=UI_TIMEOUT):
        print(COLOR_FAIL + "Cannot find button to sort followings. Continue without sorting.")
        return
    sort_button.click(timeout=UI_TIMEOUT)

    sort_options_recycler_view = device(resourceId='com.instagram.android:id/follow_list_sorting_options_recycler_view')
    if not sort_options_recycler_view.exists(timeout=UI_TIMEOUT):
        print(COLOR_FAIL + "Cannot find options to sort followings. Continue without sorting." + COLOR_ENDC)
        return

    sort_options_recycler_view.child(index=2).click(timeout=UI_TIMEOUT)


def _iterate_over_followings(device, count, on_unfollow, storage, unfollow_restriction, my_username):
    # Wait until list is rendered
    device(resourceId='com.instagram.android:id/follow_list_container',
           className='android.widget.LinearLayout').wait(timeout=UI_TIMEOUT)

    unfollowed_count = 0
    while True:
        print("Iterate over visible followings")
        random_sleep()
        screen_iterated_followings = 0

        for item in device(resourceId='com.instagram.android:id/follow_list_container',
                           className='android.widget.LinearLayout'):
            user_info_view = item.child(index=1)
            user_name_view = user_info_view.child(index=0).child()
            if not user_name_view.exists(timeout=UI_TIMEOUT_ITERATOR):
                print(COLOR_OKGREEN + "Next item not found: probably reached end of the screen." + COLOR_ENDC)
                break

            username = user_name_view.info['text']
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
            list_view = device(resourceId='android:id/list',
                               className='android.widget.ListView')
            list_view.scroll.toEnd(max_swipes=1)
        else:
            print(COLOR_OKGREEN + "No followings were iterated, finish." + COLOR_ENDC)
            return


def _do_unfollow(device, username, my_username, check_if_is_follower):
    """
    :return: whether unfollow was successful
    """
    username_view = device(resourceId='com.instagram.android:id/follow_list_username',
                           className='android.widget.TextView',
                           text=username)
    if not username_view.exists(timeout=UI_TIMEOUT):
        print(COLOR_FAIL + "Cannot find @" + username + ", skip." + COLOR_ENDC)
        return False
    username_view.click(timeout=UI_TIMEOUT)

    if check_if_is_follower and _check_is_follower(device, username, my_username):
        print("Skip @" + username + ". This user is following you.")
        device.press("back")
        return False

    profile_actions_view = device(resourceId='com.instagram.android:id/profile_header_actions_top_row',
                                  className='android.widget.LinearLayout')
    if not profile_actions_view.exists(timeout=UI_TIMEOUT):
        print(COLOR_FAIL + "Cannot find unfollow button." + COLOR_ENDC)
        take_screenshot(device)
        device.press("back")
        return False

    unfollow_button = profile_actions_view.child(index=0)
    if not unfollow_button.exists(timeout=UI_TIMEOUT):
        print(COLOR_FAIL + "Cannot find unfollow button." + COLOR_ENDC)
        take_screenshot(device)
        device.press("back")
        return False
    unfollow_button.click(timeout=UI_TIMEOUT)

    confirm_unfollow_button = device(resourceId='com.instagram.android:id/follow_sheet_unfollow_row',
                                     className='android.widget.TextView')
    if not confirm_unfollow_button.exists(timeout=UI_TIMEOUT):
        print(COLOR_FAIL + "Cannot confirm unfollow." + COLOR_ENDC)
        take_screenshot(device)
        device.press("back")
        return False
    confirm_unfollow_button.click(timeout=UI_TIMEOUT)

    random_sleep()

    unfollow_succeed = not _check_if_you_follow(device, username, my_username)
    if not unfollow_succeed:
        print(COLOR_FAIL + "Unfollow didn't work for some reason." + COLOR_ENDC)
        raise UnfollowError("Please check why unfollow doesn't work, you may be blocked!")

    print("Back to the followings list.")
    device.press("back")
    return unfollow_succeed


def _check_is_follower(device, username, my_username):
    print(COLOR_OKGREEN + "Check if @" + username + " is following you." + COLOR_ENDC)
    following_container = device(resourceId='com.instagram.android:id/row_profile_header_following_container',
                                 className='android.widget.LinearLayout')
    following_container.click(timeout=UI_TIMEOUT)

    random_sleep()

    my_username_view = device(resourceId='com.instagram.android:id/follow_list_username',
                              className='android.widget.TextView',
                              text=my_username)
    result = my_username_view.exists(timeout=UI_TIMEOUT)
    print("Back to the profile.")
    device.press("back")
    return result


def _check_if_you_follow(device, username, my_username):
    print("Make sure that you don't still follow @" + username)
    followers_container = device(resourceId='com.instagram.android:id/row_profile_header_followers_container',
                                 className='android.widget.LinearLayout')
    followers_container.click(timeout=UI_TIMEOUT)

    random_sleep()

    my_username_view = device(resourceId='com.instagram.android:id/follow_list_username',
                              className='android.widget.TextView',
                              text=my_username)
    result = my_username_view.exists(timeout=UI_TIMEOUT)
    print("Back to the profile.")
    device.press("back")
    return result


@unique
class UnfollowRestriction(Enum):
    ANY = 0
    FOLLOWED_BY_SCRIPT = 1
    FOLLOWED_BY_SCRIPT_NON_FOLLOWERS = 2


class UnfollowError(Exception):
    pass
