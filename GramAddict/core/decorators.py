import logging
import sys
import traceback
from colorama import Fore, Style
from datetime import datetime
from http.client import HTTPException
from socket import timeout

from uiautomator2.exceptions import UiObjectNotFoundError as UiObjectNotFoundErrorv2

from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.report import print_full_report
from GramAddict.core.utils import (
    close_instagram,
    open_instagram,
    random_sleep,
    save_crash,
)
from GramAddict.core.views import LanguageNotEnglishException, TabBarView

logger = logging.getLogger(__name__)


def run_safely(device, device_id, sessions, session_state, screen_record):
    def actual_decorator(func):
        def wrapper(*args, **kwargs):
            session_state = sessions[-1]
            try:
                func(*args, **kwargs)
            except KeyboardInterrupt:
                try:
                    # Catch Ctrl-C and ask if user wants to pause execution
                    logger.info(
                        "CTRL-C detected . . .",
                        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                    )
                    logger.info(
                        f"-------- PAUSED: {datetime.now().time()} --------",
                        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                    )
                    logger.info(
                        "NOTE: This is a rudimentary pause. It will restart the action, while retaining session data.",
                        extra={"color": Style.BRIGHT},
                    )
                    logger.info(
                        "Press RETURN to resume or CTRL-C again to Quit: ",
                        extra={"color": Style.BRIGHT},
                    )

                    input("")

                    logger.info(
                        f"-------- RESUMING: {datetime.now().time()} --------",
                        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                    )
                    TabBarView(device).navigateToProfile()
                except KeyboardInterrupt:
                    close_instagram(device, screen_record)
                    logger.info(
                        f"-------- FINISH: {datetime.now().time()} --------",
                        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
                    )
                    print_full_report(sessions)
                    sessions.persist(directory=session_state.my_username)
                    sys.exit(0)

            except (
                DeviceFacade.JsonRpcError,
                IndexError,
                HTTPException,
                timeout,
                UiObjectNotFoundErrorv2,
            ):
                logger.error(traceback.format_exc())
                save_crash(device)
                logger.info("No idea what it was. Let's try again.")
                # Hack for the case when IGTV was accidentally opened
                close_instagram(device, screen_record)
                random_sleep()
                open_instagram(device, screen_record)
                TabBarView(device).navigateToProfile()
            except LanguageNotEnglishException:
                logger.info(
                    "Language was changed. We'll have to start from the beginning."
                )
                TabBarView(device).navigateToProfile()
            except Exception as e:
                logger.error(traceback.format_exc())
                save_crash(device)
                close_instagram(device, screen_record)
                print_full_report(sessions)
                sessions.persist(directory=session_state.my_username)
                raise e

        return wrapper

    return actual_decorator
