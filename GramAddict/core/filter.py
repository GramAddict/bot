import json
import logging
import os

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
FIELD_MAX_POTENCY_RATIO = "max_potency_ratio"
FIELD_FOLLOW_PRIVATE_OR_EMPTY = "follow_private_or_empty"
FIELD_FOLLOW_ONLY_PRIVATE = "follow_only_private"


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
        field_max_potency_ratio = self.conditions.get(FIELD_MAX_POTENCY_RATIO)

        field_follow_only_private = self.conditions.get(FIELD_FOLLOW_ONLY_PRIVATE)

        if field_follow_only_private is not None:
            is_private = self._is_private_account(device)

            if field_follow_only_private and is_private is False:

                logger.info(
                    f"@{username} has public account, skip.",
                    extra={"color": f"{Fore.GREEN}"},
                )
                return False

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
            or field_max_potency_ratio is not None
        ):
            followers, followings = self._get_followers_and_followings(device)
            if followers != None and followings != None:
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

                if (
                    field_min_potency_ratio is not None
                    or field_max_potency_ratio is not None
                ):
                    if field_min_potency_ratio is None:
                        field_min_potency_ratio = 0
                    if field_max_potency_ratio is None:
                        field_max_potency_ratio = 999
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
    def _is_private_account(device):
        private = False
        profileView = ProfileView(device)
        try:
            private = profileView.isPrivateAccount()
        except Exception:
            logger.error("Cannot find whether it is private or not")

        return private
