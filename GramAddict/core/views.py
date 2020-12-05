import datetime
import logging
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

    def _getRecyclerView(self):
        CLASSNAME = "(androidx.recyclerview.widget.RecyclerView|android.view.View)"

        return self.device.find(classNameMatches=CLASSNAME)

    def _getFistImageView(self, recycler):
        return recycler.child(
            className="android.widget.ImageView",
            resourceIdMatches="com.instagram.android:id/image_button",
        )

    def _getRecentTab(self):
        return self.device.find(
            className="android.widget.TextView",
            textMatches=case_insensitive_re("Recent"),
        )


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
        logger.info(f"Navigate to hashtag {hashtag}")
        search_edit_text = self._getSearchEditText()
        search_edit_text.click()
        random_sleep(1, 2)
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
        random_sleep(1, 2)
        DeviceFacade.back(self.device)  # close the keyboard
        random_sleep(1, 2)
        # check if that hashtag already exists in the recent search list -> act as human
        hashtag_view_recent = self._getHashtagRow(hashtag[1:])

        if hashtag_view_recent.exists():
            hashtag_view_recent.click()
            random_sleep(5, 10)
            return HashTagView(self.device)

        logger.info(f"{hashtag} is not in recent searching hystory..")
        search_edit_text.set_text(hashtag)
        hashtag_view = self._getHashtagRow(hashtag[1:])
        random_sleep(4, 8)

        if not hashtag_view.exists():
            logger.error(f"Cannot find hashtag {hashtag}, abort.")
            save_crash(self.device)
            return None

        hashtag_view.click()
        random_sleep()

        return HashTagView(self.device)


class PostsViewList:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def swipe_to_fit_posts(self, first_post):
        """calculate the right swipe amount necessary to swipe to next post in hashtag post view"""
        POST_CONTAINER = "com.instagram.android:id/zoomable_view_container|com.instagram.android:id/carousel_media_group"
        displayWidth = self.device.get_info()["displayWidth"]
        if first_post:
            zoomable_view_container = self.device.find(
                resourceIdMatches=POST_CONTAINER
            ).get_bounds()["bottom"]

            logger.info("Scrolled down to see more posts.")

            self.device.swipe_points(
                displayWidth / 2,
                zoomable_view_container - 1,
                displayWidth / 2,
                zoomable_view_container * 0.5,
            )
        else:
            gap_view_obj = self.device.find(
                resourceIdMatches="com.instagram.android:id/gap_view"
            )
            if not gap_view_obj.exists(True):
                zoomable_view_container = self.device.find(
                    resourceIdMatches=(POST_CONTAINER)
                ).get_bounds()["bottom"]
                self.device.swipe_points(
                    displayWidth / 2,
                    zoomable_view_container - 1,
                    displayWidth / 2,
                    zoomable_view_container * 0.5,
                )
                gap_view_obj = self.device.find(
                    resourceIdMatches="com.instagram.android:id/gap_view"
                )

            gap_view = gap_view_obj.get_bounds()["top"]
            self.device.swipe_points(displayWidth / 2, gap_view, displayWidth / 2, 10)
            zoomable_view_container = self.device.find(
                resourceIdMatches=POST_CONTAINER
            ).get_bounds()["bottom"]

            self.device.swipe_points(
                displayWidth / 2,
                zoomable_view_container - 1,
                displayWidth / 2,
                zoomable_view_container * 0.5,
            )
        return

    def check_if_last_post(self, last_description):
        """check if that post has been just interacted"""
        post_description = self.device.find(
            resourceId="com.instagram.android:id/row_feed_comment_textview_layout"
        )
        if post_description.exists(True):
            new_description = post_description.get_text().upper()
            if new_description == last_description:
                logger.info("This is the last post for this hashtag")
                return True, new_description
            else:
                return False, new_description


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

    def _getPostLikeButton(self, scroll_to_find=True):
        """Find the like button right bellow a post.
        Note: sometimes the like button from the post above or bellow are
        dumped as well, so we need handle that situation.

        scroll_to_find: if the like button is not found, scroll a bit down
                        to try to find it. Default: True
        """
        MEDIA_GROUP_RE = case_insensitive_re(
            [
                "com.instagram.android:id/media_group",
                "com.instagram.android:id/carousel_media_group",
            ]
        )
        post_view_area = self.device.find(
            resourceIdMatches=case_insensitive_re("android:id/list")
        )
        if not post_view_area.exists():
            logger.debug("Cannot find post recycler view area")
            return None

        post_media_view = self.device.find(
            resourceIdMatches=MEDIA_GROUP_RE,
            className="android.widget.FrameLayout",
        )

        if not post_media_view.exists():
            logger.debug("Cannot find post media view area")
            return None

        like_btn_view = post_media_view.down(
            resourceIdMatches=case_insensitive_re(OpenedPostView.BTN_LIKE_RES_ID)
        )

        if like_btn_view.exists():
            # threshold of 30% of the display height
            threshold = int((0.3) * self.device.get_info()["displayHeight"])
            like_btn_top_bound = like_btn_view.get_bounds()["top"]
            is_like_btn_in_the_bottom = like_btn_top_bound > threshold

            if not is_like_btn_in_the_bottom:
                logger.debug(
                    f"Like button is to high ({like_btn_top_bound} px). Threshold is {threshold} px"
                )

            post_view_area_bottom_bound = post_view_area.get_bounds()["bottom"]
            is_like_btn_visible = like_btn_top_bound <= post_view_area_bottom_bound
            if not is_like_btn_visible:
                logger.debug(
                    f"Like btn out of current clickable area. Like btn top ({like_btn_top_bound}) recycler_view bottom ({post_view_area_bottom_bound})"
                )
        else:
            logger.debug("Like button not found bellow the post.")

        if (
            not like_btn_view.exists(True)
            or not is_like_btn_in_the_bottom
            or not is_like_btn_visible
        ):
            if scroll_to_find:
                logger.debug("Try to scroll tiny bit down...")
                # Remember: to scroll down we need to swipe up :)
                self.device.swipe(DeviceFacade.Direction.TOP, scale=0.2)
                like_btn_view = self.device.find(
                    resourceIdMatches=case_insensitive_re(
                        OpenedPostView.BTN_LIKE_RES_ID
                    )
                )

            if not scroll_to_find or not like_btn_view.exists(True):
                logger.error("Could not find like button bellow the post")
                return None

        return like_btn_view

    def _isPostLiked(self):

        like_btn_view = self._getPostLikeButton()
        if not like_btn_view:
            return False

        return like_btn_view.get_selected()

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
            like_btn_view = self._getPostLikeButton()
            if not like_btn_view:
                return False
            like_btn_view.click()
        else:

            if post_media_view.exists(True):
                post_media_view.double_click()
            else:
                logger.error("Could not find post area to double click")
                return False

        random_sleep()

        return self._isPostLiked()

    def open_likers(self):
        while True:
            likes_view = self.device.find(
                resourceId="com.instagram.android:id/row_feed_textview_likes",
                className="android.widget.TextView",
            )
            if likes_view.exists(True):
                likes_view_text = likes_view.get_text()
                if (
                    likes_view_text[-6:].upper() == "OTHERS"
                    or likes_view_text.upper()[-5:] == "LIKES"
                ):
                    logger.info("Opening post likers")
                    random_sleep()
                    likes_view.click(likes_view.Location.RIGHT)
                    return True
                else:
                    logger.info("This post has only 1 liker, skip")
                    return False
            else:
                return False

    def _getListViewLikers(self):
        return self.device.find(
            resourceId="android:id/list", className="android.widget.ListView"
        )

    def _getUserCountainer(self):
        return self.device.find(
            resourceId="com.instagram.android:id/row_user_container_base",
            className="android.widget.LinearLayout",
        )

    def _getUserName(self, countainer):
        return countainer.child(
            resourceId="com.instagram.android:id/row_user_primary_name",
            className="android.widget.TextView",
        )


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
                "com.instagram.android:id/action_bar_title",
                "com.instagram.android:id/action_bar_large_title",
                "com.instagram.android:id/action_bar_textview_title",
            ]
        )
        return self.action_bar.child(
            resourceIdMatches=re_case_insensitive, className="android.widget.TextView"
        )

    def getUsername(self, error=True):
        title_view = self._getActionBarTitleBtn()
        if title_view.exists():
            return title_view.get_text()
        if error:
            logger.error("Cannot get username")
        return None

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
            count = post_count_view.get_text()
            if count != None:
                return self._parseCounter(count)
            else:
                logger.error("Cannot get posts count text")
                return 0
        else:
            logger.error("Cannot get posts count text")
            return 0

    def count_photo_in_view(self):
        """return rows filled and the number of post in the last row"""
        RECYCLER_VIEW = "androidx.recyclerview.widget.RecyclerView|android.view.View"
        grid_post = self.device.find(
            classNameMatches=RECYCLER_VIEW, resourceIdMatches="android:id/list"
        )
        if grid_post.exists():  # max 4 rows supported
            for i in range(2, 6):
                lin_layout = grid_post.child(
                    index=i, className="android.widget.LinearLayout"
                )
                if i == 5 or not lin_layout.exists(True):
                    last_index = i - 1
                    last_lin_layout = grid_post.child(index=last_index)
                    for n in range(1, 4):
                        if n == 3 or not last_lin_layout.child(index=n).exists(True):
                            if n == 3:
                                return last_index, 0
                            else:
                                return last_index - 1, n
        else:
            return 0, 0

    def getProfileInfo(self):

        username = self.getUsername()
        followers = self.getFollowersCount()
        following = self.getFollowingCount()

        return username, followers, following

    def getProfileBiography(self):
        biography = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/profile_header_bio_text"
            ),
            className="android.widget.TextView",
        )
        if biography.exists():
            biography_text = biography.get_text()
            # If the biography is very long, blabla text and end with "...more" click the bottom of the text and get the new text
            is_long_bio = re.compile(
                r"{0}$".format("… more"), flags=re.IGNORECASE
            ).search(biography_text)
            if is_long_bio is not None:
                biography.click(biography.Location.BOTTOM)
                return biography.get_text()
            return biography_text
        return ""

    def getFullName(self):
        full_name_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                "com.instagram.android:id/profile_header_full_name"
            ),
            className="android.widget.TextView",
        )
        if full_name_view.exists():
            fullname_text = full_name_view.get_text()
            if fullname_text is not None:
                return fullname_text
        return ""

    def isPrivateAccount(self):
        private_profile_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                [
                    "com.instagram.android:id/private_profile_empty_state",
                    "com.instagram.android:id/row_profile_header_empty_profile_notice_title",
                    "com.instagram.android:id/row_profile_header_empty_profile_notice_container",
                ]
            )
        )
        return private_profile_view.exists(True)

    def isStoryAvailable(self):
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

    def swipe_to_fit_posts(self):
        """calculate the right swipe amount necessary to see 12 photos"""
        PROFILE_TABS_CONTAINER = "com.instagram.android:id/profile_tabs_container"
        ACTION_BAR_CONTAINER = "com.instagram.android:id/action_bar_container"
        displayWidth = self.device.get_info()["displayWidth"]
        element_to_swipe_over_obj = self.device.find(
            resourceIdMatches=PROFILE_TABS_CONTAINER
        )
        if not element_to_swipe_over_obj.exists():
            self.device.swipe_points(displayWidth / 2, 600, displayWidth / 2, 300)
            element_to_swipe_over_obj = self.device.find(
                resourceIdMatches=PROFILE_TABS_CONTAINER
            )

        element_to_swipe_over = element_to_swipe_over_obj.get_bounds()["top"]
        bar_countainer = self.device.find(
            resourceIdMatches=ACTION_BAR_CONTAINER
        ).get_bounds()["bottom"]

        logger.info("Scrolled down to see more posts.")
        self.device.swipe_points(
            displayWidth / 2, element_to_swipe_over, displayWidth / 2, bar_countainer
        )
        return

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

        attempts = 0
        while not button.exists():
            attempts += 1
            self.device.swipe(DeviceFacade.Direction.TOP, scale=0.1)
            if attempts > 2:
                logger.error(f"Cannot navigate to tab '{description}'")
                save_crash(self.device)
                return

        button.click()

    def _getRecyclerView(self):
        CLASSNAME = "(androidx.recyclerview.widget.RecyclerView|android.view.View)"

        return self.device.find(classNameMatches=CLASSNAME)


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
        return (
            "" if not reel_viewer_title.exists(True) else reel_viewer_title.get_text()
        )

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
        return None


class LanguageNotEnglishException(Exception):
    pass
