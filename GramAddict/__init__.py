import argparse
from time import sleep
import colorama
import sys

# from http.client import HTTPException
# from socket import timeout

from GramAddict.core.device_facade import create_device
from GramAddict.core.navigation import switch_to_english
from GramAddict.core.persistent_list import PersistentList
from GramAddict.core.plugin_loader import PluginLoader
from GramAddict.core.report import print_full_report
from GramAddict.core.session_state import (
    SessionState,
    SessionStateEncoder,
)
from GramAddict.core.storage import Storage
from datetime import datetime
from GramAddict.core.utils import (
    COLOR_HEADER,
    COLOR_WARNING,
    COLOR_FAIL,
    COLOR_ENDC,
    get_version,
    check_adb_connection,
    get_instagram_version,
    open_instagram,
    close_instagram,
    screen_sleep,
    save_crash,
    get_value,
    print_timeless,
    print,
)
from GramAddict.core.views import TabBarView


# Script Initialization
print_timeless(COLOR_HEADER + "GramAddict " + get_version() + COLOR_ENDC)
colorama.init()

# Global Variables
device_id = None
plugins = PluginLoader("GramAddict.plugins").plugins
sessions = PersistentList("sessions", SessionStateEncoder)
parser = argparse.ArgumentParser(description="GramAddict Instagram Bot")


def load_plugins():
    actions = {}

    for plugin in plugins:
        if plugin.arguments:
            for arg in plugin.arguments:
                try:
                    action = arg.get("action", None)
                    if action:
                        parser.add_argument(
                            arg["arg"],
                            help=arg["help"],
                            action=arg.get("action", None),
                        )
                    else:
                        parser.add_argument(
                            arg["arg"],
                            nargs=arg["nargs"],
                            help=arg["help"],
                            metavar=arg["metavar"],
                            default=arg["default"],
                        )
                    if arg.get("operation", False):
                        actions[arg["arg"]] = plugin
                except Exception as e:
                    print_timeless(
                        f"Error while importing arguments of plugin {plugin.__class__.__name__}. Error: Missing key from arguments dictionary - {e}"
                    )
    return actions


def get_args():
    if not len(sys.argv) > 1:
        parser.print_help()
        return False

    args, unknown_args = parser.parse_known_args()

    if unknown_args:
        print(
            COLOR_FAIL
            + "Unknown arguments: "
            + ", ".join(str(arg) for arg in unknown_args)
            + COLOR_ENDC
        )
        parser.print_help()
        return False

    return args


def run():
    global device_id
    loaded = load_plugins()
    args = get_args()
    enabled = []
    if not args:
        return
    dargs = vars(args)

    for k in loaded:
        if dargs[k.replace("-", "_")[2:]] != None:
            if k == "--interact":
                print_timeless(
                    f'{COLOR_WARNING}Warning: Using legacy argument "--interact". Please switch to new arguments as this will be deprecated in the near future.{COLOR_ENDC}'
                )
                if "#" in args.interact[0]:
                    enabled.append("--hashtag-likers")
                    args.hashtag_likers = args.interact
                else:
                    enabled.append("--blogger-followers")
                    args.blogger_followers = args.interact
            else:
                enabled.append(k)
    enabled = list(dict.fromkeys(enabled))

    if len(enabled) < 1:
        print_timeless(
            COLOR_FAIL
            + "You have to specify one of the actions: "
            + ", ".join(loaded)
            + COLOR_ENDC
        )
        return
    if len(enabled) > 1:
        print_timeless(
            COLOR_FAIL
            + "Running GramAddict with two or more actions is not supported yet."
            + COLOR_ENDC
        )
        return

    session_state = SessionState()
    session_state.args = args.__dict__
    sessions.append(session_state)

    device_id = args.device
    if not check_adb_connection(is_device_id_provided=(device_id is not None)):
        return

    print("Instagram version: " + get_instagram_version())
    device = create_device(device_id)
    if device is None:
        return
    while True:
        print_timeless(
            COLOR_WARNING
            + "\n-------- START: "
            + str(session_state.startTime)
            + " --------"
            + COLOR_ENDC
        )

        if args.screen_sleep:
            screen_sleep(device_id, "on")  # Turn on the device screen
        open_instagram(device_id)

        try:
            profileView = TabBarView(device).navigateToProfile()
            (
                session_state.my_username,
                session_state.my_followers_count,
                session_state.my_following_count,
            ) = profileView.getProfileInfo()
        except Exception as e:
            print(f"Exception: {e}")
            save_crash(device)
            switch_to_english(device)
            # Try again on the correct language
            profileView = TabBarView(device).navigateToProfile()
            (
                session_state.my_username,
                session_state.my_followers_count,
                session_state.my_following_count,
            ) = profileView.getProfileInfo()

        if (
            not session_state.my_username
            or not session_state.my_followers_count
            or not session_state.my_following_count
        ):
            print(COLOR_FAIL + "Could not get profile info" + COLOR_ENDC)
            exit(1)

        report_string = ""
        report_string += "Hello, @" + session_state.my_username + "! "
        report_string += (
            "You have " + str(session_state.my_followers_count) + " followers"
        )
        report_string += " and " + str(session_state.my_following_count) + " followings"
        report_string += " so far."
        print(report_string)

        storage = Storage(session_state.my_username)

        loaded[enabled[0]].run(device, device_id, args, enabled, storage, sessions)

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
