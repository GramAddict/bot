import json
import logging
import os
import re
import unicodedata

from colorama import Fore
from GramAddict.core.views import ProfileView

logger = logging.getLogger(__name__)

FILENAME_CONDITIONS = "filter.json"
FIELD_SKIP_BUSINESS = "skip_business"
FIELD_SKIP_NON_BUSINESS = "skip_non_business"
FIELD_MIN_FOLLOWERS = "min_followers"
FIELD_MAX_FOLLOWERS = "max_followers"
FIELD_MIN_FOLLOWINGS = "min_followings"
FIELD_MAX_FOLLOWINGS = "max_followings"
FIELD_MIN_POTENCY_RATIO = "min_potency_ratio"
FIELD_FOLLOW_PRIVATE_OR_EMPTY = "follow_private_or_empty"
FIELD_BLACKLIST_WORDS = "blacklist_words"
FIELD_MANDATORY_WORDS = "mandatory_words"
FIELD_SPESIFIC_ALPHABET = "spesific_alphabet"


class Filter:
    conditions = None

    def __init__(self):
        if os.path.exists(FILENAME_CONDITIONS):
            with open(FILENAME_CONDITIONS) as json_file:
                self.conditions = json.load(json_file)

    def check_profile(self, device, username):
        """
        This method assumes being on someone's profile already.
        """
        if self.conditions is None:
            return True

        field_skip_business = self.conditions.get(FIELD_SKIP_BUSINESS)
        field_skip_non_business = self.conditions.get(FIELD_SKIP_NON_BUSINESS)
        field_min_followers = self.conditions.get(FIELD_MIN_FOLLOWERS)
        field_max_followers = self.conditions.get(FIELD_MAX_FOLLOWERS)
        field_min_followings = self.conditions.get(FIELD_MIN_FOLLOWINGS)
        field_max_followings = self.conditions.get(FIELD_MAX_FOLLOWINGS)
        field_min_potency_ratio = self.conditions.get(FIELD_MIN_POTENCY_RATIO)
        field_blacklist_words = self.conditions.get(
            FIELD_BLACKLIST_WORDS
        )  # Array of words
        field_mandatory_words = self.conditions.get(
            FIELD_MANDATORY_WORDS
        )  # Array of words
        field_spesific_alphabet = self.conditions.get(FIELD_SPESIFIC_ALPHABET)

        if field_skip_business is not None or field_skip_non_business is not None:
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

        if (
            field_min_followers is not None
            or field_max_followers is not None
            or field_min_followings is not None
            or field_max_followings is not None
            or field_min_potency_ratio is not None
        ):
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
                if field_min_potency_ratio is not None and (
                    int(followings) == 0
                    or followers / followings < float(field_min_potency_ratio)
                ):
                    logger.info(
                        f"@{username}'s potency ratio is less than {field_min_potency_ratio}, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False
            else:
                logger.critical(
                    "Either followers, followings, or possibly both are undefined. Cannot filter."
                )
                return False

        if (
            field_blacklist_words is not None
            or field_mandatory_words is not None
            or field_spesific_alphabet is not None
        ):
            biography_text = self._get_profile_biography(device)
            # logger.info(f"@{username} Biography {biography_text}")
            # If we found a blacklist word return False
            if field_blacklist_words is not None:
                for w in field_blacklist_words:
                    if (
                        re.compile(r"\b({0})\b".format(w), flags=re.IGNORECASE).search(
                            biography_text
                        )
                        is not None
                    ):
                        logger.info(
                            f"@{username} found a blacklisted word '{w}' in biography, skip.",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        return False

            # For continue we need to find at least one of mandatory word
            if field_mandatory_words is not None:
                if [
                    w
                    for w in field_mandatory_words
                    if re.compile(r"\b({0})\b".format(w), flags=re.IGNORECASE).search(
                        biography_text
                    )
                    is not None
                ] == []:
                    logger.info(
                        f"@{username} mandatory words not found in biography, skip.",
                        extra={"color": f"{Fore.GREEN}"},
                    )
                    return False

            if field_spesific_alphabet is not None:
                if biography_text != "":
                    biography_text = biography_text.replace("\n", "")
                    alphabet = self._find_alphabeth(biography_text)

                    if alphabet != field_spesific_alphabet and alphabet != "":
                        logger.info(
                            f"@{username}'s biography alphabet is not wanted. ({alphabet})",
                            extra={"color": f"{Fore.GREEN}"},
                        )
                        return False
                else:
                    fullname = self._get_fullname(device)

                    if fullname != "":
                        alphabet = self._find_alphabeth(fullname)
                        if alphabet != field_spesific_alphabet and alphabet != "":
                            logger.info(
                                f"@{username}'s name alphabet is not wanted. ({alphabet})",
                                extra={"color": f"{Fore.GREEN}"},
                            )
                            return False

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
        except Exception:
            logger.error(f"Cannot find followers count view, default is {followers}")

        followings = 0
        try:
            followings = profileView.getFollowingCount()
        except Exception:
            logger.error(f"Cannot find followings count view, default is {followings}")

        return followers, followings

    @staticmethod
    def _has_business_category(device):
        business_category_view = device.find(
            resourceId="com.instagram.android:id/profile_header_business_category",
            className="android.widget.TextView",
        )
        return business_category_view.exists()

    @staticmethod
    def _get_profile_biography(device):
        profileView = ProfileView(device)
        return profileView.getProfileBiography()

    @staticmethod
    def _find_alphabeth(biography):
        a_dict = {}
        max_alph = ""
        for x in range(0, len(biography)):
            if biography[x].isalpha():
                a = unicodedata.name(biography[x]).split(" ")[0]
                if a in a_dict:
                    a_dict[a] += 1
                else:
                    a_dict[a] = 1
        if bool(a_dict):
            max_alph = max(a_dict, key=lambda k: a_dict[k])

        return max_alph

    @staticmethod
    def _get_fullname(device):
        profileView = ProfileView(device)
        fullname = ""
        try:
            fullname = profileView.getFullName()
        except Exception:
            logger.error("Cannot find fullname.")
        return fullname
