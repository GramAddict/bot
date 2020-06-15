# Since of v1.2.3 this script works on Python 3

import argparse
import sys
import traceback
from datetime import timedelta
from functools import partial
from http.client import HTTPException
from socket import timeout

import colorama
import uiautomator

from action_handle_blogger import handle_blogger
from session_state import SessionState
from storage import Storage
from utils import *

sessions = []


def main():
    colorama.init()
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
        print("bloggers = " + ", ".join(str(blogger) for blogger in args.bloggers))

    device = uiautomator.device
    storage = Storage()
    on_interaction = partial(_on_interaction,
                             interactions_limit=int(args.interactions),
                             likes_limit=int(args.total_likes_limit))

    while True:
        session_state = SessionState()
        sessions.append(session_state)

        print(COLOR_WARNING + "\n-------- START: " + str(session_state.startTime) + " --------" + COLOR_ENDC)
        open_instagram()
        _job_handle_bloggers(device, args.bloggers, int(args.likes_count), storage, on_interaction)
        close_instagram()
        session_state.finishTime = datetime.now()
        print(COLOR_WARNING + "-------- FINISH: " + str(session_state.finishTime) + " --------" + COLOR_ENDC)
        _print_report()

        if args.repeat:
            repeat = int(args.repeat)
            print("\nSleep for " + str(repeat) + " minutes")
            try:
                sleep(60 * repeat)
            except KeyboardInterrupt:
                _print_report()
                sys.exit(0)
        else:
            break

    _print_report()


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
        on_interaction = partial(on_interaction, blogger=blogger)
        while not is_handled and not state.is_job_completed:
            try:
                handle_blogger(device, blogger, likes_count, storage, _on_like, on_interaction)
                is_handled = True
            except KeyboardInterrupt:
                print(COLOR_WARNING + "-------- FINISH: " + str(datetime.now().time()) + " --------" + COLOR_ENDC)
                _print_report()
                sys.exit(0)
            except (uiautomator.JsonRPCError, IndexError, HTTPException, timeout):
                is_handled = False
                print(COLOR_FAIL + traceback.format_exc() + COLOR_ENDC)
                take_screenshot(device)
                print("Try again for @" + blogger + " from the beginning")
                # Hack for the case when IGTV was accidentally opened
                close_instagram()
                random_sleep()
                open_instagram()
            except Exception as e:
                take_screenshot(device)
                _print_report()
                raise e


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
    session_state = sessions[-1]
    session_state.totalLikes += 1


def _on_interaction(blogger, succeed, count, interactions_limit, likes_limit, on_likes_limit_reached):
    session_state = sessions[-1]
    session_state.add_interaction(blogger, succeed)

    can_continue = True

    if session_state.totalLikes >= likes_limit:
        print("Reached total likes limit, finish.")
        on_likes_limit_reached()
        can_continue = False

    if count >= interactions_limit:
        print("Made " + str(count) + " interactions, finish.")
        can_continue = False

    return can_continue


def _print_report():
    if len(sessions) > 1:
        for index, session in enumerate(sessions):
            finish_time = session.finishTime or datetime.now()
            print("\n")
            print(COLOR_WARNING + "SESSION #" + str(index + 1) + COLOR_ENDC)
            print(COLOR_WARNING + "Start time: " + str(session.startTime) + COLOR_ENDC)
            print(COLOR_WARNING + "Finish time: " + str(finish_time) + COLOR_ENDC)
            print(COLOR_WARNING + "Duration: " + str(finish_time - session.startTime) + COLOR_ENDC)
            print(COLOR_WARNING + "Total interactions: " + stringify_interactions(session.totalInteractions)
                  + COLOR_ENDC)
            print(COLOR_WARNING + "Successful interactions: " + stringify_interactions(session.successfulInteractions)
                  + COLOR_ENDC)
            print(COLOR_WARNING + "Total likes: " + str(session.totalLikes) + COLOR_ENDC)

    print("\n")
    print(COLOR_WARNING + "TOTAL" + COLOR_ENDC)

    completed_sessions = [session for session in sessions if session.is_finished()]
    print(COLOR_WARNING + "Completed sessions: " + str(len(completed_sessions)) + COLOR_ENDC)

    duration = timedelta(0)
    for session in sessions:
        finish_time = session.finishTime or datetime.now()
        duration += finish_time - session.startTime
    print(COLOR_WARNING + "Total duration: " + str(duration) + COLOR_ENDC)

    total_interactions = {}
    successful_interactions = {}
    for session in sessions:
        for blogger, count in session.totalInteractions.items():
            if total_interactions.get(blogger) is None:
                total_interactions[blogger] = count
            else:
                total_interactions[blogger] += count

        for blogger, count in session.successfulInteractions.items():
            if successful_interactions.get(blogger) is None:
                successful_interactions[blogger] = count
            else:
                successful_interactions[blogger] += count

    print(COLOR_WARNING + "Total interactions: " + stringify_interactions(total_interactions) + COLOR_ENDC)
    print(COLOR_WARNING + "Successful interactions: " + stringify_interactions(successful_interactions) + COLOR_ENDC)

    total_likes = sum(session.totalLikes for session in sessions)
    print(COLOR_WARNING + "Total likes: " + str(total_likes) + COLOR_ENDC)


if __name__ == "__main__":
    main()
