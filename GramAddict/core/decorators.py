import traceback
from http.client import HTTPException
from socket import timeout
from datetime import datetime
import sys

from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.report import print_full_report
from GramAddict.core.utils import (
    COLOR_WARNING,
    COLOR_FAIL,
    COLOR_ENDC,
    open_instagram,
    close_instagram,
    random_sleep,
    save_crash,
    print_timeless,
    print,
)

from GramAddict.core.views import LanguageNotEnglishException, TabBarView


def run_safely(device, device_id, sessions, session_state):
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
                TabBarView(device).navigateToProfile()
            except LanguageNotEnglishException:
                print_timeless("")
                print("Language was changed. We'll have to start from the beginning.")
                TabBarView(device).navigateToProfile()
            except Exception as e:
                save_crash(device)
                close_instagram(device_id)
                print_full_report(sessions)
                sessions.persist(directory=session_state.my_username)
                raise e

        return wrapper

    return actual_decorator
