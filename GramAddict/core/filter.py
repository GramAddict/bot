from time import sleep
import emoji
import yaml
from GramAddict.core.utils import random_sleep
from GramAddict.core.device_facade import Timeout
import json
import logging
import os
import re
import unicodedata
import sys

from colorama import Fore
from langdetect import detect
from enum import Enum, auto
from datetime import datetime
from GramAddict.core.views import ProfileView, FollowStatus, OpenedPostView
from GramAddict.core.resources import ClassName, ResourceID as resources

logger = logging.getLogger(__name__)

FIELD_SKIP_BUSINESS = "skip_business"
FIELD_SKIP_NON_BUSINESS = "skip_non_business"
FIELD_SKIP_FOLLOWING = "skip_following"
FIELD_SKIP_FOLLOWER = "skip_follower"
FIELD_MIN_FOLLOWERS = "min_followers"
FIELD_MAX_FOLLOWERS = "max_followers"
FIELD_MIN_FOLLOWINGS = "min_followings"
FIELD_MAX_FOLLOWINGS = "max_followings"
FIELD_MIN_POTENCY_RATIO = "min_potency_ratio"
FIELD_MAX_POTENCY_RATIO = "max_potency_ratio"
FIELD_FOLLOW_PRIVATE_OR_EMPTY = "follow_private_or_empty"
PM_TO_PRIVATE_OR_EMPTY = "pm_to_private_or_empty"
FIELD_COMMENT_PHOTOS = "comment_photos"
FIELD_COMMENT_VIDEOS = "comment_videos"
FIELD_INTERACT_ONLY_PRIVATE = "interact_only_private"
FIELD_BLACKLIST_WORDS = "blacklist_words"
FIELD_MANDATORY_WORDS = "mandatory_words"
FIELD_SPECIFIC_ALPHABET = "specific_alphabet"
FIELD_BIO_LANGUAGE = "biography_language"
FIELD_MIN_POSTS = "min_posts"

IGNORE_CHARSETS = ["MATHEMATICAL"]


def load_config(config):
    global args
    global configs
    global ResourceID
    args = config.args
    configs = config
    ResourceID = resources(config.args.app_id)


class SkipReason(Enum):
    YOU_FOLLOW = auto()
    FOLLOW_YOU = auto()
    IS_PRIVATE = auto()
    UNKNOWN_PRIVACY = auto()
    LT_FOLLOWERS = auto()
    GT_FOLLOWERS = auto()
    LT_FOLLOWINGS = auto()
    GT_FOLLOWINGS = auto()
    POTENCY_RATIO = auto()
    UNDEFINED_FOLLOWERS_FOLLOWING = auto()
    HAS_BUSINESS = auto()
    HAS_NON_BUSINESS = auto()
    NOT_ENOUGH_POSTS = auto()
    BLACKLISTED_WORD = auto()
    MISSING_MANDATORY_WORDS = auto()
    ALPHABET_NOT_MATCH = auto()
    ALPHABET_NAME_NOT_MATCH = auto()
    BIOGRAPHY_LANGUAGE_NOT_MATCH = auto()
    NOT_LOADED = auto()


class Profile(object):
    def __init__(
        self,
        follow_button_text,
        is_private,
        has_business_category,
        posts_count,
        biography,
        fullname,
    ):
        self.datetime = str(datetime.now())
        self.followers = 0
        self.followings = 0

        self.follow_button_text = follow_button_text
        self.is_private = is_private
        self.has_business_category = has_business_category
        self.posts_count = posts_count
        self.biography = biography
        self.fullname = fullname

    def set_followers_and_following(self, followers: int, followings: int):
        self.followers = followers
        self.followings = followings
        self.potency_ratio = (
            0 if self.followings == 0 else self.followers / self.followings
        )


class Filter:
    conditions = None

    def __init__(self, storage=None):
        filter_path = storage.filter_path
        if not configs.args.disable_filters:
            if os.path.exists(filter_path) and filter_path.endswith(".yml"):
                with open(filter_path, "r", encoding="utf-8") as stream:
                    try:
                        self.conditions = yaml.safe_load(stream)
                    except Exception as e:
                        logger.error(f"Error: {e}")

            elif os.path.exists(filter_path):
                with open(filter_path) as json_file:
                    try:
                        self.conditions = json.load(json_file)
                        logger.warning(
                            "Using filter.json is deprecated from version 2.3.0 and will stop working very soon, use filters.yml instead!"
                        )
                        sleep(5)
                    except Exception as e:
                        logger.error(
                            f"Please check {json_file.name}, it contains this error: {e}"
                        )
                        sys.exit(0)
            else:
                logger.warning(
                    f"The filters file {filter_path} doesn't exists. Download it from https://github.com/GramAddict/bot/blob/08e1d7aff39ec47543fa78aadd7a2f034b9ae34d/config-examples/filters.yml and place it in your account folder!"
                )
        else:
            logger.warning("Filters are disabled!")
        self.storage = storage

    def check_profile_from_list(self, device, item, username):
        """check profile from list without open it"""
        if self.conditions is None:
            return True

        field_skip_following = self.conditions.get(FIELD_SKIP_FOLLOWING, False)

        if field_skip_following:
            following = OpenedPostView(device)._isFollowing(item)

            if following:
                logger.info(
                    f"You follow @{username}, skip.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return False

        return True

    def return_check_profile(self, username, profile_data, skip_reason=None):
        if self.storage is not None:
            self.storage.add_filter_user(username, profile_data, skip_reason)

        return False if skip_reason is None else True

    def check_profile(self, device, username):
        """
        This method assumes being on someone's profile already.
        """
        if self.conditions is not None:
            field_skip_business = self.conditions.get(FIELD_SKIP_BUSINESS, False)
            field_skip_non_business = self.conditions.get(
                FIELD_SKIP_NON_BUSINESS, False
            )
            field_skip_following = self.conditions.get(FIELD_SKIP_FOLLOWING, False)
            field_skip_follower = self.conditions.get(FIELD_SKIP_FOLLOWER, False)
            field_min_followers = self.conditions.get(FIELD_MIN_FOLLOWERS)
            field_max_followers = self.conditions.get(FIELD_MAX_FOLLOWERS)
            field_min_followings = self.conditions.get(FIELD_MIN_FOLLOWINGS)
            field_max_followings = self.conditions.get(FIELD_MAX_FOLLOWINGS)
            field_min_potency_ratio = self.conditions.get(FIELD_MIN_POTENCY_RATIO, 0)
            field_max_potency_ratio = self.conditions.get(FIELD_MAX_POTENCY_RATIO, 999)
            field_blacklist_words = self.conditions.get(FIELD_BLACKLIST_WORDS, [])
            field_mandatory_words = self.conditions.get(FIELD_MANDATORY_WORDS, [])
            field_interact_only_private = self.conditions.get(
                FIELD_INTERACT_ONLY_PRIVATE, False
            )
            field_specific_alphabet = self.conditions.get(FIELD_SPECIFIC_ALPHABET)
            field_bio_language = self.conditions.get(FIELD_BIO_LANGUAGE)
            field_min_posts = self.conditions.get(FIELD_MIN_POSTS)

        profile_data = self.get_all_data(device)
        if self.conditions is None:
            return profile_data, False
        if profile_data.follow_button_text == FollowStatus.NONE:
            logger.info(
                "Profile was not fully loaded or the user uses a bug for having super huge profile description. SKIP."
            )
            return profile_data, self.return_check_profile(
                username, profile_data, SkipReason.NOT_LOADED
            )
        if field_skip_following or field_skip_follower:
            if field_skip_following:
                if profile_data.follow_button_text == FollowStatus.FOLLOWING:
                    logger.info(
                        f"You follow @{username}, skip.",
                        extra={"color": f"{Fore.CYAN}"},
                    )
                    return profile_data, self.return_check_profile(
                        username, profile_data, SkipReason.YOU_FOLLOW
                    )

            if field_skip_follower:
                if profile_data.follow_button_text == FollowStatus.FOLLOW_BACK:
                    logger.info(
                        f"@{username} follows you, skip.",
                        extra={"color": f"{Fore.CYAN}"},
                    )
                    return profile_data, self.return_check_profile(
                        username, profile_data, SkipReason.FOLLOW_YOU
                    )

        if field_interact_only_private:
            logger.debug("Checking if account is private...")

            if field_interact_only_private and profile_data.is_private is False:

                logger.info(
                    f"@{username} has public account, skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.IS_PRIVATE
                )

            elif field_interact_only_private and profile_data.is_private is None:
                logger.info(
                    f"Could not determine if @{username} is public or private, skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.UNKNOWN_PRIVACY
                )

        logger.debug("Checking if account is within follower/following parameters...")
        if profile_data.followers is not None and profile_data.followings is not None:
            if field_min_followers is not None and profile_data.followers < int(
                field_min_followers
            ):
                logger.info(
                    f"@{username} has less than {field_min_followers} followers, skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.LT_FOLLOWERS
                )
            if field_max_followers is not None and profile_data.followers > int(
                field_max_followers
            ):
                logger.info(
                    f"@{username} has more than {field_max_followers} followers, skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.GT_FOLLOWERS
                )
            if field_min_followings is not None and profile_data.followings < int(
                field_min_followings
            ):
                logger.info(
                    f"@{username} has less than {field_min_followings} followings, skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.LT_FOLLOWINGS
                )
            if field_max_followings is not None and profile_data.followings > int(
                field_max_followings
            ):
                logger.info(
                    f"@{username} has more than {field_max_followings} followings, skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.GT_FOLLOWINGS
                )

            if field_min_potency_ratio != 0 or field_max_potency_ratio != 999:
                if (
                    int(profile_data.followings) == 0
                    or profile_data.followers / profile_data.followings
                    < float(field_min_potency_ratio)
                    or profile_data.followers / profile_data.followings
                    > float(field_max_potency_ratio)
                ):
                    logger.info(
                        f"@{username}'s potency ratio is not between {field_min_potency_ratio} and {field_max_potency_ratio}, skip.",
                        extra={"color": f"{Fore.CYAN}"},
                    )
                    return profile_data, self.return_check_profile(
                        username, profile_data, SkipReason.POTENCY_RATIO
                    )

        else:
            logger.critical(
                "Either followers, followings, or possibly both are undefined. Cannot filter."
            )
            return profile_data, self.return_check_profile(
                username, profile_data, SkipReason.UNDEFINED_FOLLOWERS_FOLLOWING
            )

        if field_skip_business or field_skip_non_business:
            logger.debug("Checking if account is a business...")
            if field_skip_business and profile_data.has_business_category is True:
                logger.info(
                    f"@{username} has business account, skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.HAS_BUSINESS
                )
            if field_skip_non_business and profile_data.has_business_category is False:
                logger.info(
                    f"@{username} has non business account, skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.HAS_NON_BUSINESS
                )

        if field_min_posts is not None:
            if field_min_posts > profile_data.posts_count:
                logger.info(
                    f"@{username} doesn't have enough posts ({profile_data.posts_count}), skip.",
                    extra={"color": f"{Fore.CYAN}"},
                )
                return profile_data, self.return_check_profile(
                    username, profile_data, SkipReason.NOT_ENOUGH_POSTS
                )

        cleaned_biography = emoji.get_emoji_regexp().sub(
            "", profile_data.biography.replace("\n", "").lower()
        )
        if (
            len(field_blacklist_words) > 0
            or len(field_mandatory_words) > 0
            or field_specific_alphabet is not None
            or field_bio_language is not None
        ) and cleaned_biography != "":
            logger.debug("Pulling biography...")
            if len(field_blacklist_words) > 0:
                logger.debug(
                    "Checking if account has blacklisted words in biography..."
                )
                # If we found a blacklist word return False
                for w in field_blacklist_words:
                    blacklist_words = re.compile(
                        r"\b({0})\b".format(w), flags=re.IGNORECASE
                    ).search(cleaned_biography)
                    if blacklist_words is not None:
                        logger.info(
                            f"@{username} found a blacklisted word '{w}' in biography, skip.",
                            extra={"color": f"{Fore.CYAN}"},
                        )
                        return profile_data, self.return_check_profile(
                            username, profile_data, SkipReason.BLACKLISTED_WORD
                        )

            if len(field_mandatory_words) > 0:
                logger.debug("Checking if account has mandatory words in biography...")
                mandatory_words = [
                    w
                    for w in field_mandatory_words
                    if re.compile(r"\b({0})\b".format(w), flags=re.IGNORECASE).search(
                        cleaned_biography
                    )
                    is not None
                ]
                if mandatory_words == []:
                    logger.info(
                        f"@{username} mandatory words not found in biography, skip.",
                        extra={"color": f"{Fore.CYAN}"},
                    )
                    return profile_data, self.return_check_profile(
                        username, profile_data, SkipReason.MISSING_MANDATORY_WORDS
                    )

            if field_specific_alphabet is not None:
                logger.debug("Checking primary character set of account biography...")
                alphabet = self._find_alphabet(cleaned_biography)

                if alphabet not in field_specific_alphabet and alphabet != "":
                    logger.info(
                        f"@{username}'s biography alphabet is not in {', '.join(field_specific_alphabet)}. ({alphabet}), skip.",
                        extra={"color": f"{Fore.CYAN}"},
                    )
                    return profile_data, self.return_check_profile(
                        username, profile_data, SkipReason.ALPHABET_NOT_MATCH
                    )
            if field_bio_language is not None:
                logger.debug("Checking main language of account biography...")
                language = self._find_language(cleaned_biography)
                if language not in field_bio_language and language != "":
                    logger.info(
                        f"@{username}'s biography language is not in {', '.join(field_bio_language)}. ({language}), skip.",
                        extra={"color": f"{Fore.CYAN}"},
                    )
                    return profile_data, self.return_check_profile(
                        username,
                        profile_data,
                        SkipReason.BIOGRAPHY_LANGUAGE_NOT_MATCH,
                    )

        if field_specific_alphabet is not None:
            logger.debug("Checking primary character set of name...")
            if profile_data.fullname != "":
                alphabet = self._find_alphabet(profile_data.fullname)
                if alphabet not in field_specific_alphabet and alphabet != "":
                    logger.info(
                        f"@{username}'s name alphabet is not in {', '.join(field_specific_alphabet)}. ({alphabet}), skip.",
                        extra={"color": f"{Fore.CYAN}"},
                    )
                    return profile_data, self.return_check_profile(
                        username,
                        profile_data,
                        SkipReason.ALPHABET_NAME_NOT_MATCH,
                    )

        # If no filters return false, we are good to proceed
        return profile_data, self.return_check_profile(username, profile_data, None)

    def can_follow_private_or_empty(self):
        if self.conditions is None:
            return False

        field_follow_private_or_empty = self.conditions.get(
            FIELD_FOLLOW_PRIVATE_OR_EMPTY
        )
        return field_follow_private_or_empty is not None and bool(
            field_follow_private_or_empty
        )

    def can_pm_to_private_or_empty(self):
        if self.conditions is None:
            return False

        field_pm_to_private_or_empty = self.conditions.get(PM_TO_PRIVATE_OR_EMPTY)
        return field_pm_to_private_or_empty is not None and bool(
            field_pm_to_private_or_empty
        )

    def can_comment(self, current_mode):
        try:
            return (
                self.conditions.get(FIELD_COMMENT_PHOTOS, True),
                self.conditions.get(FIELD_COMMENT_VIDEOS, True),
                self.conditions.get("comment_" + current_mode.replace("-", "_"), False),
            )
        except Exception as e:
            logger.debug(
                f"filters.yml (or legacy filter.json) is not loaded! Exception: {e}"
            )
            return False, False, False

    def get_all_data(self, device):
        profile_picture = device.find(
            resourceIdMatches=ResourceID.PROFILE_HEADER_AVATAR_CONTAINER_TOP_LEFT_STUB
        )
        if not profile_picture.exists(Timeout.LONG):
            logger.warning(
                "Looks like this profile hasn't loaded yet! Wait a little bit more.."
            )
            if profile_picture.exists(Timeout.LONG):
                logger.info("Profile loaded!")
            else:
                logger.warning(
                    "Profile not fully loaded after 16s. Is your connection ok? Let's sleep for 1-2 minutes."
                )
                random_sleep(60, 120, modulable=False)
                if profile_picture.exists():
                    logger.warning(
                        "Profile won't load! Maybe you're softbanned or you've lost your connection!"
                    )
        profileView = ProfileView(device)
        profile = Profile(
            follow_button_text=self._get_follow_button_text(device, profileView),
            is_private=self._is_private_account(device, profileView),
            has_business_category=self._has_business_category(device, profileView),
            posts_count=self._get_posts_count(device, profileView),
            biography=self._get_profile_biography(device, profileView),
            fullname=self._get_fullname(device, profileView),
        )
        followers, following = self._get_followers_and_followings(device)
        profile.set_followers_and_following(followers, following)
        return profile

    @staticmethod
    def _get_followers_and_followings(device, profileView=None):
        followers = 0
        profileView = ProfileView(device) if profileView is None else profileView
        try:
            followers = profileView.getFollowersCount()
        except Exception as e:
            logger.error(f"Cannot find followers count view, default is {followers}.")
            logger.debug(f"Error: {e}")

        followings = 0
        try:
            followings = profileView.getFollowingCount()
        except Exception as e:
            logger.error(f"Cannot find followings count view, default is {followings}.")
            logger.debug(f"Error: {e}")
        if followers is not None and followings is not None:
            return followers, followings
        else:
            return 0, 1

    @staticmethod
    def _has_business_category(device, profileView=None):
        business_category_view = device.find(
            resourceId=ResourceID.PROFILE_HEADER_BUSINESS_CATEGORY,
            className=ClassName.TEXT_VIEW,
        )
        return business_category_view.exists()

    @staticmethod
    def _is_private_account(device, profileView=None):
        private = None
        profileView = ProfileView(device) if profileView is None else profileView
        try:
            private = profileView.isPrivateAccount()
        except Exception as e:
            logger.error("Cannot find whether it is private or not")
            logger.debug(f"Error: {e}")

        return private

    @staticmethod
    def _get_profile_biography(device, profileView=None):
        profileView = ProfileView(device) if profileView is None else profileView
        return profileView.getProfileBiography()

    @staticmethod
    def _find_alphabet(biography):
        a_dict = {}
        max_alph = "UNKNOWN"
        try:
            for x in range(0, len(biography)):
                if biography[x].isalpha():
                    a = unicodedata.name(biography[x]).split(" ")[0]
                    if a not in IGNORE_CHARSETS:
                        if a in a_dict:
                            a_dict[a] += 1
                        else:
                            a_dict[a] = 1
            if bool(a_dict):
                max_alph = max(a_dict, key=lambda k: a_dict[k])
        except Exception as e:
            logger.error(f"Cannot determine primary alphabet. Error: {e}")

        return max_alph

    @staticmethod
    def _find_language(biography):
        """Language detection algorithm is non-deterministic, which means that if you try to run it on a text which is either too short or too ambiguous, you might get different results everytime you run it."""
        language = ""
        results = []
        try:
            for _ in range(5):
                # we do a BO5, that would mitigate the inconsistency a little bit
                results.append(detect(biography))
            language = max(results, key=results.count)
        except Exception as e:
            logger.error(f"Cannot determine primary language. Error: {e}")
        return language

    @staticmethod
    def _get_fullname(device, profileView=None):
        profileView = ProfileView(device) if profileView is None else profileView
        fullname = ""
        try:
            fullname = profileView.getFullName()
        except Exception as e:
            logger.error("Cannot find full name.")
            logger.debug(f"Error: {e}")

        return fullname

    @staticmethod
    def _get_posts_count(device, profileView=None):
        profileView = ProfileView(device) if profileView is None else profileView
        posts_count = 0
        try:
            posts_count = profileView.getPostsCount()
        except Exception as e:
            logger.error("Cannot find posts count. Default is 0.")
            logger.debug(f"Error: {e}")

        return posts_count

    @staticmethod
    def _get_follow_button_text(device, profileView=None):
        profileView = ProfileView(device) if profileView is None else profileView
        _, text = profileView.getFollowButton()
        return text
