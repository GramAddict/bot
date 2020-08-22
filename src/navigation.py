from enum import Enum, unique

from src.globals import UI_TIMEOUT
from src.utils import *


def navigate(device, tab):
    tab_name = tab.name.lower()
    tab_index = tab.value

    print("Press " + tab_name)
    tab_bar = device(resourceId='com.instagram.android:id/tab_bar', className='android.widget.LinearLayout')
    button = tab_bar.child(index=tab_index)

    # Two clicks to reset tab content
    button.click(timeout=UI_TIMEOUT)
    button.click(timeout=UI_TIMEOUT)


@unique
class Tabs(Enum):
    HOME = 0
    SEARCH = 1
    PLUS = 2
    LIKES = 3
    PROFILE = 4
