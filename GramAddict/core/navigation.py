import logging

from colorama import Fore
from GramAddict.core.views import TabBarView
from GramAddict.core.utils import random_sleep
from GramAddict.core.device_facade import DeviceFacade

logger = logging.getLogger(__name__)


def switch_to_english(device):
    logger.info("Switching to English locale", extra={"color": f"{Fore.GREEN}"})
    profile_view = TabBarView(device).navigateToProfile()
    logger.info("Changing language in settings")

    options_view = profile_view.navigateToOptions()
    settingts_view = options_view.navigateToSettings()
    account_view = settingts_view.navigateToAccount()
    language_view = account_view.navigateToLanguage()
    language_view.setLanguage("english")


def open_user(device, username):
    search_view = TabBarView(device).navigateToSearch()
    profile_view = search_view.navigateToUsername(username)
    random_sleep()
    if not profile_view:
        return False

    return True


def open_likers(device):
    attempts = 0
    while True:
        likes_view = device.find(
            resourceId="com.instagram.android:id/row_feed_textview_likes",
            className="android.widget.TextView",
        )
        if likes_view.exists():
            logger.info("Opening post likers")
            random_sleep()
            likes_view.click("right")
            return True
        else:
            if attempts < 1:
                attempts += 1
                logger.info("Can't find likers, trying small swipe")
                device.swipe(DeviceFacade.Direction.TOP, scale=0.1)
                continue
            else:
                return False
