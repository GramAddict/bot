import logging

from colorama import Fore

from GramAddict.core.device_facade import Timeout
from GramAddict.core.views import (
    AccountView,
    HashTagView,
    LanguageView,
    OptionsView,
    PlacesView,
    PostsGridView,
    ProfileView,
    SearchView,
    SettingsView,
    TabBarView,
    UniversalActions,
)

logger = logging.getLogger(__name__)


def check_if_english(device):
    logger.debug("Navigate to PROFILE.")
    SearchView(device)._close_keyboard()
    ProfileView(device)._click_on_avatar()
    logger.debug("Checking if app is in English..")
    post, follower, following = ProfileView(device)._getSomeText()
    if None not in {post, follower, following}:
        if post == "Posts" and follower == "Followers" and following == "Following":
            logger.debug("Instagram in English.")
        else:
            logger.info("Switching to English locale", extra={"color": f"{Fore.GREEN}"})
            ProfileView(device).navigateToOptions()
            OptionsView(device).navigateToSettings()
            SettingsView(device).navigateToAccount()
            AccountView(device).navigateToLanguage()
            LanguageView(device).setLanguage("english")
            logger.debug(
                "After changing language, IG goes to feed. Let's go to profile view again."
            )
            ProfileView(device)._click_on_avatar()
    else:
        logger.warning(
            "Failed to check your Instagram language. Be sure to set it to English or the bot won't work!"
        )
    return ProfileView(device, is_own_profile=True)


def nav_to_blogger(device, username, current_job):
    """navigate to blogger (followers list or posts)"""
    _to_followers = True if current_job.endswith("followers") else False
    _to_following = True if current_job.endswith("following") else False
    if username is None:
        profile_view = TabBarView(device).navigateToProfile()
        if _to_followers:
            logger.info("Open your followers.")
            profile_view.navigateToFollowers()
        elif _to_following:
            logger.info("Open your following.")
            profile_view.navigateToFollowing()
    else:
        search_view = TabBarView(device).navigateToSearch()
        profile_view = search_view.navigateToUsername(username)
        if not profile_view:
            return False

        if _to_followers:
            logger.info(f"Open @{username} followers.")
            profile_view.navigateToFollowers()
        elif _to_following:
            logger.info(f"Open @{username} following.")
            profile_view.navigateToFollowing()

    return True


def nav_to_hashtag_or_place(device, target, current_job):
    """navigate to hashtag/place/feed list"""
    search_view = TabBarView(device).navigateToSearch()
    if (
        not search_view.navigateToHashtag(target)
        if current_job.startswith("hashtag")
        else not search_view.navigateToPlaces(target)
    ):
        return False

    TargetView = HashTagView if current_job.startswith("hashtag") else PlacesView

    if current_job.endswith("recent"):
        logger.info("Switching to Recent tab.")
        recent_tab = TargetView(device)._getRecentTab()
        if recent_tab.exists(Timeout.MEDIUM):
            recent_tab.click()
        else:
            return False

        if UniversalActions(device)._check_if_no_posts():
            UniversalActions(device)._reload_page()
            if UniversalActions(device)._check_if_no_posts():
                return False

    result_view = TargetView(device)._getRecyclerView()
    FistImageInView = TargetView(device)._getFistImageView(result_view)
    if FistImageInView.exists():
        logger.info(f"Opening the first result for {target}.")
        FistImageInView.click()
        return True
    else:
        logger.info(
            f"There is any result for {target} (not exists or doesn't load). Skip."
        )
        return False


def nav_to_post_likers(device, username, my_username):
    """navigate to blogger post likers"""
    if username == my_username:
        TabBarView(device).navigateToProfile()
    else:
        search_view = TabBarView(device).navigateToSearch()
        if not search_view.navigateToUsername(username):
            return False
    profile_view = ProfileView(device)
    is_private = profile_view.isPrivateAccount()
    posts_count = profile_view.getPostsCount()
    is_empty = posts_count == 0
    if is_private or is_empty:
        private_empty = "Private" if is_private else "Empty"
        logger.info(f"{private_empty} account.", extra={"color": f"{Fore.GREEN}"})
        return False
    logger.info(f"Opening the first post of {username}.")
    ProfileView(device).swipe_to_fit_posts()
    PostsGridView(device).navigateToPost(0, 0)
    return True


def nav_to_feed(device):
    TabBarView(device).navigateToHome()
