from enum import Enum, unique

from src.utils import *

SEARCH_CONTENT_DESC_REGEX = '[Ss]earch and [Ee]xplore'


def navigate(device, tab):
    tab_name = tab.name.lower()
    tab_index = tab.value

    print("Press " + tab_name)
    if tab == Tabs.SEARCH:
        _navigate_to_search(device)
        return

    tab_bar = device.find(resourceId='com.instagram.android:id/tab_bar', className='android.widget.LinearLayout')
    button = tab_bar.child(index=tab_index)

    # Two clicks to reset tab content
    button.click()
    button.click()


def switch_to_english(device):
    print(COLOR_OKGREEN + "Switching to English locale" + COLOR_ENDC)
    navigate(device, Tabs.PROFILE)
    print("Changing language in settings")

    action_bar = device.find(resourceId='com.instagram.android:id/action_bar',
                             className='android.widget.LinearLayout')
    options_view = action_bar.child(index=2, className='android.widget.ImageView')
    if not options_view.exists():
        options_view = action_bar.child(index=3, className='android.widget.ImageView')
    if not options_view.exists():
        print(COLOR_FAIL + "No idea how to open menu..." + COLOR_ENDC)
        return
    options_view.click()

    settings_button = device.find(resourceId='com.instagram.android:id/menu_settings_row',
                                  className='android.widget.TextView')
    settings_button.click()

    for account_item_index in range(6, 9):
        list_view = device.find(resourceId='android:id/list',
                                className='android.widget.ListView')
        account_item = list_view.child(index=account_item_index)
        account_item.click()

        list_view = device.find(resourceId='android:id/list',
                                className='android.widget.ListView')
        language_item = list_view.child(index=3)
        if not language_item.exists():
            print(COLOR_FAIL + "Oops, went the wrong way" + COLOR_ENDC)
            device.back()
            continue
        language_item.click()

        search_edit_text = device.find(resourceId='com.instagram.android:id/search',
                                       className='android.widget.EditText')
        if not search_edit_text.exists():
            print(COLOR_FAIL + "Oops, went the wrong way" + COLOR_ENDC)
            device.back()
            device.back()
            continue
        search_edit_text.set_text("english")

        list_view = device.find(resourceId='com.instagram.android:id/language_locale_list',
                                className='android.widget.ListView')
        english_item = list_view.child(index=0)
        english_item.click()

        break


def _navigate_to_search(device):
    # Search tab is a special case, because on some accounts there is "Reels" tab instead. If so, we have to go to the
    # "Home" tab and press search in the action bar.

    tab_bar = device.find(resourceId='com.instagram.android:id/tab_bar', className='android.widget.LinearLayout')
    search_in_tab_bar = tab_bar.child(descriptionMatches=SEARCH_CONTENT_DESC_REGEX)
    if search_in_tab_bar.exists():
        # Two clicks to reset tab content
        search_in_tab_bar.click()
        search_in_tab_bar.click()
        return

    print("Didn't find search in the tab bar...")
    navigate(device, Tabs.HOME)
    print("Press search in the action bar")
    action_bar = device.find(resourceId='com.instagram.android:id/action_bar', className='android.widget.LinearLayout')
    search_in_action_bar = action_bar.child(descriptionMatches=SEARCH_CONTENT_DESC_REGEX)
    if search_in_action_bar.exists():
        search_in_action_bar.click()
        return

    print(COLOR_FAIL + "Cannot find search tab neither in the tab bar, nor in the action bar. Maybe not English "
                       "language is set?" + COLOR_ENDC)
    switch_to_english(device)
    raise LanguageChangedException()


class LanguageChangedException(Exception):
    pass


@unique
class Tabs(Enum):
    HOME = 0
    SEARCH = 1
    PLUS = 2
    LIKES = 3
    PROFILE = 4
