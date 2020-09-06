from src.utils import *

_action_bar_bottom = None
_tab_bar_top = None


def update_interaction_rect(device):
    action_bar = device.find(resourceId='com.instagram.android:id/action_bar_container',
                             className='android.widget.FrameLayout')
    global _action_bar_bottom
    _action_bar_bottom = action_bar.get_bounds()['bottom']

    tab_bar = device.find(resourceId='com.instagram.android:id/tab_bar',
                          className='android.widget.LinearLayout')
    global _tab_bar_top
    _tab_bar_top = tab_bar.get_bounds()['top']


def is_in_interaction_rect(view):
    if _action_bar_bottom is None or _tab_bar_top is None:
        print(COLOR_FAIL + "Interaction rect is not specified in interaction_rect_checker.py" + COLOR_ENDC)
        return False

    view_top = view.get_bounds()['top']
    view_bottom = view.get_bounds()['bottom']
    return _action_bar_bottom <= view_top and view_bottom <= _tab_bar_top
