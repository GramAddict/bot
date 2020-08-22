import json

from src.counters_parser import parse
from src.globals import UI_TIMEOUT
from src.utils import *

FILENAME_CONDITIONS = "filter.json"
FIELD_SKIP_BUSINESS = "skip_business"
FIELD_SKIP_NON_BUSINESS = "skip_non_business"
FIELD_MIN_FOLLOWERS = "min_followers"
FIELD_MAX_FOLLOWERS = "max_followers"
FIELD_MIN_FOLLOWINGS = "min_followings"
FIELD_MAX_FOLLOWINGS = "max_followings"
FIELD_MIN_POTENCY_RATIO = "min_potency_ratio"
FIELD_FOLLOW_PRIVATE_OR_EMPTY = "follow_private_or_empty"


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

        if field_skip_business is not None or field_skip_non_business is not None:
            has_business_category = self._has_business_category(device)
            if field_skip_business and has_business_category is True:
                print(COLOR_OKGREEN + "@" + username + " has business account, skip." + COLOR_ENDC)
                return False
            if field_skip_non_business and has_business_category is False:
                print(COLOR_OKGREEN + "@" + username + " has non business account, skip." + COLOR_ENDC)
                return False

        if field_min_followers is not None or field_max_followers is not None \
                or field_min_followings is not None or field_max_followings is not None \
                or field_min_potency_ratio is not None:
            followers, followings = self._get_followers_and_followings(device)
            if field_min_followers is not None and followers < int(field_min_followers):
                print(COLOR_OKGREEN + "@" + username + " has less than " + str(field_min_followers) +
                      " followers, skip." + COLOR_ENDC)
                return False
            if field_max_followers is not None and followers > int(field_max_followers):
                print(COLOR_OKGREEN + "@" + username + " has more than " + str(field_max_followers) +
                      " followers, skip." + COLOR_ENDC)
                return False
            if field_min_followings is not None and followings < int(field_min_followings):
                print(COLOR_OKGREEN + "@" + username + " has less than " + str(field_min_followings) +
                      " followings, skip." + COLOR_ENDC)
                return False
            if field_max_followings is not None and followings > int(field_max_followings):
                print(COLOR_OKGREEN + "@" + username + " has more than " + str(field_max_followings) +
                      " followings, skip." + COLOR_ENDC)
                return False
            if field_min_potency_ratio is not None \
                    and (int(followings) == 0 or followers / followings < float(field_min_potency_ratio)):
                print(COLOR_OKGREEN + "@" + username + "'s potency ratio is less than " +
                      str(field_min_potency_ratio) + ", skip." + COLOR_ENDC)
                return False
        return True

    def can_follow_private_or_empty(self):
        if self.conditions is None:
            return False

        field_follow_private_or_empty = self.conditions.get(FIELD_FOLLOW_PRIVATE_OR_EMPTY)
        return field_follow_private_or_empty is not None and bool(field_follow_private_or_empty)

    @staticmethod
    def _get_followers_and_followings(device):
        followers = 0
        followers_text_view = device(resourceId='com.instagram.android:id/row_profile_header_textview_followers_count',
                                     className='android.widget.TextView')
        if followers_text_view.exists(timeout=UI_TIMEOUT):
            followers_text = followers_text_view.info['text']
            if followers_text:
                followers = parse(device, followers_text)
            else:
                print_timeless(COLOR_FAIL + "Cannot get followers count text, default is " + str(followers) +
                               COLOR_ENDC)
        else:
            print_timeless(COLOR_FAIL + "Cannot find followers count view, default is " + str(followers) + COLOR_ENDC)

        followings = 0
        followings_text_view = device(resourceId='com.instagram.android:id/row_profile_header_textview_following_count',
                                      className='android.widget.TextView')
        if followings_text_view.exists(timeout=UI_TIMEOUT):
            followings_text = followings_text_view.info['text']
            if followings_text:
                followings = parse(device, followings_text)
            else:
                print_timeless(COLOR_FAIL + "Cannot get followings count text, default is " + str(followings) +
                               COLOR_ENDC)
        else:
            print_timeless(COLOR_FAIL + "Cannot find followings count view, default is " + str(followings) + COLOR_ENDC)

        return followers, followings

    @staticmethod
    def _has_business_category(device):
        business_category_view = device(resourceId='com.instagram.android:id/profile_header_business_category',
                                        className='android.widget.TextView')
        return business_category_view.exists(timeout=UI_TIMEOUT)
