import logging
from datetime import timedelta
from functools import partial
from os import path

from atomicwrites import atomic_write
from colorama import Fore

from GramAddict.core.device_facade import Direction, Timeout
from GramAddict.core.navigation import (
    nav_to_blogger,
    nav_to_feed,
    nav_to_hashtag_or_place,
    nav_to_post_likers,
)
from GramAddict.core.resources import ClassName
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.utils import get_value, random_sleep
from GramAddict.core.views import (
    FollowingView,
    LikeMode,
    OpenedPostView,
    Owner,
    PostsViewList,
    ProfileView,
    SwipeTo,
    TabBarView,
    UniversalActions,
    case_insensitive_re,
)

logger = logging.getLogger(__name__)


def interact(
    storage,
    is_follow_limit_reached,
    username,
    interaction,
    device,
    session_state,
    current_job,
    on_interaction,
):
    if is_follow_limit_reached is not None:
        can_follow = not is_follow_limit_reached() and (
            storage.get_following_status(username) == FollowingStatus.NONE
            or storage.get_following_status(username) == FollowingStatus.NOT_IN_LIST
        )
    else:
        can_follow = False

    (
        interaction_succeed,
        followed,
        scraped,
        pm_sent,
        number_of_liked,
        number_of_watched,
        number_of_comments,
    ) = interaction(device, username=username, can_follow=can_follow)

    add_interacted_user = partial(
        storage.add_interacted_user,
        session_id=session_state.id,
        job_name=current_job,
        target=username,
    )

    add_interacted_user(
        username,
        followed=followed,
        scraped=scraped,
        liked=number_of_liked,
        watched=number_of_watched,
        commented=number_of_comments,
        pm_sent=pm_sent,
    )
    can_continue = on_interaction(
        succeed=interaction_succeed,
        followed=followed,
        scraped=scraped,
    )
    return can_continue


def random_choice(interact_percentage):
    from random import randint

    random_number = randint(1, 100)
    if interact_percentage >= random_number:
        return True
    else:
        return False


def handle_blogger(
    self,
    device,
    session_state,
    blogger,
    current_job,
    storage,
    profile_filter,
    on_interaction,
    interaction,
    is_follow_limit_reached,
):
    if not nav_to_blogger(device, blogger, session_state.my_username):
        return
    can_interact = False
    if storage.is_user_in_blacklist(blogger):
        logger.info(f"@{blogger} is in blacklist. Skip.")
    else:
        interacted, interacted_when = storage.check_user_was_interacted(blogger)
        if interacted:
            interact_after = timedelta(hours=float(self.args.can_reinteract_after))
            can_reinteract = storage.can_be_reinteract(interacted_when, interact_after)
            logger.info(
                f"@{blogger}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
            )
            if can_reinteract:
                can_interact = True
        else:
            can_interact = True

    if can_interact:
        logger.info(
            f"@{blogger}: interact",
            extra={"color": f"{Fore.YELLOW}"},
        )
        if not interact(
            storage,
            is_follow_limit_reached,
            blogger,
            interaction,
            device,
            session_state,
            current_job,
            on_interaction,
        ):
            return


def handle_blogger_from_file(
    self,
    device,
    current_filename,
    current_job,
    storage,
    on_interaction,
    interaction,
    is_follow_limit_reached,
):
    need_to_refresh = True
    on_following_list = False
    limit_reached = False
    if path.isfile(current_filename):
        with open(current_filename, "r") as f:
            for line in f:
                username = line.strip()
                if username != "":
                    if current_job == "unfollow-from-file":
                        unfollowed = do_unfollow_from_list(
                            device, username, on_following_list
                        )
                        on_following_list = True
                        if unfollowed:
                            storage.add_interacted_user(
                                username, self.session_state.id, unfollowed=True
                            )
                            self.session_state.totalUnfollowed += 1
                            limit_reached = self.session_state.check_limit(
                                self.args, limit_type=self.session_state.Limit.UNFOLLOWS
                            )
                        if limit_reached:
                            logger.info("Unfollows limit reached.")
                            break
                    else:
                        can_interact = False
                        if storage.is_user_in_blacklist(username):
                            logger.info(f"@{username} is in blacklist. Skip.")
                        else:
                            (
                                interacted,
                                interacted_when,
                            ) = storage.check_user_was_interacted(username)
                            if interacted:
                                interact_after = timedelta(
                                    hours=float(self.args.can_reinteract_after)
                                )
                                can_reinteract = storage.can_be_reinteract(
                                    interacted_when, interact_after
                                )
                                logger.info(
                                    f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                                )
                                if can_reinteract:
                                    can_interact = True
                            else:
                                can_interact = True

                        if can_interact:
                            if need_to_refresh:
                                search_view = TabBarView(device).navigateToSearch()
                            profile_view = search_view.navigateToUsername(
                                username, True
                            )
                            need_to_refresh = False
                            if not profile_view:
                                continue

                            if not interact(
                                storage,
                                is_follow_limit_reached,
                                username,
                                interaction,
                                device,
                                self.session_state,
                                current_job,
                                on_interaction,
                            ):
                                return
                            device.back()
                        else:
                            continue
                else:
                    logger.info("Line in file is blank, skip.")
            remaining = f.readlines()
        if self.args.delete_interacted_users:
            with atomic_write(current_filename, overwrite=True, encoding="utf-8") as f:
                f.writelines(remaining)
    else:
        logger.warning(f"File {current_filename} not found.")
        return

    logger.info(f"Interact with users in {current_filename} completed.")
    device.back()


def do_unfollow_from_list(device, username, on_following_list):
    if not on_following_list:
        ProfileView(device)._click_on_avatar()
        if ProfileView(device).navigateToFollowing():
            if UniversalActions(device).search_text(username):
                return FollowingView(device).do_unfollow_from_list(username)
    else:
        if username is not None:
            UniversalActions(device).search_text(username)
        return FollowingView(device).do_unfollow_from_list(username)


def handle_likers(
    self,
    device,
    session_state,
    target,
    current_job,
    storage,
    profile_filter,
    posts_end_detector,
    on_interaction,
    interaction,
    is_follow_limit_reached,
):
    if current_job == "blogger-post-likers":
        if not nav_to_post_likers(device, target, session_state.my_username):
            return False
    else:
        if not nav_to_hashtag_or_place(device, target, current_job):
            return False

    post_description = ""
    nr_same_post = 0
    nr_same_posts_max = 3
    while True:
        flag, post_description, _, _, _ = PostsViewList(device)._check_if_last_post(
            post_description, current_job
        )
        has_likers, number_of_likers = PostsViewList(device)._find_likers_container()
        if flag:
            nr_same_post += 1
            logger.info(f"Warning: {nr_same_post}/{nr_same_posts_max} repeated posts.")
            if nr_same_post == nr_same_posts_max:
                logger.info(
                    f"Scrolled through {nr_same_posts_max} posts with same description and author. Finish.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                break
        else:
            nr_same_post = 0

        if (
            has_likers
            and profile_filter.is_num_likers_in_range(number_of_likers)
            and number_of_likers != 1
        ):
            PostsViewList(device).open_likers_container()
        else:
            PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
            continue

        posts_end_detector.notify_new_page()

        likes_list_view = OpenedPostView(device)._getListViewLikers()
        if likes_list_view is None:
            return
        prev_screen_iterated_likers = []

        while True:
            logger.info("Iterate over visible likers.")
            screen_iterated_likers = []
            opened = False
            user_container = OpenedPostView(device)._getUserContainer()
            if user_container is None:
                return
            try:
                for item in OpenedPostView(device)._getUserContainer():
                    element_opened = False
                    username_view = OpenedPostView(device)._getUserName(item)
                    if not username_view.exists(Timeout.MEDIUM):
                        logger.info(
                            "Next item not found: probably reached end of the screen.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        break

                    username = username_view.get_text()
                    screen_iterated_likers.append(username)
                    posts_end_detector.notify_username_iterated(username)
                    can_interact = False
                    if storage.is_user_in_blacklist(username):
                        logger.info(f"@{username} is in blacklist. Skip.")
                    else:
                        (
                            interacted,
                            interacted_when,
                        ) = storage.check_user_was_interacted(username)
                        if interacted:
                            interact_after = timedelta(
                                hours=float(self.args.can_reinteract_after)
                            )
                            can_reinteract = storage.can_be_reinteract(
                                interacted_when, interact_after
                            )
                            logger.info(
                                f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                            )
                            if can_reinteract:
                                can_interact = True
                        else:
                            can_interact = True

                    if can_interact:
                        logger.info(
                            f"@{username}: interact",
                            extra={"color": f"{Fore.YELLOW}"},
                        )
                        element_opened = username_view.click_retry()

                        if element_opened:
                            if not interact(
                                storage,
                                is_follow_limit_reached,
                                username,
                                interaction,
                                device,
                                session_state,
                                current_job,
                                on_interaction,
                            ):
                                return
                    if element_opened:
                        opened = True
                        logger.info("Back to likers list.")
                        device.back()

            except IndexError:
                logger.info(
                    "Cannot get next item: probably reached end of the screen.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                break
            go_back = False
            if screen_iterated_likers == prev_screen_iterated_likers:
                logger.info(
                    "Iterated exactly the same likers twice.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                go_back = True
            if go_back:
                prev_screen_iterated_likers.clear()
                prev_screen_iterated_likers += screen_iterated_likers
                logger.info(
                    f"Back to {target}'s posts list.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                device.back()
                logger.info("Going to the next post.")
                PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
                break
            if posts_end_detector.is_fling_limit_reached():
                prev_screen_iterated_likers.clear()
                prev_screen_iterated_likers += screen_iterated_likers
                logger.info(
                    "Reached fling limit. Fling to see other likers.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                likes_list_view.fling(Direction.DOWN)
            else:
                prev_screen_iterated_likers.clear()
                prev_screen_iterated_likers += screen_iterated_likers
                logger.info(
                    "Scroll to see other likers.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                likes_list_view.scroll(Direction.DOWN)

            if posts_end_detector.is_the_end():
                device.back()
                PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
                break
            if not opened:
                logger.info(
                    "All likers skipped.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                posts_end_detector.notify_skipped_all()
                if posts_end_detector.is_skipped_limit_reached():
                    posts_end_detector.reset_skipped_all()
                    return


def handle_posts(
    self,
    device,
    session_state,
    target,
    current_job,
    storage,
    profile_filter,
    on_interaction,
    interaction,
    is_follow_limit_reached,
    interact_percentage,
    scraping_file,
):
    if current_job == "feed":
        nav_to_feed(device)
        count_feed_limit = get_value(
            self.args.feed,
            "Feed interact count: {}",
            10,
        )
        count = 0
        PostsViewList(device)._refresh_feed()
    else:
        if not nav_to_hashtag_or_place(device, target, current_job):
            return

    post_description = ""
    nr_same_post = 0
    nr_same_posts_max = 3
    while True:
        flag, post_description, username, is_ad, is_hashtag = PostsViewList(
            device
        )._check_if_last_post(post_description, current_job)
        has_likers, number_of_likers = PostsViewList(device)._find_likers_container()
        if not (is_ad or is_hashtag):
            if flag:
                nr_same_post += 1
                logger.info(
                    f"Warning: {nr_same_post}/{nr_same_posts_max} repeated posts."
                )
                if nr_same_post == nr_same_posts_max:
                    logger.info(
                        f"Scrolled through {nr_same_posts_max} posts with same description and author. Finish."
                    )
                    break
            else:
                nr_same_post = 0
            if random_choice(interact_percentage):
                can_interact = False
                if storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip.")
                else:
                    likes_in_range = profile_filter.is_num_likers_in_range(
                        number_of_likers
                    )
                    if current_job != "feed":
                        interacted, interacted_when = storage.check_user_was_interacted(
                            username
                        )
                        if interacted:
                            interact_after = timedelta(
                                hours=float(self.args.can_reinteract_after)
                            )
                            can_reinteract = storage.can_be_reinteract(
                                interacted_when, interact_after
                            )
                            logger.info(
                                f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                            )
                            if can_reinteract:
                                can_interact = True
                        else:
                            can_interact = True
                    else:
                        can_interact = True

                if can_interact and (likes_in_range or not has_likers):
                    logger.info(
                        f"@{username}: interact", extra={"color": f"{Fore.YELLOW}"}
                    )
                    if scraping_file is None:
                        PostsViewList(device)._like_in_post_view(LikeMode.DOUBLE_CLICK)
                        UniversalActions.detect_block(device)
                        if not PostsViewList(device)._check_if_liked():
                            PostsViewList(device)._like_in_post_view(
                                LikeMode.SINGLE_CLICK
                            )
                            UniversalActions.detect_block(device)
                        session_state.totalLikes += 1
                        if current_job == "feed":
                            count += 1
                            logger.info(
                                f"Interacted feed bloggers: {count}/{count_feed_limit}"
                            )
                            if count >= count_feed_limit:
                                logger.info(
                                    f"Interacted {count} bloggers in feed, finish."
                                )
                                TabBarView(device).navigateToProfile()
                                return
                    if current_job != "feed":
                        opened, _, _ = PostsViewList(device)._post_owner(
                            current_job, Owner.OPEN, username
                        )
                        if opened:
                            if not interact(
                                storage,
                                is_follow_limit_reached,
                                username,
                                interaction,
                                device,
                                session_state,
                                current_job,
                                on_interaction,
                            ):
                                return
                            device.back()

        PostsViewList(device).swipe_to_fit_posts(SwipeTo.HALF_PHOTO)
        PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)


def handle_followers(
    self,
    device,
    session_state,
    username,
    current_job,
    storage,
    on_interaction,
    interaction,
    is_follow_limit_reached,
    scroll_end_detector,
):
    is_myself = username == session_state.my_username
    if not nav_to_blogger(device, username, current_job):
        return

    def scroll_to_bottom(self, device):
        logger.info("Scroll to bottom.")

        def is_end_reached():
            see_all_button = device.find(
                resourceId=self.ResourceID.SEE_ALL_BUTTON,
                className=ClassName.TEXT_VIEW,
            )
            return see_all_button.exists()

        list_view = device.find(
            resourceId=self.ResourceID.LIST, className=ClassName.LIST_VIEW
        )
        while not is_end_reached():
            list_view.fling(Direction.DOWN)

        logger.info("Scroll back to the first follower.")

        def is_at_least_one_follower():
            follower = device.find(
                resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
                className=ClassName.LINEAR_LAYOUT,
            )
            return follower.exists()

        while not is_at_least_one_follower():
            list_view.scroll(Direction.UP)

        if is_myself:
            scroll_to_bottom(device)

    iterate_over_followers(
        self,
        device,
        interaction,
        is_follow_limit_reached,
        storage,
        on_interaction,
        is_myself,
        scroll_end_detector,
        session_state,
        current_job,
        username,
    )


def iterate_over_followers(
    self,
    device,
    interaction,
    is_follow_limit_reached,
    storage,
    on_interaction,
    is_myself,
    scroll_end_detector,
    session_state,
    current_job,
    target,
):
    device.find(
        resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
        className=ClassName.LINEAR_LAYOUT,
    ).wait(Timeout.LONG)

    def scrolled_to_top():
        row_search = device.find(
            resourceId=self.ResourceID.ROW_SEARCH_EDIT_TEXT,
            className=ClassName.EDIT_TEXT,
        )
        return row_search.exists()

    while True:
        logger.info("Iterate over visible followers.")
        screen_iterated_followers = []
        screen_skipped_followers_count = 0
        scroll_end_detector.notify_new_page()

        try:
            for item in device.find(
                resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
                className=ClassName.LINEAR_LAYOUT,
            ):
                element_opened = False
                user_info_view = item.child(index=1)
                user_name_view = user_info_view.child(index=0).child()
                if not user_name_view.exists():
                    logger.info(
                        "Next item not found: probably reached end of the screen.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    break

                username = user_name_view.get_text()
                screen_iterated_followers.append(username)
                scroll_end_detector.notify_username_iterated(username)

                can_interact = False
                if storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip.")
                else:
                    interacted, interacted_when = storage.check_user_was_interacted(
                        username
                    )
                    if interacted:
                        interact_after = timedelta(
                            hours=float(self.args.can_reinteract_after)
                        )
                        can_reinteract = storage.can_be_reinteract(
                            interacted_when, interact_after
                        )
                        logger.info(
                            f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                        )
                        if can_reinteract:
                            can_interact = True
                        else:
                            screen_skipped_followers_count += 1
                    else:
                        can_interact = True

                if can_interact:
                    logger.info(
                        f"@{username}: interact", extra={"color": f"{Fore.YELLOW}"}
                    )
                    element_opened = user_name_view.click_retry()

                    if element_opened:
                        if not interact(
                            storage,
                            is_follow_limit_reached,
                            username,
                            interaction,
                            device,
                            session_state,
                            current_job,
                            on_interaction,
                        ):
                            return
                    if element_opened:
                        logger.info("Back to followers list")
                        device.back()

        except IndexError:
            logger.info(
                "Cannot get next item: probably reached end of the screen.",
                extra={"color": f"{Fore.GREEN}"},
            )

        if is_myself and scrolled_to_top():
            logger.info("Scrolled to top, finish.", extra={"color": f"{Fore.GREEN}"})
            return
        elif len(screen_iterated_followers) > 0:
            load_more_button = device.find(
                resourceId=self.ResourceID.ROW_LOAD_MORE_BUTTON
            )
            load_more_button_exists = load_more_button.exists()

            if scroll_end_detector.is_the_end():
                return

            need_swipe = screen_skipped_followers_count == len(
                screen_iterated_followers
            )
            list_view = device.find(
                resourceId=self.ResourceID.LIST, className=ClassName.LIST_VIEW
            )
            if not list_view.exists():
                logger.error(
                    "Cannot find the list of followers. Trying to press back again."
                )
                device.back()
                list_view = device.find(
                    resourceId=self.ResourceID.LIST,
                    className=ClassName.LIST_VIEW,
                )

            if is_myself:
                logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                list_view.scroll(Direction.UP)
            else:
                pressed_retry = False
                if load_more_button_exists:
                    retry_button = load_more_button.child(
                        className=ClassName.IMAGE_VIEW,
                        descriptionMatches=case_insensitive_re("Retry"),
                    )
                    if retry_button.exists():
                        random_sleep()
                        """It exist but can disappear without pressing on it"""
                        if retry_button.exists():
                            logger.info('Press "Load" button and wait few seconds.')
                            retry_button.click_retry()
                            random_sleep(5, 10, modulable=False)
                            pressed_retry = True

                if need_swipe and not pressed_retry:
                    scroll_end_detector.notify_skipped_all()
                    if scroll_end_detector.is_skipped_limit_reached():
                        return
                    if scroll_end_detector.is_fling_limit_reached():
                        logger.info(
                            "Limit of all followers skipped reached, let's fling.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        list_view.fling(Direction.DOWN)
                    else:
                        logger.info(
                            "All followers skipped, let's scroll.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        list_view.scroll(Direction.DOWN)
                else:
                    logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                    list_view.scroll(Direction.DOWN)
        else:
            logger.info(
                "No followers were iterated, finish.",
                extra={"color": f"{Fore.GREEN}"},
            )
            return
