import json
import urllib.request

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
                print_timeless(COLOR_OKGREEN + "@" + username + " has business account, skip." + COLOR_ENDC)
                return False
            if field_skip_non_business and has_business_category is False:
                print_timeless(COLOR_OKGREEN + "@" + username + " has non business account, skip." + COLOR_ENDC)
                return False

        if field_min_followers is not None or field_max_followers is not None \
                or field_min_followings is not None or field_max_followings is not None \
                or field_min_potency_ratio is not None:
            followers, followings = self._get_followers_and_followings(username)
            if field_min_followers is not None and followers < int(field_min_followers):
                print_timeless(COLOR_OKGREEN + "@" + username + " has less than " + str(field_min_followers) +
                               " followers, skip." + COLOR_ENDC)
                return False
            if field_max_followers is not None and followers > int(field_max_followers):
                print_timeless(COLOR_OKGREEN + "@" + username + " has more than " + str(field_max_followers) +
                               " followers, skip." + COLOR_ENDC)
                return False
            if field_min_followings is not None and followings < int(field_min_followings):
                print_timeless(COLOR_OKGREEN + "@" + username + " has less than " + str(field_min_followings) +
                               " followings, skip." + COLOR_ENDC)
                return False
            if field_max_followings is not None and followings > int(field_max_followings):
                print_timeless(COLOR_OKGREEN + "@" + username + " has more than " + str(field_max_followings) +
                               " followings, skip." + COLOR_ENDC)
                return False
            if field_min_potency_ratio is not None \
                    and (int(followings) == 0 or followers / followings < float(field_min_potency_ratio)):
                print_timeless(COLOR_OKGREEN + "@" + username + "'s potency ratio is less than " +
                               str(field_min_potency_ratio) + ", skip." + COLOR_ENDC)
                return False
        return True

    def can_follow_private_or_empty(self):
        if self.conditions is None:
            return False

        field_follow_private_or_empty = self.conditions.get(FIELD_FOLLOW_PRIVATE_OR_EMPTY)
        return field_follow_private_or_empty is not None and bool(field_follow_private_or_empty)

    @staticmethod
    def _get_followers_and_followings(username):
        url = 'https://www.instagram.com/' + username
        with urllib.request.urlopen(url) as response:
            html = str(response.read(), "utf-8")

            followers_search_result = re.search('"edge_followed_by":{"count":([0-9]+)}', html)
            if followers_search_result:
                followers = int(followers_search_result.group(1))
            else:
                print_timeless(COLOR_FAIL + "Cannot get followers count from the html page" + COLOR_ENDC)
                followers = 0

            followings_search_result = re.search('"edge_follow":{"count":([0-9]+)}', html)
            if followings_search_result:
                followings = int(followings_search_result.group(1))
            else:
                print_timeless(COLOR_FAIL + "Cannot get followings count from the html page" + COLOR_ENDC)
                followings = 0
        return followers, followings

    @staticmethod
    def _has_business_category(device):
        business_category_view = device(resourceId='com.instagram.android:id/profile_header_business_category',
                                        className='android.widget.TextView')
        return business_category_view.exists
