import logging
import sys
import traceback
from datetime import datetime
from http.client import HTTPException
from socket import timeout

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


def run_safely(device, device_id, sessions, session_state):
    def actual_decorator(func):
        def wrapper(*args, **kwargs):
            session_state = sessions[-1]
            try:
                func(*args, **kwargs)
            except KeyboardInterrupt:
                close_instagram(device_id)
                logger.warn(f"-------- FINISH: {datetime.now().time()} --------")
                print_full_report(sessions)
                sessions.persist(directory=session_state.my_username)
                sys.exit(0)
            except (DeviceFacade.JsonRpcError, IndexError, HTTPException, timeout):
                logger.error(traceback.format_exc())
                save_crash(device)
                logger.info("No idea what it was. Let's try again.")
                # Hack for the case when IGTV was accidentally opened
                close_instagram(device_id)
                random_sleep()
                open_instagram(device_id)
                TabBarView(device).navigateToProfile()
            except LanguageNotEnglishException:
                logger.info(
                    "Language was changed. We'll have to start from the beginning."
                )
                TabBarView(device).navigateToProfile()
            except Exception as e:
                save_crash(device)
                close_instagram(device_id)
                print_full_report(sessions)
                sessions.persist(directory=session_state.my_username)
                raise e

        return wrapper

    return actual_decorator
