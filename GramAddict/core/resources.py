args = None

APP_ID = "com.instagram.android"


def load(nargs):
    global args
    args = nargs


class ResourceID:
    ACTION_BAR_CONTAINER = f"{APP_ID}:id/action_bar_container"
    ACTION_BAR_LARGE_TITLE = f"{APP_ID}:id/action_bar_large_title"
    ACTION_BAR_SEARCH_EDIT_TEXT = f"{APP_ID}:id/action_bar_search_edit_text"
    ACTION_BAR_TEXTVIEW_TITLE = f"{APP_ID}:id/action_bar_textview_title"
    ACTION_BAR_TITLE = f"{APP_ID}:id/action_bar_title"
    BUTTON = f"{APP_ID}:id/button"
    CAROUSEL_MEDIA_GROUP = f"{APP_ID}:id/carousel_media_group"
    COORDINATOR_ROOT_LAYOUT = f"{APP_ID}:id/coordinator_root_layout"
    DIALOG_ROOT_VIEW = f"{APP_ID}:id/dialog_root_view"
    FIXED_TABBAR_TABS_CONTAINER = f"{APP_ID}:id/fixed_tabbar_tabs_container"
    FOLLOW_LIST_CONTAINER = f"{APP_ID}:id/follow_list_container"
    FOLLOW_LIST_SORTING_OPTIONS_RECYCLER_VIEW = (
        f"{APP_ID}:id/follow_list_sorting_options_recycler_view"
    )
    FOLLOW_LIST_USERNAME = f"{APP_ID}:id/follow_list_username"
    FOLLOW_SHEET_UNFOLLOW_ROW = f"{APP_ID}:id/follow_sheet_unfollow_row"
    GAP_VIEW = f"{APP_ID}:id/gap_view"
    IMAGE_BUTTON = f"{APP_ID}:id/image_button"
    LANGUAGE_LIST_LOCALE = f"{APP_ID}:id/language_locale_list"
    LIST = "android:id/list"
    MEDIA_GROUP = f"{APP_ID}:id/media_group"
    MENU_SETTINGS_ROW = f"{APP_ID}:id/menu_settings_row"
    PRIVATE_PROFILE_EMPTY_STATE = f"{APP_ID}:id/private_profile_empty_state"
    PROFILE_HEADER_BIO_TEXT = f"{APP_ID}:id/profile_header_bio_text"
    PROFILE_HEADER_BUSINESS_CATEGORY = f"{APP_ID}:id/profile_header_business_category"
    PROFILE_HEADER_FULL_NAME = f"{APP_ID}:id/profile_header_full_name"
    PROFILE_TAB_LAYOUT = f"{APP_ID}:id/profile_tab_layout"
    PROFILE_TAB_ICON_VIEW = f"{APP_ID}:id/profile_tab_icon_view"
    PROFILE_TABS_CONTAINER = f"{APP_ID}:id/profile_tabs_container"
    REEL_RING = f"{APP_ID}:id/reel_ring"
    REEL_VIEWER_IMAGE_VIEW = f"{APP_ID}:id/reel_viewer_image_view"
    REEL_VIEWER_TIMESTAMP = f"{APP_ID}:id/reel_viewer_timestamp"
    REEL_VIEWER_TITLE = f"{APP_ID}:id/reel_viewer_title"
    ROW_FEED_BUTTON_LIKE = f"{APP_ID}:id/row_feed_button_like"
    ROW_FEED_COMMENT_TEXTVIEW_LAYOUT = f"{APP_ID}:id/row_feed_comment_textview_layout"
    ROW_FEED_TEXTVIEW_LIKES = f"{APP_ID}:id/row_feed_textview_likes"
    ROW_HASHTAG_TEXTVIEW_TAG_NAME = f"{APP_ID}:id/row_hashtag_textview_tag_name"
    ROW_LOAD_MORE_BUTTON = f"{APP_ID}:id/row_load_more_button"
    ROW_PROFILE_HEADER_EMPTY_PROFILE_NOTICE_CONTAINER = (
        f"{APP_ID}:id/row_profile_header_empty_profile_notice_container"
    )
    ROW_PROFILE_HEADER_EMPTY_PROFILE_NOTICE_TITLE = (
        f"{APP_ID}:id/row_profile_header_empty_profile_notice_title"
    )
    ROW_PROFILE_HEADER_FOLLOWERS_CONTAINER = f"{APP_ID}:id/row_profile_header_followers_container|{APP_ID}:id/row_profile_header_container_followers"
    ROW_PROFILE_HEADER_FOLLOWING_CONTAINER = f"{APP_ID}:id/row_profile_header_following_container|{APP_ID}:id/row_profile_header_container_following"
    ROW_PROFILE_HEADER_IMAGEVIEW = f"{APP_ID}:id/row_profile_header_imageview"
    ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWERS_COUNT = (
        f"{APP_ID}:id/row_profile_header_textview_followers_count"
    )
    ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWING_COUNT = (
        f"{APP_ID}:id/row_profile_header_textview_following_count"
    )
    ROW_PROFILE_HEADER_TEXTVIEW_POST_COUNT = (
        f"{APP_ID}:id/row_profile_header_textview_post_count"
    )
    ROW_SEARCH_EDIT_TEXT = f"{APP_ID}:id/row_search_edit_text"
    ROW_SEARCH_USER_USERNAME = f"{APP_ID}:id/row_search_user_username"
    ROW_SIMPLE_TEXT_TEXTVIEW = f"{APP_ID}:id/row_simple_text_textview"
    ROW_USER_CONTAINER_BASE = f"{APP_ID}:id/row_user_container_base"
    ROW_USER_PRIMARY_NAME = f"{APP_ID}:id/row_user_primary_name"
    SEARCH = f"{APP_ID}:id/search"
    SEE_ALL_BUTTON = f"{APP_ID}:id/see_all_button"
    SORTING_ENTRY_ROW_ICON = f"{APP_ID}:id/sorting_entry_row_icon"
    TAB_BAR = f"{APP_ID}:id/tab_bar"
    TAB_BUTTON_NAME_TEXT = f"{APP_ID}:id/tab_button_name_text"
    TAB_BUTTON_FALLBACK_ICON = f"{APP_ID}:id/tab_button_fallback_icon"
    TITLE_VIEW = f"{APP_ID}:id/title_view"
    ZOOMABLE_VIEW_CONTAINER = f"{APP_ID}:id/zoomable_view_container"


class TabBarText:
    ACTIVITY_CONTENT_DESC = "Activity"
    EFFECTS_CONTENT_DESC = "Effects"
    HOME_CONTENT_DESC = "Home"
    IGTV_CONTENT_DESC = "IGTV"
    ORDERS_CONTENT_DESC = "Orders"
    PHOTOS_OF_YOU_CONTENT_DESC = "Photos of You"
    POSTS_CONTENT_DESC = "Grid View"
    PROFILE_CONTENT_DESC = "Profile"
    RECENT_CONTENT_DESC = "Recent"
    REELS_CONTENT_DESC = "Reels"
    SEARCH_CONTENT_DESC = "[Ss]earch and [Ee]xplore"


class ClassName:
    BUTTON = "android.widget.Button"
    BUTTON_OR_TEXTVIEW_REGEX = "android.widget.Button|android.widget.TextView"
    EDIT_TEXT = "android.widget.EditText"
    FRAME_LAYOUT = "android.widget.FrameLayout"
    HORIZONTAL_SCROLL_VIEW = "android.widget.HorizontalScrollView"
    IMAGE_VIEW = "android.widget.ImageView"
    LIST_VIEW = "android.widget.ListView"
    LINEAR_LAYOUT = "android.widget.LinearLayout"
    RECYCLER_VIEW = "androidx.recyclerview.widget.RecyclerView"
    TEXT_VIEW = "android.widget.TextView"
    VIEW = "android.view.View"
    VIEW_PAGER = "androidx.viewpager.widget.ViewPager"
