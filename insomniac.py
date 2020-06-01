import argparse
import os
import re
import sys
import traceback
from functools import partial
from random import shuffle, randint
from time import sleep

import uiautomator

from storage import Storage
from utils import double_click

COLOR_HEADER = '\033[95m'
COLOR_OKBLUE = '\033[94m'
COLOR_OKGREEN = '\033[92m'
COLOR_WARNING = '\033[93m'
COLOR_FAIL = '\033[91m'
COLOR_ENDC = '\033[0m'
COLOR_BOLD = '\033[1m'
COLOR_UNDERLINE = '\033[4m'

storage = Storage()
totalInteractions = 0
totalLikes = 0


def main():
    print(COLOR_HEADER + "Insomniac " + get_version() + "\n" + COLOR_ENDC)

    if not check_adb_connection():
        return

    ok, bloggers, likes_count, total_likes_limit, interactions = parse_arguments()
    if not ok:
        return

    if total_likes_limit <= 0:
        print(COLOR_FAIL + "Zero total likes limit, no sense to proceed." + COLOR_ENDC)
        return
    else:
        print "total_likes_limit = " + str(total_likes_limit)

    if likes_count <= 0:
        print(COLOR_FAIL + "Zero likes during interaction, no sense to proceed." + COLOR_ENDC)
        return
    else:
        print "likes_count = " + str(likes_count)

    if interactions <= 0:
        print(COLOR_FAIL + "Zero interactions per each blogger, no sense to proceed." + COLOR_ENDC)
        return
    else:
        print "interactions = " + str(interactions)

    if len(bloggers) == 0:
        print(COLOR_FAIL + "Zero bloggers, no sense to proceed." + COLOR_ENDC)
        return
    else:
        print "bloggers = " + str(bloggers)

    device = uiautomator.device
    interaction = partial(interact_with_user, likes_count=likes_count)
    for blogger in bloggers:
        print(COLOR_BOLD + "\nHandle @" + blogger + COLOR_ENDC)
        is_handled = False
        while not is_handled:
            is_handled = handle_blogger(device, blogger, interaction, total_likes_limit, interactions)
            if not is_handled:
                print "Try again for @" + blogger + " from the beginning"

    print_report_and_quit()


def get_version():
    stream = os.popen('git describe --tags')
    output = stream.read()
    version_match = re.match('(v\\d+.\\d+.\\d+)', output)
    version = (version_match is None) and "(Work In Progress)" or version_match.group(1)
    stream.close()
    return version


def check_adb_connection():
    stream = os.popen('adb devices')
    output = stream.read()
    devices_count = len(re.findall('device\n', output))
    is_ok = devices_count == 1
    print "Connected devices via adb: " + str(devices_count) + ". " + (is_ok and "That's ok." or "Cannot proceed.")
    stream.close()
    return is_ok


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Instagram bot for automated Instagram interaction using Android device via ADB',
        add_help=False
    )
    parser.add_argument('--bloggers',
                        nargs='+',
                        help='list of usernames with whose followers you want to interact',
                        metavar=('username1', 'username2'),
                        default=[])
    parser.add_argument('--likes-count',
                        help='count of likes for each interacted user, 2 by default',
                        metavar='2',
                        default=2)
    parser.add_argument('--total-likes-limit',
                        help='limit on total amount of likes during the session, 1000 by default',
                        metavar='1000',
                        default=1000)
    parser.add_argument('--interactions',
                        help='number of interactions per each blogger, 100 by default',
                        metavar='100',
                        default=100)

    if not len(sys.argv) > 1:
        parser.print_help()
        return False, None, None, None, None

    args, _ = parser.parse_known_args()
    return True, args.bloggers, int(args.likes_count), int(args.total_likes_limit), int(args.interactions)


def handle_blogger(device, username, interaction, total_likes_limit, interactions_limit):
    # noinspection PyBroadException
    try:
        open_user_followers(device, username)
        iterate_over_followers(device, interaction, total_likes_limit, interactions_limit)
    except KeyboardInterrupt:
        print_report_and_quit()
    except Exception:
        print(COLOR_FAIL + traceback.format_exc() + COLOR_ENDC)
        return False
    return True


def open_user_followers(device, username):
    print "Press search"
    tab_bar = device(resourceId='com.instagram.android:id/tab_bar', className='android.widget.LinearLayout')
    search_button = tab_bar.child(index=1)
    search_button.click.wait()

    print "Open user @" + username
    search_edit_text = device(resourceId='com.instagram.android:id/action_bar_search_edit_text',
                              className='android.widget.EditText')
    search_edit_text.set_text(username)
    search_results_list = device(resourceId='android:id/list',
                                 className='android.widget.ListView')
    search_first_result = search_results_list.child(index=0)
    search_first_result.click.wait()

    print "Open @" + username + " followers"
    followers_button = device(resourceId='com.instagram.android:id/row_profile_header_followers_container',
                              className='android.widget.LinearLayout')
    followers_button.click.wait()


def iterate_over_followers(device, interaction, total_likes_limit, interactions_limit):
    interactions_count = 0
    while True:
        print "Iterate over visible followers"
        iterated_followers = []

        for item in device(resourceId='com.instagram.android:id/follow_list_container',
                           className='android.widget.LinearLayout'):
            try:
                user_info_view = item.child(index=1)
                user_name_view = user_info_view.child(index=0).child()
                username = user_name_view.text
            except uiautomator.JsonRPCError:
                print(COLOR_OKBLUE + "Possibly reached end of the screen." + COLOR_ENDC)
                break

            iterated_followers.append(username)
            if storage.check_user_was_interacted(username):
                print "@" + username + ": already interacted. Skip."
            else:
                print "@" + username + ": interact"
                item.click.wait()
                interaction(device)
                storage.add_interacted_user(username)

                global totalInteractions
                totalInteractions += 1
                interactions_count += 1

                if interactions_count >= interactions_limit:
                    print "Made " + str(interactions_count) + " interactions, finish."
                    return

                if totalLikes >= total_likes_limit:
                    print "Reached total likes limit."
                    print_report_and_quit()

                print "Back to followers list"
                device.press.back()

        if len(iterated_followers) > 0:
            print(COLOR_OKBLUE + "Need to scroll now" + COLOR_ENDC)
            list_view = device(resourceId='android:id/list',
                               className='android.widget.ListView')
            list_view.scroll.toEnd(max_swipes=1)
        else:
            print(COLOR_OKBLUE + "No followers were iterated, finish." + COLOR_ENDC)
            return


def interact_with_user(device, likes_count):
    if likes_count > 6:
        print(COLOR_FAIL + "Max number of likes per user is 6" + COLOR_ENDC)
        likes_count = 6

    random_sleep()
    photos_indices = [0, 1, 2, 3, 4, 5]
    shuffle(photos_indices)
    for i in xrange(0, likes_count):
        photo_index = photos_indices[i]
        row = photo_index / 3
        column = photo_index - row * 3

        print "Open and like photo #" + str(i + 1) + " (" + str(row + 1) + " row, " + str(column + 1) + " column)"
        if not open_photo_and_like(device, row, column):
            return


def open_photo_and_like(device, row, column):
    def open_photo():
        recycler_view = device(resourceId='android:id/list',
                               className='androidx.recyclerview.widget.RecyclerView')
        row_view = recycler_view.child(index=row + 1)
        item_view = row_view.child(index=column)
        item_view.click.wait()

    try:
        open_photo()
    except uiautomator.JsonRPCError:
        print(COLOR_WARNING + "Possibly need to scroll." + COLOR_ENDC)
        scroll_profile(device)
        try:
            open_photo()
        except uiautomator.JsonRPCError:
            print(COLOR_WARNING + "Less than 6 photos / account is private. Skip user." + COLOR_ENDC)
            return False

    random_sleep()
    print "Double click!"
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
                print "Double click didn't work, click on icon."
                like_button.click()
    except uiautomator.JsonRPCError:
        print "Double click worked successfully."

    global totalLikes
    totalLikes += 1
    random_sleep()
    print "Back to profile"
    device.press.back()
    return True


def scroll_profile(device):
    tab_bar = device(resourceId='com.instagram.android:id/tab_bar',
                     className='android.widget.LinearLayout')

    x1 = (tab_bar.bounds['right'] - tab_bar.bounds['left']) / 2
    y1 = tab_bar.bounds['top'] - 1

    vertical_offset = tab_bar.bounds['right'] - tab_bar.bounds['left']

    x2 = x1
    y2 = y1 - vertical_offset

    device.swipe(x1, y1, x2, y2)


def random_sleep():
    delay = randint(1, 4)
    print "Sleep for " + str(delay) + (delay == 1 and " second" or " seconds")
    sleep(delay)


def print_report_and_quit():
    print "\n"
    print(COLOR_OKBLUE + "Total interactions: " + str(totalInteractions) + COLOR_ENDC)
    print(COLOR_OKBLUE + "Total likes: " + str(totalLikes) + COLOR_ENDC)
    sys.exit(0)


if __name__ == "__main__":
    main()
