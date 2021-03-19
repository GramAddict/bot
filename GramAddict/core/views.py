import datetime
import logging
import re
from enum import Enum, auto
from colorama import Fore, Style
from random import randint, uniform

import emoji

from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.resources import ClassName, ResourceID as resources, TabBarText
from GramAddict.core.utils import ActionBlockedError, random_sleep, save_crash

logger = logging.getLogger(__name__)


def load_config(config):
    global args
    global configs
    global ResourceID
    args = config.args
    configs = config
    ResourceID = resources(config.args.app_id)


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


class FollowStatus(Enum):
    FOLLOW = auto()
    FOLLOWING = auto()
    FOLLOW_BACK = auto()
    REQUESTED = auto()


class SwipeTo(Enum):
    HALF_PHOTO = auto()
    NEXT_POST = auto()


class LikeMode(Enum):
    SINGLE_CLICK = auto()
    DOUBLE_CLICK = auto()


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class MediaType(Enum):
    PHOTO = auto()
    VIDEO = auto()
    IGTV = auto()
    CAROUSEL = auto()


class Owner(Enum):
    OPEN = auto()
    GET_NAME = auto()


class TabBarView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getTabBar(self):
        tab_bar = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.TAB_BAR),
            className=ClassName.LINEAR_LAYOUT,
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
        if tab == TabBarTabs.HOME:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.HOME_CONTENT_DESC),
            )
            button.wait()
        elif tab == TabBarTabs.SEARCH:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.SEARCH_CONTENT_DESC),
            )
            button.wait()
            if not button.exists():
                # Some accounts display the search btn only in Home -> action bar
                logger.debug("Didn't find search in the tab bar...")
                home_view = self.navigateToHome()
                home_view.navigateToSearch()
                return
        elif tab == TabBarTabs.REELS:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.REELS_CONTENT_DESC),
            )
            button.wait()
        elif tab == TabBarTabs.ORDERS:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.ORDERS_CONTENT_DESC),
            )
            button.wait()

        elif tab == TabBarTabs.ACTIVITY:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(
                    TabBarText.ACTIVITY_CONTENT_DESC
                ),
            )
            button.wait()
        elif tab == TabBarTabs.PROFILE:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.PROFILE_CONTENT_DESC),
            )
            button.wait()

        if button.exists():
            # Two clicks to reset tab content
            random_sleep(1, 2)
            button.click()
            random_sleep(1, 2)
            if tab is not TabBarTabs.PROFILE:
                button.click()
                random_sleep(1, 2)

            return

        logger.error(f"Didn't find tab {tab_name} in the tab bar...")


class ActionBarView:
    def __init__(self, device: DeviceFacade):
        self.device = device
        self.action_bar = self._getActionBar()

    def _getActionBar(self):
        tab_bar = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.ACTION_BAR_CONTAINER),
            className=ClassName.FRAME_LAYOUT,
        )
        return tab_bar


class HomeView(ActionBarView):
    def __init__(self, device: DeviceFacade):
        super().__init__(device)
        self.device = device

    def navigateToSearch(self):
        logger.debug("Navigate to Search")
        search_btn = self.action_bar.child(
            descriptionMatches=case_insensitive_re(TabBarText.SEARCH_CONTENT_DESC)
        )
        search_btn.click()

        return SearchView(self.device)


class HashTagView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getRecyclerView(self):
        views = f"({ClassName.RECYCLER_VIEW}|{ClassName.VIEW})"
        # wait until it gest rendered
        obj = self.device.find(classNameMatches=views)
        obj.wait()
        return obj

    def _getFistImageView(self, recycler):
        obj = recycler.child(
            className=ClassName.IMAGE_VIEW,
            resourceIdMatches=ResourceID.IMAGE_BUTTON,
        )
        obj.wait()
        return obj

    def _getRecentTab(self):
        obj = self.device.find(
            className=ClassName.TEXT_VIEW,
            textMatches=case_insensitive_re(TabBarText.RECENT_CONTENT_DESC),
        )
        obj.wait()
        return obj


# The place view for the moment It's only a copy/paste of HashTagView
# Maybe we can add the com.instagram.android:id/category_name == "Country/Region" (or other obv)


class PlacesView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getRecyclerView(self):
        views = f"({ClassName.RECYCLER_VIEW}|{ClassName.VIEW})"
        return self.device.find(classNameMatches=views)

    def _getFistImageView(self, recycler):
        return recycler.child(
            className=ClassName.IMAGE_VIEW,
            resourceIdMatches=ResourceID.IMAGE_BUTTON,
        )

    def _getRecentTab(self):
        return self.device.find(
            className=ClassName.TEXT_VIEW,
            textMatches=case_insensitive_re(TabBarText.RECENT_CONTENT_DESC),
        )

    def _getInformBody(self):
        return self.device.find(
            className=ClassName.TEXT_VIEW,
            resourceId=ResourceID.INFORM_BODY,
        )


class SearchView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getSearchEditText(self):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT
            ),
            className=ClassName.EDIT_TEXT,
        )

    def _getUsernameRow(self, username):
        obj = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.ROW_SEARCH_USER_USERNAME),
            className=ClassName.TEXT_VIEW,
            textMatches=case_insensitive_re(username),
        )
        obj.wait()
        return obj

    def _getHashtagRow(self, hashtag):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.ROW_HASHTAG_TEXTVIEW_TAG_NAME
            ),
            className=ClassName.TEXT_VIEW,
            text=f"#{hashtag}",
        )

    def _getPlaceRow(self):
        obj = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.ROW_PLACE_TITLE),
            className=ClassName.TEXT_VIEW,
        )
        obj.wait()
        return obj

    def _getTabTextView(self, tab: SearchTabs):
        tab_layout = self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.FIXED_TABBAR_TABS_CONTAINER
            ),
            className=ClassName.LINEAR_LAYOUT,
        )

        tab_text_view = tab_layout.child(
            resourceIdMatches=case_insensitive_re(ResourceID.TAB_BUTTON_NAME_TEXT),
            className=ClassName.TEXT_VIEW,
            textMatches=case_insensitive_re(tab.name),
        )
        return tab_text_view

    def _searchTabWithTextPlaceholder(self, tab: SearchTabs):
        tab_layout = self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.FIXED_TABBAR_TABS_CONTAINER
            ),
            className=ClassName.LINEAR_LAYOUT,
        )
        search_edit_text = self._getSearchEditText()

        fixed_text = "Search {}".format(tab.name if tab.name != "TAGS" else "hashtags")
        logger.debug(
            "Going to check if the search bar have as placeholder: {}".format(
                fixed_text
            )
        )

        for item in tab_layout.child(
            resourceId=ResourceID.TAB_BUTTON_FALLBACK_ICON,
            className=ClassName.IMAGE_VIEW,
        ):
            item.click()

            # Little trick for force-update the ui and placeholder text
            search_edit_text.click()
            SearchView(self.device)._close_keyboard()

            if self.device.find(
                className=ClassName.TEXT_VIEW,
                textMatches=case_insensitive_re(fixed_text),
            ).exists():
                return item
        return None

    def navigateToUsername(
        self, username, interact_usernames=False, swipe_to_accounts=True
    ):
        logger.debug("Search for @" + username)
        search_edit_text = self._getSearchEditText()
        search_edit_text.click()
        random_sleep(1, 2)
        if swipe_to_accounts:
            SearchView(self.device)._close_keyboard()
            random_sleep(1, 2)
            DeviceFacade.swipe(self.device, DeviceFacade.Direction.LEFT, 0.8)
            random_sleep(1, 2)
        if interact_usernames:
            search_edit_text.set_text(username)
        else:
            searched_user_recent = self._getUsernameRow(username)
            if searched_user_recent.exists():
                searched_user_recent.click()
                return ProfileView(self.device, is_own_profile=False)
            search_edit_text.set_text(username)
            SearchView(self.device)._close_keyboard()
        random_sleep()
        username_view = self._getUsernameRow(username)
        if not username_view.exists():
            logger.error("Cannot find user @" + username + ".")
            save_crash(self.device)
            return None
        username_view.click()

        return ProfileView(self.device, is_own_profile=False)

    def navigateToHashtag(self, hashtag):
        logger.info(f"Navigate to hashtag {emoji.emojize(hashtag, use_aliases=True)}")
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
        tabbar_container = self.device.find(
            resourceId=ResourceID.FIXED_TABBAR_TABS_CONTAINER
        )
        if tabbar_container.exists():
            delta = tabbar_container.get_bounds()["bottom"]
        else:
            delta = 375

        SearchView(self.device)._close_keyboard()
        random_sleep(1, 2)
        # check if that hashtag already exists in the recent search list -> act as human
        hashtag_view_recent = self._getHashtagRow(
            emoji.demojize(hashtag, use_aliases=True)[1:]
        )

        if hashtag_view_recent.exists():
            hashtag_view_recent.click()
            random_sleep()
            return HashTagView(self.device)

        logger.info(
            f"{emoji.emojize(hashtag, use_aliases=True)} is not in recent searching history.."
        )
        search_edit_text.set_text(emoji.emojize(hashtag, use_aliases=True))
        hashtag_view = self._getHashtagRow(emoji.emojize(hashtag, use_aliases=True)[1:])
        random_sleep()

        if not hashtag_view.exists():
            SearchView(self.device)._close_keyboard()
            UniversalActions(self.device)._swipe_points(
                direction=Direction.DOWN,
                start_point_y=randint(delta + 10, delta + 150),
                delta_y=randint(150, 250),
            )

            hashtag_view = self._getHashtagRow(
                emoji.emojize(hashtag, use_aliases=True)[1:]
            )
            if not hashtag_view.exists():
                logger.error(
                    f"Cannot find hashtag {emoji.emojize(hashtag, use_aliases=True)}."
                )
                return None

        hashtag_view.click()
        random_sleep()

        return HashTagView(self.device)

    def navigateToPlaces(self, place):
        logger.info(f"Navigate to place {place}")
        search_edit_text = self._getSearchEditText()
        search_edit_text.click()
        random_sleep(1, 2)
        place_tab = self._getTabTextView(SearchTabs.PLACES)
        if not place_tab.exists():
            logger.debug(
                "Cannot find tab: Places. Going to attempt to search for placeholder in all tabs"
            )
            place_tab = self._searchTabWithTextPlaceholder(SearchTabs.PLACES)
            if place_tab is None:
                logger.error("Cannot find tab: Places.")
                save_crash(self.device)
                return None
        place_tab.click()
        random_sleep(1, 2)
        SearchView(self.device)._close_keyboard()
        random_sleep(1, 2)

        search_edit_text.set_text(place)

        # After set_text we assume that the the first occurency It's correct
        # That's because for example if we type: 'Italia' on my English device the first result is: 'Italy' (and it's correct)
        # I mean, we can't search for text because 'Italia' != 'Italy', but It's also the correct item

        place_view = self._getPlaceRow()
        random_sleep()

        if not place_view.exists():
            logger.error(f"Cannot find place {place}, abort.")
            save_crash(self.device)
            return None

        place_view.click()
        random_sleep()

        return PlacesView(self.device)

    def _close_keyboard(self):
        flag = DeviceFacade.is_keyboard_show(self.device)
        if flag:
            logger.debug("The keyboard is currently open. Press back to close.")
            self.device.back()
        elif flag is None:
            tabbar_container = self.device.find(
                resourceId=ResourceID.FIXED_TABBAR_TABS_CONTAINER
            )
            if tabbar_container.exists():
                delta = tabbar_container.get_bounds()["bottom"]
            else:
                delta = 375
            logger.debug(
                "Failed to check if keyboard is open! Will do a little swipe up to prevent errors."
            )
            UniversalActions(self.device)._swipe_points(
                direction=Direction.UP,
                start_point_y=randint(delta + 10, delta + 150),
                delta_y=randint(50, 100),
            )


class PostsViewList:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def swipe_to_fit_posts(self, swipe: SwipeTo):
        """calculate the right swipe amount necessary to swipe to next post in hashtag post view
        in order to make it available to other plug-ins I cutted it in two moves"""
        displayWidth = self.device.get_info()["displayWidth"]
        containers_content = ResourceID.CAROUSEL_MEDIA_GROUP_AND_ZOOMABLE_VIEW_CONTAINER
        containers_gap = ResourceID.GAP_VIEW_AND_FOOTER_SPACE

        # move type: half photo
        if swipe == SwipeTo.HALF_PHOTO:
            zoomable_view_container = self.device.find(
                resourceIdMatches=containers_content
            ).get_bounds()["bottom"]
            self.device.swipe_points(
                displayWidth / 2,
                zoomable_view_container - 5,
                displayWidth / 2,
                zoomable_view_container * 0.5,
            )
        # move type: gap/footer to next post
        elif swipe == SwipeTo.NEXT_POST:
            logger.info(
                "Scroll down to see next post.", extra={"color": f"{Fore.GREEN}"}
            )
            gap_view_obj = self.device.find(resourceIdMatches=containers_gap)
            for _ in range(2):
                if not gap_view_obj.exists():
                    logger.debug("Can't find the gap obj, scroll down a little more.")
                    PostsViewList(self.device).swipe_to_fit_posts(SwipeTo.HALF_PHOTO)
                    gap_view_obj = self.device.find(resourceIdMatches=containers_gap)
                    if not gap_view_obj.exists():
                        continue
                    else:
                        break
            gap_view = gap_view_obj.get_bounds()["top"]
            zoomable_view_container = self.device.find(
                resourceIdMatches=(containers_content)
            ).get_bounds()["top"]
            self.device.swipe_points(
                displayWidth / 2,
                gap_view - 5,
                displayWidth / 2,
                zoomable_view_container + 5,
            )
            return True

    def _find_likers_container(self):
        containers_gap = ResourceID.GAP_VIEW_AND_FOOTER_SPACE
        gap_view_obj = self.device.find(resourceIdMatches=containers_gap)
        likes_view = self.device.find(
            resourceId=ResourceID.ROW_FEED_TEXTVIEW_LIKES,
            className=ClassName.TEXT_VIEW,
        )
        PostsViewList(self.device).swipe_to_fit_posts(SwipeTo.HALF_PHOTO)
        for _ in range(2):
            if not likes_view.exists():
                if not gap_view_obj.exists():
                    PostsViewList(self.device).swipe_to_fit_posts(SwipeTo.HALF_PHOTO)
                else:
                    return True
            else:
                return True
        return False

    def _check_if_only_one_liker_or_none(self):
        likes_view = self.device.find(
            resourceId=ResourceID.ROW_FEED_TEXTVIEW_LIKES,
            className=ClassName.TEXT_VIEW,
        )
        if likes_view.exists():
            likes_view_text = likes_view.get_text()
            if (
                likes_view_text[-6:].upper() == "OTHERS"
                or likes_view_text.upper()[-5:] == "LIKES"
            ):
                return False
            else:
                logger.info("This post has only 1 liker, skip.")
                return True
        else:
            logger.info("This post has no likers, skip.")
            return True

    def open_likers_container(self):
        likes_view = self.device.find(
            resourceId=ResourceID.ROW_FEED_TEXTVIEW_LIKES,
            className=ClassName.TEXT_VIEW,
        )
        logger.info("Opening post likers.")
        random_sleep()
        likes_view.click(DeviceFacade.Location.RIGHT)

    def _check_if_last_post(self, last_description):
        """check if that post has been just interacted"""
        swiped_a_bit = False
        n = 1
        while n < 3:
            post_description = self.device.find(
                resourceId=ResourceID.ROW_FEED_COMMENT_TEXTVIEW_LAYOUT
            )
            if post_description.exists():
                new_description = post_description.get_text().upper()
                if swiped_a_bit:
                    logger.debug("Revert the last swipe.")
                    UniversalActions(self.device)._swipe_points(direction=Direction.UP)
                if new_description == last_description:
                    logger.info(
                        "This post has the same description and author as the last one."
                    )
                    return True, new_description
                else:
                    return False, new_description
            else:
                if n < 2:
                    logger.debug(
                        "Can't find the description, try to swipe a little bit down."
                    )
                    UniversalActions(self.device)._swipe_points(
                        direction=Direction.DOWN
                    )
                    swiped_a_bit = True
                    n += 1
                else:
                    logger.info(
                        "Can't find the description of this post. Maybe it's blank.."
                    )
                    return False, ""

    def _if_action_bar_is_over_obj_swipe(self, obj):
        """do a swipe of the amount of the action bar"""
        action_bar_exists, _, action_bar_bottom = PostsViewList(
            self.device
        )._get_action_bar_position()
        if action_bar_exists:
            obj_top = obj.get_bounds()["top"]
            if action_bar_bottom > obj_top:
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.UP, delta_y=action_bar_bottom
                )

    def _get_action_bar_position(self):
        """action bar is overlayed, if you press on it you go back to the first post
        knowing his position is important to avoid it"""
        action_bar = self.device.find(
            resourceIdMatches=(ResourceID.ACTION_BAR_CONTAINER)
        )
        if action_bar.exists():
            return (
                True,
                action_bar.get_bounds()["top"],
                action_bar.get_bounds()["bottom"],
            )
        else:
            return False, 0, 0

    def _post_owner(self, mode: Owner):
        post_owner_obj = self.device.find(
            resourceIdMatches=(ResourceID.ROW_FEED_PHOTO_PROFILE_NAME)
        )
        post_owner_clickable = False
        for _ in range(2):
            if not post_owner_obj.exists():
                UniversalActions(self.device)._swipe_points(direction=Direction.UP)
                post_owner_obj = self.device.find(
                    resourceIdMatches=(ResourceID.ROW_FEED_PHOTO_PROFILE_NAME)
                )
            else:
                post_owner_clickable = True
                break

        if not post_owner_clickable:
            logger.info("Can't find the owner name.")
            return False
        if mode == Owner.OPEN:
            logger.info("Open post owner.")
            PostsViewList(self.device)._if_action_bar_is_over_obj_swipe(post_owner_obj)
            post_owner_obj.click()
            return True
        elif mode == Owner.GET_NAME:
            return post_owner_obj.get_text()
        else:
            return False

    def _open_likers(self):
        while True:
            likes_view = self.device.find(
                resourceId=ResourceID.ROW_FEED_TEXTVIEW_LIKES,
                className=ClassName.TEXT_VIEW,
            )
            if likes_view.exists():
                likes_view_text = likes_view.get_text()
                if (
                    likes_view_text[-6:].upper() == "OTHERS"
                    or likes_view_text.upper()[-5:] == "LIKES"
                ):
                    logger.info("Opening post likers")
                    random_sleep()
                    PostsViewList(self.device)._if_action_bar_is_over_obj_swipe(
                        likes_view
                    )
                    likes_view.click(DeviceFacade.Location.RIGHT)
                    return True
                else:
                    logger.info("This post has only 1 liker, skip")
                    return False
            else:
                return False

    def _get_post_owner_name(self):
        return self.device.find(
            resourceIdMatches=(ResourceID.ROW_FEED_PHOTO_PROFILE_NAME)
        ).get_text()

    def _like_in_post_view(self, mode: LikeMode):
        POST_CONTAINER = ResourceID.CAROUSEL_MEDIA_GROUP_AND_ZOOMABLE_VIEW_CONTAINER

        if mode == LikeMode.DOUBLE_CLICK:
            logger.info("Double click photo.")
            _, _, action_bar_bottom = PostsViewList(
                self.device
            )._get_action_bar_position()
            self.device.find(resourceIdMatches=(POST_CONTAINER)).double_click(
                obj_over=action_bar_bottom
            )
        elif mode == LikeMode.SINGLE_CLICK:
            logger.info("Like photo from button.")
            self.device.find(resourceIdMatches=ResourceID.ROW_FEED_BUTTON_LIKE).click()

    def _follow_in_post_view(self):
        logger.info("Follow blogger in place.")
        self.device.find(resourceIdMatches=(ResourceID.BUTTON)).click()

    def _comment_in_post_view(self):
        logger.info("Open comments of post.")
        self.device.find(resourceIdMatches=(ResourceID.ROW_FEED_BUTTON_COMMENT)).click()

    def _check_if_liked(self, first_attemp=True):
        STR = "Liked"
        logger.debug("Check if like succeded in post view.")
        bnt_like_obj = self.device.find(
            resourceIdMatches=ResourceID.ROW_FEED_BUTTON_LIKE
        )
        if bnt_like_obj.exists():
            if self.device.find(descriptionMatches=case_insensitive_re(STR)).exists(
                True
            ):
                logger.debug("Like is present.")
                return True
            else:
                logger.debug("Like is not present.")
                return False
        else:
            UniversalActions(self.device)._swipe_points(direction=Direction.DOWN)
            if first_attemp:
                return PostsViewList(self.device)._check_if_liked(False)
            else:
                logger.debug("Like btn not present.")
                return False


class LanguageView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def setLanguage(self, language: str):
        logger.debug(f"Set language to {language}")
        search_edit_text = self.device.find(
            resourceId=ResourceID.SEARCH,
            className=ClassName.EDIT_TEXT,
        )
        search_edit_text.set_text(language)

        list_view = self.device.find(
            resourceId=ResourceID.LANGUAGE_LIST_LOCALE,
            className=ClassName.LIST_VIEW,
        )
        first_item = list_view.child(index=0)
        first_item.click()


class AccountView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToLanguage(self):
        logger.debug("Navigate to Language")
        button = self.device.find(
            className=ClassName.BUTTON,
            index=5,
        )
        button.click()

        return LanguageView(self.device)

    def changeToUsername(self, username):
        action_bar = self.device.find(resourceId=ResourceID.ACTION_BAR_LARGE_TITLE)
        current_profile_name = action_bar.get_text()
        current_profile_name_upper = current_profile_name.upper()
        # in private accounts there is little lock which is codec as two spaces (should be \u1F512)
        if current_profile_name_upper.replace(" ", "") == username.upper():
            logger.info(
                f"You are already logged as {username}!",
                extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
            )
            return True
        logger.debug(f"You're logged as {current_profile_name.replace(' ', '')}")
        if action_bar.exists():
            action_bar.click()
            random_sleep()
            found_obj = self.device.find(
                resourceId=ResourceID.ROW_USER_TEXTVIEW,
                textMatches=case_insensitive_re(username),
            )
            if found_obj.exists():
                logger.info(
                    f"Switching to {username}...",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
                found_obj.click()
                random_sleep()
                action_bar = self.device.find(
                    resourceId=ResourceID.ACTION_BAR_LARGE_TITLE
                )
                current_profile_name = action_bar.get_text().upper()
                if current_profile_name.replace(" ", "") == username.upper():
                    return True
        return False


class SettingsView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToAccount(self):
        logger.debug("Navigate to Account")
        button = self.device.find(
            # textMatches=case_insensitive_re("Account"),
            # resourceId=ResourceID.ROW_SIMPLE_TEXT_TEXTVIEW,
            className=ClassName.BUTTON,
            index=6,
        )
        button.click()
        return AccountView(self.device)


class OptionsView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToSettings(self):
        logger.debug("Navigate to Settings")
        button = self.device.find(
            resourceId=ResourceID.MENU_SETTINGS_ROW,
            className=ClassName.TEXT_VIEW,
        )
        button.click()
        return SettingsView(self.device)


class OpenedPostView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getPostLikeButton(self, scroll_to_find=True):
        """Find the like button right bellow a post.
        Note: sometimes the like button from the post above or bellow are
        dumped as well, so we need handle that situation.

        scroll_to_find: if the like button is not found, scroll a bit down
                        to try to find it. Default: True
        """
        post_view_area = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.LIST)
        )
        if not post_view_area.exists():
            logger.debug("Cannot find post recycler view area")
            save_crash(self.device)
            self.device.back()
            return None

        post_media_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.CAROUSEL_MEDIA_GROUP_AND_ZOOMABLE_VIEW_CONTAINER
            )
        )

        if not post_media_view.exists():
            logger.debug("Cannot find post media view area")
            save_crash(self.device)
            self.device.back()
            return None

        like_btn_view = post_media_view.down(
            resourceIdMatches=case_insensitive_re(ResourceID.ROW_FEED_BUTTON_LIKE)
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
            not like_btn_view.exists()
            or not is_like_btn_in_the_bottom
            or not is_like_btn_visible
        ):
            if scroll_to_find:
                logger.debug("Try to scroll tiny bit down...")
                # Remember: to scroll down we need to swipe up :)
                for _ in range(3):
                    self.device.swipe(DeviceFacade.Direction.TOP, scale=0.25)
                    like_btn_view = self.device.find(
                        resourceIdMatches=case_insensitive_re(
                            ResourceID.ROW_FEED_BUTTON_LIKE
                        )
                    )
                    if like_btn_view.exists():
                        break

            if not scroll_to_find or not like_btn_view.exists():
                logger.error("Could not find like button bellow the post")
                return None

        return like_btn_view

    def _isPostLiked(self):

        like_btn_view = self._getPostLikeButton()
        if not like_btn_view:
            return False

        return like_btn_view.get_selected()

    def likePost(self, click_btn_like=False):
        post_media_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.CAROUSEL_MEDIA_GROUP_AND_ZOOMABLE_VIEW_CONTAINER
            )
        )

        if click_btn_like:
            like_btn_view = self._getPostLikeButton()
            if not like_btn_view:
                return False
            like_btn_view.click()
        else:
            if post_media_view.exists():
                post_media_view.double_click()
            else:
                logger.error("Could not find post area to double click")
                return False

        random_sleep()

        return self._isPostLiked()

    def _getListViewLikers(self):
        self.device.find(resourceId=ResourceID.LIST).wait()
        return self.device.find(resourceId=ResourceID.LIST)

    def _getUserCountainer(self):
        self.device.find(
            resourceId=ResourceID.ROW_USER_CONTAINER_BASE,
        ).wait()
        return self.device.find(
            resourceId=ResourceID.ROW_USER_CONTAINER_BASE,
        )

    def _getUserName(self, countainer):
        return countainer.child(
            resourceId=ResourceID.ROW_USER_PRIMARY_NAME,
            className=ClassName.TEXT_VIEW,
        )

    def _isFollowing(self, countainer):
        text = countainer.child(
            resourceId=ResourceID.BUTTON,
            classNameMatches=ClassName.BUTTON_OR_TEXTVIEW_REGEX,
        )
        # UIA1 doesn't use .get_text()
        if type(text) != str:
            text = text.get_text() if text.exists() else ""
        return True if text == "Following" or text == "Requested" else False


class PostsGridView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def scrollDown(self):
        coordinator_layout = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.COORDINATOR_ROOT_LAYOUT)
        )
        if coordinator_layout.exists():
            coordinator_layout.scroll(DeviceFacade.Direction.BOTTOM)
            return True

        return False

    def navigateToPost(self, row, col):
        obj_count = 1
        post_list_view = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.LIST)
        )
        post_list_view.wait()
        OFFSET = 1  # row with post starts from index 1
        row_view = post_list_view.child(index=row + OFFSET)
        if not row_view.exists():
            return None, None, None
        post_view = row_view.child(index=col)
        if not post_view.exists():
            return None, None, None
        content_desc = post_view.ui_info()["contentDescription"]
        if re.match("^Photo", content_desc, re.IGNORECASE):
            logger.info("It's a photo.")
            media_type = MediaType.PHOTO
        elif re.match("^Video", content_desc, re.IGNORECASE):
            logger.info("It's a video.")
            media_type = MediaType.VIDEO
        elif re.match("^IGTV", content_desc, re.IGNORECASE):
            logger.info("It's a IGTV.")
            media_type = MediaType.IGTV
        else:
            carousel_obj = re.match(
                "(\d+ photo)|(\d+ video)", content_desc, re.IGNORECASE
            )
            n_photos = (
                int(carousel_obj.group(1)[0])
                if (carousel_obj.group(1) is not None)
                else 0
            )
            n_videos = (
                int(carousel_obj.group(2)[0])
                if (carousel_obj.group(2) is not None)
                else 0
            )
            logger.info(
                f"It's a carousel with {n_photos} photo(s) and {n_videos} video(s)."
            )
            obj_count = n_photos + n_videos
            media_type = MediaType.CAROUSEL
        post_view.click()

        return OpenedPostView(self.device), media_type, obj_count


class ProfileView(ActionBarView):
    def __init__(self, device: DeviceFacade, is_own_profile=False):
        super().__init__(device)
        self.device = device
        self.is_own_profile = is_own_profile

    def navigateToOptions(self):
        logger.debug("Navigate to Options")
        button = self.action_bar.child(index=2)
        button.click()

        return OptionsView(self.device)

    def _getActionBarTitleBtn(self):
        action_bar = case_insensitive_re(
            [
                ResourceID.TITLE_VIEW,
                ResourceID.ACTION_BAR_TITLE,
                ResourceID.ACTION_BAR_LARGE_TITLE,
                ResourceID.ACTION_BAR_TEXTVIEW_TITLE,
            ]
        )
        bar = self.action_bar.child(
            resourceIdMatches=action_bar, className=ClassName.TEXT_VIEW
        )
        if not bar.exists():
            bar = self.device.find(
                resourceIdMatches=action_bar, className=ClassName.TEXT_VIEW
            )
        return bar

    def _getSomeText(self):
        try:
            post = (
                self.device.find(
                    resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_POST_CONTAINER
                )
                .child(index=1)
                .get_text()
            )
            followers = (
                self.device.find(
                    resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_FOLLOWERS_CONTAINER
                )
                .child(index=1)
                .get_text()
            )
            following = (
                self.device.find(
                    resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_FOLLOWING_CONTAINER
                )
                .child(index=1)
                .get_text()
            )
            return post, followers, following
        except:
            return None, None, None

    def _click_on_avatar(self):
        self.device.find(resourceIdMatches=ResourceID.TAB_AVATAR).wait()
        self.device.find(resourceIdMatches=ResourceID.TAB_AVATAR).click()

    def getFollowButton(self):
        button_regex = f"{ClassName.BUTTON}|{ClassName.TEXT_VIEW}"
        following_regex_all = "^Following|^Requested|^Follow Back$"
        following_or_follow_back_button = self.device.find(
            classNameMatches=button_regex,
            clickable=True,
            textMatches=following_regex_all,
        )
        following_or_follow_back_button.wait(DeviceFacade.Timeout.SHORT)
        if following_or_follow_back_button.exists():
            following_regex = "^Following|^Requested"
            following_button = self.device.find(
                classNameMatches=button_regex,
                clickable=True,
                textMatches=following_regex,
            )

            if following_button.exists():
                return following_button, FollowStatus.FOLLOWING

            followback_regex = "^Follow Back$"
            followback_button = self.device.find(
                classNameMatches=button_regex,
                clickable=True,
                textMatches=followback_regex,
            )
            if followback_button.exists():
                return followback_button, FollowStatus.FOLLOW_BACK

        return None, FollowStatus.FOLLOW

    def getUsername(self, error=True):
        title_view = self._getActionBarTitleBtn()
        if title_view.exists():
            return title_view.get_text(error).replace(" ", "")
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
            logger.error(f"Cannot parse {text}.")
        return count

    def _getFollowersTextView(self):
        followers_text_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWERS_COUNT
            ),
            className=ClassName.TEXT_VIEW,
        )
        followers_text_view.wait
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
                ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWING_COUNT
            ),
            className=ClassName.TEXT_VIEW,
        )
        following_text_view.wait()
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
                ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_POST_COUNT
            )
        )
        post_count_view.wait()
        if post_count_view.exists():
            count = post_count_view.get_text()
            if count is not None:
                return self._parseCounter(count)
        logger.error("Cannot get posts count text")
        return 0

    def count_photo_in_view(self):
        """return rows filled and the number of post in the last row"""
        views = f"({ClassName.RECYCLER_VIEW}|{ClassName.VIEW})"
        grid_post = self.device.find(
            classNameMatches=views, resourceIdMatches=ResourceID.LIST
        )
        grid_post.wait()
        if grid_post.exists():  # max 4 rows supported
            for i in range(2, 6):
                lin_layout = grid_post.child(index=i, className=ClassName.LINEAR_LAYOUT)
                if i == 5 or not lin_layout.exists():
                    last_index = i - 1
                    last_lin_layout = grid_post.child(index=last_index)
                    for n in range(1, 4):
                        if n == 3 or not last_lin_layout.child(index=n).exists():
                            if n == 3:
                                return last_index, 0
                            else:
                                return last_index - 1, n
        else:
            return 0, 0

    def getProfileInfo(self):

        username = self.getUsername().replace(" ", "")
        followers = self.getFollowersCount()
        following = self.getFollowingCount()

        return username, followers, following

    def getProfileBiography(self):
        biography = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.PROFILE_HEADER_BIO_TEXT),
            className=ClassName.TEXT_VIEW,
        )
        biography.wait(DeviceFacade.Timeout.SHORT)
        if biography.exists():
            biography_text = biography.get_text()
            # If the biography is very long, blabla text and end with "...more" click the bottom of the text and get the new text
            is_long_bio = re.compile(
                r"{0}$".format("… more"), flags=re.IGNORECASE
            ).search(biography_text)
            if is_long_bio is not None:
                logger.debug('Found "… more" in bio - trying to expand')
                username = self.getUsername()
                for _ in range(2):
                    # Clicking the biography is dangerous. Clicking "bottomright" is safest so we can try to avoid hashtags and tags
                    biography.click(DeviceFacade.Location.BOTTOMRIGHT)
                    random_sleep()
                    if username == self.getUsername():
                        return biography.get_text()
                    logger.debug(
                        "We're not in the same page - did we click a hashtag or a tag? Go back."
                    )
                    self.device.back()
                logger.info("Failed to expand biography - checking short view.")
                return biography.get_text()
            return biography_text
        return ""

    def getFullName(self):
        full_name_view = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.PROFILE_HEADER_FULL_NAME),
            className=ClassName.TEXT_VIEW,
        )
        full_name_view.wait(DeviceFacade.Timeout.SHORT)
        if full_name_view.exists():
            fullname_text = full_name_view.get_text()
            if fullname_text is not None:
                return fullname_text
        return ""

    def isPrivateAccount(self):
        private_profile_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                [
                    ResourceID.PRIVATE_PROFILE_EMPTY_STATE,
                    ResourceID.ROW_PROFILE_HEADER_EMPTY_PROFILE_NOTICE_TITLE,
                    ResourceID.ROW_PROFILE_HEADER_EMPTY_PROFILE_NOTICE_CONTAINER,
                ]
            )
        )
        return private_profile_view.exists()

    def StoryRing(self):
        return self.device.find(
            resourceId=ResourceID.REEL_RING,
            className=ClassName.VIEW,
        )

    def profileImage(self):
        return self.device.find(
            resourceId=ResourceID.ROW_PROFILE_HEADER_IMAGEVIEW,
            className=ClassName.IMAGE_VIEW,
        )

    def navigateToFollowers(self):
        logger.debug("Navigate to Followers")
        followers_button = self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.ROW_PROFILE_HEADER_FOLLOWERS_CONTAINER
            )
        )
        followers_button.click()

    def swipe_to_fit_posts(self):
        """calculate the right swipe amount necessary to see 12 photos"""
        displayWidth = self.device.get_info()["displayWidth"]
        element_to_swipe_over_obj = self.device.find(
            resourceIdMatches=ResourceID.PROFILE_TABS_CONTAINER
        )
        for _ in range(2):
            if not element_to_swipe_over_obj.exists():
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.DOWN, delta_y=randint(300, 350)
                )
                element_to_swipe_over_obj = self.device.find(
                    resourceIdMatches=ResourceID.PROFILE_TABS_CONTAINER
                )
                continue

            element_to_swipe_over = element_to_swipe_over_obj.get_bounds()["top"]
            try:
                bar_countainer = self.device.find(
                    resourceIdMatches=ResourceID.ACTION_BAR_CONTAINER
                ).get_bounds()["bottom"]

                logger.info("Scrolled down to see more posts.")
                self.device.swipe_points(
                    displayWidth / 2,
                    element_to_swipe_over,
                    displayWidth / 2,
                    bar_countainer,
                )
                return element_to_swipe_over - bar_countainer
            except:
                logger.info("I'm not able to scroll down.")
                return 0
        logger.warning("Maybe a private or empty profile in which check failed.. Skip")
        save_crash(self.device)
        return -1

    def navigateToPostsTab(self):
        self._navigateToTab(TabBarText.POSTS_CONTENT_DESC)
        return PostsGridView(self.device)

    def navigateToIgtvTab(self):
        self._navigateToTab(TabBarText.IGTV_CONTENT_DESC)
        raise Exception("Not implemented")

    def navigateToReelsTab(self):
        self._navigateToTab(TabBarText.REELS_CONTENT_DESC)
        raise Exception("Not implemented")

    def navigateToEffectsTab(self):
        self._navigateToTab(TabBarText.EFFECTS_CONTENT_DESC)
        raise Exception("Not implemented")

    def navigateToPhotosOfYouTab(self):
        self._navigateToTab(TabBarText.PHOTOS_OF_YOU_CONTENT_DESC)
        raise Exception("Not implemented")

    def _navigateToTab(self, tab: TabBarText):
        tabs_view = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.PROFILE_TAB_LAYOUT),
            className=ClassName.HORIZONTAL_SCROLL_VIEW,
        )
        button = tabs_view.child(
            descriptionMatches=case_insensitive_re(tab),
            resourceIdMatches=case_insensitive_re(ResourceID.PROFILE_TAB_ICON_VIEW),
            className=ClassName.IMAGE_VIEW,
        )

        attempts = 0
        while not button.exists():
            attempts += 1
            self.device.swipe(DeviceFacade.Direction.TOP, scale=0.1)
            if attempts > 2:
                logger.error(f"Cannot navigate to tab '{tab}'")
                save_crash(self.device)
                return

        button.click()

    def _getRecyclerView(self):
        views = f"({ClassName.RECYCLER_VIEW}|{ClassName.VIEW})"

        return self.device.find(classNameMatches=views)


class CurrentStoryView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def getStoryFrame(self):
        return self.device.find(
            resourceId=ResourceID.REEL_VIEWER_MEDIA_CONTAINER,
            className=ClassName.FRAME_LAYOUT,
        )

    def getUsername(self):
        reel_viewer_title = self.device.find(
            resourceId=ResourceID.REEL_VIEWER_TITLE,
            className=ClassName.TEXT_VIEW,
        )
        return (
            ""
            if not reel_viewer_title.exists()
            else reel_viewer_title.get_text(error=False).replace(" ", "")
        )

    def getTimestamp(self):
        reel_viewer_timestamp = self.device.find(
            resourceId=ResourceID.REEL_VIEWER_TIMESTAMP,
            className=ClassName.TEXT_VIEW,
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


class UniversalActions:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _swipe_points(
        self,
        direction: Direction,
        start_point_x=-1,
        start_point_y=-1,
        delta_x=-1,
        delta_y=450,
    ):
        displayWidth = self.device.get_info()["displayWidth"]
        displayHeight = self.device.get_info()["displayHeight"]
        middle_point_x = displayWidth / 2
        if start_point_y == -1:
            start_point_y = displayHeight / 2
        if direction == Direction.UP:
            if start_point_y + delta_y > displayHeight:
                delta = start_point_y + delta_y - displayHeight
                start_point_y = start_point_y - delta
            self.device.swipe_points(
                middle_point_x,
                start_point_y,
                middle_point_x,
                start_point_y + delta_y,
            )
        elif direction == Direction.DOWN:
            if start_point_y - delta_y < 0:
                delta = abs(start_point_y - delta_y)
                start_point_y = start_point_y + delta
            self.device.swipe_points(
                middle_point_x,
                start_point_y,
                middle_point_x,
                start_point_y - delta_y,
            )
        elif direction == Direction.LEFT:
            if start_point_x == -1:
                start_point_x = displayWidth * 2 / 3
            if delta_x == -1:
                delta_x = uniform(0.95, 1.25) * (displayWidth / 2)
            self.device.swipe_points(
                start_point_x,
                start_point_y,
                start_point_x - delta_x,
                start_point_y,
            )

    def _reload_page(self):
        logger.info("Reload page")
        UniversalActions(self.device)._swipe_points(direction=Direction.UP)

    def detect_block(device):
        logger.debug("Checking for block...")
        block_dialog = device.find(
            resourceIdMatches=ResourceID.BLOCK_POPUP,
        )
        popup_body = device.find(
            resourceIdMatches=ResourceID.IGDS_HEADLINE_BODY,
        )
        regex = r".+deleted"
        popup_appears = block_dialog.exists(DeviceFacade.Timeout.SHORT)
        if popup_appears:
            if popup_body.exists():
                is_post_deleted = re.match(regex, popup_body.get_text(), re.IGNORECASE)
                if is_post_deleted:
                    logger.info(f"{is_post_deleted.group()}")
                    logger.debug("Click on OK button.")
                    device.find(
                        resourceIdMatches=ResourceID.NEGATIVE_BUTTON,
                    ).click()
                    is_blocked = False
                else:
                    is_blocked = True
            else:
                is_blocked = True
        else:
            is_blocked = False

        if is_blocked:
            logger.error("Probably block dialog is shown.")
            raise ActionBlockedError(
                "Seems that action is blocked. Consider reinstalling Instagram app and be more careful"
                " with limits!"
            )

    def _check_if_no_posts(self):
        # wait until it gest rendered
        obj = self.device.find(resourceId=ResourceID.IGDS_HEADLINE_EMPHASIZED_HEADLINE)
        obj.wait(DeviceFacade.Timeout.SHORT)
        return obj.exists()
