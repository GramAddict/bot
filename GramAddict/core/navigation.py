from GramAddict.core.utils import (
    COLOR_OKGREEN,
    COLOR_ENDC,
    print,
)
from GramAddict.core.views import TabBarView


def switch_to_english(device):
    print(COLOR_OKGREEN + "Switching to English locale" + COLOR_ENDC)
    profile_view = TabBarView(device).navigateToProfile()
    print("Changing language in settings")

    options_view = profile_view.navigateToOptions()
    settingts_view = options_view.navigateToSettings()
    account_view = settingts_view.navigateToAccount()
    language_view = account_view.navigateToLanguage()
    language_view.setLanguage("english")
