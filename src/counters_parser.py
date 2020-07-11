from src.navigation import Tabs, navigate
from src.utils import *


def parse(device, text):
    multiplier = 1
    text = text.replace(",", "")
    if "K" in text:
        text = text.replace("K", "")
        multiplier = 1_000
    if "M" in text:
        text = text.replace("M", "")
        multiplier = 1_000_000
    try:
        count = int(float(text) * multiplier)
    except ValueError:
        print_timeless(COLOR_FAIL + "Cannot parse \"" + text + "\". Probably wrong language, will set English now." +
                       COLOR_ENDC)
        take_screenshot(device)
        _switch_to_english(device)
        raise LanguageChangedException()
    return count


def _switch_to_english(device):
    print(COLOR_OKGREEN + "Switching to English locale" + COLOR_ENDC)
    navigate(device, Tabs.PROFILE)
    print("Changing language in settings")

    action_bar = device(resourceId='com.instagram.android:id/action_bar',
                        className='android.widget.LinearLayout')
    options_view = action_bar.child(index=1)
    options_view.click.wait()

    settings_button = device(resourceId='com.instagram.android:id/menu_settings_row',
                             className='android.widget.TextView')
    settings_button.click.wait()

    list_view = device(resourceId='android:id/list',
                       className='android.widget.ListView')
    account_item = list_view.child(index=6)
    account_item.click.wait()

    list_view = device(resourceId='android:id/list',
                       className='android.widget.ListView')
    language_item = list_view.child(index=3)
    language_item.click.wait()

    search_edit_text = device(resourceId='com.instagram.android:id/search',
                              className='android.widget.EditText')
    search_edit_text.set_text("english")
    device.wait.idle()

    list_view = device(resourceId='com.instagram.android:id/language_locale_list',
                       className='android.widget.ListView')
    english_item = list_view.child(index=0)
    english_item.click.wait()


class LanguageChangedException(Exception):
    pass
