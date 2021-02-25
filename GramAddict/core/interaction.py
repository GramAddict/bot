from GramAddict.core.session_state import SessionState
from GramAddict.core import storage
import logging
import emoji
from datetime import datetime
from random import randint, shuffle, choice
from typing import Tuple
from time import time
from os import path
from colorama import Fore, Style
from GramAddict.core.report import print_short_report
from GramAddict.core.resources import ClassName, ResourceID as resources
from GramAddict.core.utils import (
    detect_block,
    get_value,
    random_sleep,
    append_to_file,
    save_crash,
)
from GramAddict.core.views import (
    ProfileView,
    CurrentStoryView,
    PostsGridView,
    SearchView,
    UniversalActions,
    Direction,
    PostsViewList,
    OpenedPostView,
    SwipeTo,
    Owner,
    LikeMode,
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
    comment_percentage,
    profile_filter,
    args,
    session_state,
    scraping_file,
    current_mode,
) -> Tuple[bool, bool, bool, int, int, int]:
    """
    :return: (whether interaction succeed, whether @username was followed during the interaction, number of liked, number of watched, number of commented)
    """
    number_of_liked = 0
    number_of_watched = 0
    number_of_commented = 0
    like_succeed = comment_done = interacted = followed = scraped = False

    if username == my_username:
        logger.info("It's you, skip.")
        return (
            interacted,
            followed,
            scraped,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    random_sleep()
    logger.debug("Checking profile..")
    start_time = time()
    if not profile_filter.check_profile(device, username):
        delta = format(time() - start_time, ".2f")
        logger.debug(f"Profile checked in {delta}s")
        return (
            interacted,
            followed,
            scraped,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    profile_view = ProfileView(device)
    posts_count = profile_view.getPostsCount()
    is_private = profile_view.isPrivateAccount()
    is_empty = posts_count == 0
    delta = format(time() - start_time, ".2f")
    logger.debug(f"Profile checked in {delta}s")
    if is_private or is_empty:
        private_empty = "Private" if is_private else "Empty"
        logger.info(f"{private_empty} account.", extra={"color": f"{Fore.GREEN}"})
        if can_follow and profile_filter.can_follow_private_or_empty():
            if scraping_file is None:
                followed = _follow(
                    device, username, follow_percentage, args, session_state, 0
                )
                return (
                    interacted,
                    followed,
                    scraped,
                    number_of_liked,
                    number_of_watched,
                    number_of_commented,
                )
        else:
            logger.info("Skip user.", extra={"color": f"{Fore.GREEN}"})
            return (
                interacted,
                followed,
                scraped,
                number_of_liked,
                number_of_watched,
                number_of_commented,
            )

    if scraping_file is not None:
        append_to_file(scraping_file, username)
        logger.info(
            f"Added @{username} at {scraping_file}",
            extra={"color": f"{Style.BRIGHT}{Fore.GREEN}"},
        )
        scraped = True
        return (
            interacted,
            followed,
            scraped,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    number_of_watched = _watch_stories(
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
    if swipe_amount == -1:
        return (
            interacted,
            followed,
            scraped,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )
    random_sleep()

    likes_value = get_value(likes_count, "Likes count: {}", 2)
    if profile_filter.can_comment(current_mode) and comment_percentage != 0:
        max_comments_pro_user = get_value(
            args.max_comments_pro_user, "Max comment count: {}", 1
        )
    if likes_value > 12:
        logger.error("Max number of likes per user is 12.")
        likes_value = 12

    start_time = time()
    full_rows, columns_last_row = profile_view.count_photo_in_view()
    end_time = format(time() - start_time, ".2f")
    photos_indices = list(range(0, full_rows * 3 + (columns_last_row)))

    logger.info(
        f"There {f'is {len(photos_indices)} post' if len(photos_indices)<=1 else f'are {len(photos_indices)} posts'} fully visible. Calculated in {end_time}s"
    )
    if (
        current_mode == "hashtag-posts-recent"
        or current_mode == "hashtag-posts-top"
        or current_mode == "place-posts-recent"
        or current_mode == "place-posts-top"
    ):
        session_state.totalLikes += 1
        photos_indices = photos_indices[1:]
        # sometimes we liked not the last picture, have to introduce the already liked thing..

    if likes_value > len(photos_indices):
        logger.info(
            f"Only {len(photos_indices)} {'photo' if len(photos_indices)<=1 else 'photos'} available"
        )
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
            like_succeed = do_like(opened_post_view, device, on_like)
            if like_succeed is True:
                number_of_liked += 1
        if profile_filter.can_comment(current_mode) and comment_percentage != 0:
            if number_of_commented < max_comments_pro_user:
                comment_done = _comment(
                    device, my_username, comment_percentage, args, session_state
                )
                if comment_done:
                    number_of_commented += 1
            else:
                logger.info(
                    f"You've already did {max_comments_pro_user} {'comment' if max_comments_pro_user<=1 else 'comments'} for this user!"
                )
        else:
            logger.debug(
                f"Comment filter for {current_mode}: {profile_filter.can_comment(current_mode)}"
            )
        logger.info("Back to profile.")
        device.back()
        if like_succeed or comment_done:
            interacted = True
        else:
            interacted = False

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
            return (
                interacted,
                followed,
                scraped,
                number_of_liked,
                number_of_watched,
                number_of_commented,
            )

        random_sleep()
    if can_follow:
        return (
            interacted,
            _follow(
                device, username, follow_percentage, args, session_state, swipe_amount
            ),
            scraped,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    return (
        interacted,
        followed,
        scraped,
        number_of_liked,
        number_of_watched,
        number_of_commented,
    )


def do_like(opened_post_view, device, on_like):
    logger.info("Double click post.")

    like_succeed = opened_post_view.likePost()
    if not like_succeed:
        logger.debug("Double click failed. Try the like button.")
        like_succeed = opened_post_view.likePost(click_btn_like=True)

    if like_succeed:
        logger.debug("Like succeed.")
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
    scraped,
    interactions_limit,
    likes_limit,
    sessions,
    session_state,
    args,
):
    session_state = sessions[-1]
    session_state.add_interaction(source, succeed, followed, scraped)

    can_continue = True
    if args.scrape_to_file is not None:
        if session_state.check_limit(
            args, limit_type=session_state.Limit.SCRAPED, output=False
        ):
            logger.info(
                "Reached interaction limit, finish.", extra={"color": f"{Fore.CYAN}"}
            )
            can_continue = False
    else:
        if session_state.check_limit(
            args, limit_type=session_state.Limit.LIKES, output=False
        ):
            logger.info(
                "Reached interaction limit, finish.", extra={"color": f"{Fore.CYAN}"}
            )
            can_continue = False
    inside_working_hours, time_left = SessionState.inside_working_hours(
        args.working_hours, args.time_delta_session
    )
    if not inside_working_hours:
        can_continue = False

    if args.scrape_to_file is not None:
        successful_user_scraped_count = session_state.totalScraped.get(source)
        if (
            successful_user_scraped_count
            and successful_user_scraped_count >= interactions_limit
        ):
            logger.info(
                f"Scraped {successful_user_scraped_count} users, finish.",
                extra={"color": f"{Fore.CYAN}"},
            )
            can_continue = False
    else:
        successful_interactions_count = session_state.successfulInteractions.get(source)
        if (
            successful_interactions_count
            and successful_interactions_count >= interactions_limit
        ):
            logger.info(
                f"Made {successful_interactions_count} successful interactions, finish.",
                extra={"color": f"{Fore.CYAN}"},
            )
            can_continue = False

    if can_continue and succeed or can_continue and scraped:
        print_short_report(source, session_state)

    return can_continue


def _comment(device, my_username, comment_percentage, args, session_state):
    if not session_state.check_limit(
        args, limit_type=session_state.Limit.COMMENTS, output=False
    ):
        comment_chance = randint(1, 100)
        if comment_chance > comment_percentage:
            return False
        UniversalActions(device)._swipe_points(
            direction=Direction.DOWN, delta_y=randint(150, 250)
        )
        for _ in range(2):
            comment_button = device.find(
                resourceId=ResourceID.ROW_FEED_BUTTON_COMMENT,
            )
            if comment_button.exists():
                logger.info("Open comments of post.")
                comment_button.click()
                random_sleep()
                comment_box = device.find(
                    resourceId=ResourceID.LAYOUT_COMMENT_THREAD_EDITTEXT
                )
                try:
                    text = comment_box.get_text()
                    limited = "Comments on this post have been limited"
                    if comment_box.exists() and text.upper() != limited.upper():
                        comment = load_random_comment(my_username)
                        if comment is None:
                            return False
                        logger.info(
                            f"Write comment: {comment}", extra={"color": f"{Fore.CYAN}"}
                        )
                        comment_box.set_text(comment)
                        random_sleep()
                        post_button = device.find(
                            resourceId=ResourceID.LAYOUT_COMMENT_THREAD_POST_BUTTON_CLICK_AREA
                        )
                        post_button.click()
                    else:
                        logger.info("Comments on this post have been limited.")
                        device.back()
                        return False
                    random_sleep()
                    detect_block(device)
                    SearchView(device)._close_keyboard()
                    random_sleep()
                    posted_text = device.find(
                        resourceId=ResourceID.ROW_COMMENT_TEXTVIEW_COMMENT,
                        textMatches=f"{my_username} {comment}",
                    )
                    when_posted = (
                        posted_text.sibling(
                            resourceId=ResourceID.ROW_COMMENT_SUB_ITEMS_BAR
                        )
                        .child(resourceId=ResourceID.ROW_COMMENT_TEXTVIEW_TIME_AGO)
                        .wait()
                    )
                    if posted_text.exists() and when_posted:
                        logger.info(
                            "Comment succeed.", extra={"color": f"{Fore.GREEN}"}
                        )
                        session_state.totalComments += 1
                        comment_confirmed = True
                    else:
                        logger.warning("Failed to check if comment succeed.")
                        comment_confirmed = False
                    random_sleep()
                    logger.info("Go back to post view.")
                    device.back()
                    return comment_confirmed
                except:
                    logger.error(
                        "Maybe some elements there have another IDs! Can't comment.."
                    )
                    save_crash(device)
                    logger.info("Go back to post view.")
                    random_sleep()
                    SearchView(device)._close_keyboard()
                    random_sleep()
                    device.back()
                    return False
            else:
                UniversalActions(device)._swipe_points(
                    direction=Direction.DOWN, delta_y=randint(150, 250)
                )
                continue
    return False


def load_random_comment(my_username):
    def nonblank_lines(f):
        for l in f:
            line = l.rstrip()
            if line:
                yield line

    lines = []
    file_name = my_username + "/" + storage.FILENAME_COMMENTS
    if path.isfile(file_name):
        with open(file_name, "r") as f:
            for line in nonblank_lines(f):
                lines.append(line)
            random_comment = choice(lines)
            return emoji.emojize(random_comment, use_aliases=True)
    else:
        logger.warning(f"{file_name} not found!")
        return None


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
                    "Cannot find neither Follow button, Follow Back button, nor Unfollow button."
                )
                save_crash(device)

        follow_button.click()
        if device.find(
            classNameMatches=ClassName.BUTTON,
            clickable=True,
            textMatches=UNFOLLOW_REGEX,
        ).wait():
            logger.info(f"Followed @{username}", extra={"color": f"{Fore.GREEN}"})
            detect_block(device)
            random_sleep()
            return True
        else:
            logger.info(
                f"Looks like I was not able to follow @{username}",
                extra={"color": f"{Fore.RED}"},
            )
            detect_block(device)
            random_sleep()
            return False
    else:
        logger.info("Reached total follows limit, not following.")
        return False


def _on_watch(sessions, session_state):
    session_state = sessions[-1]
    session_state.totalWatched += 1


def _on_comment(sessions, session_state):
    session_state = sessions[-1]
    session_state.totalCommented += 1


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
            return 0

        stories_to_watch = get_value(stories_to_watch, "Stories count: {}", 0)

        if stories_to_watch > 6:
            logger.error("Max number of stories per user is 6")
            stories_to_watch = 6

        if stories_to_watch == 0:
            return 0
        stories_ring = profile_view.StoryRing()
        if stories_ring.exists():
            stories_counter = 0
            logger.debug("Open the first story")
            stories_ring.click()
            story_view = CurrentStoryView(device)
            random_sleep(1, 2, modulable=False)
            story_view.getStoryFrame().wait()

            if profile_view.getUsername(error=False) != username:
                start = datetime.now()
                on_watch()
                stories_counter += 1
                for _ in range(0, 7):
                    random_sleep(0.5, 1, modulable=False)
                    if profile_view.getUsername(error=False) == username:
                        break

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
                                    logger.debug("Going to the next story..")
                                    story_frame.click(story_frame.Location.RIGHT)
                                    on_watch()
                                    stories_counter += 1
                                    for _ in range(0, 7):
                                        random_sleep(0.5, 1, modulable=False)
                                        if (
                                            profile_view.getUsername(error=False)
                                            == username
                                        ):
                                            break

                            except Exception as e:
                                logger.error(e)
                                save_crash(device)
                                break
                        else:
                            break

                for _ in range(0, 4):
                    if profile_view.getUsername(error=False) != username:
                        device.back()
                        random_sleep()
                    else:
                        break
                logger.info(
                    f"Watched stories for {(datetime.now()-start).total_seconds():.2f}s."
                )
                return stories_counter
            else:
                logger.warning("Failed to open the story container.")
                return False
        return 0
    else:
        logger.info("Reached total watch limit, not watching stories.")
        return False
