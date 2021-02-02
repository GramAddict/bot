import logging, os
from datetime import datetime, timedelta
from sys import exit
from time import sleep
import random

from colorama import Fore, Style

from GramAddict.core.config import Config
from GramAddict.core.device_facade import create_device
from GramAddict.core.filter import load_config as load_filter
from GramAddict.core.interaction import load_config as load_interaction
from GramAddict.core.log import (
    configure_logger,
    update_log_file_name,
    is_log_file_updated,
)
from GramAddict.core.navigation import switch_to_english
from GramAddict.core.persistent_list import PersistentList
from GramAddict.core.report import print_full_report
from GramAddict.core.session_state import SessionState, SessionStateEncoder
from GramAddict.core.storage import Storage
from GramAddict.core.utils import (
    check_adb_connection,
    close_instagram,
    get_instagram_version,
    get_value,
    kill_atx_agent,
    load_config as load_utils,
    open_instagram,
    random_sleep,
    save_crash,
    update_available,
)
from GramAddict.core.views import (
    AccountView,
    ProfileView,
    TabBarView,
    load_config as load_views,
)
from GramAddict.version import __version__

# Pre-Load Config
configs = Config(first_run=True)

# Logging initialization
configure_logger(configs.debug, configs.username)
logger = logging.getLogger(__name__)
if update_available():
    logger.warn(
        "NOTICE: There is an update available. Please update so that you can get all the latest features and bugfixes. https://github.com/GramAddict/bot"
    )
logger.info(
    f"GramAddict {__version__}", extra={"color": f"{Style.BRIGHT}{Fore.MAGENTA}"}
)

# Global Variables
sessions = PersistentList("sessions", SessionStateEncoder)

# Load Config
configs.load_plugins()
configs.parse_args()


def run():
    # Some plugins need config values without being passed
    # through. Because we do a weird config/argparse hybrid,
    # we need to load the configs in a weird way
    load_filter(configs)
    load_interaction(configs)
    load_utils(configs)
    load_views(configs)

    if not configs.args or not check_adb_connection():
        return

    if len(configs.enabled) < 1:
        logger.error(
            "You have to specify one of the actions: " + ", ".join(configs.actions)
        )
        return

    logger.info("Instagram version: " + get_instagram_version())
    device = create_device(configs.device_id, configs.args.uia_version)

    if device is None:
        return

    while True:
        session_state = SessionState(configs)
        sessions.append(session_state)

        device.wake_up()

        logger.info(
            "-------- START: "
            + str(session_state.startTime.strftime("%H:%M:%S - %Y/%m/%d"))
            + " --------",
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
                exit(0)

        logger.info("Device screen on and unlocked.")

        open_instagram(device, configs.args.screen_record)

        try:
            random_sleep()
            profileView = TabBarView(device).navigateToProfile()
            random_sleep()
            if configs.args.username is not None:
                success = AccountView(device).changeToUsername(configs.args.username)
                if not success:
                    logger.error(
                        f"Not able to change to {configs.args.username}, abort!"
                    )
                    device.back()
                    break

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
            session_state.my_username is None
            or session_state.my_followers_count is None
            or session_state.my_following_count is None
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
        if configs.args.shuffle_jobs:
            jobs_list = random.sample(configs.enabled, len(configs.enabled))
        else:
            jobs_list = configs.enabled
        for plugin in jobs_list:
            if not session_state.check_limit(
                configs.args, limit_type=session_state.Limit.ALL, output=False
            ):
                logger.info(f"Current job: {plugin}", extra={"color": f"{Fore.BLUE}"})
                if ProfileView(device).getUsername() != session_state.my_username:
                    logger.debug("Not in your main profile.")
                    TabBarView(device).navigateToProfile()
                configs.actions[plugin].run(device, configs, storage, sessions, plugin)

            else:
                logger.info(
                    "Successful or Total Interactions limit reached. Ending session."
                )
                break

        close_instagram(device, configs.args.screen_record)
        session_state.finishTime = datetime.now()

        if configs.args.screen_sleep:
            device.screen_off()
            logger.info("Screen turned off for sleeping time")

        kill_atx_agent(device)

        logger.info(
            "-------- FINISH: "
            + str(session_state.finishTime.strftime("%H:%M:%S - %Y/%m/%d"))
            + " --------",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )

        if configs.args.repeat:
            print_full_report(sessions)
            repeat = get_value(configs.args.repeat, "Sleep for {} minutes", 180)
            logger.info(
                f'Will start again at {(datetime.now()+ timedelta(minutes=repeat)).strftime("%H:%M:%S (%Y/%m/%d)")}'
            )
            try:
                sleep(60 * repeat)
            except KeyboardInterrupt:
                print_full_report(sessions)
                sessions.persist(directory=session_state.my_username)
                exit(0)
        else:
            break

    print_full_report(sessions)
    sessions.persist(directory=session_state.my_username)
