from src.navigation import navigate, Tabs
from src.utils import *


def get_my_username(device):
    navigate(device, Tabs.PROFILE)
    title_view = device(resourceId='com.instagram.android:id/title_view',
                        className='android.widget.TextView')
    if title_view.exists:
        username = title_view.text
        print("Hello, @" + username)
        return username
    else:
        print(COLOR_FAIL + "Failed to get username" + COLOR_ENDC)
        return ""
