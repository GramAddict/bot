import re

PROFILE_USERNAME_RES_ID = (
    re.escape("com.instagram.android:id/") + f"(title_view|action_bar_large_title)"
)
PROFILE_USERNAME_CLASS_NAME = "android.widget.TextView"
