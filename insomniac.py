# Since of v1.2.3 this script works on Python 3

import argparse
import random
import sys
import traceback
from datetime import timedelta
from enum import Enum, unique
from functools import partial
from http.client import HTTPException
from socket import timeout

import colorama
import uiautomator

from src.action_get_my_profile_info import get_my_profile_info
from src.action_handle_blogger import handle_blogger
from src.action_unfollow import unfollow
from src.counters_parser import LanguageChangedException
from src.filter import Filter
from src.navigation import navigate, Tabs
from src.persistent_list import PersistentList
from src.session_state import SessionState, SessionStateEncoder
from src.storage import Storage
from src.utils import *

device_id = None
sessions = PersistentList("sessions", SessionStateEncoder)


def main():
    random.seed()
    colorama.init()
    print_timeless(COLOR_HEADER + "Insomniac " + get_version() + "\n" + COLOR_ENDC)

    ok, args = _parse_arguments()
    if not ok:
        return

    global device_id
    device_id = args.device
    device = uiautomator.device if device_id is None else uiautomator.Device(device_id)

    if not check_adb_connection(is_device_id_provided=(device_id is not None)):
        return

    mode = None
    is_interact_enabled = len(args.interact) > 0
    is_unfollow_enabled = int(args.unfollow) > 0
    is_unfollow_non_followers_enabled = int(args.unfollow_non_followers) > 0
    total_enabled = int(is_interact_enabled) + int(is_unfollow_enabled) + int(is_unfollow_non_followers_enabled)
    if total_enabled == 0:
        print_timeless(COLOR_FAIL + "You have to specify one of the actions: --interact, --unfollow, "
                                    "--unfollow-non-followers" + COLOR_ENDC)
        return
    elif total_enabled > 1:
        print_timeless(COLOR_FAIL + "Running Insomniac with two or more actions is not supported yet." + COLOR_ENDC)
        return
    else:
        if is_interact_enabled:
            print("Action: interact with @" + ", @".join(str(blogger) for blogger in args.interact))
            mode = Mode.INTERACT
        elif is_unfollow_enabled:
            print("Action: unfollow " + str(args.unfollow))
            mode = Mode.UNFOLLOW
        elif is_unfollow_non_followers_enabled:
            print("Action: unfollow " + str(args.unfollow_non_followers) + " non followers")
            mode = Mode.UNFOLLOW_NON_FOLLOWERS

    profile_filter = Filter()
    on_interaction = partial(_on_interaction,
                             interactions_limit=int(args.interactions_count),
                             likes_limit=int(args.total_likes_limit))

    while True:
        session_state = SessionState()
        session_state.args = args.__dict__
        sessions.append(session_state)

        print_timeless(COLOR_WARNING + "\n-------- START: " + str(session_state.startTime) + " --------" + COLOR_ENDC)
        open_instagram(device_id)
        session_state.my_username, session_state.my_followers_count = get_my_profile_info(device)
        storage = Storage(session_state.my_username)

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        if mode == Mode.INTERACT:
            _job_handle_bloggers(device,
                                 args.interact,
                                 int(args.likes_count),
                                 int(args.follow_percentage),
                                 storage,
                                 profile_filter,
                                 on_interaction)
        elif mode == Mode.UNFOLLOW:
            _job_unfollow(device, int(args.unfollow), storage, only_non_followers=False)
        elif mode == Mode.UNFOLLOW_NON_FOLLOWERS:
            _job_unfollow(device, int(args.unfollow_non_followers), storage, only_non_followers=True)

        close_instagram(device_id)
        print_copyright(session_state.my_username)
        session_state.finishTime = datetime.now()
        print_timeless(COLOR_WARNING + "-------- FINISH: " + str(session_state.finishTime) + " --------" + COLOR_ENDC)

        if args.repeat:
            _print_report()
            repeat = int(args.repeat)
            print_timeless("")
            print("Sleep for " + str(repeat) + " minutes")
            try:
                sleep(60 * repeat)
            except KeyboardInterrupt:
                _print_report()
                sessions.persist(directory=session_state.my_username)
                sys.exit(0)
        else:
            break

    _print_report()
    sessions.persist(directory=session_state.my_username)


def _job_handle_bloggers(device, bloggers, likes_count, follow_percentage, storage, profile_filter, on_interaction):
    class State:
        def __init__(self):
            pass

        is_job_completed = False

    state = State()
    session_state = sessions[-1]

    def on_likes_limit_reached():
        state.is_job_completed = True

    on_interaction = partial(on_interaction, on_likes_limit_reached=on_likes_limit_reached)

    for blogger in bloggers:
        is_myself = blogger == session_state.my_username
        print_timeless("")
        print(COLOR_BOLD + "Handle @" + blogger + (is_myself and " (it\'s you)" or "") + COLOR_ENDC)
        on_interaction = partial(on_interaction, blogger=blogger)

        @_run_safely(device=device)
        def job():
            handle_blogger(device,
                           blogger,
                           session_state.my_username,
                           likes_count,
                           follow_percentage,
                           storage,
                           profile_filter,
                           _on_like,
                           on_interaction)
            state.is_job_completed = True

        while not state.is_job_completed:
            job()


def _job_unfollow(device, count, storage, only_non_followers):
    class State:
        def __init__(self):
            pass

        unfollowed_count = 0
        is_job_completed = False

    state = State()
    session_state = sessions[-1]

    def on_unfollow():
        state.unfollowed_count += 1
        session_state.totalUnfollowed += 1

    @_run_safely(device=device)
    def job():
        unfollow(device,
                 count - state.unfollowed_count,
                 on_unfollow,
                 storage,
                 only_non_followers,
                 session_state.my_username)
        print("Unfollowed " + str(state.unfollowed_count) + ", finish.")
        state.is_job_completed = True

    while not state.is_job_completed and state.unfollowed_count < count:
        job()


def _parse_arguments():
    parser = argparse.ArgumentParser(
        description='Instagram bot for automated Instagram interaction using Android device via ADB',
        add_help=False
    )
    parser.add_argument('--interact',
                        nargs='+',
                        help='list of usernames with whose followers you want to interact',
                        metavar=('username1', 'username2'),
                        default=[])
    parser.add_argument('--likes-count',
                        help='number of likes for each interacted user, 2 by default',
                        metavar='2',
                        default='2')
    parser.add_argument('--total-likes-limit',
                        help='limit on total amount of likes during the session, 300 by default',
                        metavar='300',
                        default='1000')
    parser.add_argument('--interactions-count',
                        help='number of interactions per each blogger, 70 by default. Only successful interactions'
                             ' count',
                        metavar='70',
                        default='70')
    parser.add_argument('--repeat',
                        help='repeat the same session again after N minutes after completion, disabled by default',
                        metavar='180')
    parser.add_argument('--follow-percentage',
                        help='follow given percentage of interacted users, 0 by default',
                        metavar='50',
                        default='0')
    parser.add_argument('--unfollow',
                        help='unfollow at most given number of users. Only users followed by this script will '
                             'be unfollowed. The order is from oldest to newest followings',
                        metavar='100',
                        default='0')
    parser.add_argument('--unfollow-non-followers',
                        help='unfollow at most given number of users, that don\'t follow you back. Only users followed '
                             'by this script will be unfollowed. The order is from oldest to newest followings',
                        metavar='100',
                        default='0')
    parser.add_argument('--device',
                        help='device identifier. Should be used only when multiple devices are connected at once',
                        metavar='2443de990e017ece')

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


def _on_interaction(blogger, succeed, followed, interactions_limit, likes_limit, on_likes_limit_reached):
    session_state = sessions[-1]
    session_state.add_interaction(blogger, succeed, followed)

    can_continue = True

    if session_state.totalLikes >= likes_limit:
        print("Reached total likes limit, finish.")
        on_likes_limit_reached()
        can_continue = False

    successful_interactions_count = session_state.get_successful_interactions_count()
    if successful_interactions_count >= interactions_limit:
        print("Made " + str(successful_interactions_count) + " successful interactions, finish.")
        can_continue = False

    return can_continue


def _print_report():
    if len(sessions) > 1:
        for index, session in enumerate(sessions):
            finish_time = session.finishTime or datetime.now()
            print_timeless("\n")
            print_timeless(COLOR_WARNING + "SESSION #" + str(index + 1) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Start time: " + str(session.startTime) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Finish time: " + str(finish_time) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Duration: " + str(finish_time - session.startTime) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total interactions: " + stringify_interactions(session.totalInteractions)
                           + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Successful interactions: "
                           + stringify_interactions(session.successfulInteractions) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total likes: " + str(session.totalLikes) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total followed: " + str(session.totalFollowed) + COLOR_ENDC)
            print_timeless(COLOR_WARNING + "Total unfollowed: " + str(session.totalUnfollowed) + COLOR_ENDC)

    print_timeless("\n")
    print_timeless(COLOR_WARNING + "TOTAL" + COLOR_ENDC)

    completed_sessions = [session for session in sessions if session.is_finished()]
    print_timeless(COLOR_WARNING + "Completed sessions: " + str(len(completed_sessions)) + COLOR_ENDC)

    duration = timedelta(0)
    for session in sessions:
        finish_time = session.finishTime or datetime.now()
        duration += finish_time - session.startTime
    print_timeless(COLOR_WARNING + "Total duration: " + str(duration) + COLOR_ENDC)

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

    print_timeless(COLOR_WARNING + "Total interactions: " + stringify_interactions(total_interactions) + COLOR_ENDC)
    print_timeless(COLOR_WARNING + "Successful interactions: " + stringify_interactions(successful_interactions)
                   + COLOR_ENDC)

    total_likes = sum(session.totalLikes for session in sessions)
    print_timeless(COLOR_WARNING + "Total likes: " + str(total_likes) + COLOR_ENDC)

    total_followed = sum(session.totalFollowed for session in sessions)
    print_timeless(COLOR_WARNING + "Total followed: " + str(total_followed) + COLOR_ENDC)

    total_unfollowed = sum(session.totalUnfollowed for session in sessions)
    print_timeless(COLOR_WARNING + "Total unfollowed: " + str(total_unfollowed) + COLOR_ENDC)


def _run_safely(device):
    def actual_decorator(func):
        def wrapper(*args, **kwargs):
            session_state = sessions[-1]
            try:
                func(*args, **kwargs)
            except KeyboardInterrupt:
                close_instagram(device_id)
                print_copyright(session_state.my_username)
                print_timeless(COLOR_WARNING + "-------- FINISH: " + str(datetime.now().time()) + " --------" +
                               COLOR_ENDC)
                _print_report()
                sessions.persist(directory=session_state.my_username)
                sys.exit(0)
            except (uiautomator.JsonRPCError, IndexError, HTTPException, timeout):
                print(COLOR_FAIL + traceback.format_exc() + COLOR_ENDC)
                take_screenshot(device)
                print("No idea what it was. Let's try again.")
                # Hack for the case when IGTV was accidentally opened
                close_instagram(device_id)
                random_sleep()
                open_instagram(device_id)
                navigate(device, Tabs.PROFILE)
            except LanguageChangedException:
                print_timeless("")
                print("Language was changed. We'll have to start from the beginning.")
                navigate(device, Tabs.PROFILE)
            except Exception as e:
                take_screenshot(device)
                close_instagram(device_id)
                _print_report()
                sessions.persist(directory=session_state.my_username)
                raise e
        return wrapper
    return actual_decorator


@unique
class Mode(Enum):
    INTERACT = 0
    UNFOLLOW = 1
    UNFOLLOW_NON_FOLLOWERS = 2


if __name__ == "__main__":
    main()
