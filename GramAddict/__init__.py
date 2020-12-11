import configargparse
import logging
import sys
import yaml
from datetime import datetime
from time import sleep

from colorama import Fore, Style

from GramAddict.core.device_facade import DeviceFacade, create_device
from GramAddict.core.log import (
    configure_logger,
    update_log_file_name,
    is_log_file_updated,
)
from GramAddict.core.navigation import switch_to_english
from GramAddict.core.persistent_list import PersistentList
from GramAddict.core.plugin_loader import PluginLoader
from GramAddict.core.report import print_full_report
from GramAddict.core.resources import load as load_resources
from GramAddict.core.session_state import SessionState, SessionStateEncoder
from GramAddict.core.storage import Storage
from GramAddict.core.utils import (
    check_adb_connection,
    close_instagram,
    get_instagram_version,
    get_value,
    load as load_utils,
    open_instagram,
    random_sleep,
    save_crash,
    update_available,
)
from GramAddict.core.views import TabBarView
from GramAddict.version import __version__

# Pre-Load Config
config, config_list = {}, []
username = False
args = sys.argv
if "--config" in args:
    try:
        file_name = args[args.index("--config") + 1]
        with open(file_name) as fin:
            # preserve order of yaml
            config_list = [line.strip() for line in fin]
            fin.seek(0)
            # pre-load config for debug and username
            config = yaml.safe_load(fin)
    except IndexError:
        print("Please provide a filename with your --config argument.")
        exit(0)

    username = config.get("username", False)
    debug = config.get("debug", False)

debug = True if "--debug" in args else False
if "--username" in args:
    try:
        username = args[args.index("--username") + 1]
    except IndexError:
        print("Please provide a username with your --username argument.")
        exit(0)

# Logging initialization
configure_logger(debug, username)
logger = logging.getLogger(__name__)
if update_available():
    logger.warn(
        "NOTICE: There is an update available. Please update so that you can get all the latest features and bugfixes. https://github.com/GramAddict/bot"
    )
logger.info(
    f"GramAddict {__version__}", extra={"color": f"{Style.BRIGHT}{Fore.MAGENTA}"}
)

# Configure ArgParse
parser = configargparse.ArgumentParser(description="GramAddict Instagram Bot")
parser.add(
    "-c", "--config", required=False, is_config_file=True, help="config file path"
)

# Global Variables
device_id = None
plugins = PluginLoader("GramAddict.plugins").plugins
sessions = PersistentList("sessions", SessionStateEncoder)


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
                        actions[arg["arg"][2:]] = plugin
                except Exception as e:
                    logger.error(
                        f"Error while importing arguments of plugin {plugin.__class__.__name__}. Error: Missing key from arguments dictionary - {e}"
                    )
    return actions


def get_args(loaded):
    def _is_legacy_arg(arg):
        if arg == "interact" or arg == "hashtag-likers":
            logger.warn(
                "You are using a legacy argument, please refer to https://docs.gramaddict.org."
            )
            return True
        return False

    enabled = []
    logger.debug(f"Arguments used: {' '.join(sys.argv[1:])}")
    if config:
        logger.debug(f"Config used: {config}")
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

    if config_list:
        for item in config_list:
            item = item.split(":")[0]
            if (
                item in loaded
                and getattr(args, item.replace("-", "_")) != None
                and not _is_legacy_arg(item)
            ):
                enabled.append(item)
    else:
        for item in sys.argv:
            nitem = item[2:]
            if item.startswith("--"):
                if (
                    nitem in loaded
                    and getattr(args, nitem.replace("-", "_")) != None
                    and not _is_legacy_arg(nitem)
                ):
                    enabled.append(nitem)
    return args, enabled


def run():
    global device_id
    loaded = load_plugins()
    args, enabled = get_args(loaded)
    if not args:
        return
    load_resources(args)
    load_utils(args)

    if len(enabled) < 1:
        logger.error("You have to specify one of the actions: " + ", ".join(loaded))
        return

    device_id = args.device
    if not check_adb_connection(is_device_id_provided=(device_id is not None)):
        return
    logger.info("Instagram version: " + get_instagram_version(device_id))
    device = create_device(device_id, args.uia_version)

    if device is None:
        return

    while True:
        session_state = SessionState()
        session_state.args = args.__dict__
        sessions.append(session_state)

        device.wake_up()

        logger.info(
            "-------- START: " + str(session_state.startTime) + " --------",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )

        if not device.get_info()["screenOn"]:
            device.press_power()
        if device.is_screen_locked():
            device.unlock()
            if device.is_screen_locked():
                logger.error(
                    "Can't unlock your screen. There may be a passcode on it. If you would like your screen to be turned on and unlocked automatically, please remove the passcode."
                )
                sys.exit()

        logger.info("Device screen on and unlocked.")

        open_instagram(device_id)

        try:
            profileView = TabBarView(device).navigateToProfile()
            random_sleep()
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
            random_sleep()
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
                f"Username: {session_state.my_username}, Followers: {session_state.my_followers_count}, Following: {session_state.my_following_count}"
            )
            save_crash(device)
            exit(1)

        if not is_log_file_updated():
            try:
                update_log_file_name(session_state.my_username)
            except Exception as e:
                logger.error(
                    f"Failed to update log file name. Will continue anyway. {e}"
                )
                save_crash(device)

        report_string = f"Hello, @{session_state.my_username}! You have {session_state.my_followers_count} followers and {session_state.my_following_count} followings so far."

        logger.info(report_string, extra={"color": f"{Style.BRIGHT}"})

        storage = Storage(session_state.my_username)
        for plugin in enabled:
            if not session_state.check_limit(
                args, limit_type=session_state.Limit.ALL, output=False
            ):
                logger.info(f"Running plugin: {plugin}")
                loaded[plugin].run(
                    device, device_id, args, enabled, storage, sessions, plugin
                )
            else:
                logger.info(
                    "Successful or Total Interactions limit reached. Ending session."
                )
                break

        close_instagram(device_id)
        session_state.finishTime = datetime.now()

        if args.screen_sleep:
            device.screen_off()
            logger.info("Screen turned off for sleeping time")

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
