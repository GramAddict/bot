from src.counters_parser import parse
from src.navigation import navigate, Tabs
from src.utils import *


def get_my_profile_info(device):
    navigate(device, Tabs.PROFILE)

    username = None
    title_view = device(resourceId='com.instagram.android:id/title_view',
                        className='android.widget.TextView')
    if title_view.exists:
        username = title_view.text
    else:
        print(COLOR_FAIL + "Failed to get username" + COLOR_ENDC)

    followers = None
    followers_text_view = device(resourceId='com.instagram.android:id/row_profile_header_textview_followers_count',
                                 className='android.widget.TextView')
    if followers_text_view.exists:
        followers_text = followers_text_view.text
        if followers_text:
            followers = parse(device, followers_text)
        else:
            print(COLOR_FAIL + "Cannot get your followers count text" + COLOR_ENDC)
    else:
        print(COLOR_FAIL + "Cannot find your followers count view" + COLOR_ENDC)

    report_string = ""
    if username:
        report_string += "Hello, @" + username + "!"
    if followers:
        report_string += " You have " + str(followers) + " followers so far."

    if not report_string == "":
        print(report_string)

    return username, followers
