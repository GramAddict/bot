import logging
import sys
import traceback
from datetime import datetime
from http.client import HTTPException
from socket import timeout

from colorama import Fore, Style
from uiautomator2.exceptions import UiObjectNotFoundError

from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.report import print_full_report
from GramAddict.core.utils import (
    check_if_crash_popup_is_there,
    close_instagram,
    open_instagram,
    print_telegram_reports,
    random_sleep,
    save_crash,
    RandomStop,
    stop_bot,
)
from GramAddict.core.views import TabBarView

logger = logging.getLogger(__name__)


def run_safely(device, device_id, sessions, session_state, screen_record, configs):
    def actual_decorator(func):
        def wrapper(*args, **kwargs):
            session_state = sessions[-1]
            try:
                func(*args, **kwargs)
            except KeyboardInterrupt:
                # Respect immediate exit on Ctrl-C
                logger.info(
                    "CTRL-C detected, stopping the bot.",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                stop_bot(device, sessions, session_state)

            except RandomStop:
                logger.info(
                    "Random stop triggered, stopping the bot.",
                    extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                )
                stop_bot(device, sessions, session_state)

            except DeviceFacade.AppHasCrashed:
                logger.warning("App has crashed / has been closed!")
                restart(
                    device,
                    sessions,
                    session_state,
                    configs,
                    normal_crash=False,
                    print_traceback=False,
                )

            except (
                DeviceFacade.JsonRpcError,
                IndexError,
                HTTPException,
                timeout,
                UiObjectNotFoundError,
            ):
                restart(
                    device,
                    sessions,
                    session_state,
                    configs,
                )

            except Exception as e:
                logger.error(traceback.format_exc())
                for exception_line in traceback.format_exception_only(type(e), e):
                    logger.critical(
                        f"'{exception_line}' -> This kind of exception will stop the bot (no restart)."
                    )
                logger.info(
                    f"List of running apps: {', '.join(device.deviceV2.app_list_running())}"
                )
                save_crash(device)
                close_instagram(device)
                print_full_report(sessions, configs.args.scrape_to_file)
                sessions.persist(directory=session_state.my_username)
                if getattr(configs.args, "telegram_reports", False):
                    print_telegram_reports(
                        configs,
                        True,
                        None,
                        None,
                        session_state=session_state,
                        sessions=sessions,
                    )
                raise e from e

        return wrapper

    return actual_decorator


def restart(
    device: DeviceFacade,
    sessions,
    session_state,
    configs,
    normal_crash: bool = True,
    print_traceback: bool = True,
):
    if print_traceback:
        logger.error(traceback.format_exc())
        save_crash(device)
    logger.info(
        f"List of running apps: {', '.join(device.deviceV2.app_list_running())}."
    )
    if configs.args.count_app_crashes or normal_crash:
        session_state.totalCrashes += 1
        if session_state.check_limit(
            limit_type=session_state.Limit.CRASHES, output=True
        ):
            logger.error(
                "Reached crashes limit. Bot has crashed too much! Please check what's going on."
            )
            stop_bot(device, sessions, session_state)
        logger.info("Something unexpected happened. Let's try again.")
    close_instagram(device)
    check_if_crash_popup_is_there(device)
    random_sleep()
    if not open_instagram(device):
        print_full_report(sessions, configs.args.scrape_to_file)
        sessions.persist(directory=session_state.my_username)
        if getattr(configs.args, "telegram_reports", False):
            print_telegram_reports(
                configs,
                True,
                None,
                None,
                session_state=session_state,
                sessions=sessions,
            )
        sys.exit(2)
    TabBarView(device).navigateToProfile()
