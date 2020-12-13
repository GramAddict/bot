import logging
from random import randint, shuffle
from typing import Tuple
from time import time
from colorama import Fore
from GramAddict.core.navigation import switch_to_english
from GramAddict.core.report import print_short_report
from GramAddict.core.resources import ClassName, ResourceID as resources
from GramAddict.core.utils import detect_block, get_value, random_sleep, save_crash
from GramAddict.core.views import (
    LanguageNotEnglishException,
    ProfileView,
    CurrentStoryView,
    PostsGridView,
    UniversalActions,
    Direction,
)

logger = logging.getLogger(__name__)

FOLLOW_REGEX = "^Follow$"
FOLLOWBACK_REGEX = "^Follow Back$"
UNFOLLOW_REGEX = "^Following|^Requested"


def load_config(config):
    global args
    global configs
    global ResourceID
    args = config.args
    configs = config
    ResourceID = resources(config.args.app_id)


def interact_with_user(
    device,
    username,
    my_username,
    likes_count,
    on_like,
    stories_count,
    stories_percentage,
    on_watch,
    can_follow,
    follow_percentage,
    profile_filter,
    args,
    session_state,
    current_mode,
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
        logger.error("Max number of likes per user is 12.")
        likes_value = 12

    profile_view = ProfileView(device)
    is_private = profile_view.isPrivateAccount()
    posts_count = profile_view.getPostsCount()
    is_empty = posts_count == 0

    if is_private or is_empty:
        private_empty = "Private" if is_private else "Empty"
        logger.info(f"{private_empty} account.", extra={"color": f"{Fore.GREEN}"})
        if can_follow and profile_filter.can_follow_private_or_empty():
            followed = _follow(
                device, username, follow_percentage, args, session_state, 0
            )
            return True, followed
        else:
            logger.info("Skip user.", extra={"color": f"{Fore.GREEN}"})
            return False, False

    _watch_stories(
        device,
        profile_view,
        username,
        stories_count,
        stories_percentage,
        on_watch,
        args,
        session_state,
    )

    swipe_amount = ProfileView(device).swipe_to_fit_posts()
    random_sleep()
    start_time = time()
    full_rows, columns_last_row = profile_view.count_photo_in_view()
    end_time = format(time() - start_time, ".2f")
    photos_indices = list(range(0, full_rows * 3 + (columns_last_row)))

    logger.info(
        f"There are {len(photos_indices)} posts fully visible. Calculated in {end_time}s"
    )
    if current_mode == "hashtag-posts-recent" or current_mode == "hashtag-posts-top":
        session_state.totalLikes += 1
        photos_indices = photos_indices[1:]

    if likes_value > len(photos_indices):
        logger.info(f"Only {len(photos_indices)} photo(s) available")
    else:
        shuffle(photos_indices)
        photos_indices = photos_indices[:likes_value]
        photos_indices = sorted(photos_indices)
    for i in range(0, len(photos_indices)):
        photo_index = photos_indices[i]
        row = photo_index // 3
        column = photo_index - row * 3
        logger.info(f"Open post #{i + 1} ({row + 1} row, {column + 1} column)")
        opened_post_view = PostsGridView(device).navigateToPost(row, column)
        random_sleep()

        like_succeed = False
        if opened_post_view:
            logger.info("Double click post.")

            like_succeed = opened_post_view.likePost()
            if not like_succeed:
                logger.debug("Double click failed. Try the like button.")
                like_succeed = opened_post_view.likePost(click_btn_like=True)

            if like_succeed:
                logger.debug("Like succeed. Check for block.")
                detect_block(device)
                on_like()
            else:
                logger.warning("Fail to like post. Let's continue...")

            logger.info("Back to profile.")
            device.back()

        if not opened_post_view or not like_succeed:
            reason = "open" if not opened_post_view else "like"
            logger.info(f"Could not {reason} photo. Posts count: {posts_count}")

            if can_follow and profile_filter.can_follow_private_or_empty():
                followed = _follow(
                    device,
                    username,
                    follow_percentage,
                    args,
                    session_state,
                    swipe_amount,
                )
            else:
                followed = False

            if not followed:
                logger.info("Skip user.", extra={"color": f"{Fore.GREEN}"})
            return False, followed

        random_sleep()
    if can_follow:
        return True, _follow(
            device, username, follow_percentage, args, session_state, swipe_amount
        )

    return True, False


def do_like(opened_post_view, device, on_like):
    logger.info("Double click post")

    like_succeed = opened_post_view.likePost()
    if not like_succeed:
        logger.debug("Double click failed. Try the like button.")
        like_succeed = opened_post_view.likePost(click_btn_like=True)

    if like_succeed:
        logger.info("Like succeeded!")
        detect_block(device)
        on_like()
    else:
        logger.warning("Fail to like post. Let's continue...")

    return like_succeed


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
    sessions,
    session_state,
    args,
):
    session_state = sessions[-1]
    session_state.add_interaction(source, succeed, followed)

    can_continue = True

    if session_state.check_limit(
        args, limit_type=session_state.Limit.LIKES, output=False
    ):
        logger.info("Reached interaction limit, finish.")
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


def _follow(device, username, follow_percentage, args, session_state, swipe_amount):
    if not session_state.check_limit(
        args, limit_type=session_state.Limit.FOLLOWS, output=False
    ):
        follow_chance = randint(1, 100)
        if follow_chance > follow_percentage:
            return False

        coordinator_layout = device.find(resourceId=ResourceID.COORDINATOR_ROOT_LAYOUT)
        if coordinator_layout.exists() and swipe_amount != 0:
            UniversalActions(device)._swipe_points(
                direction=Direction.UP, delta_y=swipe_amount
            )

        random_sleep()

        follow_button = device.find(
            classNameMatches=ClassName.BUTTON,
            clickable=True,
            textMatches=FOLLOW_REGEX,
        )

        if not follow_button.exists():
            unfollow_button = device.find(
                classNameMatches=ClassName.BUTTON,
                clickable=True,
                textMatches=UNFOLLOW_REGEX,
            )
            followback_button = device.find(
                classNameMatches=ClassName.BUTTON,
                clickable=True,
                textMatches=FOLLOWBACK_REGEX,
            )
            if unfollow_button.exists():
                logger.info(
                    f"You already follow @{username}.", extra={"color": f"{Fore.GREEN}"}
                )
                return False
            elif followback_button.exists():
                logger.info(
                    f"@{username} already follows you.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return False
            else:
                logger.error(
                    "Cannot find neither Follow button, Follow Back button, nor Unfollow button. Maybe not English language is set?"
                )
                save_crash(device)
                switch_to_english(device)
                raise LanguageNotEnglishException()

        follow_button.click()
        detect_block(device)
        logger.info(f"Followed @{username}", extra={"color": f"{Fore.GREEN}"})
        random_sleep()
        return True
    else:
        logger.info("Reached total follows limit, not following.")
        return False


def _on_watch(sessions, session_state):
    session_state = sessions[-1]
    session_state.totalWatched += 1


def _watch_stories(
    device,
    profile_view,
    username,
    stories_to_watch,
    stories_percentage,
    on_watch,
    args,
    session_state,
):
    if not session_state.check_limit(
        args, limit_type=session_state.Limit.WATCHES, output=False
    ):
        story_chance = randint(1, 100)
        if story_chance > stories_percentage:
            return False

        stories_to_watch = get_value(stories_to_watch, "Stories count: {}", 0)

        if stories_to_watch > 6:
            logger.error("Max number of stories per user is 6")
            stories_to_watch = 6

        if stories_to_watch == 0:
            return False

        if profile_view.isStoryAvailable():
            profile_picture = profile_view.profileImage()
            if profile_picture.exists():
                profile_picture.click()  # Open the first story
                on_watch()
                random_sleep()

                if stories_to_watch > 1:
                    story_view = CurrentStoryView(device)
                    for _iter in range(0, stories_to_watch - 1):
                        if story_view.getUsername() == username:
                            try:
                                story_frame = story_view.getStoryFrame()
                                if (
                                    story_frame.exists()
                                    and _iter <= stories_to_watch - 1
                                ):
                                    story_frame.click(story_view.Location.RIGHT)
                                    on_watch()
                                    random_sleep()
                            except Exception:
                                break
                        else:
                            break

                for attempt in range(0, 4):
                    if profile_view.getUsername(error=False) != username:
                        if attempt != 0:
                            device.back()
                        # Maybe it's just an error please one half seconds before search again for username tab
                        # This little delay prevent too much back tap and to see more stories than stories_to_watch value
                        random_sleep()
                    else:
                        break
                return True
        return False
    else:
        logger.info("Reached total watch limit, not watching stories.")
        return False
