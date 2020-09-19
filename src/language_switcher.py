from src.navigation import navigate, Tabs
from src.utils import *


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


class LanguageChangedException(Exception):
    pass
