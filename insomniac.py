import argparse
import os
import re
import sys
import traceback
from datetime import datetime
from functools import partial

import uiautomator

from action_handle_blogger import handle_blogger
from storage import Storage
from utils import *

totalInteractions = 0
successfulInteractions = 0
totalLikes = 0
startTime = datetime.now()


def main():
    print(COLOR_HEADER + "Insomniac " + _get_version() + "\n" + COLOR_ENDC)

    if not _check_adb_connection():
        return

    ok, bloggers, likes_count, total_likes_limit, interactions = _parse_arguments()
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
    storage = Storage()
    on_interaction = partial(_on_interaction,
                             interactions_limit=interactions,
                             likes_limit=total_likes_limit,
                             print_report_and_quit=_print_report_and_quit)

    for blogger in bloggers:
        print(COLOR_BOLD + "\nHandle @" + blogger + COLOR_ENDC)
        is_handled = False
        while not is_handled:
            # noinspection PyBroadException
            try:
                handle_blogger(device, blogger, likes_count, storage, _on_like, on_interaction)
                is_handled = True
            except KeyboardInterrupt:
                _print_report_and_quit()
                return
            except Exception:
                is_handled = False
                print(COLOR_FAIL + traceback.format_exc() + COLOR_ENDC)

            if not is_handled:
                print "Try again for @" + blogger + " from the beginning"

    _print_report_and_quit()


def _get_version():
    stream = os.popen('git describe --tags')
    output = stream.read()
    version_match = re.match('(v\\d+.\\d+.\\d+)', output)
    version = (version_match is None) and "(Work In Progress)" or version_match.group(1)
    stream.close()
    return version


def _check_adb_connection():
    stream = os.popen('adb devices')
    output = stream.read()
    devices_count = len(re.findall('device\n', output))
    is_ok = devices_count == 1
    print "Connected devices via adb: " + str(devices_count) + ". " + (is_ok and "That's ok." or "Cannot proceed.")
    stream.close()
    return is_ok


def _parse_arguments():
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


def _on_like():
    global totalLikes
    totalLikes += 1


def _on_interaction(succeed, count, interactions_limit, likes_limit, print_report_and_quit):
    if succeed:
        global successfulInteractions
        successfulInteractions += 1

    global totalInteractions
    totalInteractions += 1

    if totalLikes >= likes_limit:
        print "Reached total likes limit."
        print_report_and_quit()

    return count < interactions_limit


def _print_report_and_quit():
    print "\n"
    print(COLOR_OKBLUE + "Total interactions: " + str(totalInteractions) + COLOR_ENDC)
    print(COLOR_OKBLUE + "Successful interactions: " + str(successfulInteractions) + COLOR_ENDC)
    print(COLOR_OKBLUE + "Total likes: " + str(totalLikes) + COLOR_ENDC)
    working_time = datetime.now() - startTime
    print(COLOR_OKBLUE + "Time worked: " + str(working_time) + COLOR_ENDC)
    sys.exit(0)


if __name__ == "__main__":
    main()
