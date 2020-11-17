import argparse
import logging
import sys
from datetime import datetime
from time import sleep

from colorama import Fore, Style

from GramAddict.core.device_facade import create_device
from GramAddict.core.log import configure_logger
from GramAddict.core.navigation import switch_to_english
from GramAddict.core.persistent_list import PersistentList
from GramAddict.core.plugin_loader import PluginLoader
from GramAddict.core.report import print_full_report
from GramAddict.core.session_state import SessionState, SessionStateEncoder
from GramAddict.core.storage import Storage
from GramAddict.core.utils import (
    check_adb_connection,
    close_instagram,
    get_instagram_version,
    get_value,
    get_version,
    open_instagram,
    save_crash,
    screen_sleep,
)
from GramAddict.core.views import TabBarView

# Logging initialization
configure_logger()
logger = logging.getLogger(__name__)
logger.info(
    "GramAddict " + get_version(), extra={"color": f"{Style.BRIGHT}{Fore.MAGENTA}"}
)

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
                            arg["arg"], help=arg["help"], action=arg.get("action", None)
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
                    logger.error(
                        f"Error while importing arguments of plugin {plugin.__class__.__name__}. Error: Missing key from arguments dictionary - {e}"
                    )
    return actions


def get_args():
    logger.info(f"Arguments used: {' '.join(sys.argv[1:])}")
    if not len(sys.argv) > 1:
        parser.print_help()
        return False

    args, unknown_args = parser.parse_known_args()

    if unknown_args:
        logger.error(
            "Unknown arguments: " + ", ".join(str(arg) for arg in unknown_args)
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
                logger.warn(
                    'Using legacy argument "--interact". Please switch to new arguments as this will be deprecated in the near future.'
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
        logger.error("You have to specify one of the actions: " + ", ".join(loaded))
        return
    if len(enabled) > 1:
        logger.error(
            "Running GramAddict with two or more actions is not supported yet."
        )
        return

    session_state = SessionState()
    session_state.args = args.__dict__
    sessions.append(session_state)

    device_id = args.device
    if not check_adb_connection(is_device_id_provided=(device_id is not None)):
        return
    logger.info("Instagram version: " + get_instagram_version())
    device = create_device(device_id)
    if device is None:
        return
    while True:
        logger.info(
            "-------- START: " + str(session_state.startTime) + " --------",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
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
            logger.error(f"Exception: {e}")
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
            session_state.my_username == None
            or session_state.my_followers_count == None
            or session_state.my_following_count == None
        ):
            logger.critical(
                "Could not get one of the following from your profile: username, # of followers, # of followings. This is typically due to a soft ban. Review the crash screenshot to see if this is the case."
            )
            logger.critical(
                f"Username: {getattr(session_state,'my_username')}, Followers: {getattr(session_state,'my_followers_count')}, Following: {getattr(session_state,'my_following_count')}"
            )
            save_crash(device)
            exit(1)

        username = session_state.my_username
        followers = session_state.my_followers_count
        following = session_state.my_following_count
        report_string = f"Hello, @{username}! You have {followers} followers and {following} followings so far."
        logger.info(report_string, extra={"color": f"{Style.BRIGHT}"})

        storage = Storage(session_state.my_username)

        loaded[enabled[0]].run(device, device_id, args, enabled, storage, sessions)

        close_instagram(device_id)
        session_state.finishTime = datetime.now()

        if args.screen_sleep:
            screen_sleep(device_id, "off")  # Turn off the device screen

        logger.info(
            "-------- FINISH: " + str(session_state.finishTime) + " --------",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )

        if args.repeat:
            print_full_report(sessions)
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
