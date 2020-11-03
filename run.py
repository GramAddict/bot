import argparse
import random
import sys
import traceback
from enum import Enum, unique
from functools import partial
from http.client import HTTPException
from socket import timeout

import colorama

from src.action_get_my_profile_info import get_my_profile_info
from src.action_handle_blogger import handle_blogger
from src.action_unfollow import unfollow, UnfollowRestriction
from src.analytics import generate_analytics
from src.counters_parser import LanguageChangedException
from src.device_facade import create_device, DeviceFacade
from src.filter import Filter
from src.navigation import navigate, Tabs
from src.persistent_list import PersistentList
from src.report import print_full_report, print_short_report
from src.session_state import SessionState, SessionStateEncoder
from src.storage import Storage
from src.utils import *

device_id = None
sessions = PersistentList("sessions", SessionStateEncoder)


def main():
    random.seed()
    colorama.init()
    print_timeless(COLOR_HEADER + "GramAddict " + get_version() + "\n" + COLOR_ENDC)

    ok, args = _parse_arguments()
    if not ok:
        return

    if args.analytics:
        generate_analytics(args.analytics)
        return

    global device_id
    device_id = args.device
    if not check_adb_connection(is_device_id_provided=(device_id is not None)):
        return

    print("Instagram version: " + get_instagram_version())

    args.old = False
    device = create_device(args.old, device_id)
    if device is None:
        return

    mode = None
    is_interact_enabled = len(args.interact) > 0
    is_unfollow_enabled = args.unfollow is not None
    is_unfollow_non_followers_enabled = args.unfollow_non_followers is not None
    is_unfollow_any_enabled = args.unfollow_any is not None
    is_analytics_enabled = args.analytics is not None
    total_enabled = (
        int(is_interact_enabled)
        + int(is_unfollow_enabled)
        + int(is_unfollow_non_followers_enabled)
        + int(is_unfollow_any_enabled)
        + int(is_analytics_enabled)
    )
    if total_enabled == 0:
        print_timeless(
            COLOR_FAIL
            + "You have to specify one of the actions: --interact, --unfollow, "
            "--unfollow-non-followers, --unfollow-any, --analytics" + COLOR_ENDC + COLOR_ENDC
        )
        return
    elif total_enabled > 1:
        print_timeless(
            COLOR_FAIL
            + "Running GramAddict with two or more actions is not supported yet."
            + COLOR_ENDC
        )
        return
    else:
        if is_interact_enabled:
            print(
                "Action: interact with @"
                + ", @".join(str(blogger) for blogger in args.interact)
            )
            mode = Mode.INTERACT
        elif is_unfollow_enabled:
            print("Action: unfollow " + str(args.unfollow))
            mode = Mode.UNFOLLOW
        elif is_unfollow_non_followers_enabled:
            print(
                "Action: unfollow "
                + str(args.unfollow_non_followers)
                + " non followers"
            )
            mode = Mode.UNFOLLOW_NON_FOLLOWERS
        elif is_unfollow_any_enabled:
            print("Action: unfollow any " + str(args.unfollow_any))
            mode = Mode.UNFOLLOW_ANY
        elif is_analytics_enabled:
            print("Action: generate analytics report " + str(args.unfollow_any))
            mode = Mode.UNFOLLOW_ANY

    profile_filter = Filter()

    while True:
        session_state = SessionState()
        session_state.args = args.__dict__
        sessions.append(session_state)

        if args.screen_sleep:
            screen_sleep(device_id, "on")  # Turn on the device screen

        print_timeless(
            COLOR_WARNING
            + "\n-------- START: "
            + str(session_state.startTime)
            + " --------"
            + COLOR_ENDC
        )
        open_instagram(device_id)
        (
            session_state.my_username,
            session_state.my_followers_count,
            session_state.my_following_count,
        ) = get_my_profile_info(device)
        storage = Storage(session_state.my_username)

        # IMPORTANT: in each job we assume being on the top of the Profile tab already
        if mode == Mode.INTERACT:
            on_interaction = partial(
                _on_interaction, likes_limit=int(args.total_likes_limit)
            )

            _job_handle_bloggers(
                device,
                args.interact,
                args.likes_count,
                int(args.follow_percentage),
                int(args.follow_limit) if args.follow_limit else None,
                storage,
                profile_filter,
                args.interactions_count,
                on_interaction,
            )
        elif mode == Mode.UNFOLLOW:
            print_timeless("")
            _job_unfollow(
                device,
                get_value(args.unfollow, "Unfollow {}", 100),
                storage,
                int(args.min_following),
                UnfollowRestriction.FOLLOWED_BY_SCRIPT,
            )
        elif mode == Mode.UNFOLLOW_NON_FOLLOWERS:
            print_timeless("")
            _job_unfollow(
                device,
                get_value(
                    args.unfollow_non_followers, "Unfollow {} non followers", 100
                ),
                storage,
                int(args.min_following),
                UnfollowRestriction.FOLLOWED_BY_SCRIPT_NON_FOLLOWERS,
            )
        elif mode == Mode.UNFOLLOW_ANY:
            print_timeless("")
            _job_unfollow(
                device,
                get_value(args.unfollow_any, "Unfollow {} any", 100),
                storage,
                int(args.min_following),
                UnfollowRestriction.ANY,
            )
        elif mode == Mode.REMOVE_MASS_FOLLOWERS:
            _job_remove_mass_followers(
                device,
                int(args.remove_mass_followers),
                int(args.max_following),
                storage,
            )

        close_instagram(device_id)
        session_state.finishTime = datetime.now()

        if args.screen_sleep:
            screen_sleep(device_id, "off")  # Turn off the device screen

        print_timeless(
            COLOR_WARNING
            + "-------- FINISH: "
            + str(session_state.finishTime)
            + " --------"
            + COLOR_ENDC
        )

        if args.repeat:
            print_full_report(sessions)
            print_timeless("")
            repeat = get_value(args.repeat, "Sleep for {} minutes", 180)
            try:
                sleep(60 * repeat)
            except KeyboardInterrupt:
                print_full_report(sessions)
                sessions.persist(directory=session_state.my_username)
                sys.exit(0)
        else:
            break

    print_full_report(sessions)
    sessions.persist(directory=session_state.my_username)


def _job_handle_bloggers(
    device,
    bloggers,
    likes_count,
    follow_percentage,
    follow_limit,
    storage,
    profile_filter,
    interactions_count,
    on_interaction,
):
    class State:
        def __init__(self):
            pass

        is_job_completed = False
        is_likes_limit_reached = False

    state = None
    session_state = sessions[-1]

    def on_likes_limit_reached():
        state.is_likes_limit_reached = True

    on_interaction = partial(
        on_interaction, on_likes_limit_reached=on_likes_limit_reached
    )

    if len(sessions) > 1:
        random.shuffle(bloggers)

    for blogger in bloggers:
        state = State()
        is_myself = blogger == session_state.my_username
        print_timeless("")
        print(
            COLOR_BOLD
            + "Handle @"
            + blogger
            + (is_myself and " (it's you)" or "")
            + COLOR_ENDC
        )
        on_interaction = partial(
            on_interaction,
            blogger=blogger,
            interactions_limit=get_value(
                interactions_count, "Interactions count: {}", 70
            ),
        )

        @_run_safely(device=device)
        def job():
            handle_blogger(
                device,
                blogger,
                session_state,
                likes_count,
                follow_percentage,
                follow_limit,
                storage,
                profile_filter,
                _on_like,
                on_interaction,
            )
            state.is_job_completed = True

        while not state.is_job_completed and not state.is_likes_limit_reached:
            job()

        if state.is_likes_limit_reached:
            break


def _job_unfollow(device, count, storage, min_following, unfollow_restriction):
    class State:
        def __init__(self):
            pass

        unfollowed_count = 0
        is_job_completed = False

    state = State()
    session_state = sessions[-1]
    new_count = min(count, session_state.my_following_count - min_following)
    if new_count <= 0:
        print(
            "You want to unfollow "
            + str(count)
            + ", you have "
            + str(session_state.my_following_count)
            + " followings, min following is "
            + str(min_following)
            + ". Finish."
        )
        return

    def on_unfollow():
        state.unfollowed_count += 1
        session_state.totalUnfollowed += 1

    @_run_safely(device=device)
    def job():
        unfollow(
            device,
            new_count - state.unfollowed_count,
            on_unfollow,
            storage,
            unfollow_restriction,
            session_state.my_username,
        )
        print("Unfollowed " + str(state.unfollowed_count) + ", finish.")
        state.is_job_completed = True

    while not state.is_job_completed and state.unfollowed_count < new_count:
        job()


def _parse_arguments():
    parser = argparse.ArgumentParser(
        description="Instagram bot for automated Instagram interaction using Android device via ADB",
        add_help=False,
    )
    parser.add_argument(
        "--interact",
        nargs="+",
        help="list of usernames with whose followers you want to interact",
        metavar=("username1", "username2"),
        default=[],
    )
    parser.add_argument(
        "--likes-count",
        help="number of likes for each interacted user, 2 by default. It can be a number (e.g. 2) or "
        "a range (e.g. 2-4)",
        metavar="2-4",
        default="2",
    )
    parser.add_argument(
        "--total-likes-limit",
        help="limit on total amount of likes during the session, 300 by default",
        metavar="300",
        default="1000",
    )
    parser.add_argument(
        "--interactions-count",
        help="number of interactions per each blogger, 70 by default. It can be a number (e.g. 70) or "
        "a range (e.g. 60-80). Only successful interactions count",
        metavar="60-80",
        default="70",
    )
    parser.add_argument(
        "--repeat",
        help="repeat the same session again after N minutes after completion, disabled by default. "
        "It can be a number of minutes (e.g. 180) or a range (e.g. 120-180)",
        metavar="120-180",
    )
    parser.add_argument(
        "--follow-percentage",
        help="follow given percentage of interacted users, 0 by default",
        metavar="50",
        default="0",
    )
    parser.add_argument(
        "--follow-limit",
        help="limit on amount of follows during interaction with each one user's followers, "
        "disabled by default",
        metavar="50",
    )
    parser.add_argument(
        "--unfollow",
        help="unfollow at most given number of users. Only users followed by this script will "
        "be unfollowed. The order is from oldest to newest followings. "
        "It can be a number (e.g. 100) or a range (e.g. 100-200)",
        metavar="100-200",
    )
    parser.add_argument(
        "--unfollow-non-followers",
        help="unfollow at most given number of users, that don't follow you back. Only users followed "
        "by this script will be unfollowed. The order is from oldest to newest followings. "
        "It can be a number (e.g. 100) or a range (e.g. 100-200)",
        metavar="100-200",
    )
    parser.add_argument(
        "--unfollow-any",
        help="unfollow at most given number of users. The order is from oldest to newest followings. "
        "It can be a number (e.g. 100) or a range (e.g. 100-200)",
        metavar="100-200",
    )
    parser.add_argument(
        "--min-following",
        help="minimum amount of followings, after reaching this amount unfollow stops",
        metavar="100",
        default=0,
    )
    parser.add_argument(
        "--device",
        help="device identifier. Should be used only when multiple devices are connected at once",
        metavar="2443de990e017ece",
    )
    parser.add_argument(
        "--screen-sleep",
        help="take care of your device screen by turning it off during sleeping time",
        action="store_true",
    )
    parser.add_argument("--max-following", help=argparse.SUPPRESS, default=1000)
    parser.add_argument(
        "--analytics",
        help="generate a PDF analytics report of specified username session data.",
        metavar="username",
    )

    if not len(sys.argv) > 1:
        parser.print_help()
        return False, None

    args, unknown_args = parser.parse_known_args()

    if unknown_args:
        print(
            COLOR_FAIL
            + "Unknown arguments: "
            + ", ".join(str(arg) for arg in unknown_args)
            + COLOR_ENDC
        )
        parser.print_help()
        return False, None

    return True, args


def _on_like():
    session_state = sessions[-1]
    session_state.totalLikes += 1


def _on_interaction(
    blogger, succeed, followed, interactions_limit, likes_limit, on_likes_limit_reached
):
    session_state = sessions[-1]
    session_state.add_interaction(blogger, succeed, followed)

    can_continue = True

    if session_state.totalLikes >= likes_limit:
        print("Reached total likes limit, finish.")
        on_likes_limit_reached()
        can_continue = False

    successful_interactions_count = session_state.successfulInteractions.get(blogger)
    if (
        successful_interactions_count
        and successful_interactions_count >= interactions_limit
    ):
        print(
            "Made "
            + str(successful_interactions_count)
            + " successful interactions, finish."
        )
        can_continue = False

    if can_continue and succeed:
        print_short_report(blogger, session_state)

    return can_continue


def _run_safely(device):
    def actual_decorator(func):
        def wrapper(*args, **kwargs):
            session_state = sessions[-1]
            try:
                func(*args, **kwargs)
            except KeyboardInterrupt:
                close_instagram(device_id)
                print_timeless(
                    COLOR_WARNING
                    + "-------- FINISH: "
                    + str(datetime.now().time())
                    + " --------"
                    + COLOR_ENDC
                )
                print_full_report(sessions)
                sessions.persist(directory=session_state.my_username)
                sys.exit(0)
            except (DeviceFacade.JsonRpcError, IndexError, HTTPException, timeout):
                print(COLOR_FAIL + traceback.format_exc() + COLOR_ENDC)
                save_crash(device)
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
                save_crash(device)
                close_instagram(device_id)
                print_full_report(sessions)
                sessions.persist(directory=session_state.my_username)
                raise e

        return wrapper

    return actual_decorator


@unique
class Mode(Enum):
    INTERACT = 0
    UNFOLLOW = 1
    UNFOLLOW_NON_FOLLOWERS = 2
    UNFOLLOW_ANY = 3


if __name__ == "__main__":
    main()
