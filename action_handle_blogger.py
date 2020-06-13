from functools import partial
from random import shuffle

import uiautomator

from utils import *


def handle_blogger(device,
                   username,
                   likes_count,
                   storage,
                   on_like,
                   on_interaction):
    interaction = partial(_interact_with_user, likes_count=likes_count, on_like=on_like)

    _open_user_followers(device, username)
    _iterate_over_followers(device, interaction, storage, on_interaction)


def _open_user_followers(device, username):
    print("Press search")
    tab_bar = device(resourceId='com.instagram.android:id/tab_bar', className='android.widget.LinearLayout')
    search_button = tab_bar.child(index=1)
    search_button.click.wait()

    print("Open user @" + username)
    search_edit_text = device(resourceId='com.instagram.android:id/action_bar_search_edit_text',
                              className='android.widget.EditText')
    search_edit_text.set_text(username)
    search_results_list = device(resourceId='android:id/list',
                                 className='android.widget.ListView')
    search_first_result = search_results_list.child(index=0)
    search_first_result.click.wait()

    print("Open @" + username + " followers")
    followers_button = device(resourceId='com.instagram.android:id/row_profile_header_followers_container',
                              className='android.widget.LinearLayout')
    followers_button.click.wait()


def _iterate_over_followers(device, interaction, storage, on_interaction):
    followers_per_screen = None
    interactions_count = 0

    while True:
        print("Iterate over visible followers")
        screen_iterated_followers = 0

        for item in device(resourceId='com.instagram.android:id/follow_list_container',
                           className='android.widget.LinearLayout'):
            try:
                user_info_view = item.child(index=1)
                user_name_view = user_info_view.child(index=0).child()
                username = user_name_view.text
            except uiautomator.JsonRPCError:
                print(COLOR_OKBLUE + "Next item not found: probably reached end of the screen." + COLOR_ENDC)
                if followers_per_screen is None:
                    followers_per_screen = screen_iterated_followers
                break

            screen_iterated_followers += 1
            if storage.check_user_was_interacted(username):
                print("@" + username + ": already interacted. Skip.")
            else:
                print("@" + username + ": interact")
                item.click.wait()

                interaction_succeed = interaction(device)
                storage.add_interacted_user(username)
                interactions_count += 1
                can_continue = on_interaction(succeed=interaction_succeed, count=interactions_count)

                if not can_continue:
                    return

                print("Back to followers list")
                device.press.back()

            if followers_per_screen and screen_iterated_followers >= followers_per_screen:
                print(COLOR_OKBLUE + str(screen_iterated_followers) +
                      " items iterated: probably reached end of the screen." + COLOR_ENDC)
                break

        if screen_iterated_followers > 0:
            print(COLOR_OKBLUE + "Need to scroll now" + COLOR_ENDC)
            list_view = device(resourceId='android:id/list',
                               className='android.widget.ListView')
            list_view.scroll.toEnd(max_swipes=1)
        else:
            print(COLOR_OKBLUE + "No followers were iterated, finish." + COLOR_ENDC)
            return


def _interact_with_user(device, likes_count, on_like):
    if likes_count > 6:
        print(COLOR_FAIL + "Max number of likes per user is 6" + COLOR_ENDC)
        likes_count = 6

    random_sleep()
    print("Scroll down to see more photos.")
    if not _scroll_profile(device):
        return False

    photos_indices = [0, 1, 2, 3, 4, 5]
    shuffle(photos_indices)
    for i in range(0, likes_count):
        photo_index = photos_indices[i]
        row = photo_index // 3
        column = photo_index - row * 3

        print("Open and like photo #" + str(i + 1) + " (" + str(row + 1) + " row, " + str(column + 1) + " column)")
        if not _open_photo_and_like(device, row, column, on_like):
            return False

    return True


def _open_photo_and_like(device, row, column, on_like):
    def open_photo():
        # recycler_view has a className 'androidx.recyclerview.widget.RecyclerView' on modern Android versions and
        # 'android.view.View' on Android 5.0.1 and probably earlier versions
        recycler_view = device(resourceId='android:id/list')
        row_view = recycler_view.child(index=row + 1)
        item_view = row_view.child(index=column)
        item_view.click.wait()

    try:
        open_photo()
    except uiautomator.JsonRPCError:
        print(COLOR_WARNING + "Less than 6 photos. Skip user." + COLOR_ENDC)
        return False

    random_sleep()
    print("Double click!")
    double_click(device,
                 resourceId='com.instagram.android:id/layout_container_main',
                 className='android.widget.FrameLayout')
    random_sleep()

    action_bar = device(resourceId='com.instagram.android:id/action_bar_container',
                        className='android.widget.FrameLayout')
    action_bar_bottom = action_bar.bounds['bottom']

    # If double click didn't work, set like by icon click
    try:
        # Click only button which is under the action bar. It fixes bug with accidental back icon click
        for like_button in device(resourceId='com.instagram.android:id/row_feed_button_like',
                                  className='android.widget.ImageView',
                                  selected=False):
            like_button_top = like_button.bounds['top']
            if like_button_top > action_bar_bottom:
                print("Double click didn't work, click on icon.")
                like_button.click()
                random_sleep()
    except uiautomator.JsonRPCError:
        print("Double click worked successfully.")

    on_like()
    print("Back to profile")
    device.press.back()
    return True


def _scroll_profile(device):
    tab_bar = device(resourceId='com.instagram.android:id/tab_bar',
                     className='android.widget.LinearLayout')

    try:
        profile_tabs_container = device(resourceId='com.instagram.android:id/profile_tabs_container',
                                        className='android.widget.LinearLayout')
        profile_tabs_container_top = profile_tabs_container.bounds['top']
    except uiautomator.JsonRPCError:
        print(COLOR_WARNING + "Cannot scroll: empty / private account. Skip user." + COLOR_ENDC)
        return False

    action_bar_container = device(resourceId='com.instagram.android:id/action_bar_container',
                                  className='android.widget.FrameLayout')
    action_bar_container_bottom = action_bar_container.bounds['bottom']

    x1 = (tab_bar.bounds['right'] - tab_bar.bounds['left']) / 2
    y1 = tab_bar.bounds['top'] - 1

    vertical_offset = profile_tabs_container_top - action_bar_container_bottom

    x2 = x1
    y2 = y1 - vertical_offset

    device.swipe(x1, y1, x2, y2)
    return True
