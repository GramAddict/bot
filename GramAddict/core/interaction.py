from GramAddict.core.device_facade import Location, SleepTime, Timeout
from GramAddict.core.session_state import SessionState
from GramAddict.core import storage
import logging
import emoji
from datetime import datetime
from random import randint, shuffle, choice
from typing import Tuple
from time import sleep, time
from os import path
from colorama import Fore, Style
from GramAddict.core.report import print_scrape_report, print_short_report
from GramAddict.core.resources import ClassName, ResourceID as resources
from GramAddict.core.utils import (
    get_value,
    random_sleep,
    append_to_file,
    save_crash,
)
from GramAddict.core.views import (
    MediaType,
    ProfileView,
    CurrentStoryView,
    PostsGridView,
    SearchView,
    UniversalActions,
    Direction,
    case_insensitive_re,
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
    stories_percentage,
    can_follow,
    follow_percentage,
    comment_percentage,
    pm_percentage,
    profile_filter,
    args,
    session_state,
    scraping_file,
    current_mode,
) -> Tuple[bool, bool, bool, bool, int, int, int]:
    """
    :return: (whether interaction succeed, whether @username was followed during the interaction, if you scraped that account, if you sent a PM, number of liked, number of watched, number of commented)
    """
    number_of_liked = 0
    number_of_watched = 0
    number_of_commented = 0
    like_succeed = comment_done = interacted = followed = scraped = sent_pm = False

    if username == my_username:
        logger.info("It's you, skip.")
        return (
            interacted,
            followed,
            scraped,
            sent_pm,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    logger.debug("Checking profile..")
    start_time = time()
    profile_data, skipped = profile_filter.check_profile(device, username)
    if skipped:
        delta = format(time() - start_time, ".2f")
        logger.debug(f"Profile checked in {delta}s")
        return (
            interacted,
            followed,
            scraped,
            sent_pm,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    profile_view = ProfileView(device)
    delta = format(time() - start_time, ".2f")
    logger.debug(f"Profile checked in {delta}s")
    if profile_data.is_private or (profile_data.posts_count == 0):
        private_empty = "Private" if profile_data.is_private else "Empty"
        logger.info(f"{private_empty} account.", extra={"color": f"{Fore.GREEN}"})
        if (
            can_send_PM(session_state, pm_percentage)
            and profile_filter.can_pm_to_private_or_empty
        ):
            sent_pm = _send_PM(
                device, session_state, my_username, 0, profile_data.is_private
            )
        if can_follow and profile_filter.can_follow_private_or_empty():
            if scraping_file is None:
                followed = _follow(
                    device, username, follow_percentage, args, session_state, 0
                )
                return (
                    interacted,
                    followed,
                    scraped,
                    sent_pm,
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
                sent_pm,
                number_of_liked,
                number_of_watched,
                number_of_commented,
            )

    # handle the scraping mode
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
            sent_pm,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    # if not in scarping mode, we will interact
    number_of_watched = _watch_stories(
        device,
        profile_view,
        username,
        stories_percentage,
        args,
        session_state,
    )

    swipe_amount = ProfileView(device).swipe_to_fit_posts()
    if swipe_amount == -1:
        return (
            interacted,
            followed,
            scraped,
            sent_pm,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    likes_value = get_value(likes_count, "Likes count: {}", 2)
    (
        _,
        _,
        can_comment_job,
    ) = profile_filter.can_comment(current_mode)
    if can_comment_job and comment_percentage != 0:
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
    if current_mode in [
        "hashtag-posts-recent",
        "hashtag-posts-top",
        "place-posts-recent",
        "place-posts-top",
        "feed",
    ]:
        # in these jobs we did a like already at the post
        photos_indices = photos_indices[1:]
        # sometimes we liked not the last picture, have to introduce the already liked thing..

    if likes_value > len(photos_indices):
        logger.info(
            f"Only {len(photos_indices)} {'photo' if len(photos_indices)<=1 else 'photos'} available."
        )
    else:
        shuffle(photos_indices)
        photos_indices = photos_indices[:likes_value]
        photos_indices = sorted(photos_indices)

    for i in range(0, len(photos_indices)):
        photo_index = photos_indices[i]
        row = photo_index // 3
        column = photo_index - row * 3
        logger.info(f"Open post #{i + 1} ({row + 1} row, {column + 1} column).")
        opened_post_view, media_type, obj_count = PostsGridView(device).navigateToPost(
            row, column
        )

        like_succeed = False
        if opened_post_view:
            _browse_carousel(device, media_type, obj_count)
            like_succeed = do_like(opened_post_view, device, session_state, media_type)
            if like_succeed is True:
                number_of_liked += 1
            if comment_percentage != 0:
                if can_comment(media_type, profile_filter, current_mode):
                    if number_of_commented < max_comments_pro_user:
                        comment_done = _comment(
                            device,
                            my_username,
                            comment_percentage,
                            args,
                            session_state,
                            media_type,
                        )
                        if comment_done:
                            number_of_commented += 1
                    else:
                        logger.info(
                            f"You've already did {max_comments_pro_user} {'comment' if max_comments_pro_user<=1 else 'comments'} for this user!"
                        )
            logger.info("Back to profile.")
            device.back()
        if like_succeed or comment_done:
            interacted = True
        else:
            interacted = False

        if not opened_post_view or not like_succeed:
            reason = "open" if not opened_post_view else "like"
            logger.info(
                f"Could not {reason} photo. Posts count: {profile_data.posts_count}"
            )

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
                sent_pm,
                number_of_liked,
                number_of_watched,
                number_of_commented,
            )

    if can_send_PM(session_state, pm_percentage):
        sent_pm = _send_PM(device, session_state, my_username, swipe_amount)
        swipe_amount = 0
    if can_follow:
        return (
            interacted,
            _follow(
                device, username, follow_percentage, args, session_state, swipe_amount
            ),
            scraped,
            sent_pm,
            number_of_liked,
            number_of_watched,
            number_of_commented,
        )

    return (
        interacted,
        followed,
        scraped,
        sent_pm,
        number_of_liked,
        number_of_watched,
        number_of_commented,
    )


def can_send_PM(session_state, pm_percentage):
    pm_chance = randint(1, 100)
    if not session_state.check_limit(
        args, limit_type=session_state.Limit.PM, output=True
    ) and (pm_chance <= pm_percentage):
        return True
    else:
        return False


def can_comment(media_type, profile_filter, current_mode):
    (
        can_comment_photos,
        can_comment_videos,
        can_comment_job,
    ) = profile_filter.can_comment(current_mode)
    if can_comment_job:
        if media_type == MediaType.PHOTO and can_comment_photos:
            return True
        elif media_type == MediaType.VIDEO and can_comment_videos:
            return True
    else:
        logger.debug(
            f"Can't comment because filter for {current_mode} in json is: {profile_filter.can_comment(current_mode)}"
        )
        return False


def do_like(opened_post_view, device, session_state, media_type):
    if (
        media_type == MediaType.VIDEO or media_type == MediaType.IGTV
    ) and args.watch_video_time != "0":
        watching_time = get_value(args.watch_video_time, "Watching video for {}s.", 0)
        sleep(watching_time)
    logger.info("Double click post.")
    like_succeed = opened_post_view.likePost()
    if not like_succeed:
        logger.debug("Double click failed. Try the like button.")
        like_succeed = opened_post_view.likePost(click_btn_like=True)

    if like_succeed:
        logger.debug("Like succeed.")
        UniversalActions.detect_block(device)
        session_state.totalLikes += 1
    else:
        logger.warning("Fail to like post. Let's continue...")

    return like_succeed


def is_follow_limit_reached_for_source(session_state, follow_limit, source):
    if follow_limit is None:
        return False

    followed_count = session_state.totalFollowed.get(source)
    return followed_count is not None and followed_count >= follow_limit


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

    inside_working_hours, _ = SessionState.inside_working_hours(
        args.working_hours, args.time_delta_session
    )
    if not inside_working_hours:
        can_continue = False
    else:
        successful_interactions_count = session_state.successfulInteractions.get(source)
        if (
            successful_interactions_count
            and successful_interactions_count >= interactions_limit
        ):
            logger.info(
                "Reached interaction limit for that source, going to the next one..",
                extra={"color": f"{Fore.CYAN}"},
            )
            can_continue = False

        if args.scrape_to_file is not None:
            if session_state.check_limit(
                args, limit_type=session_state.Limit.SCRAPED, output=False
            ):
                logger.info(
                    "Reached scraped limit, finish.", extra={"color": f"{Fore.CYAN}"}
                )
                can_continue = False
        else:
            if session_state.check_limit(
                args, limit_type=session_state.Limit.LIKES, output=False
            ):
                logger.info(
                    "Reached likes limit, finish.", extra={"color": f"{Fore.CYAN}"}
                )
                can_continue = False

            if session_state.check_limit(
                args, limit_type=session_state.Limit.FOLLOWS, output=False
            ):
                logger.info(
                    "Reached followed limit, finish.", extra={"color": f"{Fore.CYAN}"}
                )
                can_continue = False

            if session_state.check_limit(
                args, limit_type=session_state.Limit.TOTAL, output=False
            ):
                logger.info(
                    "Reached total interaction limit, finish.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                can_continue = False
            if session_state.check_limit(
                args, limit_type=session_state.Limit.SUCCESS, output=False
            ):
                logger.info(
                    "Reached total succesfully interaction limit, finish.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                can_continue = False

    if (can_continue and succeed) or scraped:
        if scraped:
            print_scrape_report(source, session_state)
        else:
            print_short_report(source, session_state)

    return can_continue


def _browse_carousel(device, media_type, obj_count):
    if media_type == MediaType.CAROUSEL:
        carousel_percentage = get_value(configs.args.carousel_percentage, None, 0)
        carousel_count = get_value(configs.args.carousel_count, None, 1)
        if carousel_percentage > randint(0, 100) and carousel_count > 1:
            logger.info("Watching photos/videos in carousel.")
            if obj_count < carousel_count:
                logger.info(f"There are only {obj_count} media in this carousel!")
                carousel_count = obj_count
            n = 1
            while n < carousel_count:
                UniversalActions(device)._swipe_points(
                    direction=Direction.LEFT,
                )
                n += 1


def _comment(device, my_username, comment_percentage, args, session_state, media_type):
    if not session_state.check_limit(
        args, limit_type=session_state.Limit.COMMENTS, output=False
    ):
        comment_chance = randint(1, 100)
        if comment_chance > comment_percentage:
            return False
        # we have to do a little swipe for preventing get the previus post comments button (which is covered by top bar, but present in hierarchy!!)
        UniversalActions(device)._swipe_points(
            direction=Direction.DOWN, delta_y=randint(150, 250)
        )
        tab_bar = device.find(
            resourceId=ResourceID.TAB_BAR,
        )
        media = device.find(
            resourceIdMatches=ResourceID.CAROUSEL_MEDIA_GROUP_AND_ZOOMABLE_VIEW_CONTAINER,
        )
        if int(tab_bar.get_bounds()["top"]) - int(media.get_bounds()["bottom"]) < 150:
            UniversalActions(device)._swipe_points(
                direction=Direction.DOWN, delta_y=randint(150, 250)
            )
        # look at hashtag of comment
        for _ in range(2):
            comment_button = device.find(
                resourceId=ResourceID.ROW_FEED_BUTTON_COMMENT,
            )
            if comment_button.exists():
                logger.info("Open comments of post.")
                comment_button.click()
                comment_box = device.find(
                    resourceId=ResourceID.LAYOUT_COMMENT_THREAD_EDITTEXT,
                    enabled="true",
                )
                if comment_box.exists():
                    comment = load_random_comment(my_username, media_type)
                    if comment is None:
                        SearchView(device)._close_keyboard()
                        device.back()
                        return False
                    logger.info(
                        f"Write comment: {comment}", extra={"color": f"{Fore.CYAN}"}
                    )
                    comment_box.set_text(comment)

                    post_button = device.find(
                        resourceId=ResourceID.LAYOUT_COMMENT_THREAD_POST_BUTTON_CLICK_AREA
                    )
                    post_button.click()
                else:
                    logger.info("Comments on this post have been limited.")
                    SearchView(device)._close_keyboard()
                    device.back()
                    return False

                UniversalActions.detect_block(device)
                SearchView(device)._close_keyboard()
                posted_text = device.find(
                    text=f"{my_username} {comment}",
                )
                when_posted = posted_text.sibling(
                    resourceId=ResourceID.ROW_COMMENT_SUB_ITEMS_BAR
                ).child(resourceId=ResourceID.ROW_COMMENT_TEXTVIEW_TIME_AGO)
                if posted_text.exists(Timeout.MEDIUM) and when_posted.exists(
                    Timeout.MEDIUM
                ):
                    logger.info("Comment succeed.", extra={"color": f"{Fore.GREEN}"})
                    session_state.totalComments += 1
                    comment_confirmed = True
                else:
                    logger.warning("Failed to check if comment succeed.")
                    comment_confirmed = False

                logger.info("Go back to post view.")
                device.back()
                return comment_confirmed
            else:
                like_button = device.find(
                    resourceId=ResourceID.ROW_FEED_BUTTON_LIKE,
                )
                if like_button.exists():
                    logger.info("This post have comments disabled.")
                    return False
                UniversalActions(device)._swipe_points(
                    direction=Direction.DOWN, delta_y=randint(150, 250)
                )
                continue
    return False


def _send_PM(device, session_state, my_username, swipe_amount, private=False):
    if private:
        options = device.find(
            classNameMatches=ClassName.FRAME_LAYOUT,
            descriptionMatches=case_insensitive_re("^Options$"),
        )
        if options.exists(Timeout.SHORT):
            options.click()
        else:
            return False
        send_pm = device.find(
            classNameMatches=ClassName.BUTTON,
            textMatches=case_insensitive_re("^Send Message$"),
        )
        if send_pm.exists(Timeout.SHORT):
            send_pm.click()
        else:
            return False
    else:
        coordinator_layout = device.find(resourceId=ResourceID.COORDINATOR_ROOT_LAYOUT)
        if coordinator_layout.exists() and swipe_amount != 0:
            UniversalActions(device)._swipe_points(
                direction=Direction.UP, delta_y=swipe_amount
            )
        message_button = device.find(
            classNameMatches=ClassName.BUTTON_OR_TEXTVIEW_REGEX,
            enabled=True,
            textMatches="Message",
        )
        if message_button.exists(Timeout.SHORT):
            message_button.click()
        else:
            logger.warning("Cannot find the button for sending PMs!")
            return False
    message_box = device.find(
        resourceId=ResourceID.ROW_THREAD_COMPOSER_EDITTEXT,
        className=ClassName.EDIT_TEXT,
        enabled="true",
    )
    if message_box.exists():
        message = load_random_message(my_username)
        if message is None:
            logger.warning("You forgot to populate your PM list!")
            device.back()
            return False
        logger.info(
            f"Write private message: {message}", extra={"color": f"{Fore.CYAN}"}
        )
        message_box.set_text(message)
        send_button = device.find(
            resourceId=ResourceID.ROW_THREAD_COMPOSER_BUTTON_SEND,
            className=ClassName.TEXT_VIEW,
        )
        send_button.click()
        UniversalActions.detect_block(device)
        SearchView(device)._close_keyboard()
        posted_text = device.find(text=f"{message}")
        message_sending_icon = device.find(
            resourceId=ResourceID.ACTION_ICON, className=ClassName.IMAGE_VIEW
        )
        if message_sending_icon.exists():
            random_sleep()
        if posted_text.exists(Timeout.MEDIUM) and not message_sending_icon.exists():
            logger.info("PM send succeed.", extra={"color": f"{Fore.GREEN}"})
            session_state.totalPm += 1
            pm_confirmed = True
        else:
            logger.warning("Failed to check if PM send succeed.")
            pm_confirmed = False
        logger.info("Go back to profile view.")
        device.back()
        return pm_confirmed
    else:
        logger.info("PM to this user have been limited.")
        SearchView(device)._close_keyboard()
        device.back()
        return False


def load_random_message(my_username):
    def nonblank_lines(f):
        for ln in f:
            line = ln.rstrip()
            if line:
                yield line

    lines = []
    file_name = f"{storage.ACCOUNTS}/{my_username}/{storage.FILENAME_MESSAGES}"
    if path.isfile(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            for line in nonblank_lines(f):
                lines.append(line)
            random_message = choice(lines)
            if random_message != "":
                return emoji.emojize(random_message, use_aliases=True)
            else:
                return None


def load_random_comment(my_username, media_type):
    def nonblank_lines(f):
        for ln in f:
            line = ln.rstrip()
            if line:
                yield line

    lines = []
    file_name = f"{storage.ACCOUNTS}/{my_username}/{storage.FILENAME_COMMENTS}"
    if path.isfile(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            for line in nonblank_lines(f):
                lines.append(line)
            try:
                photo_header = lines.index("%PHOTO")
                video_header = lines.index("%VIDEO")
                carousel_header = lines.index("%CAROUSEL")
            except Exception as e:
                logger.error(f"Exception: {e}")
                logger.warning(
                    f"You didn't follow the rules of sections for {file_name}! Look at config example."
                )
                return None
            photo_comments = lines[photo_header + 1 : video_header]
            video_comments = lines[video_header + 1 : carousel_header]
            carousel_comments = lines[carousel_header + 1 :]
            if media_type == MediaType.PHOTO:
                random_comment = (
                    choice(photo_comments) if len(photo_comments) > 0 else ""
                )
            if media_type == MediaType.VIDEO or media_type == MediaType.IGTV:
                random_comment = (
                    choice(video_comments) if len(video_comments) > 0 else ""
                )
            if media_type == MediaType.CAROUSEL:
                random_comment = (
                    choice(carousel_comments) if len(carousel_comments) > 0 else ""
                )
            if random_comment != "":
                return emoji.emojize(random_comment, use_aliases=True)
            else:
                return None
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
        if coordinator_layout.exists(Timeout.MEDIUM) and swipe_amount != 0:
            UniversalActions(device)._swipe_points(
                direction=Direction.UP, delta_y=swipe_amount
            )

        follow_button = device.find(
            clickable=True,
            textMatches=FOLLOW_REGEX,
        )

        if not follow_button.exists():
            unfollow_button = device.find(
                clickable=True,
                textMatches=UNFOLLOW_REGEX,
            )
            followback_button = device.find(
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
            clickable=True,
            textMatches=UNFOLLOW_REGEX,
        ).exists(Timeout.SHORT):
            logger.info(f"Followed @{username}", extra={"color": f"{Fore.GREEN}"})
            UniversalActions.detect_block(device)
            return True
        else:
            logger.info(
                f"Looks like I was not able to follow @{username}, maybe you got softbanned for this action!",
                extra={"color": f"{Fore.RED}"},
            )
            UniversalActions.detect_block(device)
            return False
    else:
        logger.info("Reached total follows limit, not following.")
        return False


def _watch_stories(
    device,
    profile_view,
    username,
    stories_percentage,
    args,
    session_state,
):
    if not session_state.check_limit(
        args, limit_type=session_state.Limit.WATCHES, output=False
    ):
        story_chance = randint(1, 100)
        if story_chance > stories_percentage:
            return 0

        stories_to_watch = get_value(args.stories_count, "Stories count: {}.", 0)

        if stories_to_watch > 6:
            logger.error("Max number of stories per user is 6.")
            stories_to_watch = 6

        if stories_to_watch == 0:
            return 0
        stories_ring = profile_view.StoryRing()
        if stories_ring.exists():
            stories_counter = 0
            logger.debug("Open the first story.")
            stories_ring.click(sleep=SleepTime.ZERO)
            story_view = CurrentStoryView(device)
            random_sleep(1, 2, modulable=False, logging=False)
            story_view.getStoryFrame().wait(Timeout.SHORT)

            if profile_view.getUsername(watching_stories=True) != username:
                start = datetime.now()
                session_state.totalWatched += 1
                stories_counter += 1
                for _ in range(0, 7):
                    random_sleep(0.5, 1, modulable=False, logging=False)
                    if profile_view.getUsername(watching_stories=True) == username:
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
                                    story_frame.click(
                                        mode=Location.RIGHTEDGE,
                                        sleep=SleepTime.ZERO,
                                        crash_report_if_fails=False,
                                    )
                                    session_state.totalWatched += 1
                                    stories_counter += 1
                                    for _ in range(0, 7):
                                        random_sleep(
                                            0.5, 1, modulable=False, logging=False
                                        )
                                        if (
                                            profile_view.getUsername(
                                                watching_stories=True
                                            )
                                            == username
                                        ):
                                            break

                            except Exception as e:
                                logger.debug(f"Exception: {e}")
                                logger.debug(
                                    "Ignore this error! Stories ended while we were pressing on the next one."
                                )
                                break
                        else:
                            break

                for _ in range(0, 4):
                    if profile_view.getUsername(watching_stories=True) != username:
                        device.back()
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
