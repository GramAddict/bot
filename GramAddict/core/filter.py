import json
import logging
import os
import re
import unicodedata

from colorama import Fore
from GramAddict.core.views import ProfileView, FollowStatus, OpenedPostView
from GramAddict.core.resources import ResourceID, ClassName

logger = logging.getLogger(__name__)

FILENAME_CONDITIONS = "filter.json"
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
FIELD_INTERACT_ONLY_PRIVATE = "interact_only_private"
FIELD_BLACKLIST_WORDS = "blacklist_words"
FIELD_MANDATORY_WORDS = "mandatory_words"
FIELD_SPECIFIC_ALPHABET = "specific_alphabet"
FIELD_MIN_POSTS = "min_posts"

IGNORE_CHARSETS = ["MATHEMATICAL"]


class Filter:
    conditions = None

    def __init__(self):
        if os.path.exists(FILENAME_CONDITIONS):
            with open(FILENAME_CONDITIONS) as json_file:
                self.conditions = json.load(json_file)

    def check_profile_from_list(self, device, item, username):
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

    def check_profile(self, device, username):
        """
        This method assumes being on someone's profile already.
        """
        if self.conditions is None:
            return True

        field_skip_business = self.conditions.get(FIELD_SKIP_BUSINESS, False)
        field_skip_non_business = self.conditions.get(FIELD_SKIP_NON_BUSINESS, False)
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
        field_min_posts = self.conditions.get(FIELD_MIN_POSTS)

        if field_skip_following or field_skip_follower:
            profileView = ProfileView(device)
            button, text = profileView.getFollowButton()

            if field_skip_following:
                if text == FollowStatus.FOLLOWING:
                    logger.info(
                        f"You follow @{username}, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False

            if field_skip_follower:
                if text == FollowStatus.FOLLOW_BACK:
                    logger.info(
                        f"@{username} follows you, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False

        if field_interact_only_private:
            logger.debug("Checking if account is private...")
            is_private = self._is_private_account(device)

            if field_interact_only_private and is_private is False:

                logger.info(
                    f"@{username} has public account, skip.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return False

            elif field_interact_only_private and is_private is None:
                logger.info(
                    f"Could not determine if @{username} is public or private, skip.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return False

        if (
            field_min_followers is not None
            or field_max_followers is not None
            or field_min_followings is not None
            or field_max_followings is not None
            or field_min_potency_ratio is not None
            or field_max_potency_ratio is not None
        ):
            logger.debug(
                "Checking if account is within follower/following parameters..."
            )
            followers, followings = self._get_followers_and_followings(device)
            if followers is not None and followings is not None:
                if field_min_followers is not None and followers < int(
                    field_min_followers
                ):
                    logger.info(
                        f"@{username} has less than {field_min_followers} followers, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False
                if field_max_followers is not None and followers > int(
                    field_max_followers
                ):
                    logger.info(
                        f"@{username} has has more than {field_max_followers} followers, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False
                if field_min_followings is not None and followings < int(
                    field_min_followings
                ):
                    logger.info(
                        f"@{username} has less than {field_min_followings} followings, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False
                if field_max_followings is not None and followings > int(
                    field_max_followings
                ):
                    logger.info(
                        f"@{username} has more than {field_max_followings} followings, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False

                if field_min_potency_ratio != 0 or field_max_potency_ratio != 999:
                    if (
                        int(followings) == 0
                        or followers / followings < float(field_min_potency_ratio)
                        or followers / followings > float(field_max_potency_ratio)
                    ):
                        logger.info(
                            f"@{username}'s potency ratio is not between {field_min_potency_ratio} and {field_max_potency_ratio}, skip.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        return False

            else:
                logger.critical(
                    "Either followers, followings, or possibly both are undefined. Cannot filter."
                )
                return False

        if field_skip_business or field_skip_non_business:
            logger.debug("Checking if account is a business...")
            has_business_category = self._has_business_category(device)
            if field_skip_business and has_business_category is True:
                logger.info(
                    f"@{username} has business account, skip.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return False
            if field_skip_non_business and has_business_category is False:
                logger.info(
                    f"@{username} has non business account, skip.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return False

        if field_min_posts is not None:
            posts_count = self._get_posts_count(device)
            if field_min_posts > posts_count:
                logger.info(
                    f"@{username} doesn't have enough posts ({posts_count}), skip.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return False

        if (
            len(field_blacklist_words) > 0
            or len(field_mandatory_words) > 0
            or field_specific_alphabet is not None
        ):
            logger.debug("Pulling biography...")
            biography = self._get_profile_biography(device)

            if len(field_blacklist_words) > 0:
                logger.debug(
                    "Checking if account has blacklisted words in biography..."
                )
                # If we found a blacklist word return False
                for w in field_blacklist_words:
                    blacklist_words = re.compile(
                        r"\b({0})\b".format(w), flags=re.IGNORECASE
                    ).search(biography)
                    if blacklist_words is not None:
                        logger.info(
                            f"@{username} found a blacklisted word '{w}' in biography, skip.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        return False

            if len(field_mandatory_words) > 0:
                logger.debug("Checking if account has mandatory words in biography...")
                mandatory_words = [
                    w
                    for w in field_mandatory_words
                    if re.compile(r"\b({0})\b".format(w), flags=re.IGNORECASE).search(
                        biography
                    )
                    is not None
                ]
                if mandatory_words == []:
                    logger.info(
                        f"@{username} mandatory words not found in biography, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False

            if field_specific_alphabet is not None:
                if biography != "":
                    logger.debug(
                        "Checking primary character set of account biography..."
                    )
                    biography = biography.replace("\n", "")
                    alphabet = self._find_alphabet(biography, field_specific_alphabet)

                    if alphabet != field_specific_alphabet and alphabet != "":
                        logger.info(
                            f"@{username}'s biography alphabet is not {field_specific_alphabet}. ({alphabet}), skip.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        return False
                else:
                    logger.debug("Checking primary character set of name...")
                    fullname = self._get_fullname(device)

                    if fullname != "":
                        alphabet = self._find_alphabet(
                            fullname, field_specific_alphabet
                        )
                        if alphabet != field_specific_alphabet and alphabet != "":
                            logger.info(
                                f"@{username}'s name alphabet is not {field_specific_alphabet}. ({alphabet}), skip.",
                                extra={"color": f"{Fore.GREEN}"},
                            )
                            return False

        # If no filters return false, we are good to proceed
        return True

    def can_follow_private_or_empty(self):
        if self.conditions is None:
            return False

        field_follow_private_or_empty = self.conditions.get(
            FIELD_FOLLOW_PRIVATE_OR_EMPTY
        )
        return field_follow_private_or_empty is not None and bool(
            field_follow_private_or_empty
        )

    @staticmethod
    def _get_followers_and_followings(device):
        followers = 0
        profileView = ProfileView(device)
        try:
            followers = profileView.getFollowersCount()
        except Exception as e:
            logger.error(f"Cannot find followers count view, default is {followers}")
            logger.debug(f"Error: {e}")

        followings = 0
        try:
            followings = profileView.getFollowingCount()
        except Exception as e:
            logger.error(f"Cannot find followings count view, default is {followings}")
            logger.debug(f"Error: {e}")

        return followers, followings

    @staticmethod
    def _has_business_category(device):
        business_category_view = device.find(
            resourceId=ResourceID.PROFILE_HEADER_BUSINESS_CATEGORY,
            className=ClassName.TEXT_VIEW,
        )
        return business_category_view.exists(True)

    @staticmethod
    def _is_private_account(device):
        private = None
        profileView = ProfileView(device)
        try:
            private = profileView.isPrivateAccount()
        except Exception as e:
            logger.error("Cannot find whether it is private or not")
            logger.debug(f"Error: {e}")

        return private

    @staticmethod
    def _get_profile_biography(device):
        profileView = ProfileView(device)
        return profileView.getProfileBiography()

    @staticmethod
    def _find_alphabet(biography, alphabet):
        a_dict = {}
        max_alph = alphabet
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
            logger.error(f"Cannot determine primary alphabet. Default is {max_alph}")
            logger.debug(f"Error: {e}")

        return max_alph

    @staticmethod
    def _get_fullname(device):
        profileView = ProfileView(device)
        fullname = ""
        try:
            fullname = profileView.getFullName()
        except Exception as e:
            logger.error("Cannot find full name.")
            logger.debug(f"Error: {e}")

        return fullname

    @staticmethod
    def _get_posts_count(device):
        profileView = ProfileView(device)
        posts_count = 0
        try:
            posts_count = profileView.getPostsCount()
        except Exception as e:
            logger.error("Cannot find posts count. Default is 0.")
            logger.debug(f"Error: {e}")

        return posts_count
