import logging
from functools import partial
from colorama import Fore
from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.storage import FollowingStatus
from GramAddict.core.navigation import (
    nav_to_hashtag_or_place,
    nav_to_blogger,
    nav_to_post_likers,
)
from GramAddict.core.resources import ClassName, ResourceID as resources
from GramAddict.core.utils import (
    random_sleep,
)
from GramAddict.core.views import (
    PostsViewList,
    OpenedPostView,
    SwipeTo,
    Owner,
    LikeMode,
    UniversalActions,
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
    target,
    on_interaction,
):
    can_follow = not is_follow_limit_reached() and (
        storage.get_following_status(username) == FollowingStatus.NONE
        or storage.get_following_status(username) == FollowingStatus.NOT_IN_LIST
    )

    (
        interaction_succeed,
        followed,
        scraped,
        number_of_liked,
        number_of_watched,
        number_of_comments,
    ) = interaction(device, username=username, can_follow=can_follow)

    add_interacted_user = partial(
        storage.add_interacted_user,
        session_id=session_state.id,
        job_name=current_job,
        target=target,
    )

    add_interacted_user(
        username,
        followed=followed,
        scraped=scraped,
        liked=number_of_liked,
        watched=number_of_watched,
        commented=number_of_comments,
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
    if interact_percentage > random_number:
        return True
    else:
        return False


def handle_likers(
    device,
    session_state,
    target,
    follow_limit,
    current_job,
    storage,
    profile_filter,
    posts_end_detector,
    on_interaction,
    interaction,
    is_follow_limit_reached,
    is_blogger_post_likers,
):
    if is_blogger_post_likers:
        if not nav_to_post_likers(device, target, session_state.my_username):
            return False
    else:
        if not nav_to_hashtag_or_place(device, target, current_job):
            return False

    post_description = ""
    nr_same_post = 0
    nr_same_posts_max = 3
    while True:
        likers_container_exists = PostsViewList(device)._find_likers_container()
        has_one_liker_or_none = PostsViewList(device)._check_if_only_one_liker_or_none()

        flag, post_description = PostsViewList(device)._check_if_last_post(
            post_description
        )
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

        if likers_container_exists and not has_one_liker_or_none:
            PostsViewList(device).open_likers_container()
        else:
            PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
            continue

        posts_end_detector.notify_new_page()
        random_sleep()

        likes_list_view = OpenedPostView(device)._getListViewLikers()
        prev_screen_iterated_likers = []

        while True:
            logger.info("Iterate over visible likers.")
            screen_iterated_likers = []
            opened = False

            try:
                for item in OpenedPostView(device)._getUserCountainer():
                    username_view = OpenedPostView(device)._getUserName(item)
                    if not username_view.exists():
                        logger.info(
                            "Next item not found: probably reached end of the screen.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        break

                    username = username_view.get_text()
                    profile_interact = profile_filter.check_profile_from_list(
                        device, item, username
                    )
                    screen_iterated_likers.append(username)
                    posts_end_detector.notify_username_iterated(username)
                    if not profile_interact:
                        continue
                    elif storage.is_user_in_blacklist(username):
                        logger.info(f"@{username} is in blacklist. Skip.")
                        continue
                    elif storage.check_user_was_interacted(username):
                        logger.info(f"@{username}: already interacted. Skip.")
                        continue
                    else:
                        logger.info(
                            f"@{username}: interact",
                            extra={"color": f"{Fore.YELLOW}"},
                        )
                        username_view.click()
                        if not interact(
                            storage,
                            is_follow_limit_reached,
                            username,
                            interaction,
                            device,
                            session_state,
                            current_job,
                            target,
                            on_interaction,
                        ):
                            return

                    opened = True
                    logger.info("Back to likers list.")
                    device.back()
                    random_sleep()

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
                random_sleep()
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
                likes_list_view.fling(DeviceFacade.Direction.BOTTOM)
            else:
                prev_screen_iterated_likers.clear()
                prev_screen_iterated_likers += screen_iterated_likers
                logger.info(
                    "Scroll to see other likers.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                likes_list_view.scroll(DeviceFacade.Direction.BOTTOM)

            if posts_end_detector.is_the_end():
                random_sleep()
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
    device,
    session_state,
    target,
    follow_limit,
    current_job,
    storage,
    scraping_file,
    profile_filter,
    on_interaction,
    interaction,
    is_follow_limit_reached,
    interact_percentage,
):

    if not nav_to_hashtag_or_place(device, target, current_job):
        return

    post_description = ""
    nr_same_post = 0
    nr_same_posts_max = 3
    while True:
        flag, post_description = PostsViewList(device)._check_if_last_post(
            post_description
        )
        if flag:
            nr_same_post += 1
            logger.info(f"Warning: {nr_same_post}/{nr_same_posts_max} repeated posts.")
            if nr_same_post == nr_same_posts_max:
                logger.info(
                    f"Scrolled through {nr_same_posts_max} posts with same description and author. Finish."
                )
                break
        else:
            nr_same_post = 0
        if random_choice(interact_percentage):
            username = PostsViewList(device)._post_owner(Owner.GET_NAME)[:-3]
            if storage.is_user_in_blacklist(username):
                logger.info(f"@{username} is in blacklist. Skip.")
            elif storage.check_user_was_interacted(username):
                logger.info(f"@{username}: already interacted. Skip.")
            else:
                logger.info(f"@{username}: interact", extra={"color": f"{Fore.YELLOW}"})
                if scraping_file is None:
                    PostsViewList(device)._like_in_post_view(LikeMode.DOUBLE_CLICK)
                    UniversalActions.detect_block(device)
                    if not PostsViewList(device)._check_if_liked():
                        PostsViewList(device)._like_in_post_view(LikeMode.SINGLE_CLICK)
                        UniversalActions.detect_block(device)
                    session_state.totalLikes += 1
                    random_sleep(1, 2)
                if PostsViewList(device)._post_owner(Owner.OPEN):
                    if not interact(
                        storage,
                        is_follow_limit_reached,
                        username,
                        interaction,
                        device,
                        session_state,
                        current_job,
                        target,
                        on_interaction,
                    ):
                        return
                    device.back()

        PostsViewList(device).swipe_to_fit_posts(SwipeTo.HALF_PHOTO)
        random_sleep(0, 1)
        PostsViewList(device).swipe_to_fit_posts(SwipeTo.NEXT_POST)
        random_sleep()


def handle_followers(
    self,
    device,
    session_state,
    username,
    follow_limit,
    current_job,
    storage,
    profile_filter,
    scroll_end_detector,
    on_interaction,
    interaction,
    is_follow_limit_reached,
):
    is_myself = username == session_state.my_username
    if not nav_to_blogger(device, username, current_job):
        return

    def scroll_to_bottom(self, device):
        logger.info("Scroll to bottom")

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
            list_view.fling(DeviceFacade.Direction.BOTTOM)

        logger.info("Scroll back to the first follower")

        def is_at_least_one_follower():
            follower = device.find(
                resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
                className=ClassName.LINEAR_LAYOUT,
            )
            return follower.exists()

        while not is_at_least_one_follower():
            list_view.scroll(DeviceFacade.Direction.TOP)

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
    ).wait()

    def scrolled_to_top():
        row_search = device.find(
            resourceId=self.ResourceID.ROW_SEARCH_EDIT_TEXT,
            className=ClassName.EDIT_TEXT,
        )
        return row_search.exists()

    while True:
        logger.info("Iterate over visible followers")
        random_sleep()
        screen_iterated_followers = []
        screen_skipped_followers_count = 0
        scroll_end_detector.notify_new_page()

        try:
            for item in device.find(
                resourceId=self.ResourceID.FOLLOW_LIST_CONTAINER,
                className=ClassName.LINEAR_LAYOUT,
            ):
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

                if storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip.")
                elif not is_myself and storage.check_user_was_interacted(username):
                    logger.info(f"@{username}: already interacted. Skip.")
                    screen_skipped_followers_count += 1
                elif is_myself and storage.check_user_was_interacted_recently(username):
                    logger.info(
                        f"@{username}: already interacted in the last week. Skip."
                    )
                    screen_skipped_followers_count += 1
                else:
                    logger.info(f"@{username}: interact")
                    user_name_view.click()

                    if not interact(
                        storage,
                        is_follow_limit_reached,
                        username,
                        interaction,
                        device,
                        session_state,
                        current_job,
                        target,
                        on_interaction,
                    ):
                        return

                    logger.info("Back to followers list")
                    device.back()
                    random_sleep()

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
                list_view.scroll(DeviceFacade.Direction.TOP)
            else:
                pressed_retry = False
                if load_more_button_exists:
                    retry_button = load_more_button.child(
                        className=ClassName.IMAGE_VIEW
                    )
                    if retry_button.exists():
                        logger.info('Press "Load" button')
                        retry_button.click()
                        random_sleep()
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
                        list_view.fling(DeviceFacade.Direction.BOTTOM)
                    else:
                        logger.info(
                            "All followers skipped, let's scroll.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        list_view.scroll(DeviceFacade.Direction.BOTTOM)
                else:
                    logger.info("Need to scroll now", extra={"color": f"{Fore.GREEN}"})
                    list_view.scroll(DeviceFacade.Direction.BOTTOM)
        else:
            logger.info(
                "No followers were iterated, finish.",
                extra={"color": f"{Fore.GREEN}"},
            )
            return
