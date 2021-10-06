import logging
import random
from datetime import datetime, timedelta
from sys import exit
from time import sleep

from colorama import Fore, Style

from GramAddict.core.config import Config
from GramAddict.core.device_facade import create_device, get_device_info
from GramAddict.core.filter import load_config as load_filter
from GramAddict.core.interaction import load_config as load_interaction
from GramAddict.core.log import (
    configure_logger,
    is_log_file_updated,
    update_log_file_name,
)
from GramAddict.core.navigation import check_if_english
from GramAddict.core.persistent_list import PersistentList
from GramAddict.core.report import print_full_report
from GramAddict.core.session_state import SessionState, SessionStateEncoder
from GramAddict.core.storage import Storage
from GramAddict.core.utils import (
    ask_for_a_donation,
    can_repeat,
    check_adb_connection,
    check_if_updated,
    close_instagram,
    config_examples,
    get_instagram_version,
    get_value,
    kill_atx_agent,
)
from GramAddict.core.utils import load_config as load_utils
from GramAddict.core.utils import (
    move_usernames_to_accounts,
    open_instagram,
    pre_post_script,
    print_telegram_reports,
    save_crash,
    set_time_delta,
    stop_bot,
    wait_for_next_session,
)
from GramAddict.core.views import AccountView, ProfileView, SearchView, TabBarView
from GramAddict.core.views import load_config as load_views

TESTED_IG_VERSION = "208.0.0.32.135"


def start_bot(**kwargs):
    # Pre-Load Config
    if not kwargs:
        configs = Config(first_run=True)
    else:
        configs = Config(first_run=True, module=True, **kwargs)

    # Logging initialization
    configure_logger(configs.debug, configs.username)
    logger = logging.getLogger(__name__)
    if "config" not in configs.args:
        logger.info(
            "We strongly recommend to use a config.yml file. Follow these links for more details: https://docs.gramaddict.org/#/configuration and https://github.com/GramAddict/bot/tree/master/config-examples",
            extra={"color": f"{Fore.GREEN}{Style.BRIGHT}"},
        )
        sleep(3)

    # Config-example hint
    config_examples()

    # Check for updates
    check_if_updated()

    # Move username folders to a main directory -> accounts
    if "--move-folders-in-accounts" in configs.args:
        move_usernames_to_accounts()

    # Global Variables
    sessions = PersistentList("sessions", SessionStateEncoder)

    # Load Config
    configs.load_plugins()
    configs.parse_args()
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
    if str(configs.args.total_sessions) != "-1":
        total_sessions = get_value(configs.args.total_sessions, None, -1)
    else:
        total_sessions = -1

    # init
    analytics_at_end = False
    telegram_reports_at_end = False
    followers_now = None
    following_now = None

    while True:
        set_time_delta(configs.args)
        inside_working_hours, time_left = SessionState.inside_working_hours(
            configs.args.working_hours, configs.args.time_delta_session
        )
        if not inside_working_hours:
            wait_for_next_session(
                time_left, session_state, sessions, device, configs.args.screen_record
            )
        pre_post_script(path=configs.args.pre_script)
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

        logger.info("Device screen ON and unlocked.")
        if open_instagram(device, configs.args.screen_record, configs.args.close_apps):
            try:
                running_ig_version = get_instagram_version()
                logger.info(f"Instagram version: {running_ig_version}")
                if tuple(running_ig_version.split(".")) > tuple(
                    TESTED_IG_VERSION.split(".")
                ):
                    logger.info(
                        f"You have a newer version of IG then the one we tested! (Tested version: {TESTED_IG_VERSION})",
                        extra={"color": f"{Style.BRIGHT}"},
                    )
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
            AccountView(device).refresh_account()
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

        report_string = f"Hello, @{session_state.my_username}! You have {session_state.my_followers_count} followers and {session_state.my_following_count} followings so far."
        logger.info(report_string, extra={"color": f"{Style.BRIGHT}"})
        if configs.args.repeat:
            logger.info(
                f"You have {total_sessions + 1 - len(sessions) if total_sessions > 0 else 'infinite'} session(s) left. You can stop the bot by pressing CTRL+C in console.",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            sleep(3)
        storage = Storage(session_state.my_username)
        if configs.args.shuffle_jobs:
            jobs_list = random.sample(configs.enabled, len(configs.enabled))
        else:
            jobs_list = configs.enabled

        if "analytics" in jobs_list:
            jobs_list.remove("analytics")
            if configs.args.analytics:
                analytics_at_end = True
        if "telegram-reports" in jobs_list:
            jobs_list.remove("telegram-reports")
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

        # save the session in sessions.json
        session_state.finishTime = datetime.now()
        sessions.persist(directory=session_state.my_username)

        # print reports
        if telegram_reports_at_end:
            logger.info("Going back to your profile..")
            ProfileView(device)._click_on_avatar()
            AccountView(device).refresh_account()
            (
                _,
                _,
                followers_now,
                following_now,
            ) = ProfileView(device).getProfileInfo()

        if analytics_at_end:
            configs.actions["analytics"].run(
                device, configs, storage, sessions, "analytics"
            )

        # turn off bot
        close_instagram(device, configs.args.screen_record)
        if configs.args.screen_sleep:
            device.screen_off()
            logger.info("Screen turned off for sleeping time.")

        kill_atx_agent(device)

        logger.info(
            "-------- FINISH: "
            + str(session_state.finishTime.strftime("%H:%M:%S - %Y/%m/%d"))
            + " --------",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        pre_post_script(pre=False, path=configs.args.post_script)

        if configs.args.repeat and can_repeat(len(sessions), total_sessions):
            print_full_report(sessions, configs.args.scrape_to_file)
            inside_working_hours, time_left = SessionState.inside_working_hours(
                configs.args.working_hours, configs.args.time_delta_session
            )
            if inside_working_hours:
                time_left = (
                    get_value(configs.args.repeat, "Sleep for {} minutes.", 180) * 60
                )
                print_telegram_reports(
                    configs,
                    telegram_reports_at_end,
                    followers_now,
                    following_now,
                    time_left,
                )
                logger.info(
                    f'Next session will start at: {(datetime.now() + timedelta(seconds=time_left)).strftime("%H:%M:%S (%Y/%m/%d)")}.'
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
                print_telegram_reports(
                    configs,
                    telegram_reports_at_end,
                    followers_now,
                    following_now,
                    time_left.total_seconds(),
                )
                wait_for_next_session(
                    time_left,
                    session_state,
                    sessions,
                    device,
                    configs.args.screen_record,
                )
        else:
            break
    print_telegram_reports(
        configs,
        telegram_reports_at_end,
        followers_now,
        following_now,
    )
    print_full_report(sessions, configs.args.scrape_to_file)
    ask_for_a_donation()
