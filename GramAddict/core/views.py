import logging
import datetime
import re
from enum import Enum, auto

from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.utils import random_sleep, save_crash

logger = logging.getLogger(__name__)


def case_insensitive_re(str_list):
    if isinstance(str_list, str):
        strings = str_list
    else:
        strings = "|".join(str_list)
    re_str = f"(?i)({strings})"
    return re_str


class TabBarTabs(Enum):
    HOME = auto()
    SEARCH = auto()
    REELS = auto()
    ORDERS = auto()
    ACTIVITY = auto()
    PROFILE = auto()


class SearchTabs(Enum):
    TOP = auto()
    ACCOUNTS = auto()
    TAGS = auto()
    PLACES = auto()


class ProfileTabs(Enum):
    POSTS = auto()
    IGTV = auto()
    REELS = auto()
    EFFECTS = auto()
    PHOTOS_OF_YOU = auto()


class TabBarView:
    HOME_CONTENT_DESC = "Home"
    SEARCH_CONTENT_DESC = "[Ss]earch and [Ee]xplore"
    REELS_CONTENT_DESC = "Reels"
    ORDERS_CONTENT_DESC = "Orders"
    ACTIVITY_CONTENT_DESC = "Activity"
    PROFILE_CONTENT_DESC = "Profile"

    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getTabBar(self):
        tab_bar = self.device.find(
            resourceIdMatches=case_insensitive_re("com.instagram.android:id/tab_bar"),
            className="android.widget.LinearLayout",
        )
        return tab_bar

    def navigateToHome(self):
        self._navigateTo(TabBarTabs.HOME)
        return HomeView(self.device)

    def navigateToSearch(self):
        self._navigateTo(TabBarTabs.SEARCH)
        return SearchView(self.device)

    def navigateToReels(self):
        self._navigateTo(TabBarTabs.REELS)

    def navigateToOrders(self):
        self._navigateTo(TabBarTabs.ORDERS)

    def navigateToActivity(self):
        self._navigateTo(TabBarTabs.ACTIVITY)

    def navigateToProfile(self):
        self._navigateTo(TabBarTabs.PROFILE)
        return ProfileView(self.device, is_own_profile=True)

    def _navigateTo(self, tab: TabBarTabs):
        tab_name = tab.name
        logger.debug(f"Navigate to {tab_name}")
        button = None
        tabBarView = self._getTabBar()
        if tab == TabBarTabs.HOME:
            button = tabBarView.child(
                descriptionMatches=case_insensitive_re(TabBarView.HOME_CONTENT_DESC)
            )
        elif tab == TabBarTabs.SEARCH:
            button = tabBarView.child(
                descriptionMatches=case_insensitive_re(TabBarView.SEARCH_CONTENT_DESC)
            )
            if not button.exists():
                # Some accounts display the search btn only in Home -> action bar
                logger.debug("Didn't find search in the tab bar...")
                home_view = self.navigateToHome()
                home_view.navigateToSearch()
                return
        elif tab == TabBarTabs.REELS:
            button = tabBarView.child(
                descriptionMatches=case_insensitive_re(TabBarView.REELS_CONTENT_DESC)
            )
        elif tab == TabBarTabs.ORDERS:
            button = tabBarView.child(
                descriptionMatches=case_insensitive_re(TabBarView.ORDERS_CONTENT_DESC)
            )
        elif tab == TabBarTabs.ACTIVITY:
            button = tabBarView.child(
                descriptionMatches=case_insensitive_re(TabBarView.ACTIVITY_CONTENT_DESC)
            )
        elif tab == TabBarTabs.PROFILE:
            button = tabBarView.child(
                descriptionMatches=case_insensitive_re(TabBarView.PROFILE_CONTENT_DESC)
            )

        if button.exists():
            # Two clicks to reset tab content
            button.click()
            button.click()

            return

        logger.error(
            f"Didn't find tab {tab_name} in the tab bar... Maybe English language is not set!?"
        )

        raise LanguageNotEnglishException()


class ActionBarView:
    def __init__(self, device: DeviceFacade):
        self.device = device
        self.action_bar = self._getActionBar()

    def _getActionBar(self):
        tab_bar = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/action_bar_container"
            ),
            className="android.widget.FrameLayout",
        )
        return tab_bar


class HomeView(ActionBarView):
    def __init__(self, device: DeviceFacade):
        super().__init__(device)
        self.device = device

    def navigateToSearch(self):
        logger.debug("Navigate to Search")
        search_btn = self.action_bar.child(
            descriptionMatches=case_insensitive_re(TabBarView.SEARCH_CONTENT_DESC)
        )
        search_btn.click()

        return SearchView(self.device)


class HashTagView:
    def __init__(self, device: DeviceFacade):
        self.device = device


class SearchView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getSearchEditText(self):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/action_bar_search_edit_text"
            ),
            className="android.widget.EditText",
        )

    def _getUsernameRow(self, username):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/row_search_user_username"
            ),
            className="android.widget.TextView",
            text=username,
        )

    def _getHashtagRow(self, hashtag):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/row_hashtag_textview_tag_name"
            ),
            className="android.widget.TextView",
            text=f"#{hashtag}",
        )

    def _getTabTextView(self, tab: SearchTabs):
        tab_layout = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/fixed_tabbar_tabs_container"
            ),
            className="android.widget.LinearLayout",
        )

        tab_text_view = tab_layout.child(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/tab_button_name_text"
            ),
            className="android.widget.TextView",
            textMatches=case_insensitive_re(tab.name),
        )
        return tab_text_view

    def _searchTabWithTextPlaceholder(self, tab: SearchTabs):
        tab_layout = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/fixed_tabbar_tabs_container"
            ),
            className="android.widget.LinearLayout",
        )
        search_edit_text = self._getSearchEditText()

        fixed_text = "Search {}".format(tab.name if tab.name != "TAGS" else "hashtags")
        logger.debug(
            "Going to check if the search bar have as placeholder: {}".format(
                fixed_text
            )
        )
        for item in tab_layout.child(
            resourceId="com.instagram.android:id/tab_button_fallback_icon",
            className="android.widget.ImageView",
        ):
            item.click()
            # random_sleep()

            # Little trick for force-update the ui and placeholder text
            search_edit_text.click()
            self.device.back()

            if self.device.find(
                className="android.widget.TextView",
                textMatches=case_insensitive_re(fixed_text),
            ).exists():
                return item
        return None

    def navigateToUsername(self, username):
        logger.debug("Navigate to profile @" + username)
        search_edit_text = self._getSearchEditText()
        search_edit_text.click()

        search_edit_text.set_text(username)
        username_view = self._getUsernameRow(username)

        if not username_view.exists():
            logger.error("Cannot find user @" + username + ", abort.")
            return None

        username_view.click()

        return ProfileView(self.device, is_own_profile=False)

    def navigateToHashtag(self, hashtag):
        logger.debug(f"Navigate to hashtag {hashtag}")
        search_edit_text = self._getSearchEditText()
        search_edit_text.click()

        random_sleep()
        hashtag_tab = self._getTabTextView(SearchTabs.TAGS)
        if not hashtag_tab.exists():
            logger.debug(
                "Cannot find tab: Tags. Going to attempt to search for placeholder in all tabs"
            )
            hashtag_tab = self._searchTabWithTextPlaceholder(SearchTabs.TAGS)
            if hashtag_tab is None:
                logger.error("Cannot find tab: Tags.")
                save_crash(self.device)
                return None
        hashtag_tab.click()

        search_edit_text.set_text(hashtag)
        hashtag_view = self._getHashtagRow(hashtag[1:])

        if not hashtag_view.exists():
            logger.error(f"Cannot find hashtag {hashtag}, abort.")
            save_crash(self.device)
            return None

        hashtag_view.click()

        return HashTagView(self.device)


class LanguageView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def setLanguage(self, language: str):
        logger.debug(f"Set language to {language}")
        search_edit_text = self.device.find(
            resourceId="com.instagram.android:id/search",
            className="android.widget.EditText",
        )
        search_edit_text.set_text(language)

        list_view = self.device.find(
            resourceId="com.instagram.android:id/language_locale_list",
            className="android.widget.ListView",
        )
        first_item = list_view.child(index=0)
        first_item.click()


class AccountView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToLanguage(self):
        logger.debug("Navigate to Language")
        button = self.device.find(
            textMatches=case_insensitive_re("Language"),
            resourceId="com.instagram.android:id/row_simple_text_textview",
            className="android.widget.TextView",
        )
        button.click()

        return LanguageView(self.device)


class SettingsView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToAccount(self):
        logger.debug("Navigate to Account")
        button = self.device.find(
            textMatches=case_insensitive_re("Account"),
            resourceId="com.instagram.android:id/row_simple_text_textview",
            className="android.widget.TextView",
        )
        button.click()
        return AccountView(self.device)


class OptionsView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToSettings(self):
        logger.debug("Navigate to Settings")
        button = self.device.find(
            textMatches=case_insensitive_re("Settings"),
            resourceId="com.instagram.android:id/menu_settings_row",
            className="android.widget.TextView",
        )
        button.click()
        return SettingsView(self.device)


class OpenedPostView:
    BTN_LIKE_RES_ID = "com.instagram.android:id/row_feed_button_like"

    def __init__(self, device: DeviceFacade):
        self.device = device

    def isPostLiked(self):
        like_btn_view = self.device.find(
            resourceIdMatches=case_insensitive_re(OpenedPostView.BTN_LIKE_RES_ID)
        )
        if like_btn_view.exists():
            return like_btn_view.get_selected()

        logger.error("Cannot find button like")

        return False

    def likePost(self, click_btn_like=False):
        MEDIA_GROUP_RE = case_insensitive_re(
            [
                "com.instagram.android:id/media_group",
                "com.instagram.android:id/carousel_media_group",
            ]
        )
        post_media_view = self.device.find(
            resourceIdMatches=MEDIA_GROUP_RE, className="android.widget.FrameLayout"
        )

        if click_btn_like:
            like_btn_view = self.device.find(
                resourceIdMatches=case_insensitive_re(OpenedPostView.BTN_LIKE_RES_ID)
            )
            if post_media_view.exists() and like_btn_view.exists():
                image_bottom_bound = post_media_view.get_bounds()["bottom"]
                like_btn_top_bound = like_btn_view.get_bounds()["top"]
                # to avoid clicking in a like button that is for another picture (previous one)
                if like_btn_top_bound >= image_bottom_bound:
                    like_btn_view.click()
                else:
                    logger.debug(
                        "Like btn out of current view. Don't click, just ignore."
                    )
            else:
                logger.error("Cannot find button like to click")
        else:

            if post_media_view.exists():
                post_media_view.double_click()
            else:
                logger.error("Could not find post area to double click")


class PostsGridView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def scrollDown(self):
        coordinator_layout = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/coordinator_root_layout"
            )
        )
        if coordinator_layout.exists():
            coordinator_layout.scroll(DeviceFacade.Direction.BOTTOM)
            return True

        return False

    def navigateToPost(self, row, col):
        post_list_view = self.device.find(
            resourceIdMatches=case_insensitive_re("android:id/list")
        )
        OFFSET = 1  # row with post starts from index 1
        row_view = post_list_view.child(index=row + OFFSET)
        if not row_view.exists():
            return None
        post_view = row_view.child(index=col)
        if not post_view.exists():
            return None
        post_view.click()

        return OpenedPostView(self.device)


class ProfileView(ActionBarView):
    def __init__(self, device: DeviceFacade, is_own_profile=False):
        super().__init__(device)
        self.device = device
        self.is_own_profile = is_own_profile

    def navigateToOptions(self):
        logger.debug("Navigate to Options")
        button = self.action_bar.child(
            descriptionMatches=case_insensitive_re("Options")
        )
        button.click()

        return OptionsView(self.device)

    def _getActionBarTitleBtn(self):
        re_case_insensitive = case_insensitive_re(
            [
                "com.instagram.android:id/title_view",
                "com.instagram.android:id/action_bar_large_title",
                "com.instagram.android:id/action_bar_textview_title",
            ]
        )
        return self.action_bar.child(
            resourceIdMatches=re_case_insensitive, className="android.widget.TextView"
        )

    def getUsername(self):
        title_view = self._getActionBarTitleBtn()
        if title_view.exists():
            return title_view.get_text()
        logger.error("Cannot get username")
        return ""

    def _parseCounter(self, text):
        multiplier = 1
        text = text.replace(",", "")
        text = text.replace(".", "")
        if "K" in text:
            text = text.replace("K", "")
            multiplier = 1000
        if "M" in text:
            text = text.replace("M", "")
            multiplier = 1000000
        try:
            count = int(float(text) * multiplier)
        except ValueError:
            logger.error(f"Cannot parse {text}. Probably wrong language ?!")
            raise LanguageNotEnglishException()
        return count

    def _getFollowersTextView(self):
        followers_text_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/row_profile_header_textview_followers_count"
            ),
            className="android.widget.TextView",
        )
        return followers_text_view

    def getFollowersCount(self):
        followers = None
        followers_text_view = self._getFollowersTextView()
        if followers_text_view.exists():
            followers_text = followers_text_view.get_text()
            if followers_text:
                followers = self._parseCounter(followers_text)
            else:
                logger.error("Cannot get your followers count text")
        else:
            logger.error("Cannot find your followers count view")

        return followers

    def _getFollowingTextView(self):
        following_text_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/row_profile_header_textview_following_count"
            ),
            className="android.widget.TextView",
        )
        return following_text_view

    def getFollowingCount(self):
        following = None
        following_text_view = self._getFollowingTextView()
        if following_text_view.exists():
            following_text = following_text_view.get_text()
            if following_text:
                following = self._parseCounter(following_text)
            else:
                logger.error("Cannot get following count text")
        else:
            logger.error("Cannot find following count view")

        return following

    def getPostsCount(self):
        post_count_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/row_profile_header_textview_post_count"
            ),
            className="android.widget.TextView",
        )
        if post_count_view.exists():
            return self._parseCounter(post_count_view.get_text())
        else:
            logger.error("Cannot get posts count text")
            return 0

    def getProfileInfo(self):

        username = self.getUsername()
        followers = self.getFollowersCount()
        following = self.getFollowingCount()

        return username, followers, following

    def isPrivateAccount(self):
        private_profile_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                [
                    "com.instagram.android:id/private_profile_empty_state",
                    "com.instagram.android:id/row_profile_header_empty_profile_notice_title",
                ]
            )
        )
        return private_profile_view.exists()

    def haveStory(self):
        return self.device.find(
            resourceId="com.instagram.android:id/reel_ring",
            className="android.view.View",
        ).exists()

    def profileImage(self):
        return self.device.find(
            resourceId="com.instagram.android:id/row_profile_header_imageview",
            className="android.widget.ImageView",
        )

    def navigateToFollowers(self):
        logger.debug("Navigate to Followers")
        FOLLOWERS_BUTTON_ID_REGEX = case_insensitive_re(
            [
                "com.instagram.android:id/row_profile_header_followers_container",
                "com.instagram.android:id/row_profile_header_container_followers",
            ]
        )
        followers_button = self.device.find(resourceIdMatches=FOLLOWERS_BUTTON_ID_REGEX)
        followers_button.click()

    def navigateToPostsTab(self):
        self._navigateToTab(ProfileTabs.POSTS)
        return PostsGridView(self.device)

    def navigateToIgtvTab(self):
        self._navigateToTab(ProfileTabs.IGTV)
        raise Exception("Not implemented")

    def navigateToReelsTab(self):
        self._navigateToTab(ProfileTabs.REELS)
        raise Exception("Not implemented")

    def navigateToEffectsTab(self):
        self._navigateToTab(ProfileTabs.EFFECTS)
        raise Exception("Not implemented")

    def navigateToPhotosOfYouTab(self):
        self._navigateToTab(ProfileTabs.PHOTOS_OF_YOU)
        raise Exception("Not implemented")

    def _navigateToTab(self, tab: ProfileTabs):
        TABS_RES_ID = "com.instagram.android:id/profile_tab_layout"
        TABS_CLASS_NAME = "android.widget.HorizontalScrollView"
        tabs_view = self.device.find(
            resourceIdMatches=case_insensitive_re(TABS_RES_ID),
            className=TABS_CLASS_NAME,
        )

        TAB_RES_ID = "com.instagram.android:id/profile_tab_icon_view"
        TAB_CLASS_NAME = "android.widget.ImageView"
        description = ""
        if tab == ProfileTabs.POSTS:
            description = "Grid View"
        elif tab == ProfileTabs.IGTV:
            description = "IGTV"
        elif tab == ProfileTabs.REELS:
            description = "Reels"
        elif tab == ProfileTabs.EFFECTS:
            description = "Effects"
        elif tab == ProfileTabs.PHOTOS_OF_YOU:
            description = "Photos of You"

        button = tabs_view.child(
            descriptionMatches=case_insensitive_re(description),
            resourceIdMatches=case_insensitive_re(TAB_RES_ID),
            className=TAB_CLASS_NAME,
        )
        if not button.exists():
            logger.error(f"Cannot navigate to to tab '{description}'")
            save_crash(self.device)
        else:
            button.click()


class CurrentStoryView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def getStoryFrame(self):
        return self.device.find(
            resourceId="com.instagram.android:id/reel_viewer_image_view",
            className="android.widget.FrameLayout",
        )

    def getUsername(self):
        reel_viewer_title = self.device.find(
            resourceId="com.instagram.android:id/reel_viewer_title",
            className="android.widget.TextView",
        )
        return "" if not reel_viewer_title.exists() else reel_viewer_title.get_text()

    def getTimestamp(self):
        reel_viewer_timestamp = self.device.find(
            resourceId="com.instagram.android:id/reel_viewer_timestamp",
            className="android.widget.TextView",
        )
        if reel_viewer_timestamp.exists():
            timestamp = reel_viewer_timestamp.get_text().strip()
            value = int(re.sub("[^0-9]", "", timestamp))
            if timestamp[-1] == "s":
                return datetime.timestamp(
                    datetime.datetime.now() - datetime.timedelta(seconds=value)
                )
            elif timestamp[-1] == "m":
                return datetime.timestamp(
                    datetime.datetime.now() - datetime.timedelta(minutes=value)
                )
            elif timestamp[-1] == "h":
                return datetime.timestamp(
                    datetime.datetime.now() - datetime.timedelta(hours=value)
                )
            else:
                return datetime.timestamp(
                    datetime.datetime.now() - datetime.timedelta(days=value)
                )
        return ""


class LanguageNotEnglishException(Exception):
    pass
