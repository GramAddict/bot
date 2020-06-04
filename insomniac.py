import argparse
import sys
import traceback
from datetime import datetime, timedelta
from functools import partial

import uiautomator

from action_handle_blogger import handle_blogger
from session_state import SessionState
from storage import Storage
from utils import *

sessionState = SessionState()
completedSessions = 0
totalTimeWorked = timedelta(0)


def main():
    print(COLOR_HEADER + "Insomniac " + get_version() + "\n" + COLOR_ENDC)

    if not check_adb_connection():
        return

    ok, args = _parse_arguments()
    if not ok:
        return

    if len(args.bloggers) == 0:
        print(COLOR_FAIL + "Zero bloggers, no sense to proceed." + COLOR_ENDC)
        return
    else:
        print "bloggers = " + ", ".join(str(blogger) for blogger in args.bloggers)

    device = uiautomator.device
    storage = Storage()
    on_interaction = partial(_on_interaction,
                             interactions_limit=int(args.interactions),
                             likes_limit=int(args.total_likes_limit))

    while True:
        print(COLOR_OKBLUE + "\n-------- START: " + str(datetime.now().time()) + " --------" + COLOR_ENDC)
        open_instagram()
        _job_handle_bloggers(device, args.bloggers, int(args.likes_count), storage, on_interaction)

        global completedSessions
        completedSessions += 1
        global totalTimeWorked
        totalTimeWorked += datetime.now() - sessionState.startTime

        close_instagram()
        print(COLOR_OKBLUE + "-------- FINISH: " + str(datetime.now().time()) + " --------" + COLOR_ENDC)
        _print_report()
        sessionState.reset()

        if args.repeat:
            repeat = int(args.repeat)
            print "\nSleep for " + str(repeat) + " minutes"
            try:
                sleep(60 * repeat)
            except KeyboardInterrupt:
                sys.exit(0)
        else:
            break


def _job_handle_bloggers(device, bloggers, likes_count, storage, on_interaction):
    class State:
        def __init__(self):
            pass

        is_job_completed = False

    state = State()

    def on_likes_limit_reached():
        state.is_job_completed = True

    on_interaction = partial(on_interaction, on_likes_limit_reached=on_likes_limit_reached)

    for blogger in bloggers:
        print(COLOR_BOLD + "\nHandle @" + blogger + COLOR_ENDC)
        is_handled = False
        while not is_handled and not state.is_job_completed:
            # noinspection PyBroadException
            try:
                handle_blogger(device, blogger, likes_count, storage, _on_like, on_interaction)
                is_handled = True
            except KeyboardInterrupt:
                print(COLOR_OKBLUE + "-------- FINISH: " + str(datetime.now().time()) + " --------" + COLOR_ENDC)
                _print_report()
                sys.exit(0)
            except Exception:
                is_handled = False
                print(COLOR_FAIL + traceback.format_exc() + COLOR_ENDC)
                print "Try again for @" + blogger + " from the beginning"


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
    parser.add_argument('--repeat',
                        help='repeat the same session again after N minutes after completion, disabled by default',
                        metavar='180')

    if not len(sys.argv) > 1:
        parser.print_help()
        return False, None

    args, unknown_args = parser.parse_known_args()

    if unknown_args:
        print(COLOR_FAIL + "Unknown arguments: " + ", ".join(str(arg) for arg in unknown_args) + COLOR_ENDC)
        parser.print_help()
        return False, None

    return True, args


def _on_like():
    sessionState.totalLikes += 1


def _on_interaction(succeed, count, interactions_limit, likes_limit, on_likes_limit_reached):
    sessionState.totalInteractions += 1

    if succeed:
        sessionState.successfulInteractions += 1

    can_continue = True

    if sessionState.totalLikes >= likes_limit:
        print "Reached total likes limit, finish."
        on_likes_limit_reached()
        can_continue = False

    if count >= interactions_limit:
        print "Made " + str(count) + " interactions, finish."
        can_continue = False

    return can_continue


def _print_report():
    print "\n"
    print(COLOR_OKBLUE + "Total interactions: " + str(sessionState.totalInteractions) + COLOR_ENDC)
    print(COLOR_OKBLUE + "Successful interactions: " + str(sessionState.successfulInteractions) + COLOR_ENDC)
    print(COLOR_OKBLUE + "Total likes: " + str(sessionState.totalLikes) + COLOR_ENDC)
    print(COLOR_OKBLUE + "Completed sessions: " + str(completedSessions) + COLOR_ENDC)
    session_time = datetime.now() - sessionState.startTime
    print(COLOR_OKBLUE + "Last session time: " + str(session_time) + COLOR_ENDC)
    print(COLOR_OKBLUE + "Total time of Instagram being opened: " + str(totalTimeWorked) + COLOR_ENDC)


if __name__ == "__main__":
    main()
