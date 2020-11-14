import logging

from colorama import Fore
from GramAddict.core.views import TabBarView

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
