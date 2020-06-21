from storage import FollowingStatus
from utils import *


def unfollow(device, count, on_unfollow, storage):
    _open_my_followings(device)
    _sort_followings_by_date(device)
    _iterate_over_followings(device, count, on_unfollow, storage)


def _open_my_followings(device):
    print("Press profile")
    tab_bar = device(resourceId='com.instagram.android:id/tab_bar', className='android.widget.LinearLayout')
    search_button = tab_bar.child(index=4)
    search_button.click.wait()

    print("Open my followings")
    followings_button = device(resourceId='com.instagram.android:id/row_profile_header_following_container',
                               className='android.widget.LinearLayout')
    followings_button.click.wait()


def _sort_followings_by_date(device):
    print("Sort followings by date: from oldest to newest.")
    sort_button = device(resourceId='com.instagram.android:id/sorting_entry_row_icon',
                         className='android.widget.ImageView')

    if not sort_button.exists:
        print(COLOR_FAIL + "Cannot find button to sort followings. Continue without sorting.")
        return

    sort_button.click.wait()
    sort_options_recycler_view = device(resourceId='com.instagram.android:id/follow_list_sorting_options_recycler_view')
    sort_options_recycler_view.child(index=2).click.wait()


def _iterate_over_followings(device, count, on_unfollow, storage):
    unfollowed_count = 0
    while True:
        print("Iterate over visible followings")
        screen_iterated_followings = 0

        for item in device(resourceId='com.instagram.android:id/follow_list_container',
                           className='android.widget.LinearLayout'):
            user_info_view = item.child(index=1)
            if not user_info_view.exists:
                print(COLOR_OKGREEN + "Next item not found: probably reached end of the screen." + COLOR_ENDC)
                break

            user_name_view = user_info_view.child(index=0).child()
            username = user_name_view.text
            screen_iterated_followings += 1

            following_status = storage.get_following_status(username)
            if following_status == FollowingStatus.FOLLOWED:
                print("Unfollow @" + username)

                unfollow_button = item.child(resourceId='com.instagram.android:id/button',
                                             className='android.widget.TextView')
                unfollow_button.click.wait()
                _close_dialog_if_shown(device)
                storage.add_interacted_user(username, unfollowed=True)
                on_unfollow()

                random_sleep()

                unfollowed_count += 1
                if unfollowed_count >= count:
                    return
            else:
                print("Skip @" + username + ". Following status: " + following_status.name + ".")

        if screen_iterated_followings > 0:
            print(COLOR_OKGREEN + "Need to scroll now" + COLOR_ENDC)
            list_view = device(resourceId='android:id/list',
                               className='android.widget.ListView')
            list_view.scroll.toEnd(max_swipes=1)
        else:
            print(COLOR_OKGREEN + "No followings were iterated, finish." + COLOR_ENDC)
            return


def _close_dialog_if_shown(device):
    dialog_root_view = device(resourceId='com.instagram.android:id/dialog_root_view',
                              className='android.widget.FrameLayout')
    if not dialog_root_view.exists:
        return

    print(COLOR_OKGREEN + "Dialog shown, confirm unfollowing." + COLOR_ENDC)
    random_sleep()
    unfollow_button = dialog_root_view.child(index=0).child(resourceId='com.instagram.android:id/primary_button',
                                                            className='android.widget.TextView')
    unfollow_button.click.wait()
