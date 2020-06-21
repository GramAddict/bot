from utils import *


def get_my_username(device):
    print("Press profile")
    tab_bar = device(resourceId='com.instagram.android:id/tab_bar', className='android.widget.LinearLayout')
    profile_button = tab_bar.child(index=4)

    # Two clicks to reset tab content
    profile_button.click.wait()
    profile_button.click.wait()

    title_view = device(resourceId='com.instagram.android:id/title_view',
                        className='android.widget.TextView')
    if title_view.exists:
        username = title_view.text
        print("Hello, @" + username)
        return username
    else:
        print(COLOR_FAIL + "Failed to get username" + COLOR_ENDC)
        return ""
