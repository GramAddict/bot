import logging
from random import randint, shuffle
from typing import Tuple

from colorama import Fore
from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.navigation import switch_to_english
from GramAddict.core.report import print_short_report
from GramAddict.core.utils import detect_block, get_value, random_sleep, save_crash
from GramAddict.core.views import LanguageNotEnglishException, ProfileView

logger = logging.getLogger(__name__)

BUTTON_REGEX = "android.widget.Button"
FOLLOW_REGEX = "^Follow"
UNFOLLOW_REGEX = "^Following|^Requested"


def interact_with_user(
    device,
    username,
    my_username,
    likes_count,
    on_like,
    can_follow,
    follow_percentage,
    profile_filter,
) -> Tuple[bool, bool]:
    """
    :return: (whether interaction succeed, whether @username was followed during the interaction)
    """
    if username == my_username:
        logger.info("It's you, skip.")
        return False, False

    random_sleep()

    if not profile_filter.check_profile(device, username):
        return False, False

    likes_value = get_value(likes_count, "Likes count: {}", 2)
    if likes_value > 12:
        logger.error("Max number of likes per user is 12")
        likes_value = 12

    profile_view = ProfileView(device)
    is_private = profile_view.isPrivateAccount()
    posts_count = profile_view.getPostsCount()
    is_empty = posts_count == 0

    if is_private or is_empty:
        private_empty = "Private" if is_private else "Empty"
        logger.info(f"{private_empty} account.", extra={"color": f"{Fore.GREEN}"})
        if can_follow and profile_filter.can_follow_private_or_empty():
            followed = _follow(device, username, follow_percentage)
        else:
            followed = False
            logger.info("Skip user.", extra={"color": f"{Fore.GREEN}"})
        return False, followed

    posts_tab_view = profile_view.navigateToPostsTab()
    if posts_tab_view.scrollDown():  # scroll down to view all maximum 12 posts
        logger.info("Scrolled down to see more posts.")
    random_sleep()
    number_of_rows_to_use = min((likes_value * 2) // 3 + 1, 4)
    photos_indices = list(range(0, number_of_rows_to_use * 3))
    shuffle(photos_indices)
    photos_indices = photos_indices[:likes_value]
    photos_indices = sorted(photos_indices)
    for i in range(0, likes_value):
        photo_index = photos_indices[i]
        row = photo_index // 3
        column = photo_index - row * 3
        logger.info(f"Open post #{i + 1} ({row + 1} row, {column + 1} column")
        opened_post_view = posts_tab_view.navigateToPost(row, column)
        random_sleep()

        like_succeed = False
        if opened_post_view:
            logger.info("Double click post")
            opened_post_view.likePost()
            random_sleep()
            if not opened_post_view.isPostLiked():
                logger.debug("Double click failed. Try the like button.")
                opened_post_view.likePost(click_btn_like=True)
                random_sleep()

            like_succeed = opened_post_view.isPostLiked()
            if like_succeed:
                detect_block(device)
                on_like()

            logger.info("Back to profile")
            device.back()

        if not opened_post_view or not like_succeed:
            reason = "open" if not opened_post_view else "like"
            logger.info(f"Could not {reason} photo. Posts count: {posts_count}")

            if can_follow and profile_filter.can_follow_private_or_empty():
                followed = _follow(device, username, follow_percentage)
            else:
                followed = False

            if not followed:
                logger.info("Skip user.", extra={"color": f"{Fore.GREEN}"})
            return False, followed

        random_sleep()
    if can_follow:
        return True, _follow(device, username, follow_percentage)

    return True, False


def is_follow_limit_reached_for_source(session_state, follow_limit, source):
    if follow_limit is None:
        return False

    followed_count = session_state.totalFollowed.get(source)
    return followed_count is not None and followed_count >= follow_limit


def _on_like(sessions, session_state):
    session_state = sessions[-1]
    session_state.totalLikes += 1


def _on_interaction(
    source,
    succeed,
    followed,
    interactions_limit,
    likes_limit,
    on_likes_limit_reached,
    sessions,
    session_state,
):
    session_state = sessions[-1]
    session_state.add_interaction(source, succeed, followed)

    can_continue = True

    if session_state.totalLikes >= likes_limit:
        logger.info("Reached total likes limit, finish.")
        on_likes_limit_reached()
        can_continue = False

    successful_interactions_count = session_state.successfulInteractions.get(source)
    if (
        successful_interactions_count
        and successful_interactions_count >= interactions_limit
    ):
        logger.info(
            f"Made {successful_interactions_count} successful interactions, finish."
        )
        can_continue = False

    if can_continue and succeed:
        print_short_report(source, session_state)

    return can_continue


def _on_likes_limit_reached(state):
    state.is_likes_limit_reached = True


def _follow(device, username, follow_percentage):
    follow_chance = randint(1, 100)
    if follow_chance > follow_percentage:
        return False

    logger.info("Following...")
    coordinator_layout = device.find(
        resourceId="com.instagram.android:id/coordinator_root_layout"
    )
    if coordinator_layout.exists():
        coordinator_layout.scroll(DeviceFacade.Direction.TOP)

    random_sleep()

    follow_button = device.find(
        classNameMatches=BUTTON_REGEX,
        clickable=True,
        textMatches=FOLLOW_REGEX,
    )

    if not follow_button.exists():
        unfollow_button = device.find(
            classNameMatches=BUTTON_REGEX,
            clickable=True,
            textMatches=UNFOLLOW_REGEX,
        )
        if unfollow_button.exists():
            logger.info(
                f"You already follow @{username}.", extra={"color": f"{Fore.GREEN}"}
            )
            return False
        else:
            logger.error(
                "Cannot find neither Follow button, nor Unfollow button. Maybe not English language is set?"
            )
            save_crash(device)
            switch_to_english(device)
            raise LanguageNotEnglishException()

    follow_button.click()
    detect_block(device)
    logger.info(f"Followed @{username}", extra={"color": f"{Fore.GREEN}"})
    random_sleep()
    return True
