import logging
import sys
from random import randint

from colorama import Fore

from GramAddict.core.device_facade import Timeout
from GramAddict.core.utils import get_value
from GramAddict.core.views import (
    Direction,
    HashTagView,
    PlacesView,
    PostsGridView,
    ProfileView,
    TabBarView,
    UniversalActions,
    _fast_open_random_grid_click,
)

logger = logging.getLogger(__name__)


def check_if_english(device):
    """check if app is in English"""
    logger.debug("Checking if app is in English..")
    post, follower, following = ProfileView(device)._getSomeText()
    if None in {post, follower, following}:
        logger.warning(
            "Failed to check your Instagram language. Be sure to set it to English or the bot won't work!"
        )
    elif post == "posts" and follower == "followers" and following == "following":
        logger.debug("Instagram in English.")
    else:
        # Don't hard-exit; just warn so the session continues.
        logger.error(
            "Instagram seems not set to English (got: "
            f"post='{post}', followers='{follower}', following='{following}'). "
            "Please switch to English to avoid misclicks."
        )
    return ProfileView(device, is_own_profile=True)


def nav_to_blogger(device, username, current_job):
    """navigate to blogger (followers list or posts)"""
    _to_followers = bool(current_job.endswith("followers"))
    _to_following = bool(current_job.endswith("following"))
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
        if not search_view.navigate_to_target(username, current_job):
            return False

        profile_view = ProfileView(device, is_own_profile=False)
        if _to_followers:
            logger.info(f"Open @{username} followers.")
            profile_view.navigateToFollowers()
        elif _to_following:
            logger.info(f"Open @{username} following.")
            profile_view.navigateToFollowing()

    return True


def nav_to_hashtag_or_place(device, target, current_job, storage=None, args=None):
    """navigate to hashtag/place/feed list"""
    search_view = TabBarView(device).navigateToSearch()
    allow_reels = False
    open_any = False
    fast_open = False
    if args is not None:
        fast_open = True
        watch_reels = get_value(args.watch_reels, None, 0) or 0
        reels_limit = get_value(args.reels_watches_limit, None, 0) or 0
        allow_reels = bool(getattr(args, "single_image_reels_as_posts", False)) or (
            watch_reels > 0 or reels_limit > 0
        )
        raw_open_any = getattr(args, "grid_open_any", False)
        if isinstance(raw_open_any, bool):
            open_any = raw_open_any
        elif isinstance(raw_open_any, (int, float)):
            open_any = raw_open_any > 0
        elif isinstance(raw_open_any, str):
            open_any = raw_open_any.strip().lower() in ("1", "true", "yes", "on")
        raw_fast_open = getattr(args, "fast_grid_open", False)
        if isinstance(raw_fast_open, bool):
            fast_open = raw_fast_open
        elif isinstance(raw_fast_open, (int, float)):
            fast_open = raw_fast_open > 0
        elif isinstance(raw_fast_open, str):
            fast_open = raw_fast_open.strip().lower() in ("1", "true", "yes", "on")
        if getattr(args, "disable_fast_grid_open", False):
            fast_open = False

    TargetView = HashTagView if current_job.startswith("hashtag") else PlacesView

    def _open_random_from_grid() -> bool:
        attempts = 5
        for attempt in range(attempts):
            if attempt > 0 or randint(1, 100) <= 60:
                logger.debug("Random grid scroll before opening a result.")
                UniversalActions(device)._swipe_points(
                    direction=Direction.UP, delta_y=randint(450, 900)
                )
            result_view = TargetView(device)._getRecyclerView()
            if fast_open:
                if _fast_open_random_grid_click(device, result_view, attempts=2):
                    logger.info(f"Opening a random result for {target} (fast).")
                    return True
                logger.debug("Fast grid click failed; retrying.")
                continue
            candidate = TargetView(device)._getFistImageView(
                result_view,
                storage=storage,
                current_job=current_job,
                allow_recent=attempt == attempts - 1,
                allow_reels=allow_reels,
                open_any=open_any,
            )
            if candidate is not None and candidate.exists():
                logger.info(f"Opening a random result for {target}.")
                candidate.click()
                return True
        logger.info(f"No suitable tiles found for {target}; skipping.")
        return False

    if search_view.is_on_target_results(target):
        logger.info(f"Already on {target} results; opening a random result.")
        return _open_random_from_grid()
    else:
        if not search_view.navigate_to_target(target, current_job):
            return False

    # Recent tab removed in new IG; stay on default "For you"/"Top" without switching.
    if current_job.endswith("recent"):
        logger.info("Recent tab deprecated; staying on default search tab.")
    return _open_random_from_grid()


def nav_to_post_likers(device, username, my_username):
    """navigate to blogger post likers"""
    if username == my_username:
        TabBarView(device).navigateToProfile()
    else:
        search_view = TabBarView(device).navigateToSearch()
        if not search_view.navigate_to_target(username, "account"):
            return False
    profile_view = ProfileView(device)
    profile_view.wait_profile_header_loaded()
    is_private = profile_view.isPrivateAccount()
    posts_count = profile_view.getPostsCount()
    is_empty = posts_count == 0 if posts_count is not None else False
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
