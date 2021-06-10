from GramAddict.core.navigation import check_if_english
import logging
from datetime import datetime, timedelta
from sys import exit
from time import sleep
import random

from colorama import Fore, Style

from GramAddict.core.config import Config
from GramAddict.core.device_facade import create_device, get_device_info
from GramAddict.core.filter import load_config as load_filter
from GramAddict.core.interaction import load_config as load_interaction
from GramAddict.core.log import (
    configure_logger,
    update_log_file_name,
    is_log_file_updated,
)
from GramAddict.core.persistent_list import PersistentList
from GramAddict.core.report import print_full_report
from GramAddict.core.session_state import SessionState, SessionStateEncoder
from GramAddict.core.storage import Storage
from GramAddict.core.utils import (
    check_adb_connection,
    close_instagram,
    config_examples,
    get_instagram_version,
    get_value,
    kill_atx_agent,
    load_config as load_utils,
    move_usernames_to_accounts,
    open_instagram,
    save_crash,
    set_time_delta,
    stop_bot,
    update_available,
    wait_for_next_session,
)
from GramAddict.core.views import (
    AccountView,
    ProfileView,
    SearchView,
    TabBarView,
    load_config as load_views,
)
from GramAddict.version import __version__

# Pre-Load Config
configs = Config(first_run=True)

# Logging initialization
configure_logger(configs.debug, configs.username)
logger = logging.getLogger(__name__)
if "--config" not in configs.args:
    logger.info(
        "We strongly recommend to use a config.yml file. Follow these links for more details: https://docs.gramaddict.org/#/configuration and https://github.com/GramAddict/bot/tree/master/config-examples",
        extra={"color": f"{Fore.GREEN}{Style.BRIGHT}"},
    )
    sleep(3)

# Config-example hint
config_examples()

# Check for updates
is_update, version = update_available()
if is_update:
    logger.warning("NEW VERSION FOUND!")
    logger.warning(
        f"Version {version} has been released! Please update so that you can get all the latest features and bugfixes. https://github.com/GramAddict/bot"
    )
    logger.warning("HOW TO UPDATE:")
    logger.warning("If you installed with pip: pip3 install GramAddict -U")
    logger.warning("If you installed with git: git pull")
    sleep(5)
else:
    logger.info("Bot is updated.", extra={"color": f"{Style.BRIGHT}"})
logger.info(
    f"GramAddict v.{__version__}", extra={"color": f"{Style.BRIGHT}{Fore.MAGENTA}"}
)

# Move username folders to a main directory -> accounts
move_usernames_to_accounts()

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
    device = create_device(configs.device_id)
    session_state = None
    while True:
        set_time_delta(configs.args)
        inside_working_hours, time_left = SessionState.inside_working_hours(
            configs.args.working_hours, configs.args.time_delta_session
        )
        if not inside_working_hours:
            wait_for_next_session(
                time_left, session_state, sessions, device, configs.args.screen_record
            )
        get_device_info(device)
        session_state = SessionState(configs)
        session_state.set_limits_session(configs.args)
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
        if open_instagram(device, configs.args.screen_record, configs.args.close_apps):
            try:
                tested_ig_version = "190.0.0.36.119"
                running_ig_version = get_instagram_version()
                running_ig_version_splitted = running_ig_version.split(".")
                last_ig_version_tested = tested_ig_version.split(".")
                logger.info(f"Instagram version: {running_ig_version}")
                for n in range(len(running_ig_version_splitted)):
                    if int(running_ig_version_splitted[n]) > int(
                        last_ig_version_tested[n]
                    ):
                        logger.info(
                            f"You have a newer version of IG then the one we tested! (Tested version: {tested_ig_version})",
                            extra={"color": f"{Style.BRIGHT}"},
                        )
                        break
                    else:
                        if int(running_ig_version_splitted[n]) == int(
                            last_ig_version_tested[n]
                        ):
                            continue
                        break
            except Exception as e:
                logger.error(f"Error retrieving the IG version. Exception: {e}")

            SearchView(device)._close_keyboard()
        else:
            break
        try:
            profileView = check_if_english(device)
            if configs.args.username is not None:
                success = AccountView(device).changeToUsername(configs.args.username)
                if not success:
                    logger.error(
                        f"Not able to change to {configs.args.username}, abort!"
                    )
                    save_crash(device)
                    device.back()
                    break

            (
                session_state.my_username,
                session_state.my_posts_count,
                session_state.my_followers_count,
                session_state.my_following_count,
            ) = profileView.getProfileInfo()
        except Exception as e:
            logger.error(f"Exception: {e}")
            save_crash(device)
            break

        if (
            session_state.my_username is None
            or session_state.my_posts_count is None
            or session_state.my_followers_count is None
            or session_state.my_following_count is None
        ):
            logger.critical(
                "Could not get one of the following from your profile: username, # of posts, # of followers, # of followings. This is typically due to a soft ban. Review the crash screenshot to see if this is the case."
            )
            logger.critical(
                f"Username: {session_state.my_username}, Posts: {session_state.my_posts_count}, Followers: {session_state.my_followers_count}, Following: {session_state.my_following_count}"
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
        AccountView(device).refresh_account()
        report_string = f"Hello, @{session_state.my_username}! You have {session_state.my_followers_count} followers and {session_state.my_following_count} followings so far."

        logger.info(report_string, extra={"color": f"{Style.BRIGHT}"})

        storage = Storage(session_state.my_username)
        if configs.args.shuffle_jobs:
            jobs_list = random.sample(configs.enabled, len(configs.enabled))
        else:
            jobs_list = configs.enabled
        analytics_at_end = False
        telegram_reports_at_end = False
        for job in jobs_list:
            if job == "analytics":
                jobs_list.remove(job)
                if configs.args.analytics:
                    analytics_at_end = True
            if job == "telegram-reports":
                jobs_list.remove(job)
                if configs.args.telegram_reports:
                    telegram_reports_at_end = True
        for plugin in jobs_list:
            inside_working_hours, time_left = SessionState.inside_working_hours(
                configs.args.working_hours, configs.args.time_delta_session
            )
            if not inside_working_hours:
                logger.info(
                    "Outside of working hours. Ending session.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                break
            if not session_state.check_limit(
                configs.args, limit_type=session_state.Limit.ALL, output=True
            ):
                logger.info(
                    f"Current job: {plugin}",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
                if configs.args.scrape_to_file is not None:
                    logger.warning("You're in scraping mode!")
                if ProfileView(device).getUsername() != session_state.my_username:
                    logger.debug("Not in your main profile.")
                    TabBarView(device).navigateToProfile()
                configs.actions[plugin].run(device, configs, storage, sessions, plugin)

            else:
                logger.info(
                    "At last one of these limits has been reached: interactions/successful/follower/likes or scraped. Ending session.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                break
        close_instagram(device, configs.args.screen_record)
        session_state.finishTime = datetime.now()

        if configs.args.screen_sleep:
            device.screen_off()
            logger.info("Screen turned off for sleeping time.")

        kill_atx_agent(device)

        # save the session in sessions.json
        sessions.persist(directory=session_state.my_username)

        # print reports
        if analytics_at_end:
            configs.actions["analytics"].run(
                device, configs, storage, sessions, "analytics"
            )
        if telegram_reports_at_end:
            configs.actions["telegram-reports"].run(
                device, configs, storage, sessions, "telegram-reports"
            )

        logger.info(
            "-------- FINISH: "
            + str(session_state.finishTime.strftime("%H:%M:%S - %Y/%m/%d"))
            + " --------",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )

        if configs.args.repeat:
            print_full_report(sessions, configs.args.scrape_to_file)
            inside_working_hours, time_left = SessionState.inside_working_hours(
                configs.args.working_hours, configs.args.time_delta_session
            )
            if inside_working_hours:
                time_left = (
                    get_value(configs.args.repeat, "Sleep for {} minutes", 180) * 60
                )
                logger.info(
                    f'Will start again at {(datetime.now()+ timedelta(seconds=time_left)).strftime("%H:%M:%S (%Y/%m/%d)")}'
                )
                try:
                    sleep(time_left)
                except KeyboardInterrupt:
                    stop_bot(
                        device,
                        sessions,
                        session_state,
                        configs.args.screen_record,
                        was_sleeping=True,
                    )
            else:
                wait_for_next_session(
                    time_left,
                    session_state,
                    sessions,
                    device,
                    configs.args.screen_record,
                )
        else:
            break

    print_full_report(sessions, configs.args.scrape_to_file)
