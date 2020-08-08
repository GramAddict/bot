from src.counters_parser import parse, LanguageChangedException
from src.interaction_rect_checker import update_interaction_rect
from src.navigation import navigate, Tabs
from src.utils import *


def get_my_profile_info(device):
    navigate(device, Tabs.PROFILE)
    update_interaction_rect(device)

    username = None
    title_view = device(resourceId='com.instagram.android:id/title_view',
                        className='android.widget.TextView')
    if title_view.exists:
        username = title_view.text
    else:
        print(COLOR_FAIL + "Failed to get username" + COLOR_ENDC)

    try:
        followers = _get_followers_count(device)
    except LanguageChangedException:
        # Try again on the correct language
        navigate(device, Tabs.PROFILE)
        followers = _get_followers_count(device)

    try:
        following = _get_following_count(device)
    except LanguageChangedException:
        # Try again on the correct language
        navigate(device, Tabs.PROFILE)
        following = _get_following_count(device)

    report_string = ""
    if username:
        report_string += "Hello, @" + username + "!"
    if followers is not None:
        report_string += " You have " + str(followers) + " followers"
        if following is not None:
            report_string += " and " + str(following) + " followings"
        report_string += " so far."

    if not report_string == "":
        print(report_string)

    return username, followers, following


def _get_followers_count(device):
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

    return followers


def _get_following_count(device):
    following = None
    following_text_view = device(resourceId='com.instagram.android:id/row_profile_header_textview_following_count',
                                 className='android.widget.TextView')
    if following_text_view.exists:
        following_text = following_text_view.text
        if following_text:
            following = parse(device, following_text)
        else:
            print(COLOR_FAIL + "Cannot get your following count text" + COLOR_ENDC)
    else:
        print(COLOR_FAIL + "Cannot find your following count view" + COLOR_ENDC)

    return following
