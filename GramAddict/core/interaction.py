import code

from random import shuffle, randint
from typing import Tuple

from GramAddict.core.device_facade import DeviceFacade
from GramAddict.core.navigation import switch_to_english
from GramAddict.core.report import print_short_report
from GramAddict.core.utils import (
    COLOR_OKGREEN,
    COLOR_FAIL,
    COLOR_ENDC,
    COLOR_BOLD,
    save_crash,
    get_value,
    random_sleep,
    detect_block,
    print,
)
from GramAddict.core.views import LanguageNotEnglishException, ProfileView

TEXTVIEW_OR_BUTTON_REGEX = "android.widget.TextView|android.widget.Button"
FOLLOW_REGEX = "Follow|Follow Back"
UNFOLLOW_REGEX = "Following|Requested"


def interact_with_user(
    device,
    username,
    my_username,
    likes_count,
    stories_count,
    on_like,
    on_watch,
    can_follow,
    follow_percentage,
    profile_filter
) -> Tuple[bool, bool]:
    """
    :return: (whether interaction succeed, whether @username was followed during the interaction)
    """
    if username == my_username:
        print("It's you, skip.")
        return False, False

    random_sleep()

    if not profile_filter.check_profile(device, username):
        return False, False

    likes_value = get_value(likes_count, "Likes count: {}", 2)
    if likes_value > 12:
        print(COLOR_FAIL + "Max number of likes per user is 12" + COLOR_ENDC)
        likes_value = 12

    profile_view = ProfileView(device)
    is_private = profile_view.isPrivateAccount()
    posts_count = profile_view.getPostsCount()
    is_empty = posts_count == 0

    if is_private or is_empty:
        private_empty = "Private" if is_private else "Empty"

        print(COLOR_OKGREEN + f"{private_empty} account." + COLOR_ENDC)
        if can_follow and profile_filter.can_follow_private_or_empty():
            followed = _follow(device, username, follow_percentage)
        else:
            followed = False
            print(COLOR_OKGREEN + "Skip user." + COLOR_ENDC)
        return False, followed

    # stories_percentage = 100
    stories_value = get_value(stories_count, "Stories count: {}", 2)
    if stories_value > 6:
        print(COLOR_FAIL + "Max number of stories per user is 6" + COLOR_ENDC)
        stories_value = 6

    watched_amount = _watch_stories(device, username, stories_value)  # , stories_percentage, )
    print(COLOR_OKGREEN + "We have watched {} stories of @{}".format(watched_amount, username) + "." + COLOR_ENDC)
    for _iter in range(0, watched_amount):  # Another way to do this?
        on_watch()  # +=1

    # return False, False

    posts_tab_view = profile_view.navigateToPostsTab()
    if posts_tab_view.scrollDown():  # scroll down to view all maximum 12 posts
        print("Scrolled down to see more posts.")
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

        print(
            "Open post #"
            + str(i + 1)
            + " ("
            + str(row + 1)
            + " row, "
            + str(column + 1)
            + " column)"
        )
        opened_post_view = posts_tab_view.navigateToPost(row, column)
        random_sleep()

        like_succeed = False
        if opened_post_view:
            print("Double click post")
            opened_post_view.likePost()
            random_sleep()
            if not opened_post_view.isPostLiked():
                print("Double click failed. Try the like button.")
                opened_post_view.likePost(click_btn_like=True)
                random_sleep()

            like_succeed = opened_post_view.isPostLiked()
            if like_succeed:
                detect_block(device)
                on_like()

            print("Back to profile")
            device.back()

        if not opened_post_view or not like_succeed:
            reason = "open" if not opened_post_view else "like"
            print(
                f"{COLOR_BOLD}Could not {reason} photo. Posts count: {posts_count} {COLOR_ENDC}"
            )

            if can_follow and profile_filter.can_follow_private_or_empty():
                followed = _follow(device, username, follow_percentage)
            else:
                followed = False

            if not followed:
                print(COLOR_OKGREEN + "Skip user." + COLOR_ENDC)
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
        print("Reached total likes limit, finish.")
        on_likes_limit_reached()
        can_continue = False

    successful_interactions_count = session_state.successfulInteractions.get(source)
    if (
        successful_interactions_count
        and successful_interactions_count >= interactions_limit
    ):
        print(
            "Made "
            + str(successful_interactions_count)
            + " successful interactions, finish."
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

    print("Following...")
    coordinator_layout = device.find(
        resourceId="com.instagram.android:id/coordinator_root_layout"
    )
    if coordinator_layout.exists():
        coordinator_layout.scroll(DeviceFacade.Direction.TOP)

    random_sleep()

    profile_header_actions_layout = device.find(
        resourceId="com.instagram.android:id/profile_header_actions_top_row",
        className="android.widget.LinearLayout",
    )
    if not profile_header_actions_layout.exists():
        print(COLOR_FAIL + "Cannot find profile actions." + COLOR_ENDC)
        return False

    follow_button = profile_header_actions_layout.child(
        classNameMatches=TEXTVIEW_OR_BUTTON_REGEX,
        clickable=True,
        textMatches=FOLLOW_REGEX,
    )
    if not follow_button.exists():
        unfollow_button = profile_header_actions_layout.child(
            classNameMatches=TEXTVIEW_OR_BUTTON_REGEX,
            clickable=True,
            textMatches=UNFOLLOW_REGEX,
        )
        if unfollow_button.exists():
            print(COLOR_OKGREEN + "You already follow @" + username + "." + COLOR_ENDC)
            return False
        else:
            print(
                COLOR_FAIL
                + "Cannot find neither Follow button, nor Unfollow button. Maybe not "
                "English language is set?" + COLOR_ENDC
            )
            save_crash(device)
            switch_to_english(device)
            raise LanguageNotEnglishException()

    follow_button.click()
    detect_block(device)
    print(COLOR_OKGREEN + "Followed @" + username + COLOR_ENDC)
    random_sleep()
    return True


def _on_watch(sessions, session_state):
    session_state = sessions[-1]
    session_state.totalWatched += 1


def _watch_stories(device, username, stories_value):  # , stories_percentage):
    # stories_chance = randint(1, 100)
    # if stories_chance > stories_percentage:
    #     return 0

    if stories_value == 0:
        return 0

    reel_ring = device.find(
        resourceId="com.instagram.android:id/reel_ring",
        className="android.view.View",
    )
    if reel_ring.exists():
        stories_to_watch = randint(1, stories_value)
        print("This user have a stories, going to watch {}/or max stories".format(stories_to_watch))
        profile_picture = device.find(
            resourceId="com.instagram.android:id/row_profile_header_imageview",
            className="android.widget.ImageView",
        )
        profile_picture.click()  # Open the first story
        random_sleep(2, 6)
        if stories_to_watch > 1:
            for watched_amount in range(0, stories_to_watch):
                reel_viewer_title = device.find(
                    resourceId="com.instagram.android:id/reel_viewer_title",
                    className="android.widget.TextView"
                )
                if reel_viewer_title.exists():
                    storie_frame = device.find(
                        resourceId="com.instagram.android:id/reel_viewer_image_view",
                        className="android.widget.FrameLayout",
                    )
                    if storie_frame.exists() and watched_amount != stories_to_watch:
                        storie_frame.click("right")
                        random_sleep(2, 6)
                else:
                    # print("We are again in profile page")
                    break
        else:
            watched_amount = 0

        # Iteartion completed, please check again if we are in story view
        reel_viewer_title = device.find(
            resourceId="com.instagram.android:id/reel_viewer_title",
            className="android.widget.TextView"
        )
        if reel_viewer_title.exists():
            print("Back to user page")
            device.back()
        random_sleep(3, 6)
        # It's not really accurate, becase the stories can reach the max time for example
        return watched_amount + 1
    return 0
