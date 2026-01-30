import datetime
import logging
import re
import platform
from collections import deque
from enum import Enum, auto
from random import choice, randint, uniform
from time import sleep
from typing import Optional, Tuple

import emoji
from colorama import Fore, Style

from GramAddict.core.device_facade import (
    DeviceFacade,
    Direction,
    Location,
    Mode,
    SleepTime,
    Timeout,
)
from GramAddict.core.resources import ClassName
from GramAddict.core.resources import ResourceID as resources
from GramAddict.core.resources import TabBarText
from GramAddict.core.utils import (
    ActionBlockedError,
    Square,
    get_value,
    random_choice,
    random_sleep,
    save_crash,
    stop_bot,
)

logger = logging.getLogger(__name__)
_RECENT_GRID_TILES = deque(maxlen=30)


def _select_grid_recycler_view(device: DeviceFacade):
    """Pick the RecyclerView that actually contains the search grid tiles."""
    selector = device.find(
        resourceIdMatches=ResourceID.RECYCLER_VIEW,
        className=ClassName.RECYCLER_VIEW,
    )
    if not selector.exists(Timeout.LONG):
        logger.debug("RecyclerView doesn't exists.")
        return selector
    try:
        count = selector.count_items()
    except Exception:
        count = 1
    if count <= 1:
        return device.find(
            resourceIdMatches=ResourceID.RECYCLER_VIEW,
            className=ClassName.RECYCLER_VIEW,
            index=0,
        )
    best = None
    best_idx = None
    best_area = -1
    for idx in range(count):
        rv = device.find(
            resourceIdMatches=ResourceID.RECYCLER_VIEW,
            className=ClassName.RECYCLER_VIEW,
            index=idx,
        )
        if not rv.exists(Timeout.TINY):
            continue
        has_grid_tile = False
        try:
            has_grid_tile = rv.child(
                resourceId=ResourceID.GRID_CARD_LAYOUT_CONTAINER
            ).exists(Timeout.TINY)
        except Exception:
            has_grid_tile = False
        if not has_grid_tile:
            try:
                has_grid_tile = rv.child(
                    resourceId=ResourceID.PLAY_COUNT_CONTAINER
                ).exists(Timeout.TINY)
            except Exception:
                has_grid_tile = False
        if not has_grid_tile:
            continue
        try:
            bounds = rv.get_bounds()
            area = (bounds["right"] - bounds["left"]) * (
                bounds["bottom"] - bounds["top"]
            )
        except Exception:
            area = 0
        if area > best_area:
            best_area = area
            best = rv
            best_idx = idx
    if best is not None:
        logger.debug(
            f"RecyclerView candidates: {count}; picked index {best_idx}."
        )
        return best
    return device.find(
        resourceIdMatches=ResourceID.RECYCLER_VIEW,
        className=ClassName.RECYCLER_VIEW,
        index=0,
    )


def _collect_grid_tiles(
    device: DeviceFacade,
    recycler: Optional[DeviceFacade.View],
    allow_reels: bool = False,
):
    """Collect visible grid tiles without iterating the recycler view directly."""
    tiles = []
    seen_keys = set()
    bounds = None
    if recycler is not None:
        try:
            if recycler.exists(Timeout.TINY):
                bounds = recycler.get_bounds()
        except Exception:
            bounds = None

    def _within_bounds(b: dict) -> bool:
        if not bounds:
            return True
        cx = (b["left"] + b["right"]) / 2
        cy = (b["top"] + b["bottom"]) / 2
        return (
            bounds["left"] <= cx <= bounds["right"]
            and bounds["top"] <= cy <= bounds["bottom"]
        )

    def _add_tile(tile, key_prefix: str):
        try:
            if not tile.exists(Timeout.TINY):
                return
            tile_bounds = tile.get_bounds()
        except Exception:
            return
        if not _within_bounds(tile_bounds):
            return
        key = f"{key_prefix}:{tile_bounds.get('left')}:{tile_bounds.get('top')}"
        if key in seen_keys:
            return
        seen_keys.add(key)
        tiles.append(tile)

    # Regular grid tiles
    tile_selector = device.find(resourceId=ResourceID.GRID_CARD_LAYOUT_CONTAINER)
    try:
        tile_count = tile_selector.count_items()
    except Exception:
        tile_count = 0
    for idx in range(min(tile_count, 30)):
        tile = device.find(resourceId=ResourceID.GRID_CARD_LAYOUT_CONTAINER, index=idx)
        _add_tile(tile, "grid")

    # Reel tiles (play count badge)
    if allow_reels:
        reel_selector = device.find(resourceId=ResourceID.PLAY_COUNT_CONTAINER)
        try:
            reel_count = reel_selector.count_items()
        except Exception:
            reel_count = 0
        for idx in range(min(reel_count, 15)):
            reel = device.find(
                resourceId=ResourceID.PLAY_COUNT_CONTAINER, index=idx
            )
            try:
                tile = reel.up()
            except Exception:
                tile = None
            if tile is None:
                continue
            _add_tile(tile, "reel")

    # Fallback: if nothing collected, try to iterate the recycler directly (best effort).
    if not tiles and recycler is not None:
        try:
            for idx, tile in enumerate(recycler):
                if idx > 15:
                    break
                tiles.append(tile)
        except Exception:
            pass
    return tiles


def _search_ui_visible(device: DeviceFacade) -> bool:
    match_ids = case_insensitive_re(
        f"{ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT}|"
        f"{ResourceID.ROW_SEARCH_EDIT_TEXT}|"
        f"{ResourceID.SEARCH_TAB_BAR_LAYOUT}"
    )
    try:
        return device.find(resourceIdMatches=match_ids).exists(Timeout.TINY)
    except Exception:
        return False


def _fast_open_random_grid_click(
    device: DeviceFacade,
    recycler: Optional[DeviceFacade.View],
    attempts: int = 3,
) -> bool:
    if recycler is None or not recycler.exists(Timeout.TINY):
        return False
    try:
        bounds = recycler.get_bounds()
    except Exception:
        return False
    width = bounds["right"] - bounds["left"]
    height = bounds["bottom"] - bounds["top"]
    if width <= 0 or height <= 0:
        return False
    col_width = width / 3
    min_y = bounds["top"] + height * 0.08
    max_y = bounds["bottom"] - height * 0.05
    for _ in range(max(attempts, 1)):
        col = randint(0, 2)
        x = int(bounds["left"] + col_width * (col + uniform(0.2, 0.8)))
        y = int(uniform(min_y, max_y))
        try:
            logger.debug(
                f"Fast grid click at ({x},{y}). Bounds: ({bounds['left']}-{bounds['right']},{bounds['top']}-{bounds['bottom']})"
            )
            device.deviceV2.click(x, y)
            random_sleep(0.6, 1.2, modulable=False)
        except Exception:
            continue
        if not _search_ui_visible(device):
            return True
    return False


def _grid_tile_desc(tile, image) -> str:
    """Best-effort content description from a grid tile."""
    for getter in (
        getattr(tile, "get_desc", None),
        getattr(image, "get_desc", None),
        getattr(tile, "get_text", None),
        getattr(image, "get_text", None),
    ):
        if getter is None:
            continue
        try:
            desc = getter()
        except Exception:
            continue
        if desc:
            return str(desc).strip()
    return ""


def _parse_username_from_tile_desc(desc: str) -> Optional[str]:
    if not desc:
        return None
    # Common accessibility strings: "Photo by <user>", "Reel by <user>", etc.
    match = re.search(
        r"(?:Photo|Video|Reel|Carousel|Post|Clip|IGTV)\s+by\s+([^\n\.]+)",
        desc,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r"\bby\s+([^\n\.]+)", desc, re.IGNORECASE)
    if not match:
        return None
    username = match.group(1).strip()
    username = re.split(
        r"\s+on\s+|[·•|]|\s+at\s+row\s+",
        username,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    username = username.strip().lstrip("@").strip(" .")
    return username or None


def _grid_tile_signature(
    username: Optional[str],
    desc: str,
    tile,
    image,
    idx: int,
) -> str:
    if username:
        return f"user:{username.casefold()}"
    if desc:
        return f"desc:{desc}"
    try:
        bounds = image.get_bounds() if image is not None else tile.get_bounds()
        return (
            f"bounds:{bounds.get('left', 0)}:{bounds.get('top', 0)}:"
            f"{bounds.get('right', 0)}:{bounds.get('bottom', 0)}"
        )
    except Exception:
        return f"idx:{idx}"


def load_config(config):
    global args
    global configs
    global ResourceID
    args = config.args
    configs = config
    ResourceID = resources(config.args.app_id)


def case_insensitive_re(str_list):
    strings = str_list if isinstance(str_list, str) else "|".join(str_list)
    return f"(?i)({strings})"


def _reel_like_use_double_tap(double_tap_pct: int) -> bool:
    if not double_tap_pct:
        return False
    return randint(1, 100) <= double_tap_pct


def _double_tap_reel_media(device: DeviceFacade) -> bool:
    # Prefer reel media/container views for double-tap likes
    selectors = [
        {"resourceIdMatches": case_insensitive_re(ResourceID.REEL_VIEWER_MEDIA_CONTAINER)},
        {"resourceId": ResourceID.REEL_VIEWER_MEDIA_CONTAINER},
        {"resourceId": ResourceID.CLIPS_VIDEO_CONTAINER},
        {"resourceId": ResourceID.CLIPS_VIEWER_CONTAINER},
        {"resourceId": ResourceID.CLIPS_VIEWER_VIEW_PAGER},
        {"resourceId": ResourceID.CLIPS_MEDIA_COMPONENT},
        {"resourceId": ResourceID.CLIPS_ITEM_OVERLAY_COMPONENT},
        {"resourceIdMatches": case_insensitive_re(ResourceID.CLIPS_LINEAR_LAYOUT_CONTAINER)},
        {"resourceId": ResourceID.CLIPS_ROOT_LAYOUT},
        {"resourceId": ResourceID.CLIPS_GESTURE_MANAGER},
        {"resourceId": ResourceID.CLIPS_SWIPE_REFRESH_CONTAINER},
    ]
    for sel in selectors:
        try:
            view = device.find(**sel)
            if view.exists(Timeout.SHORT):
                view.double_click()
                return True
        except Exception:
            continue
    return False


def _is_reel_liked(device: DeviceFacade) -> Optional[bool]:
    like_btn = device.find(resourceIdMatches=case_insensitive_re(ResourceID.LIKE_BUTTON))
    if not like_btn.exists():
        like_btn = device.find(descriptionMatches=case_insensitive_re("like"))
    if like_btn.exists(Timeout.SHORT):
        return like_btn.get_selected()
    return None


def _click_reel_like_button(device: DeviceFacade) -> Optional[bool]:
    like_btn = device.find(resourceIdMatches=case_insensitive_re(ResourceID.LIKE_BUTTON))
    if not like_btn.exists():
        like_btn = device.find(descriptionMatches=case_insensitive_re("like"))
    if not like_btn.exists(Timeout.SHORT):
        return None
    like_btn.click()
    UniversalActions.detect_block(device)
    random_sleep(inf=0.3, sup=0.7, modulable=False)
    return _is_reel_liked(device)

class TabBarTabs(Enum):
    HOME = auto()
    SEARCH = auto()
    REELS = auto()
    ORDERS = auto()
    ACTIVITY = auto()
    PROFILE = auto()


class SearchTabs(Enum):
    TOP = auto()
    ACCOUNTS = auto()
    TAGS = auto()
    PLACES = auto()


class FollowStatus(Enum):
    FOLLOW = auto()
    FOLLOWING = auto()
    FOLLOW_BACK = auto()
    REQUESTED = auto()
    NONE = auto()


class SwipeTo(Enum):
    HALF_PHOTO = auto()
    NEXT_POST = auto()


class LikeMode(Enum):
    SINGLE_CLICK = auto()
    DOUBLE_CLICK = auto()


class MediaType(Enum):
    PHOTO = auto()
    VIDEO = auto()
    REEL = auto()
    IGTV = auto()
    CAROUSEL = auto()
    UNKNOWN = auto()


class Owner(Enum):
    OPEN = auto()
    GET_NAME = auto()
    GET_POSITION = auto()


class TabBarView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getTabBar(self):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.TAB_BAR),
            className=ClassName.LINEAR_LAYOUT,
        )

    def navigateToHome(self):
        self._navigateTo(TabBarTabs.HOME)
        return HomeView(self.device)

    def navigateToSearch(self):
        self._navigateTo(TabBarTabs.SEARCH)
        return SearchView(self.device)

    def navigateToReels(self):
        self._navigateTo(TabBarTabs.REELS)

    def navigateToOrders(self):
        self._navigateTo(TabBarTabs.ORDERS)

    def navigateToActivity(self):
        self._navigateTo(TabBarTabs.ACTIVITY)

    def navigateToProfile(self):
        self._navigateTo(TabBarTabs.PROFILE)
        return ProfileView(self.device, is_own_profile=True)

    def _get_new_profile_position(self) -> Optional[DeviceFacade.View]:
        buttons = self.device.find(className=ResourceID.BUTTON)
        for button in buttons:
            if button.get_desc() == "Profile":
                return button
        return None

    def _navigateTo(self, tab: TabBarTabs):
        tab_name = tab.name
        logger.debug(f"Navigate to {tab_name}")
        button = None
        UniversalActions.close_keyboard(self.device)
        if tab == TabBarTabs.HOME:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.HOME_CONTENT_DESC),
            )
            if not button.exists():
                button = self.device.find(resourceId=ResourceID.FEED_TAB)

        elif tab == TabBarTabs.SEARCH:
            # If we're already on a search results screen (no tab bar), avoid navigating away.
            try:
                if self.device.find(
                    resourceIdMatches=case_insensitive_re(
                        f"{ResourceID.SEARCH_TAB_BAR_LAYOUT}|"
                        f"{ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT}|"
                        f"{ResourceID.ROW_SEARCH_EDIT_TEXT}"
                    )
                ).exists(Timeout.TINY):
                    logger.debug("Search UI detected; already in search context.")
                    return
            except Exception:
                pass
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.SEARCH_CONTENT_DESC),
            )

            if not button.exists():
                # Some accounts display the search btn only in Home -> action bar
                logger.debug("Didn't find search in the tab bar, try resource id...")
                button = self.device.find(resourceId=ResourceID.SEARCH_TAB)
                if not button.exists():
                    logger.debug("Still no search tab, try Home action bar fallback.")
                    home_view = self.navigateToHome()
                    home_view.navigateToSearch()
                    return
        elif tab == TabBarTabs.REELS:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.REELS_CONTENT_DESC),
            )

        elif tab == TabBarTabs.ORDERS:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.ORDERS_CONTENT_DESC),
            )

        elif tab == TabBarTabs.ACTIVITY:
            # IG 410 home has the heart/notifications as a top action-bar button
            button = self.device.find(resourceId=ResourceID.ACTION_BAR_NOTIFICATION)
            if not button.exists():
                # Ensure we are on Home so the action bar is visible
                home_tab = self.device.find(resourceId=ResourceID.FEED_TAB)
                if home_tab.exists():
                    home_tab.click(sleep=SleepTime.SHORT)
                    random_sleep(0.2, 0.6, modulable=False)
                    button = self.device.find(resourceId=ResourceID.ACTION_BAR_NOTIFICATION)
            if not button.exists():
                button = self.device.find(
                    resourceIdMatches=ResourceID.TAB_BAR_ACTIVITY,
                )
            if not button.exists():
                button = self.device.find(
                    classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                    descriptionMatches=case_insensitive_re(
                        TabBarText.ACTIVITY_CONTENT_DESC
                    ),
                )

        elif tab == TabBarTabs.PROFILE:
            button = self.device.find(
                classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
                descriptionMatches=case_insensitive_re(TabBarText.PROFILE_CONTENT_DESC),
            )
            if not button.exists():
                button = self._get_new_profile_position()

        # If still not found, try to restore tab bar by pressing back once
        if (button is None or not button.exists(Timeout.SHORT)) and not self.device.find(
            resourceIdMatches=ResourceID.TAB_BAR
        ).exists(Timeout.SHORT):
            self.device.back()
            random_sleep(0.3, 0.8, modulable=False)
            if tab == TabBarTabs.SEARCH:
                button = self.device.find(resourceId=ResourceID.SEARCH_TAB)
            elif tab == TabBarTabs.HOME:
                button = self.device.find(resourceId=ResourceID.FEED_TAB)

        if button is not None and button.exists(Timeout.MEDIUM):
            # Default to a double tap to refresh tab content; single-tap for tabs where a refresh clears state (search) or triggers extra UI (profile/activity).
            button.click(sleep=SleepTime.SHORT)
            if tab == TabBarTabs.HOME:
                try:
                    refresh_pct = get_value(
                        getattr(args, "home_tab_refresh_percentage", 0), None, 0
                    )
                except Exception:
                    refresh_pct = 0
                if refresh_pct and random_choice(int(refresh_pct)):
                    button.click(sleep=SleepTime.SHORT)
            elif tab not in (TabBarTabs.PROFILE, TabBarTabs.ACTIVITY, TabBarTabs.SEARCH):
                button.click(sleep=SleepTime.SHORT)
            return

        logger.error(f"Didn't find tab {tab_name} in the tab bar...")


class ActionBarView:
    def __init__(self, device: DeviceFacade):
        self.device = device
        self.action_bar = self._getActionBar()

    def _getActionBar(self):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.ACTION_BAR_CONTAINER),
            className=ClassName.FRAME_LAYOUT,
        )


class HomeView(ActionBarView):
    def __init__(self, device: DeviceFacade):
        super().__init__(device)
        self.device = device

    def navigateToSearch(self):
        logger.debug("Navigate to Search")
        search_btn = self.action_bar.child(
            descriptionMatches=case_insensitive_re(TabBarText.SEARCH_CONTENT_DESC)
        )
        if search_btn.exists():
            search_btn.click()
            self._maybe_refresh_search()
            return
        # Fallback to search tab button
        tab_button = self.device.find(resourceId=ResourceID.SEARCH_TAB)
        if tab_button.exists(Timeout.SHORT):
            tab_button.click()
            self._maybe_refresh_search()
        else:
            logger.error("Search button not found in action bar or tab bar.")

        return SearchView(self.device)

    def _maybe_refresh_search(self):
        from random import randint

        # 20-30% chance to do a light pull-to-refresh in search for human-like behavior
        if randint(1, 100) <= randint(20, 30):
            logger.debug("Random search refresh (human-like).")
            UniversalActions(self.device)._swipe_points(
                direction=Direction.DOWN, start_point_y=350, delta_y=350
            )
            random_sleep(0.6, 1.2, modulable=False)


class HashTagView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getRecyclerView(self):
        obj = _select_grid_recycler_view(self.device)
        if obj.exists(Timeout.LONG):
            logger.debug("RecyclerView exists.")
        return obj

    def _getFistImageView(
        self,
        recycler,
        storage=None,
        current_job: Optional[str] = None,
        allow_recent: bool = False,
        allow_reels: bool = False,
        open_any: bool = False,
    ):
        """
        Prefer the first non-reel tile to avoid landing in the reels viewer.
        We detect reels via the play-count badge used on search reels results
        (preview_clip_play_count) or a content description containing 'reel'.
        """
        candidates = []
        reel_candidates = []
        recent_candidates = []
        recent_reel_candidates = []
        skipped_interacted = 0
        seen = set()

        def _tile_looks_like_reel(tile, click_target, desc: str) -> bool:
            for candidate in (tile, click_target):
                if candidate is None:
                    continue
                try:
                    reel_badge = candidate.child(
                        resourceId=ResourceID.SEARCH_REEL_INDICATOR
                    )
                    if reel_badge.exists(Timeout.TINY):
                        return True
                    if candidate.child(
                        resourceId=ResourceID.PLAY_COUNT_CONTAINER
                    ).exists(Timeout.TINY):
                        return True
                    if candidate.child(
                        resourceId=ResourceID.PLAY_COUNT_LOGO
                    ).exists(Timeout.TINY):
                        return True
                except Exception:
                    continue
            return bool(desc and re.search(r"\breel\b", desc, re.IGNORECASE))

        def _consider_tile(tile, click_target, idx, is_reel: Optional[bool] = None):
            nonlocal skipped_interacted
            if click_target is None:
                return
            desc = _grid_tile_desc(tile, click_target)
            username = _parse_username_from_tile_desc(desc)
            if is_reel is None and not open_any:
                is_reel = _tile_looks_like_reel(tile, click_target, desc)
            if not open_any:
                if (
                    storage is not None
                    and username
                    and current_job not in (None, "feed")
                ):
                    if storage.is_user_in_blacklist(username):
                        logger.debug(
                            f"Skip grid tile for @{username}: in blacklist."
                        )
                        return
                    interacted, interacted_when = storage.check_user_was_interacted(
                        username
                    )
                    if interacted:
                        can_reinteract = storage.can_be_reinteract(
                            interacted_when,
                            get_value(args.can_reinteract_after, None, 0),
                        )
                        if not can_reinteract:
                            skipped_interacted += 1
                            return
            sig = _grid_tile_signature(username, desc, tile, click_target, idx)
            if sig in seen:
                return
            seen.add(sig)
            if sig in _RECENT_GRID_TILES:
                if open_any:
                    recent_candidates.append((click_target, sig))
                elif is_reel:
                    recent_reel_candidates.append((click_target, sig))
                else:
                    recent_candidates.append((click_target, sig))
                return
            if open_any:
                candidates.append((click_target, sig))
                return
            if is_reel:
                if allow_reels:
                    reel_candidates.append((click_target, sig))
                else:
                    logger.debug("Skip reel tile in hashtag grid.")
                return
            candidates.append((click_target, sig))

        # Iterate a few visible tiles to find non-reel candidates
        for idx, tile in enumerate(
            _collect_grid_tiles(self.device, recycler, allow_reels=allow_reels)
        ):
            if idx > 15:
                break
            image = tile.child(resourceIdMatches=ResourceID.IMAGE_BUTTON)
            click_target = None
            if image.exists(Timeout.SHORT):
                click_target = image
            else:
                try:
                    if tile.info.get("clickable", False):
                        click_target = tile
                except Exception:
                    click_target = tile
            _consider_tile(tile, click_target, idx)

        # Fallback: when only one tile is detected, scan all visible image buttons inside the grid.
        if len(candidates) + len(reel_candidates) <= 1:
            recycler_bounds = None
            try:
                if recycler is not None and recycler.exists(Timeout.TINY):
                    recycler_bounds = recycler.get_bounds()
            except Exception:
                recycler_bounds = None
            if recycler_bounds:
                for img_idx, image in enumerate(
                    self.device.find(resourceIdMatches=ResourceID.IMAGE_BUTTON)
                ):
                    if img_idx > 24:
                        break
                    try:
                        if not image.exists(Timeout.TINY):
                            continue
                        bounds = image.get_bounds()
                    except Exception:
                        continue
                    cx = (bounds["left"] + bounds["right"]) / 2
                    cy = (bounds["top"] + bounds["bottom"]) / 2
                    if not (
                        recycler_bounds["left"] <= cx <= recycler_bounds["right"]
                        and recycler_bounds["top"] <= cy <= recycler_bounds["bottom"]
                    ):
                        continue
                    tile = image.up()
                    _consider_tile(tile, image, idx=100 + img_idx)
        if candidates:
            if open_any:
                logger.debug(f"Random tile in view exists ({len(candidates)} candidates).")
            else:
                logger.debug(
                    f"Random non-reel image in view exists ({len(candidates)} candidates)."
                )
            picked, sig = choice(candidates)
            _RECENT_GRID_TILES.append(sig)
            return picked
        if not open_any and allow_reels and reel_candidates:
            logger.debug(
                f"Random reel tile in view exists ({len(reel_candidates)} candidates)."
            )
            picked, sig = choice(reel_candidates)
            _RECENT_GRID_TILES.append(sig)
            return picked
        if allow_recent:
            if recent_candidates:
                logger.debug(
                    f"Only recent tiles found ({len(recent_candidates)})."
                )
                picked, sig = choice(recent_candidates)
                _RECENT_GRID_TILES.append(sig)
                return picked
            if not open_any and allow_reels and recent_reel_candidates:
                logger.debug(
                    f"Only recent reel tiles found ({len(recent_reel_candidates)})."
                )
                picked, sig = choice(recent_reel_candidates)
                _RECENT_GRID_TILES.append(sig)
                return picked
        if skipped_interacted:
            logger.debug(
                f"Skipped {skipped_interacted} tile(s) for already-interacted users."
            )
        logger.debug("No suitable tiles detected in this view.")
        return None

    def _getRecentTab(self):
        # Recent tab was removed in newer IG; fall back to "For you"/"Top"
        candidates = [
            TabBarText.RECENT_CONTENT_DESC,
            "For you",
            "Top",
        ]
        for title in candidates:
            obj = self.device.find(
                className=ClassName.TEXT_VIEW,
                textMatches=case_insensitive_re(title),
            )
            if obj.exists(Timeout.SHORT):
                logger.debug(f"{title} tab exists.")
                return obj
        logger.debug("Recent/For you tab doesn't exist.")
        return self.device.find(className=ClassName.TEXT_VIEW, text="")  # dummy


# The place view for the moment It's only a copy/paste of HashTagView
# Maybe we can add the com.instagram.android:id/category_name == "Country/Region" (or other obv)


class PlacesView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getRecyclerView(self):
        obj = _select_grid_recycler_view(self.device)
        if obj.exists(Timeout.LONG):
            logger.debug("RecyclerView exists.")
        return obj

    def _getFistImageView(
        self,
        recycler,
        storage=None,
        current_job: Optional[str] = None,
        allow_recent: bool = False,
        allow_reels: bool = False,
        open_any: bool = False,
    ):
        # Places grid rarely shows reels; still try to skip them for safety.
        candidates = []
        reel_candidates = []
        recent_candidates = []
        recent_reel_candidates = []
        skipped_interacted = 0
        seen = set()

        def _tile_looks_like_reel(tile, click_target, desc: str) -> bool:
            for candidate in (tile, click_target):
                if candidate is None:
                    continue
                try:
                    reel_badge = candidate.child(
                        resourceId=ResourceID.SEARCH_REEL_INDICATOR
                    )
                    if reel_badge.exists(Timeout.TINY):
                        return True
                    if candidate.child(
                        resourceId=ResourceID.PLAY_COUNT_CONTAINER
                    ).exists(Timeout.TINY):
                        return True
                    if candidate.child(
                        resourceId=ResourceID.PLAY_COUNT_LOGO
                    ).exists(Timeout.TINY):
                        return True
                except Exception:
                    continue
            return bool(desc and re.search(r"\breel\b", desc, re.IGNORECASE))

        def _consider_tile(tile, click_target, idx, is_reel: Optional[bool] = None):
            nonlocal skipped_interacted
            if click_target is None:
                return
            desc = _grid_tile_desc(tile, click_target)
            username = _parse_username_from_tile_desc(desc)
            if is_reel is None and not open_any:
                is_reel = _tile_looks_like_reel(tile, click_target, desc)
            if not open_any:
                if (
                    storage is not None
                    and username
                    and current_job not in (None, "feed")
                ):
                    if storage.is_user_in_blacklist(username):
                        logger.debug(
                            f"Skip grid tile for @{username}: in blacklist."
                        )
                        return
                    interacted, interacted_when = storage.check_user_was_interacted(
                        username
                    )
                    if interacted:
                        can_reinteract = storage.can_be_reinteract(
                            interacted_when,
                            get_value(args.can_reinteract_after, None, 0),
                        )
                        if not can_reinteract:
                            skipped_interacted += 1
                            return
            sig = _grid_tile_signature(username, desc, tile, click_target, idx)
            if sig in seen:
                return
            seen.add(sig)
            if sig in _RECENT_GRID_TILES:
                if open_any:
                    recent_candidates.append((click_target, sig))
                elif is_reel:
                    recent_reel_candidates.append((click_target, sig))
                else:
                    recent_candidates.append((click_target, sig))
                return
            if open_any:
                candidates.append((click_target, sig))
                return
            if is_reel:
                if allow_reels:
                    reel_candidates.append((click_target, sig))
                else:
                    logger.debug("Skip reel tile in places grid.")
                return
            candidates.append((click_target, sig))

        for idx, tile in enumerate(
            _collect_grid_tiles(self.device, recycler, allow_reels=allow_reels)
        ):
            if idx > 15:
                break
            image = tile.child(resourceIdMatches=ResourceID.IMAGE_BUTTON)
            click_target = None
            if image.exists(Timeout.SHORT):
                click_target = image
            else:
                try:
                    if tile.info.get("clickable", False):
                        click_target = tile
                except Exception:
                    click_target = tile
            _consider_tile(tile, click_target, idx)

        # Fallback: when only one tile is detected, scan all visible image buttons inside the grid.
        if len(candidates) + len(reel_candidates) <= 1:
            recycler_bounds = None
            try:
                if recycler is not None and recycler.exists(Timeout.TINY):
                    recycler_bounds = recycler.get_bounds()
            except Exception:
                recycler_bounds = None
            if recycler_bounds:
                for img_idx, image in enumerate(
                    self.device.find(resourceIdMatches=ResourceID.IMAGE_BUTTON)
                ):
                    if img_idx > 24:
                        break
                    try:
                        if not image.exists(Timeout.TINY):
                            continue
                        bounds = image.get_bounds()
                    except Exception:
                        continue
                    cx = (bounds["left"] + bounds["right"]) / 2
                    cy = (bounds["top"] + bounds["bottom"]) / 2
                    if not (
                        recycler_bounds["left"] <= cx <= recycler_bounds["right"]
                        and recycler_bounds["top"] <= cy <= recycler_bounds["bottom"]
                    ):
                        continue
                    tile = image.up()
                    _consider_tile(tile, image, idx=100 + img_idx)
        if candidates:
            if open_any:
                logger.debug(f"Random tile in view exists ({len(candidates)} candidates).")
            else:
                logger.debug(
                    f"Random non-reel image in view exists ({len(candidates)} candidates)."
                )
            picked, sig = choice(candidates)
            _RECENT_GRID_TILES.append(sig)
            return picked
        if not open_any and allow_reels and reel_candidates:
            logger.debug(
                f"Random reel tile in view exists ({len(reel_candidates)} candidates)."
            )
            picked, sig = choice(reel_candidates)
            _RECENT_GRID_TILES.append(sig)
            return picked
        if allow_recent:
            if recent_candidates:
                logger.debug(
                    f"Only recent tiles found ({len(recent_candidates)})."
                )
                picked, sig = choice(recent_candidates)
                _RECENT_GRID_TILES.append(sig)
                return picked
            if not open_any and allow_reels and recent_reel_candidates:
                logger.debug(
                    f"Only recent reel tiles found ({len(recent_reel_candidates)})."
                )
                picked, sig = choice(recent_reel_candidates)
                _RECENT_GRID_TILES.append(sig)
                return picked
        if skipped_interacted:
            logger.debug(
                f"Skipped {skipped_interacted} tile(s) for already-interacted users."
            )
        logger.debug("No suitable tiles detected in this view.")
        return None

    def _getRecentTab(self):
        candidates = [
            TabBarText.RECENT_CONTENT_DESC,
            "For you",
            "Top",
        ]
        for title in candidates:
            obj = self.device.find(
                className=ClassName.TEXT_VIEW,
                textMatches=case_insensitive_re(title),
            )
            if obj.exists(Timeout.SHORT):
                return obj
        return self.device.find(className=ClassName.TEXT_VIEW, text="")

    def _getInformBody(self):
        return self.device.find(
            className=ClassName.TEXT_VIEW,
            resourceId=ResourceID.INFORM_BODY,
        )


class SearchView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _getSearchEditText(self):
        for _ in range(2):
            obj = self.device.find(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT
                ),
            )
            if obj.exists(Timeout.LONG):
                return obj
            logger.error(
                "Can't find the search bar! Refreshing it by pressing Home and Search again.."
            )
            UniversalActions.close_keyboard(self.device)
            TabBarView(self.device).navigateToHome()
            TabBarView(self.device).navigateToSearch()
        logger.error("Can't find the search bar!")
        return None

    def is_on_target_results(self, target: str) -> bool:
        try:
            search_edit = self.device.find(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT
                )
            )
            if not search_edit.exists(Timeout.TINY):
                return False
            current = (search_edit.get_text(error=False) or "").strip()
            target_norm = emoji.emojize(target, use_aliases=True).strip()
            current_norm = current.lstrip("#").casefold()
            target_norm = target_norm.lstrip("#").casefold()
            if not target_norm or current_norm != target_norm:
                return False
            if self.device.find(
                resourceIdMatches=case_insensitive_re(ResourceID.SEARCH_TAB_BAR_LAYOUT)
            ).exists(Timeout.TINY):
                return True
            if self.device.find(
                resourceIdMatches=case_insensitive_re(ResourceID.RECYCLER_VIEW)
            ).exists(Timeout.TINY):
                return True
        except Exception:
            return False
        return False

    def _getUsernameRow(self, username):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.ROW_SEARCH_USER_USERNAME),
            className=ClassName.TEXT_VIEW,
            textMatches=case_insensitive_re(username),
        )

    def _getHashtagRow(self, hashtag):
        return self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.ROW_HASHTAG_TEXTVIEW_TAG_NAME
            ),
            className=ClassName.TEXT_VIEW,
            text=f"#{hashtag}",
        )

    def _getPlaceRow(self):
        obj = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.ROW_PLACE_TITLE),
        )
        obj.wait(Timeout.MEDIUM)
        return obj

    def _getTabTextView(self, tab: SearchTabs):
        # New search results tabs use plain Buttons with text ("For you", "Accounts", "Not personalized")
        tab_text = {
            SearchTabs.TOP: "For you",
            SearchTabs.ACCOUNTS: "Accounts",
            SearchTabs.TAGS: "Tags",
            SearchTabs.PLACES: "Places",
        }.get(tab, tab.name)
        # Try container-specific search first
        tab_layout = self.device.find(resourceIdMatches=case_insensitive_re(ResourceID.SEARCH_TAB_BAR_LAYOUT))
        if tab_layout.exists():
            candidate = tab_layout.child(textMatches=case_insensitive_re(tab_text))
            if candidate.exists():
                return candidate
        # Fallback: global button lookup by text
        candidate = self.device.find(className=ClassName.BUTTON, textMatches=case_insensitive_re(tab_text))
        if candidate.exists():
            return candidate
        return None

    def _searchTabWithTextPlaceholder(self, tab: SearchTabs):
        tab_layout = self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.FIXED_TABBAR_TABS_CONTAINER
            ),
        )
        search_edit_text = self._getSearchEditText()

        fixed_text = "Search {}".format(tab.name if tab.name != "TAGS" else "hashtags")
        logger.debug(
            "Going to check if the search bar have as placeholder: {}".format(
                fixed_text
            )
        )

        for item in tab_layout.child(
            resourceId=ResourceID.TAB_BUTTON_FALLBACK_ICON,
            className=ClassName.IMAGE_VIEW,
        ):
            item.click()

            # Little trick for force-update the ui and placeholder text
            if search_edit_text is not None:
                search_edit_text.click()

            if self.device.find(
                className=ClassName.TEXT_VIEW,
                textMatches=case_insensitive_re(fixed_text),
            ).exists():
                return item
        return None

    def navigate_to_target(self, target: str, job: str) -> bool:
        target = emoji.emojize(target, use_aliases=True)
        logger.info(f"Navigate to {target}")
        if self.is_on_target_results(target):
            logger.info(f"Already on {target} results; skipping re-search.")
            return True
        search_edit_text = self._getSearchEditText()
        if search_edit_text is not None:
            logger.debug("Pressing on searchbar.")
            search_edit_text.click(sleep=SleepTime.SHORT)
        else:
            logger.debug("There is no searchbar!")
            return False
        if self._check_current_view(target, job):
            logger.info(f"{target} is in recent history.")
            return True
        search_edit_text.set_text(
            target,
            Mode.PASTE if args.dont_type else Mode.TYPE,
        )
        if self._check_current_view(target, job):
            logger.info(f"{target} is in top view.")
            return True
        echo_text = self.device.find(resourceId=ResourceID.ECHO_TEXT)
        if echo_text.exists(Timeout.SHORT):
            logger.debug("Pressing on see all results.")
            echo_text.click()
        # at this point we have the tabs available
        self._switch_to_target_tag(job)
        if self._check_current_view(target, job, in_place_tab=True):
            return True
        return False

    def _switch_to_target_tag(self, job: str):
        if "place" in job:
            tab = SearchTabs.PLACES
        elif "hashtag" in job:
            tab = SearchTabs.TAGS
        else:
            tab = SearchTabs.ACCOUNTS

        obj = self._getTabTextView(tab)
        if obj is not None:
            logger.info(f"Switching to {tab.name}")
            obj.click()

    def _check_current_view(
        self, target: str, job: str, in_place_tab: bool = False
    ) -> bool:
        if "place" in job:
            if not in_place_tab:
                return False
            else:
                obj = self._getPlaceRow()
        else:
            # Prefer explicit user row id, then fallback to visible text
            obj = self.device.find(
                resourceIdMatches=case_insensitive_re(ResourceID.ROW_SEARCH_USER_USERNAME),
                textMatches=case_insensitive_re(target),
            )
            if not obj.exists():
                obj = self.device.find(textMatches=case_insensitive_re(target))
        if obj.exists():
            obj.click()
            # Wait for profile page to load when opening accounts
            if "hashtag" not in job and "place" not in job:
                header = self.device.find(
                    resourceIdMatches=case_insensitive_re(
                        f"{ResourceID.ROW_PROFILE_HEADER_IMAGEVIEW}|{ResourceID.PROFILE_HEADER_AVATAR_CONTAINER_TOP_LEFT_STUB}"
                    )
                )
                header.exists(Timeout.LONG)
            # If we landed on a reel from search grid, optionally watch/like before returning
            self._handle_search_reel_autoplay_if_reel(current_job=job, target=target)
            return True
        return False

    def _handle_search_reel_autoplay_if_reel(
        self, current_job: Optional[str] = None, target: Optional[str] = None
    ):
        reels_count = get_value(args.watch_reels, None, 0)
        if reels_count is None:
            reels_count = 0
        dwell_regular = get_value(args.reels_watch_time, None, 6, its_time=True)
        if dwell_regular is None:
            dwell_regular = 6
        dwell_ads = get_value(
            args.reels_ad_watch_time, None, dwell_regular, its_time=True
        )
        if dwell_ads is None:
            dwell_ads = dwell_regular
        # Detect reel viewer presence using strong reel markers to avoid false positives
        if not PostsViewList(self.device)._is_in_reel_viewer():
            return

        storage = getattr(configs, "storage", None)
        if (
            args.single_image_reels_as_posts
            and PostsViewList(self.device)._is_single_image_reel()
        ):
            session_state = getattr(configs, "session_state", None)
            return PostsViewList(self.device)._handle_single_image_reel_as_post(
                session_state,
                storage=storage,
                current_job=current_job,
                target=target,
            )

        if reels_count <= 0:
            logger.info("Reel viewer detected; watch-reels disabled, exiting viewer.")
            # Back twice in case the first back closes overlays only
            self.device.back()
            random_sleep(inf=0.5, sup=1.2, modulable=False)
            self.device.back()
            random_sleep(inf=0.5, sup=1.2, modulable=False)
            return True

        like_pct = get_value(args.reels_like_percentage, None, 0)
        doubletap_pct = get_value(args.reels_like_doubletap_percentage, None, 0)
        session_state = getattr(configs, "session_state", None)
        likes_limit_logged = False
        reel_likes_limit_logged = False
        reel_watch_limit_logged = False
        extra_watch_logged = False
        extra_watch_remaining = None
        reels_likes_limit = 0
        reels_watches_limit = 0
        extra_watch_limit = 0
        if session_state is not None:
            reels_likes_limit = int(session_state.args.current_reels_likes_limit)
            reels_watches_limit = int(session_state.args.current_reels_watches_limit)
            extra_watch_limit = int(
                session_state.args.current_reels_watch_after_like_limit
            )
            if reels_watches_limit == 0:
                logger.info("Reel watch limit is 0; skipping reels.")
                # Back twice in case the first back closes overlays only
                self.device.back()
                random_sleep(inf=0.5, sup=1.2, modulable=False)
                self.device.back()
                random_sleep(inf=0.5, sup=1.2, modulable=False)
                return True
        logger.info(
            f"Reel viewer detected; watching up to {reels_count} reels (watch-reels)."
        )
        post_view = PostsViewList(self.device)
        for _ in range(reels_count):
            if (
                session_state is not None
                and reels_watches_limit > 0
                and session_state.totalReelWatched >= reels_watches_limit
            ):
                if not reel_watch_limit_logged:
                    logger.info("Reel watch limit reached; stopping session.")
                    reel_watch_limit_logged = True
                sessions = getattr(configs, "sessions", None)
                if sessions is None:
                    logger.warning("Sessions list unavailable; exiting reels viewer.")
                    self.device.back()
                    random_sleep(inf=0.5, sup=1.2, modulable=False)
                    self.device.back()
                    random_sleep(inf=0.5, sup=1.2, modulable=False)
                    return True
                stop_bot(self.device, sessions, session_state)
                return True
            username = post_view._get_reel_author_username()
            if not username:
                logger.debug(
                    "Reel author not detected; cannot check interacted history."
                )
            skip_like_for_user = False
            if storage is not None and username and current_job not in (None, "feed"):
                if storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip reel interaction.")
                    skip_like_for_user = True
                else:
                    interacted, interacted_when = storage.check_user_was_interacted(
                        username
                    )
                    if interacted:
                        can_reinteract = storage.can_be_reinteract(
                            interacted_when,
                            get_value(args.can_reinteract_after, None, 0),
                        )
                        logger.info(
                            f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                        )
                        if not can_reinteract:
                            skip_like_for_user = True
            already_liked = _is_reel_liked(self.device)
            if already_liked:
                logger.info("Reel already liked; skipping like.")
                skip_like_for_user = True
                if storage is not None and username and session_state is not None:
                    storage.add_interacted_user(
                        username,
                        session_id=session_state.id,
                        liked=1,
                        job_name=current_job,
                        target=target,
                    )
                logger.info("Reel already liked; swiping immediately.")
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.UP, delta_y=800
                )
                random_sleep(inf=0.1, sup=0.3, modulable=False)
                if session_state is not None:
                    session_state.totalWatched += 1
                    session_state.totalReelWatched += 1
                    if extra_watch_remaining is not None:
                        extra_watch_remaining -= 1
                        if extra_watch_remaining <= 0:
                            logger.info(
                                "Like limit reached; extra reels watched, exiting."
                            )
                            break
                    if (
                        reels_watches_limit > 0
                        and session_state.totalReelWatched >= reels_watches_limit
                    ):
                        logger.info("Reel watch limit reached; stopping session.")
                        sessions = getattr(configs, "sessions", None)
                        if sessions is None:
                            logger.warning(
                                "Sessions list unavailable; exiting reels viewer."
                            )
                            self.device.back()
                            random_sleep(inf=0.5, sup=1.2, modulable=False)
                            self.device.back()
                            random_sleep(inf=0.5, sup=1.2, modulable=False)
                            return True
                        stop_bot(self.device, sessions, session_state)
                        return True
                continue
            is_ad = self._is_reel_ad_only()
            if is_ad and not args.reels_like_ads:
                logger.debug("Search reel is an ad; skipping immediately.")
                UniversalActions(self.device)._swipe_points(direction=Direction.UP, delta_y=800)
                random_sleep(inf=0.5, sup=1.2, modulable=False)
                if session_state is not None:
                    session_state.totalWatched += 1
                    session_state.totalReelWatched += 1
                    if extra_watch_remaining is not None:
                        extra_watch_remaining -= 1
                        if extra_watch_remaining <= 0:
                            logger.info(
                                "Like limit reached; extra reels watched, exiting."
                            )
                            break
                    if (
                        reels_watches_limit > 0
                        and session_state.totalReelWatched >= reels_watches_limit
                    ):
                        logger.info("Reel watch limit reached; stopping session.")
                        sessions = getattr(configs, "sessions", None)
                        if sessions is None:
                            logger.warning(
                                "Sessions list unavailable; exiting reels viewer."
                            )
                            self._exit_reel_viewer()
                            self.last_reel_handled = True
                            return True
                        stop_bot(self.device, sessions, session_state)
                        self.last_reel_handled = True
                        return True
                continue

            likes_limit_reached = False
            if session_state is not None:
                likes_limit = int(session_state.args.current_likes_limit)
                global_likes_reached = (
                    likes_limit > 0 and session_state.totalLikes >= likes_limit
                )
                reel_likes_reached = (
                    reels_likes_limit > 0
                    and session_state.totalReelLikes >= reels_likes_limit
                )
                if global_likes_reached and not likes_limit_logged:
                    logger.info("Like limit reached; skipping reel likes.")
                    likes_limit_logged = True
                if reel_likes_reached and not reel_likes_limit_logged:
                    logger.info("Reel-like limit reached; skipping reel likes.")
                    reel_likes_limit_logged = True
                likes_limit_reached = global_likes_reached or reel_likes_reached
                if likes_limit_reached and extra_watch_remaining is None:
                    extra_watch_remaining = max(0, extra_watch_limit)
                    if extra_watch_remaining == 0:
                        logger.info(
                            "Like limit reached; extra watch disabled, stopping reels."
                        )
                        break
                    if not extra_watch_logged:
                        logger.info(
                            f"Like limit reached; watching {extra_watch_remaining} more reels before exiting."
                        )
                        extra_watch_logged = True

            if session_state is not None:
                limits_reached, _, _ = session_state.check_limit(
                    limit_type=session_state.Limit.ALL
                )
                if limits_reached:
                    logger.info(
                        "Session limits reached while in search reels; stopping session."
                    )
                    sessions = getattr(configs, "sessions", None)
                    if sessions is None:
                        logger.warning(
                            "Sessions list unavailable; exiting reels viewer."
                        )
                        # Back twice in case the first back closes overlays only
                        self.device.back()
                        random_sleep(inf=0.5, sup=1.2, modulable=False)
                        self.device.back()
                        random_sleep(inf=0.5, sup=1.2, modulable=False)
                        return True
                    stop_bot(self.device, sessions, session_state)

            if (
                like_pct
                and not likes_limit_reached
                and not skip_like_for_user
                and (args.reels_like_ads or not is_ad)
                and randint(1, 100) <= like_pct
            ):
                used_doubletap = _reel_like_use_double_tap(doubletap_pct)
                liked = None
                method = None
                if used_doubletap and _double_tap_reel_media(self.device):
                    random_sleep(inf=0.3, sup=0.7, modulable=False)
                    liked = _is_reel_liked(self.device)
                    if not liked:
                        logger.info(
                            "Double-tap did not confirm like; trying heart."
                        )
                        liked = _click_reel_like_button(self.device)
                        if liked:
                            method = "heart"
                    else:
                        method = "double-tap"
                else:
                    liked = _click_reel_like_button(self.device)
                    if liked:
                        method = "heart"
                if liked:
                    logger.info(f"Liked reel ({method}).")
                    if session_state is not None:
                        session_state.totalLikes += 1
                        session_state.totalReelLikes += 1
                    if storage is not None and username and session_state is not None:
                        storage.add_interacted_user(
                            username,
                            session_id=session_state.id,
                            liked=1,
                            job_name=current_job,
                            target=target,
                        )
                elif liked is None:
                    logger.warning("Reel like could not be confirmed.")
            stay_time = dwell_ads if is_ad else dwell_regular
            random_sleep(inf=max(1, stay_time - 1), sup=stay_time + 1, modulable=False)
            if session_state is not None:
                session_state.totalWatched += 1
                session_state.totalReelWatched += 1
                if extra_watch_remaining is not None:
                    extra_watch_remaining -= 1
                    if extra_watch_remaining <= 0:
                        logger.info(
                            "Like limit reached; extra reels watched, exiting."
                        )
                        break
                if (
                    reels_watches_limit > 0
                    and session_state.totalReelWatched >= reels_watches_limit
                ):
                    logger.info("Reel watch limit reached; stopping session.")
                    sessions = getattr(configs, "sessions", None)
                    if sessions is None:
                        logger.warning(
                            "Sessions list unavailable; exiting reels viewer."
                        )
                        self.device.back()
                        random_sleep(inf=0.5, sup=1.2, modulable=False)
                        self.device.back()
                        random_sleep(inf=0.5, sup=1.2, modulable=False)
                        return True
                    stop_bot(self.device, sessions, session_state)
                    return True
            logger.info("Swiping to next reel.")
            UniversalActions(self.device)._swipe_points(direction=Direction.UP, delta_y=800)
        if session_state is not None:
            limits_reached, _, _ = session_state.check_limit(
                limit_type=session_state.Limit.ALL
            )
            if limits_reached:
                logger.info(
                    "Session limits reached after search reels; stopping session."
                )
                sessions = getattr(configs, "sessions", None)
                if sessions is None:
                    logger.warning(
                        "Sessions list unavailable; exiting reels viewer."
                    )
                    self.device.back()
                    random_sleep(inf=0.5, sup=1.2, modulable=False)
                    self.device.back()
                    random_sleep(inf=0.5, sup=1.2, modulable=False)
                    return True
                stop_bot(self.device, sessions, session_state)
        logger.info("Returning from search reels.")
        # Back twice in case the first back closes overlays only
        self.device.back()
        random_sleep(inf=0.5, sup=1.2, modulable=False)
        self.device.back()
        random_sleep(inf=0.5, sup=1.2, modulable=False)
        return True

    def _is_reel_ad_only(self) -> bool:
        """Lightweight ad detector for reels to pick dwell timing."""
        sponsored_txts = [
            "sponsored",
            "gesponsert",
            "pubblicité",
            "publicidad",
            "sponsorisé",
            "advertisement",
            "ad",
        ]
        if self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.SPONSORED_CONTENT_SERVER_RENDERED_ROOT)
        ).exists(Timeout.TINY):
            return True
        if self.device.find(resourceId=ResourceID.AD_BADGE).exists(Timeout.TINY):
            return True
        if self.device.find(textMatches=case_insensitive_re("|".join(sponsored_txts))).exists(
            Timeout.TINY
        ):
            return True
        if self.device.find(
            descriptionMatches=case_insensitive_re("|".join(sponsored_txts))
        ).exists(Timeout.TINY):
            return True
        return False

    def _fallback_reel_hit(self) -> bool:
        """
        Last-ditch detector when normal selectors fail: look for the large reels viewpager with bounds ~full screen.
        """
        try:
            vp = self.device.find(className="androidx.viewpager.widget.ViewPager")
            if vp.exists(Timeout.TINY):
                b = vp.get_bounds()
                if b.get("bottom", 0) - b.get("top", 0) > self.device.get_info()[
                    "displayHeight"
                ] * 0.85:
                    return True
        except Exception:
            pass
        return False


class PostsViewList:
    def __init__(self, device: DeviceFacade):
        self.device = device
        self.has_tags = False
        self.reel_flag = False
        self._last_media_log_key = None
        self.last_reel_handled = False

    def _is_single_image_reel(self) -> bool:
        try:
            return self.device.find(
                resourceId=ResourceID.CLIPS_SINGLE_IMAGE_MEDIA_CONTENT
            ).exists(Timeout.TINY)
        except Exception:
            return False

    def _get_reel_author_username(self) -> Optional[str]:
        try:
            author = self.device.find(resourceId=ResourceID.CLIPS_AUTHOR_USERNAME)
            if author.exists(Timeout.TINY):
                text = (author.get_text(error=False) or "").strip()
                if text:
                    return text
        except Exception:
            pass
        # Fallback: parse from content description
        try:
            media = self.device.find(resourceId=ResourceID.CLIPS_MEDIA_COMPONENT)
            if media.exists(Timeout.TINY):
                desc = media.get_desc() or ""
                match = re.search(r"Reel by ([^\\.]+)", desc)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass
        try:
            media = self.device.find(resourceId=ResourceID.CLIPS_VIDEO_CONTAINER)
            if media.exists(Timeout.TINY):
                desc = media.get_desc() or ""
                match = re.search(r"Reel by ([^\\.]+)", desc)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass
        return None

    def _has_tab_or_search_ui(self) -> bool:
        # Single selector to keep UIA2 calls minimal on heavy search/grid pages.
        match_ids = case_insensitive_re(
            f"{ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT}|"
            f"{ResourceID.ROW_SEARCH_EDIT_TEXT}|"
            f"{ResourceID.SEARCH_TAB_BAR_LAYOUT}"
        )
        try:
            return self.device.find(resourceIdMatches=match_ids).exists(Timeout.TINY)
        except Exception:
            return False

    def _fallback_reel_hit(self) -> bool:
        """
        Last-ditch detector when normal selectors fail: look for the large reels viewpager with bounds ~full screen.
        """
        try:
            vp = self.device.find(className="androidx.viewpager.widget.ViewPager")
            if vp.exists(Timeout.TINY):
                b = vp.get_bounds()
                if b.get("bottom", 0) - b.get("top", 0) > self.device.get_info()[
                    "displayHeight"
                ] * 0.85:
                    return True
        except Exception:
            pass
        return False

    def log_media_detection(self, username: Optional[str] = None) -> None:
        if self._has_tab_or_search_ui():
            return
        if self._is_in_reel_viewer():
            subtype = None
            try:
                if self._is_single_image_reel():
                    subtype = "single-image"
                elif self.device.find(
                    resourceId=ResourceID.CLIPS_VIDEO_CONTAINER
                ).exists(Timeout.TINY):
                    subtype = "video"
            except Exception:
                subtype = None
            key = f"reel:{subtype or 'unknown'}:{username or ''}"
            if key != self._last_media_log_key:
                if subtype == "single-image" and args.single_image_reels_as_posts:
                    msg = "Detected media: PHOTO (single-image reel)"
                else:
                    msg = "Detected media: REEL"
                if subtype == "single-image":
                    if not args.single_image_reels_as_posts:
                        msg += " (single-image clip)"
                elif subtype == "video":
                    msg += " (video)"
                logger.info(msg)
                self._last_media_log_key = key
            return

        if not self.in_post_view():
            return
        media, content_desc = self._get_media_container()
        if content_desc is None:
            return
        media_type, obj_count = self.detect_media_type(content_desc)
        if media_type is None:
            return
        key = f"post:{media_type.name}:{obj_count}:{content_desc}"
        if key == self._last_media_log_key:
            return
        if media_type == MediaType.CAROUSEL and obj_count:
            logger.info(f"Detected media: CAROUSEL ({obj_count} items)")
        else:
            logger.info(f"Detected media: {media_type.name}")
        self._last_media_log_key = key

    def _is_reel_ad_only(self) -> bool:
        """Lightweight ad detector for reels to pick dwell timing."""
        sponsored_txts = [
            "sponsored",
            "gesponsert",
            "pubblicité",
            "publicidad",
            "sponsorisé",
            "advertisement",
            "ad",
        ]
        if self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.SPONSORED_CONTENT_SERVER_RENDERED_ROOT
            )
        ).exists(Timeout.TINY):
            return True
        if self.device.find(resourceId=ResourceID.AD_BADGE).exists(Timeout.TINY):
            return True
        if self.device.find(
            textMatches=case_insensitive_re("|".join(sponsored_txts))
        ).exists(Timeout.TINY):
            return True
        if self.device.find(
            descriptionMatches=case_insensitive_re("|".join(sponsored_txts))
        ).exists(Timeout.TINY):
            return True
        return False

    def _is_in_reel_viewer(self) -> bool:
        """
        Detect the full-screen reels/clips viewer reliably across recent IG builds.
        """
        if self._has_tab_or_search_ui():
            logger.debug("Search UI visible; skip reel detection.")
            return False
        strong_selectors = [
            {
                "resourceId": ResourceID.CLIPS_VIDEO_CONTAINER,
                "descriptionMatches": case_insensitive_re("Reel by"),
            },
            {"resourceId": ResourceID.CLIPS_MEDIA_COMPONENT},
            {"resourceId": ResourceID.CLIPS_ITEM_OVERLAY_COMPONENT},
            {"resourceId": ResourceID.CLIPS_UFI_COMPONENT},
            {"resourceId": ResourceID.CLIPS_AUTHOR_USERNAME},
            {"resourceId": ResourceID.REEL_VIEWER_TITLE},
            {"resourceId": ResourceID.REEL_VIEWER_TIMESTAMP},
            {"descriptionMatches": case_insensitive_re("Reel by")},
        ]
        for sel in strong_selectors:
            try:
                if self.device.find(**sel).exists(Timeout.SHORT):
                    logger.debug(f"View classification: REEL (marker={sel})")
                    return True
            except Exception:
                continue
        # Fallback heuristic: large ViewPager typical of reels viewer
        if self._fallback_reel_hit():
            if self._has_tab_or_search_ui():
                logger.debug(
                    "Fallback viewpager detected, but tab/search UI is visible; skip reel classification."
                )
                return False
            logger.debug("View classification: UNKNOWN (fallback=viewpager, no reel markers)")
        return False

    def _exit_reel_viewer(self):
        logger.info("Leaving reels viewer.")
        # One back first; if still in viewer, back again.
        self.device.back()
        random_sleep(inf=0.5, sup=1.2, modulable=False)
        if self._is_in_reel_viewer():
            self.device.back()
            random_sleep(inf=0.5, sup=1.2, modulable=False)

    def in_post_view(self) -> bool:
        """
        Heuristic to decide if we're on a standard post view (not grid, not reels).
        """
        if self._has_tab_or_search_ui():
            logger.debug("Search UI visible; not a post view.")
            return False
        markers = [
            {"resourceIdMatches": ResourceID.MEDIA_CONTAINER},
            {"resourceIdMatches": ResourceID.ROW_FEED_PHOTO_PROFILE_NAME},
            {"resourceIdMatches": ResourceID.ROW_FEED_BUTTON_LIKE},
            {"resourceIdMatches": ResourceID.ROW_FEED_TEXT},
        ]
        for sel in markers:
            try:
                view = self.device.find(**sel)
                if view.exists(Timeout.SHORT):
                    # For media container, ensure it actually has children/bounds
                    if sel.get("resourceIdMatches") == ResourceID.MEDIA_CONTAINER:
                        if view.count_items() == 0:
                            continue
                    logger.debug(f"View classification: POST (marker={sel})")
                    return True
            except Exception:
                continue
        # If not a post view, log whether this is a reel or unknown view.
        if self._is_in_reel_viewer():
            logger.debug("View classification: REEL (in_post_view fallback)")
        else:
            logger.debug("View classification: UNKNOWN (not post, not reel)")
        return False

    def maybe_watch_reel_viewer(
        self,
        session_state,
        force: bool = False,
        storage=None,
        current_job: Optional[str] = None,
        target: Optional[str] = None,
    ) -> bool:
        """If we're in the reels viewer (e.g., opened from search/grid), watch a few reels and return."""
        reels_count = get_value(args.watch_reels, None, 0)
        if reels_count is None:
            reels_count = 0

        if self._has_tab_or_search_ui():
            return False

        # Allow a short wait for the viewer to fully render
        detected = False
        for _ in range(4):
            if force or self._is_in_reel_viewer():
                detected = True
                break
            random_sleep(inf=0.35, sup=0.55, modulable=False)
        if not detected:
            logger.debug("Reel viewer not detected; skipping reel handler.")
            return False
        self.log_media_detection()

        if args.single_image_reels_as_posts and self._is_single_image_reel():
            handled = self._handle_single_image_reel_as_post(
                session_state,
                storage=storage,
                current_job=current_job,
                target=target,
            )
            if handled:
                self.last_reel_handled = True
            return handled

        # Respect 0 == disabled: just back out safely.
        if reels_count <= 0:
            logger.info("Reel viewer detected; watch-reels disabled, exiting viewer.")
            self._exit_reel_viewer()
            self.last_reel_handled = True
            return True
        like_pct = get_value(args.reels_like_percentage, None, 0)
        doubletap_pct = get_value(args.reels_like_doubletap_percentage, None, 0)
        dwell_regular = get_value(args.reels_watch_time, None, 6, its_time=True)
        if dwell_regular is None:
            dwell_regular = 6
        dwell_ads = get_value(
            args.reels_ad_watch_time, None, dwell_regular, its_time=True
        )
        if dwell_ads is None:
            dwell_ads = dwell_regular
        # Ensure min dwell so we don't rapid-swipe: floor at 3s
        dwell_regular = max(dwell_regular, 3)
        dwell_ads = max(dwell_ads, 3)

        logger.info(
            f"Reel viewer detected; watching up to {reels_count} reels (watch-reels)."
        )
        likes_limit_logged = False
        reel_likes_limit_logged = False
        reel_watch_limit_logged = False
        extra_watch_logged = False
        extra_watch_remaining = None
        reels_likes_limit = int(session_state.args.current_reels_likes_limit)
        reels_watches_limit = int(session_state.args.current_reels_watches_limit)
        extra_watch_limit = int(
            session_state.args.current_reels_watch_after_like_limit
        )
        if reels_watches_limit == 0:
            logger.info("Reel watch limit is 0; skipping reels.")
            self._exit_reel_viewer()
            return True
        for _ in range(reels_count):
            username = self._get_reel_author_username()
            if not username:
                logger.debug("Reel author not detected; cannot check interacted history.")
            skip_like_for_user = False
            if storage is not None and username and current_job not in (None, "feed"):
                if storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip reel interaction.")
                    skip_like_for_user = True
                else:
                    interacted, interacted_when = storage.check_user_was_interacted(
                        username
                    )
                    if interacted:
                        can_reinteract = storage.can_be_reinteract(
                            interacted_when,
                            get_value(args.can_reinteract_after, None, 0),
                        )
                        logger.info(
                            f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                        )
                        if not can_reinteract:
                            skip_like_for_user = True
            already_liked = _is_reel_liked(self.device)
            if already_liked:
                logger.info("Reel already liked; skipping like.")
                skip_like_for_user = True
                if storage is not None and username and session_state is not None:
                    storage.add_interacted_user(
                        username,
                        session_id=session_state.id,
                        liked=1,
                        job_name=current_job,
                        target=target,
                    )
                logger.info("Reel already liked; swiping immediately.")
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.UP, delta_y=800
                )
                random_sleep(inf=0.1, sup=0.3, modulable=False)
                if session_state is not None:
                    session_state.totalWatched += 1
                    session_state.totalReelWatched += 1
                    if extra_watch_remaining is not None:
                        extra_watch_remaining -= 1
                        if extra_watch_remaining <= 0:
                            logger.info(
                                "Like limit reached; extra reels watched, exiting."
                            )
                            break
                continue
            if (
                reels_watches_limit > 0
                and session_state.totalReelWatched >= reels_watches_limit
            ):
                if not reel_watch_limit_logged:
                    logger.info("Reel watch limit reached; stopping session.")
                    reel_watch_limit_logged = True
                sessions = getattr(configs, "sessions", None)
                if sessions is None:
                    logger.warning("Sessions list unavailable; exiting reels viewer.")
                    self._exit_reel_viewer()
                    self.last_reel_handled = True
                    return True
                stop_bot(self.device, sessions, session_state)
                self.last_reel_handled = True
                return True
            is_ad = self._is_reel_ad_only()
            likes_limit = int(session_state.args.current_likes_limit)
            global_likes_reached = (
                likes_limit > 0 and session_state.totalLikes >= likes_limit
            )
            reel_likes_reached = (
                reels_likes_limit > 0
                and session_state.totalReelLikes >= reels_likes_limit
            )
            likes_limit_reached = global_likes_reached or reel_likes_reached
            if global_likes_reached and not likes_limit_logged:
                logger.info("Like limit reached; skipping reel likes.")
                likes_limit_logged = True
            if reel_likes_reached and not reel_likes_limit_logged:
                logger.info("Reel-like limit reached; skipping reel likes.")
                reel_likes_limit_logged = True
            if likes_limit_reached and extra_watch_remaining is None:
                extra_watch_remaining = max(0, extra_watch_limit)
                if extra_watch_remaining == 0:
                    logger.info(
                        "Like limit reached; extra watch disabled, stopping reels."
                    )
                    break
                if not extra_watch_logged:
                    logger.info(
                        f"Like limit reached; watching {extra_watch_remaining} more reels before exiting."
                    )
                    extra_watch_logged = True

            limits_reached, _, _ = session_state.check_limit(
                limit_type=session_state.Limit.ALL
            )
            if limits_reached:
                logger.info("Session limits reached while in reels; stopping session.")
                sessions = getattr(configs, "sessions", None)
                if sessions is None:
                    logger.warning("Sessions list unavailable; exiting reels viewer.")
                    self._exit_reel_viewer()
                    self.last_reel_handled = True
                    return True
                stop_bot(self.device, sessions, session_state)

            if (
                like_pct
                and not likes_limit_reached
                and not skip_like_for_user
                and (args.reels_like_ads or not is_ad)
                and randint(1, 100) <= like_pct
            ):
                used_doubletap = _reel_like_use_double_tap(doubletap_pct)
                liked = None
                method = None
                if used_doubletap and _double_tap_reel_media(self.device):
                    random_sleep(inf=0.3, sup=0.7, modulable=False)
                    liked = _is_reel_liked(self.device)
                    if not liked:
                        logger.info(
                            "Double-tap did not confirm like; trying heart."
                        )
                        liked = _click_reel_like_button(self.device)
                        if liked:
                            method = "heart"
                    else:
                        method = "double-tap"
                else:
                    liked = _click_reel_like_button(self.device)
                    if liked:
                        method = "heart"
                if liked:
                    session_state.totalLikes += 1
                    session_state.totalReelLikes += 1
                    logger.info(f"Liked reel ({method}).")
                    if storage is not None and username and session_state is not None:
                        storage.add_interacted_user(
                            username,
                            session_id=session_state.id,
                            liked=1,
                            job_name=current_job,
                            target=target,
                        )
                elif liked is None:
                    logger.warning("Reel like could not be confirmed.")
            # Human-ish dwell based on config
            stay_time = dwell_ads if is_ad else dwell_regular
            random_sleep(inf=max(1, stay_time - 1), sup=stay_time + 1, modulable=False)
            session_state.totalWatched += 1
            session_state.totalReelWatched += 1
            if extra_watch_remaining is not None:
                extra_watch_remaining -= 1
                if extra_watch_remaining <= 0:
                    logger.info(
                        "Like limit reached; extra reels watched, exiting."
                    )
                    break
            if (
                reels_watches_limit > 0
                and session_state.totalReelWatched >= reels_watches_limit
            ):
                logger.info("Reel watch limit reached; stopping session.")
                sessions = getattr(configs, "sessions", None)
                if sessions is None:
                    logger.warning("Sessions list unavailable; exiting reels viewer.")
                    self._exit_reel_viewer()
                    self.last_reel_handled = True
                    return True
                stop_bot(self.device, sessions, session_state)
                self.last_reel_handled = True
                return True
            logger.info("Swiping to next reel.")
            UniversalActions(self.device)._swipe_points(
                direction=Direction.UP, delta_y=800
            )
            # Post-swipe pause derived from configured watch time to stay human-like
            swipe_pause = min(max(0.5, stay_time * 0.3), 3)
            random_sleep(inf=swipe_pause * 0.8, sup=swipe_pause * 1.2, modulable=False)
        limits_reached, _, _ = session_state.check_limit(
            limit_type=session_state.Limit.ALL
        )
        if limits_reached:
            logger.info("Session limits reached after reels; stopping session.")
            sessions = getattr(configs, "sessions", None)
            if sessions is None:
                logger.warning("Sessions list unavailable; exiting reels viewer.")
                self._exit_reel_viewer()
                self.last_reel_handled = True
                return True
            stop_bot(self.device, sessions, session_state)
        logger.info("Returning from reels viewer to previous screen.")
        self._exit_reel_viewer()
        self.last_reel_handled = True
        return True

    def _handle_single_image_reel_as_post(
        self,
        session_state,
        storage=None,
        current_job: Optional[str] = None,
        target: Optional[str] = None,
    ) -> bool:
        logger.info("Single-image reel detected; treating as photo post.")
        username = self._get_reel_author_username()
        if not username:
            logger.debug("Reel author not detected; cannot check interacted history.")
        if storage is not None and username:
            if storage.is_user_in_blacklist(username):
                logger.info(f"@{username} is in blacklist. Skip.")
                self._exit_reel_viewer()
                return True
            if current_job not in (None, "feed"):
                interacted, interacted_when = storage.check_user_was_interacted(
                    username
                )
                if interacted:
                    can_reinteract = storage.can_be_reinteract(
                        interacted_when, get_value(args.can_reinteract_after, None, 0)
                    )
                    logger.info(
                        f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                    )
                    if not can_reinteract:
                        self._exit_reel_viewer()
                        return True
        # If already liked, skip any interaction logic and record interaction history.
        liked_state = _is_reel_liked(self.device)
        if liked_state:
            logger.info("Single-image reel already liked; skipping interaction.")
            if storage is not None and username and session_state is not None:
                storage.add_interacted_user(
                    username,
                    session_id=session_state.id,
                    liked=1,
                    job_name=current_job,
                    target=target,
                )
            self._exit_reel_viewer()
            return True
        watch_time = get_value(args.watch_photo_time, None, 0, its_time=True)
        if watch_time is None:
            watch_time = 0
        if watch_time > 0:
            logger.info(f"Watching photo for {watch_time}s.")
            sleep(watch_time)

        interact_pct = get_value(args.interact_percentage, None, 0)
        if not random_choice(interact_pct):
            logger.info("Skip interaction on single-image reel (chance).")
            self._exit_reel_viewer()
            return True

        like_pct = get_value(args.likes_percentage, None, 0)
        likes_limit = 0
        if session_state is not None:
            likes_limit = int(session_state.args.current_likes_limit)
        likes_limit_reached = False
        if session_state is not None and likes_limit > 0:
            likes_limit_reached = session_state.totalLikes >= likes_limit
        if like_pct and not likes_limit_reached and randint(1, 100) <= like_pct:
            liked = _click_reel_like_button(self.device)
            if liked:
                logger.info("Liked single-image reel as photo.")
                if session_state is not None:
                    session_state.totalLikes += 1
                if storage is not None and username and session_state is not None:
                    storage.add_interacted_user(
                        username,
                        session_id=session_state.id,
                        liked=1,
                        job_name=current_job,
                        target=target,
                    )
            elif liked is None:
                logger.warning("Single-image reel like could not be confirmed.")
        self._exit_reel_viewer()
        return True

    def swipe_to_fit_posts(self, swipe: SwipeTo):
        """calculate the right swipe amount necessary to swipe to next post in hashtag post view
        in order to make it available to other plug-ins I cut it in two moves"""
        displayWidth = self.device.get_info()["displayWidth"]
        containers_content = ResourceID.MEDIA_CONTAINER
        containers_gap = ResourceID.GAP_VIEW_AND_FOOTER_SPACE
        suggested_users = ResourceID.NETEGO_CAROUSEL_HEADER

        # move type: half photo
        if swipe == SwipeTo.HALF_PHOTO:
            media = self.device.find(resourceIdMatches=containers_content)
            if not media.exists(Timeout.SHORT):
                logger.info("Media container not found; skipping current post.")
                return
            zoomable_view_container = media.get_bounds()["bottom"]
            ac_exists, _, ac_bottom = PostsViewList(
                self.device
            )._get_action_bar_position()
            if ac_exists and zoomable_view_container < ac_bottom:
                zoomable_view_container += ac_bottom
            self.device.swipe_points(
                displayWidth / 2,
                zoomable_view_container - 5,
                displayWidth / 2,
                zoomable_view_container * 0.5,
            )
        elif swipe == SwipeTo.NEXT_POST:
            logger.info(
                "Scroll down to see next post.", extra={"color": f"{Fore.GREEN}"}
            )
            gap_view_obj = self.device.find(index=-1, resourceIdMatches=containers_gap)
            obj1 = None
            found_gap = False
            for _ in range(3):
                if not gap_view_obj.exists():
                    logger.debug("Can't find the gap obj, scroll down a little more.")
                    PostsViewList(self.device).swipe_to_fit_posts(SwipeTo.HALF_PHOTO)
                    gap_view_obj = self.device.find(resourceIdMatches=containers_gap)
                    if not gap_view_obj.exists():
                        continue
                    else:
                        found_gap = True
                        break
                else:
                    found_gap = True
                    media = self.device.find(resourceIdMatches=containers_content)
                    if not media.exists(Timeout.SHORT):
                        logger.info("Media container missing; scroll generically.")
                        UniversalActions(self.device)._swipe_points(
                            direction=Direction.UP, delta_y=1000
                        )
                        return
                    if (
                        gap_view_obj.get_bounds()["bottom"]
                        < media.get_bounds()["bottom"]
                    ):
                        PostsViewList(self.device).swipe_to_fit_posts(
                            SwipeTo.HALF_PHOTO
                        )
                        continue
                    suggested = self.device.find(resourceIdMatches=suggested_users)
                    if suggested.exists():
                        for _ in range(2):
                            PostsViewList(self.device).swipe_to_fit_posts(
                                SwipeTo.HALF_PHOTO
                            )
                            footer_obj = self.device.find(
                                resourceIdMatches=ResourceID.FOOTER_SPACE
                            )
                            if footer_obj.exists():
                                obj1 = footer_obj.get_bounds()["bottom"]
                                break
                    break
            if not found_gap:
                logger.debug("Gap/footer not found; perform generic scroll.")
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.UP, delta_y=900
                )
                return
            if obj1 is None and gap_view_obj.exists():
                obj1 = gap_view_obj.get_bounds()["bottom"]
            containers_content = self.device.find(resourceIdMatches=containers_content)

            obj2 = (
                (
                    containers_content.get_bounds()["bottom"]
                    + containers_content.get_bounds()["top"]
                )
                * 1
                / 3
            )

            self.device.swipe_points(
                displayWidth / 2,
                obj1 - 5,
                displayWidth / 2,
                obj2 + 5,
            )
            return True

    def _find_likers_container(self):
        universal_actions = UniversalActions(self.device)
        containers_gap = ResourceID.GAP_VIEW_AND_FOOTER_SPACE
        media_container = ResourceID.MEDIA_CONTAINER
        likes = 0
        # If we're in reels, defer to reel handler instead of scrolling for media.
        if self._is_in_reel_viewer():
            self.reel_flag = True
            return False, 0
        for _ in range(4):
            gap_view_obj = self.device.find(resourceIdMatches=containers_gap)
            likes_view = self.device.find(
                index=-1,
                resourceId=ResourceID.ROW_FEED_TEXTVIEW_LIKES,
                className=ClassName.TEXT_VIEW,
            )
            description_view = self.device.find(
                resourceIdMatches=ResourceID.ROW_FEED_COMMENT_TEXTVIEW_LAYOUT
            )
            media = self.device.find(
                resourceIdMatches=media_container,
            )
            media_count = media.count_items()
            logger.debug(f"I can see {media_count} media(s) in this view..")

            if media_count == 0:
                # Nothing detected as media; perform a bigger downward scroll to move to the next post
                universal_actions._swipe_points(Direction.UP, delta_y=900)
                continue

            if media_count > 1 and (
                media.get_bounds()["bottom"]
                < self.device.get_info()["displayHeight"] / 3
            ):
                universal_actions._swipe_points(Direction.DOWN, delta_y=100)
                continue
            if not likes_view.exists():
                if description_view.exists() or gap_view_obj.exists():
                    return False, likes
                else:
                    universal_actions._swipe_points(Direction.DOWN, delta_y=100)
                    continue
            elif media.get_bounds()["bottom"] > likes_view.get_bounds()["bottom"]:
                universal_actions._swipe_points(Direction.DOWN, delta_y=100)
                continue
            logger.debug("Likers container exists!")
            likes = self._get_number_of_likers(likes_view)
            return likes_view.exists(), likes
        return False, 0

    def _get_number_of_likers(self, likes_view):
        likes = 0
        if likes_view.exists():
            likes_view_text = likes_view.get_text().replace(",", "")
            matches_likes = re.search(
                r"(?P<likes>\d+) (?:others|likes)", likes_view_text, re.IGNORECASE
            )
            matches_view = re.search(
                r"(?P<views>\d+) views", likes_view_text, re.IGNORECASE
            )
            if hasattr(matches_likes, "group"):
                likes = int(matches_likes.group("likes"))
                logger.info(
                    f"This post has {likes if 'likes' in likes_view_text else likes + 1} like(s)."
                )
                return likes
            elif hasattr(matches_view, "group"):
                views = int(matches_view.group("views"))
                logger.info(
                    f"I can see only that this post has {views} views(s). It may contain likes.."
                )
                return -1
            else:
                if likes_view_text.endswith("others"):
                    logger.info("This post has more than 1 like.")
                    return -1
                else:
                    logger.info("This post has only 1 like.")
                    likes = 1
                    return likes
        else:
            logger.info("This post has no likes, skip.")
            return likes

    def open_likers_container(self):
        """Open likes container"""
        post_liked_by_a_following = False
        logger.info("Opening post likers.")
        facepil_stub = self.device.find(
            index=-1, resourceId=ResourceID.ROW_FEED_LIKE_COUNT_FACEPILE_STUB
        )

        if facepil_stub.exists():
            logger.debug("Facepile present, pressing on it!")
            facepil_stub.click()
        else:
            random_sleep(1, 2, modulable=False)
            likes_view = self.device.find(
                index=-1,
                resourceId=ResourceID.ROW_FEED_TEXTVIEW_LIKES,
                className=ClassName.TEXT_VIEW,
            )
            if " Liked by" in likes_view.get_text():
                post_liked_by_a_following = True
            elif likes_view.child().count_items() < 2:
                likes_view.click()
                return
            if likes_view.child().exists():
                if post_liked_by_a_following:
                    likes_view.child().click()
                    return
                foil = likes_view.get_bounds()
                hole = likes_view.child().get_bounds()
                try:
                    sq1 = Square(
                        foil["left"],
                        foil["top"],
                        hole["left"],
                        foil["bottom"],
                    ).point()
                    sq2 = Square(
                        hole["left"],
                        foil["top"],
                        hole["right"],
                        hole["top"],
                    ).point()
                    sq3 = Square(
                        hole["left"],
                        hole["bottom"],
                        hole["right"],
                        foil["bottom"],
                    ).point()
                    sq4 = Square(
                        hole["right"],
                        foil["top"],
                        foil["right"],
                        foil["bottom"],
                    ).point()
                except ValueError:
                    logger.debug(f"Point calculation fails: F:{foil} H:{hole}")
                    likes_view.click(Location.RIGHT)
                    return
                sq_list = [sq1, sq2, sq3, sq4]
                available_sq_list = [x for x in sq_list if x == x]
                if available_sq_list:
                    likes_view.click(Location.CUSTOM, coord=choice(available_sq_list))
                else:
                    likes_view.click(Location.RIGHT)
            elif not post_liked_by_a_following:
                likes_view.click(Location.RIGHT)
            else:
                likes_view.click(Location.LEFT)

    def _has_tags(self) -> bool:
        tags_icon = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.INDICATOR_ICON_VIEW)
        )
        self.has_tags = tags_icon.exists()
        return self.has_tags

    @staticmethod
    def _desc_is_sponsored(desc: str) -> bool:
        if not desc:
            return False
        sponsored_txts = [
            "sponsored",
            "gesponsert",
            "pubblicité",
            "publicidad",
            "sponsorisé",
            "advertisement",
        ]
        pattern = r"\b(" + "|".join(map(re.escape, sponsored_txts)) + r")\b"
        return re.search(pattern, desc, re.IGNORECASE) is not None

    def _check_if_last_post(
        self, last_description, current_job
    ) -> Tuple[bool, str, str, bool, bool, bool]:
        """check if that post has been just interacted"""
        universal_actions = UniversalActions(self.device)
        # Mark reel flag if we are in reel viewer so caller can handle it.
        if self._is_in_reel_viewer():
            logger.info("Reel opened instead of a post, handled elsewhere.")
            self.reel_flag = True
            return False, "", "", False, False, False
        username, is_ad, is_hashtag = PostsViewList(self.device)._post_owner(
            current_job, Owner.GET_NAME
        )
        has_tags = self._has_tags()
        # Avoid getting stuck if a Reel opens in full-screen
        reel_retry = 0
        while True:
            if self._is_in_reel_viewer() and reel_retry < 3:
                # Let outer loop handle via maybe_watch_reel_viewer; just signal new post needed.
                logger.info("Reel opened instead of a post, handled elsewhere.")
                return False, "", "", False, False, False

            post_description = self.device.find(
                index=-1,
                resourceIdMatches=ResourceID.ROW_FEED_TEXT,
                textStartsWith=username,
            )
            if not post_description.exists() and post_description.count_items() >= 1:
                text = post_description.get_text()
                post_description = self.device.find(
                    index=-1,
                    resourceIdMatches=ResourceID.ROW_FEED_TEXT,
                    text=text,
                )
            if not post_description.exists():
                # Some feed layouts render descriptions as IgTextLayoutView without a resource-id
                alt_description = self.device.find(
                    classNameMatches=case_insensitive_re("IgTextLayoutView"),
                    textStartsWith=username,
                )
                if not alt_description.exists() and alt_description.count_items() >= 1:
                    text = alt_description.get_text()
                    alt_description = self.device.find(
                        classNameMatches=case_insensitive_re("IgTextLayoutView"),
                        text=text,
                    )
                if alt_description.exists():
                    logger.debug("Description found via IgTextLayoutView.")
                    new_description = alt_description.get_text().upper()
                    if new_description != last_description:
                        return (
                            False,
                            new_description,
                            username,
                            is_ad,
                            is_hashtag,
                            has_tags,
                        )
                    logger.info(
                        "This post has the same description and author as the last one."
                    )
                    return True, new_description, username, is_ad, is_hashtag, has_tags
            if not post_description.exists():
                media, content_desc = self._get_media_container()
                if content_desc:
                    new_description = content_desc.upper()
                    if new_description != last_description:
                        return (
                            False,
                            new_description,
                            username,
                            is_ad,
                            is_hashtag,
                            has_tags,
                        )
                    logger.info(
                        "This post has the same media description and author as the last one."
                    )
                    return True, new_description, username, is_ad, is_hashtag, has_tags
            if post_description.exists():
                logger.debug("Description found!")
                new_description = post_description.get_text().upper()
                if new_description != last_description:
                    return False, new_description, username, is_ad, is_hashtag, has_tags
                logger.info(
                    "This post has the same description and author as the last one."
                )
                return True, new_description, username, is_ad, is_hashtag, has_tags
            else:
                gap_view_obj = self.device.find(resourceId=ResourceID.GAP_VIEW)
                feed_composer = self.device.find(
                    resourceId=ResourceID.FEED_INLINE_COMPOSER_BUTTON_TEXTVIEW
                )
                if gap_view_obj.exists() and gap_view_obj.get_bounds()["bottom"] < (
                    self.device.get_info()["displayHeight"] / 3
                ):
                    universal_actions._swipe_points(
                        direction=Direction.UP, delta_y=400
                    )
                    continue
                row_feed_profile_header = self.device.find(
                    resourceId=ResourceID.ROW_FEED_PROFILE_HEADER
                )
                if row_feed_profile_header.count_items() > 1:
                    logger.info("This post hasn't the description...")
                    return False, "", username, is_ad, is_hashtag, has_tags
                profile_header_is_above = row_feed_profile_header.is_above_this(
                    gap_view_obj if gap_view_obj.exists() else feed_composer
                )
                if profile_header_is_above is not None:
                    if not profile_header_is_above:
                        logger.info("This post hasn't the description...")
                        return False, "", username, is_ad, is_hashtag, has_tags

                logger.debug(
                    f"Can't find the description of {username}'s post, try to swipe a little bit down."
                )
                universal_actions._swipe_points(direction=Direction.UP, delta_y=600)
                reel_retry += 1
                if reel_retry >= 5:
                    logger.info("Skip post after repeated missing description.")
                    return False, "", username, is_ad, is_hashtag, has_tags

    def _if_action_bar_is_over_obj_swipe(self, obj):
        """do a swipe of the amount of the action bar"""
        action_bar_exists, _, action_bar_bottom = PostsViewList(
            self.device
        )._get_action_bar_position()
        if action_bar_exists:
            obj_top = obj.get_bounds()["top"]
            if action_bar_bottom > obj_top:
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.UP, delta_y=action_bar_bottom
                )

    def _get_action_bar_position(self) -> Tuple[bool, int, int]:
        """action bar is overlay, if you press on it, you go back to the first post
        knowing his position is important to avoid it: exists, top, bottom"""
        try:
            action_bar = self.device.find(
                resourceIdMatches=ResourceID.ACTION_BAR_CONTAINER
            )
            if action_bar.exists():
                bounds = action_bar.get_bounds()
                return True, bounds.get("top", 0), bounds.get("bottom", 0)
        except Exception as exc:  # Fallback when action bar is not present in this view
            logger.debug(f"Action bar lookup failed: {exc}")
        return False, 0, 0

    def _refresh_feed(self):
        logger.info("Scroll feed to fetch fresh posts.")
        refresh_pill = self.device.find(resourceId=ResourceID.NEW_FEED_PILL)
        if refresh_pill.exists(Timeout.SHORT):
            refresh_pill.click()
        else:
            # Avoid pull-to-refresh; simply scroll down the feed to see new items
            UniversalActions(self.device)._swipe_points(
                direction=Direction.UP, start_point_y=1500, delta_y=900
            )
        random_sleep(inf=0.5, sup=1.5, modulable=False)

    def _post_owner(self, current_job, mode: Owner, username=None):
        """returns a tuple[var, bool, bool]"""
        is_ad = False
        is_hashtag = False
        if username is None and mode == Owner.GET_NAME and current_job == "feed":
            _, content_desc = self._get_media_container()
            if content_desc:
                media_username = _parse_username_from_tile_desc(content_desc)
                if media_username:
                    is_ad = self._desc_is_sponsored(content_desc)
                    is_hashtag = media_username.startswith("#")
                    return media_username, is_ad, is_hashtag
        if username is None:
            post_owner_obj = self.device.find(
                resourceIdMatches=ResourceID.ROW_FEED_PHOTO_PROFILE_NAME
            )
        else:
            for _ in range(2):
                post_owner_obj = self.device.find(
                    resourceIdMatches=ResourceID.ROW_FEED_PHOTO_PROFILE_NAME,
                    textStartsWith=username,
                )
                notification = self.device.find(
                    resourceIdMatches=ResourceID.NOTIFICATION_MESSAGE
                )
                if not post_owner_obj.exists and notification.exists():
                    logger.warning(
                        "There is a notification there! Please disable them in settings.. We will wait 10 seconds before continue.."
                    )
                    sleep(10)
        post_owner_clickable = False

        for _ in range(3):
            if not post_owner_obj.exists():
                if mode == Owner.OPEN:
                    comment_description = self.device.find(
                        resourceIdMatches=ResourceID.ROW_FEED_COMMENT_TEXTVIEW_LAYOUT,
                        textStartsWith=username,
                    )
                    if (
                        not comment_description.exists()
                        and comment_description.count_items() >= 1
                    ):
                        comment_description = self.device.find(
                            resourceIdMatches=ResourceID.ROW_FEED_COMMENT_TEXTVIEW_LAYOUT,
                            text=comment_description.get_text(),
                        )

                    if comment_description.exists():
                        logger.info("Open post owner from description.")
                        comment_description.child().click()
                        return True, is_ad, is_hashtag
                UniversalActions(self.device)._swipe_points(direction=Direction.UP)
                post_owner_obj = self.device.find(
                    resourceIdMatches=ResourceID.ROW_FEED_PHOTO_PROFILE_NAME,
                )
            else:
                post_owner_clickable = True
                break

        if not post_owner_clickable:
            logger.info("Can't find the owner name, skip.")
            return False, is_ad, is_hashtag
        if mode == Owner.OPEN:
            logger.info("Open post owner.")
            PostsViewList(self.device)._if_action_bar_is_over_obj_swipe(post_owner_obj)
            post_owner_obj.click()
            return True, is_ad, is_hashtag
        elif mode == Owner.GET_NAME:
            if current_job == "feed":
                is_ad, is_hashtag, username = PostsViewList(
                    self.device
                )._check_if_ad_or_hashtag(post_owner_obj)
            if username is None:
                username = (
                    post_owner_obj.get_text().replace("•", "").strip().split(" ", 1)[0]
                )
            return username, is_ad, is_hashtag

        elif mode == Owner.GET_POSITION:
            return post_owner_obj.get_bounds(), is_ad
        else:
            return None, is_ad, is_hashtag

    def _get_post_owner_name(self):
        return self.device.find(
            resourceIdMatches=ResourceID.ROW_FEED_PHOTO_PROFILE_NAME
        ).get_text()

    def _get_media_container(self):
        media = self.device.find(resourceIdMatches=ResourceID.CAROUSEL_AND_MEDIA_GROUP)
        content_desc = media.get_desc() if media.exists() else None
        return media, content_desc

    @staticmethod
    def detect_media_type(content_desc) -> Tuple[Optional[MediaType], Optional[int]]:
        """
        Detect the nature and amount of a media
        :return: MediaType and count
        :rtype: MediaType, int
        """
        obj_count = 1
        if content_desc is None:
            return None, None
        if re.match(r"^,|^\s*$", content_desc, re.IGNORECASE):
            logger.info(
                "That media is missing content description, so I don't know which kind of video it is."
            )
            media_type = MediaType.UNKNOWN
        elif re.match(r"^Photo|^Hidden Photo", content_desc, re.IGNORECASE):
            logger.info("It's a photo.")
            media_type = MediaType.PHOTO
        elif re.match(r"^Video|^Hidden Video", content_desc, re.IGNORECASE):
            logger.info("It's a video.")
            media_type = MediaType.VIDEO
        elif re.match(r"^IGTV", content_desc, re.IGNORECASE):
            logger.info("It's a IGTV.")
            media_type = MediaType.IGTV
        elif re.match(r"^Reel", content_desc, re.IGNORECASE):
            logger.info("It's a Reel.")
            media_type = MediaType.REEL
        else:
            carousel_obj = re.finditer(
                r"((?P<photo>\d+) photo)|((?P<video>\d+) video)",
                content_desc,
                re.IGNORECASE,
            )
            n_photos = 0
            n_videos = 0
            for match in carousel_obj:
                if match.group("photo"):
                    n_photos = int(match.group("photo"))
                if match.group("video"):
                    n_videos = int(match.group("video"))
            logger.info(
                f"It's a carousel with {n_photos} photo(s) and {n_videos} video(s)."
            )
            obj_count = n_photos + n_videos
            media_type = MediaType.CAROUSEL
        return media_type, obj_count

    def _like_in_post_view(
        self,
        mode: LikeMode,
        skip_media_check: bool = False,
        already_watched: bool = False,
    ):
        post_view_list = PostsViewList(self.device)
        opened_post_view = OpenedPostView(self.device)
        if skip_media_check:
            return
        media, content_desc = self._get_media_container()
        if content_desc is None:
            return
        if not already_watched:
            media_type, _ = post_view_list.detect_media_type(content_desc)
            opened_post_view.watch_media(media_type)
        if mode == LikeMode.DOUBLE_CLICK:
            if media_type in (MediaType.CAROUSEL, MediaType.PHOTO):
                logger.info("Double click on post.")
                _, _, action_bar_bottom = PostsViewList(
                    self.device
                )._get_action_bar_position()
                media.double_click(obj_over=action_bar_bottom)
            else:
                self._like_in_post_view(
                    mode=LikeMode.SINGLE_CLICK, skip_media_check=True
                )
        elif mode == LikeMode.SINGLE_CLICK:
            like_button_exists, _ = self._find_likers_container()
            if like_button_exists:
                logger.info("Clicking on the little heart ❤️.")
                self.device.find(
                    resourceIdMatches=ResourceID.ROW_FEED_BUTTON_LIKE
                ).click()

    def _follow_in_post_view(self):
        logger.info("Follow blogger in place.")
        self.device.find(resourceIdMatches=ResourceID.BUTTON).click()

    def _comment_in_post_view(self):
        logger.info("Open comments of post.")
        self.device.find(resourceIdMatches=ResourceID.ROW_FEED_BUTTON_COMMENT).click()

    def _check_if_liked(self):
        logger.debug("Check if like succeeded in post view.")
        bnt_like_obj = self.device.find(
            resourceIdMatches=ResourceID.ROW_FEED_BUTTON_LIKE
        )
        if bnt_like_obj.exists():
            STR = "Liked"
            if self.device.find(descriptionMatches=case_insensitive_re(STR)).exists():
                logger.debug("Like is present.")
                return True
            else:
                logger.debug("Like is not present.")
                return False
        else:
            UniversalActions(self.device)._swipe_points(
                direction=Direction.DOWN, delta_y=100
            )
            return PostsViewList(self.device)._check_if_liked()

    def _check_if_ad_or_hashtag(
        self, post_owner_obj
    ) -> Tuple[bool, bool, Optional[str]]:
        is_hashtag = False
        is_ad = False
        logger.debug("Checking if it's an AD or an hashtag..")
        owner_name = post_owner_obj.get_text() or post_owner_obj.get_desc() or ""
        if not owner_name:
            logger.info("Can't find the owner name, need to use OCR.")
            try:
                import pytesseract as pt

                owner_name = self.get_text_from_screen(pt, post_owner_obj)
            except ImportError:
                logger.error(
                    "You need to install pytesseract (the wrapper: pip install pytesseract) in order to use OCR feature."
                )
            except pt.TesseractNotFoundError:
                logger.error(
                    "You need to install Tesseract (the engine: it depends on your system) in order to use OCR feature."
                )
        if owner_name.startswith("#"):
            is_hashtag = True
            logger.debug("Looks like an hashtag, skip.")
        # Detect ads via adjacent label, dedicated ad badge, or global Sponsored markers
        sponsored_txts = [
            "sponsored",
            "gesponsert",
            "pubblicité",
            "publicidad",
            "sponsorisé",
            "advertisement",
            "ad",
        ]
        # IG embeds a dedicated ad root; detect it early
        ad_root = self.device.find(
            resourceIdMatches=ResourceID.SPONSORED_CONTENT_SERVER_RENDERED_ROOT
        )
        if ad_root.exists(Timeout.TINY):
            logger.debug("Sponsored root detected, mark as AD.")
            is_ad = True
        if not is_ad:
            ad_badge = post_owner_obj.sibling(resourceId=ResourceID.AD_BADGE)
            if ad_badge.exists(Timeout.TINY):
                logger.debug("Ad badge under username detected, mark as AD.")
                is_ad = True
        if not is_ad:
            ad_label = post_owner_obj.sibling(resourceId=ResourceID.SECONDARY_LABEL)
            if ad_label.exists(Timeout.TINY):
                label_text = (
                    ad_label.get_text(error=False) or ad_label.get_desc() or ""
                ).strip()
                if label_text and self._desc_is_sponsored(label_text):
                    logger.debug("Secondary label indicates ad, mark as AD.")
                    is_ad = True
        if is_hashtag:
            owner_name = owner_name.split("•")[0].strip()

        return is_ad, is_hashtag, owner_name

    def get_text_from_screen(self, pt, obj) -> Optional[str]:

        if platform.system() == "Windows":
            pt.pytesseract.tesseract_cmd = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )

        screenshot = self.device.screenshot()
        bounds = obj.ui_info().get("visibleBounds", None)
        if bounds is None:
            logger.info("Can't find the bounds of the object.")
            return None
        screenshot_cropped = screenshot.crop(
            [
                bounds.get("left"),
                bounds.get("top"),
                bounds.get("right"),
                bounds.get("bottom"),
            ]
        )
        return pt.image_to_string(screenshot_cropped).split(" ")[0].rstrip()


class LanguageView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def setLanguage(self, language: str):
        logger.debug(f"Set language to {language}.")
        search_edit_text = self.device.find(
            resourceId=ResourceID.SEARCH,
            className=ClassName.EDIT_TEXT,
        )
        search_edit_text.set_text(language, Mode.PASTE if args.dont_type else Mode.TYPE)

        list_view = self.device.find(
            resourceId=ResourceID.LANGUAGE_LIST_LOCALE,
            className=ClassName.LIST_VIEW,
        )
        first_item = list_view.child(index=0)
        first_item.click()
        random_sleep()


class AccountView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToLanguage(self):
        logger.debug("Navigate to Language")
        button = self.device.find(
            className=ClassName.BUTTON,
            index=6,
        )
        if button.exists():
            button.click()
            return LanguageView(self.device)
        else:
            logger.error("Not able to set your app in English! Do it by yourself!")
            exit(0)

    def navigate_to_main_account(self):
        logger.debug("Navigating to main account...")
        profile_view = ProfileView(self.device)
        profile_view.click_on_avatar()
        if not profile_view.wait_profile_header_loaded():
            profile_view.click_on_avatar()
            profile_view.wait_profile_header_loaded()

    def changeToUsername(self, username: str):
        action_bar = ProfileView._getActionBarTitleBtn(self)
        if action_bar is not None:
            current_profile_name = action_bar.get_text()
            # in private accounts there is little lock which is codec as two spaces (should be \u1F512)
            if current_profile_name.strip().upper() == username.upper():
                logger.info(
                    f"You are already logged as {username}!",
                    extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
                )
                return True
            logger.debug(f"You're logged as {current_profile_name.strip()}")
            selector = self.device.find(resourceId=ResourceID.ACTION_BAR_TITLE_CHEVRON)
            selector.click()
            if self._find_username(username):
                if action_bar is not None:
                    current_profile_name = action_bar.get_text()
                    if current_profile_name.strip().upper() == username.upper():
                        return True
                else:
                    logger.error(
                        "Cannot find action bar (where you select your account)!"
                    )
        return False

    def _find_username(self, username, has_scrolled=False):
        list_view = self.device.find(resourceId=ResourceID.LIST)
        username_obj = self.device.find(
            resourceIdMatches=f"{ResourceID.ROW_USER_TEXTVIEW}|{ResourceID.USERNAME_TEXTVIEW}",
            textMatches=case_insensitive_re(username),
        )
        if username_obj.exists(Timeout.SHORT):
            logger.info(
                f"Switching to {username}...",
                extra={"color": f"{Style.BRIGHT}{Fore.BLUE}"},
            )
            username_obj.click()
            return True
        elif list_view.is_scrollable() and not has_scrolled:
            logger.debug("User list is scrollable.")
            list_view.scroll(Direction.DOWN)
            self._find_username(username, has_scrolled=True)
        return False

    def refresh_account(self):
        selectors = [
            dict(resourceIdMatches=ResourceID.PROFILE_HEADER_METRICS_FULL_WIDTH),
            dict(resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_POST_CONTAINER),
        ]
        textview = None
        for sel in selectors:
            textview = self.device.find(**sel)
            if textview.exists(Timeout.SHORT):
                break

        universal_actions = UniversalActions(self.device)
        if textview and textview.exists(Timeout.SHORT):
            logger.info("Refresh account...")
            universal_actions._swipe_points(
                direction=Direction.DOWN,
                start_point_y=textview.get_bounds()["bottom"],
                delta_y=280,
            )
            random_sleep(modulable=False)
        # Ensure header still visible; fallback scroll if not
        header_visible = False
        for sel in selectors:
            if self.device.find(**sel).exists(Timeout.SHORT):
                header_visible = True
                break
        if not header_visible:
            logger.debug(
                "Can't see Posts/Followers/Following after refresh, nudging view to reveal header."
            )
            universal_actions._swipe_points(Direction.UP)


class SettingsView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToAccount(self):
        logger.debug("Navigate to Account")
        button = self.device.find(
            className=ClassName.BUTTON,
            index=5,
        )
        if button.exists():
            button.click()
            return AccountView(self.device)
        else:
            logger.error("Not able to set your app in English! Do it by yourself!")
            exit(2)


class OptionsView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def navigateToSettings(self):
        logger.debug("Navigate to Settings")
        button = self.device.find(
            resourceId=ResourceID.MENU_OPTION_TEXT,
            className=ClassName.TEXT_VIEW,
        )
        if button.exists():
            button.click()
            return SettingsView(self.device)
        else:
            logger.error("Not able to set your app in English! Do it by yourself!")
            exit(0)


class OpenedPostView:
    def __init__(self, device: DeviceFacade):
        self.device = device
        self.has_tags = False

    def _get_post_like_button(self) -> Optional[DeviceFacade.View]:
        post_media_view = self.device.find(resourceIdMatches=ResourceID.MEDIA_CONTAINER)
        if post_media_view.exists(Timeout.MEDIUM):
            attempt = 0
            while True:
                like_button = post_media_view.down(
                    resourceIdMatches=ResourceID.ROW_FEED_BUTTON_LIKE
                )
                if like_button.viewV2 is not None or attempt == 3:
                    return like_button if like_button.exists() else None
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.DOWN, delta_y=100
                )
                attempt += 1
        return None

    def _is_post_liked(self) -> Tuple[Optional[bool], Optional[DeviceFacade.View]]:
        """
        Check if post is liked
        :return: post is liked or not
        :rtype: bool
        """
        like_btn_view = self._get_post_like_button()
        if not like_btn_view:
            return False, None

        return like_btn_view.get_selected(), like_btn_view

    def like_post(self) -> bool:
        """
        Like the post with a double click and check if it's liked
        :return: post has been liked
        :rtype: bool
        """
        post_media_view = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.MEDIA_CONTAINER)
        )
        liked = False
        if post_media_view.exists():
            logger.info("Liking post.")
            if self.has_tags:
                logger.info(
                    "Post has tags, better going with a single click on the little heart ❤️."
                )
                like_button = self._get_post_like_button()
                if like_button is not None:
                    like_button.click()
                    liked, _ = self._is_post_liked()
                else:
                    logger.warning("Can't find the like button object!")
            else:
                post_media_view.double_click()
                liked, like_button = self._is_post_liked()
                if not liked and like_button is not None:
                    logger.info("Double click failed, clicking on the little heart ❤️.")
                    like_button.click()
                    liked, _ = self._is_post_liked()
        return liked

    def like_comments(
        self, probability: int, max_likes: int, sort_preference: Optional[str] = None
    ) -> int:
        """
        Open the comment sheet, optionally change sort, and like a few comments.
        """
        if probability <= 0 or max_likes <= 0:
            return 0
        logger.info("Opening comments to like.")
        comment_button = self.device.find(
            resourceIdMatches=ResourceID.ROW_FEED_BUTTON_COMMENT
        )
        if not comment_button.exists():
            comment_button = self.device.find(
                descriptionMatches=case_insensitive_re("comment")
            )
        if not comment_button.exists():
            logger.warning("Cannot find comment button.")
            return 0
        comment_button.click()
        UniversalActions.detect_block(self.device)
        random_sleep(inf=1, sup=2, modulable=False)

        if sort_preference:
            sort_button = self.device.find(
                textMatches=case_insensitive_re(
                    ["For you", "Top", "Newest", "Most relevant", "Following"]
                )
            )
            if sort_button.exists(Timeout.SHORT):
                current_label = sort_button.get_text()
                if current_label and sort_preference.lower() not in current_label.lower():
                    sort_button.click()
                    option = self.device.find(
                        textMatches=case_insensitive_re(sort_preference)
                    )
                    if option.exists(Timeout.SHORT):
                        option.click()
                        random_sleep(inf=1, sup=2, modulable=False)

        liked = 0
        attempts = 0
        comment_list = self.device.find(resourceIdMatches=ResourceID.RECYCLER_VIEW)
        like_desc_regex = case_insensitive_re(["tap to like comment", "like comment"])
        while liked < max_likes and attempts < 5:
            like_selector = self.device.find(descriptionMatches=like_desc_regex)
            count = like_selector.count_items()
            for idx in range(count):
                like_btn = self.device.find(
                    index=idx, descriptionMatches=like_desc_regex
                )
                if not like_btn.exists():
                    continue
                try:
                    if like_btn.get_property("selected"):
                        continue
                except Exception:
                    pass
                if randint(1, 100) > probability:
                    continue
                like_btn.click()
                UniversalActions.detect_block(self.device)
                liked += 1
                random_sleep(inf=1, sup=2, modulable=False)
                if liked >= max_likes:
                    break
            if liked >= max_likes:
                break
            if comment_list.exists():
                comment_list.scroll(Direction.DOWN)
            else:
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.UP, delta_y=600
                )
            attempts += 1
            random_sleep(inf=1, sup=2, modulable=False)
        self.device.back()
        return liked

    def start_video(self) -> bool:
        """
        Press on play button if present
        :return: has play button been pressed
        :rtype: bool
        """
        play_button = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.VIEW_PLAY_BUTTON)
        )
        if play_button.exists(Timeout.TINY):
            logger.debug("Pressing on play button.")
            play_button.click()
            return True
        return False

    def open_video(self) -> bool:
        """
        Open video in full-screen mode
        :return: video in full-screen mode
        :rtype: bool
        """
        post_media_view = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.MEDIA_CONTAINER)
        )
        in_fullscreen = False
        if post_media_view.exists():
            logger.info("Going in full screen.")
            post_media_view.click()
            in_fullscreen, _ = self._is_video_in_fullscreen()
        return in_fullscreen

    def watch_media(self, media_type: MediaType) -> None:
        """
        Watch media for the amount of time specified in config
        :return: None
        :rtype: None
        """
        if (
            media_type
            in (MediaType.IGTV, MediaType.REEL, MediaType.VIDEO, MediaType.UNKNOWN)
            and args.watch_video_time != "0"
        ):
            in_fullscreen, _ = self._is_video_in_fullscreen()
            time_left = self._get_video_time_left()
            watching_time = get_value(
                args.watch_video_time, name=None, default=0, its_time=True
            )
            if time_left > 0 and media_type != MediaType.REEL and in_fullscreen:
                logger.info(f"This video is about {time_left}s long.")
                # hardcoded 5 seconds, so we have the time to doing everything without going to the next video, hopefully
                watching_time = min(
                    watching_time,
                    time_left - 5,
                )
            logger.info(
                f"Watching video for {watching_time if watching_time > 0 else 'few '}s."
            )

        elif (
            media_type in (MediaType.CAROUSEL, MediaType.PHOTO)
            and args.watch_photo_time != "0"
        ):
            self._has_tags()
            watching_time = get_value(
                args.watch_photo_time, "Watching photo for {}s.", 0, its_time=True
            )
        else:
            return None
        if watching_time > 0:
            sleep(watching_time)

    def _get_video_time_left(self) -> int:
        timer = self.device.find(resourceId=ResourceID.TIMER)
        if timer.exists():
            raw_time = timer.get_text().split(":")
            try:
                return int(raw_time[0]) * 60 + int(raw_time[1])
            except (IndexError, ValueError):
                return 0
        return 0

    def _is_video_in_fullscreen(self) -> Tuple[bool, DeviceFacade.View]:
        """
        Check if video is in full-screen mode
        """
        video_container = self.device.find(
            resourceIdMatches=case_insensitive_re(
                ResourceID.VIDEO_CONTAINER_AND_CLIPS_VIDEO_CONTAINER
            )
        )
        return video_container.exists(), video_container

    def _is_video_liked(self) -> Tuple[Optional[bool], Optional[DeviceFacade.View]]:
        """
        Check if video has been liked
        """
        like_button = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.LIKE_BUTTON)
        )
        if like_button.exists():
            return like_button.get_selected(), like_button
        return False, None

    def _has_tags(self) -> bool:
        tags_icon = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.INDICATOR_ICON_VIEW)
        )
        self.has_tags = tags_icon.exists()
        return self.has_tags

    def like_video(self) -> bool:
        """
        Like the video with a double click and check if it's liked
        :return: video has been liked
        :rtype: bool
        """
        sidebar = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.UFI_STACK)
        )
        liked = False
        full_screen, obj = self._is_video_in_fullscreen()
        if full_screen:
            logger.info("Liking video.")
            obj.double_click()
            UniversalActions.detect_block(self.device)
            if not sidebar.exists():
                logger.debug("Showing sidebar...")
                obj.click()
            liked, like_button = self._is_video_liked()
            if not liked:
                logger.info("Double click failed, clicking on the little heart ❤️.")
                if like_button is not None:
                    like_button.click()
                    UniversalActions.detect_block(self.device)
                else:
                    logger.error("We are seeing another video.")
                liked, _ = self._is_video_liked()
        return liked

    def _getListViewLikers(self):
        for _ in range(2):
            obj = self.device.find(resourceId=ResourceID.LIST)
            if obj.exists(Timeout.LONG):
                return obj
            logger.debug("Can't find likers list, try again..")
        logger.error("Can't load likers list..")
        return None

    def _getUserContainer(self):
        obj = self.device.find(
            resourceIdMatches=ResourceID.USER_LIST_CONTAINER,
        )
        return obj if obj.exists(Timeout.LONG) else None

    def _getUserName(self, container):
        return container.child(
            resourceId=ResourceID.ROW_USER_PRIMARY_NAME,
        )

    def _isFollowing(self, container):
        text = container.child(
            resourceId=ResourceID.BUTTON,
            classNameMatches=ClassName.BUTTON_OR_TEXTVIEW_REGEX,
        )
        if not isinstance(text, str):
            text = text.get_text() if text.exists() else ""
        return text in ["Following", "Requested"]


class PostsGridView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def scrollDown(self):
        coordinator_layout = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.COORDINATOR_ROOT_LAYOUT)
        )
        if coordinator_layout.exists():
            coordinator_layout.scroll(Direction.DOWN)
            return True

        return False

    def _get_post_view(self):
        return self.device.find(resourceIdMatches=case_insensitive_re(ResourceID.LIST))

    def navigateToPost(self, row, col):
        post_list_view = self._get_post_view()
        post_list_view.wait(Timeout.MEDIUM)
        OFFSET = 1  # row with post starts from index 1
        row_view = post_list_view.child(index=row + OFFSET)
        if not row_view.exists():
            return None, None, None
        post_view = row_view.child(index=col)
        if not post_view.exists():
            return None, None, None
        content_desc = post_view.ui_info()["contentDescription"]
        media_type, obj_count = PostsViewList.detect_media_type(content_desc)
        post_view.click()

        return OpenedPostView(self.device), media_type, obj_count


class ProfileView(ActionBarView):
    def __init__(self, device: DeviceFacade, is_own_profile=False):
        super().__init__(device)
        self.device = device
        self.is_own_profile = is_own_profile

    def navigateToOptions(self):
        logger.debug("Navigate to Options")
        button = self.action_bar.child(index=2)
        button.click()

        return OptionsView(self.device)

    def _getActionBarTitleBtn(self, watching_stories=False):
        bar = case_insensitive_re(
            [
                ResourceID.TITLE_VIEW,
                ResourceID.ACTION_BAR_TITLE,
                ResourceID.ACTION_BAR_LARGE_TITLE,
                ResourceID.ACTION_BAR_TEXTVIEW_TITLE,
                ResourceID.ACTION_BAR_TITLE_AUTO_SIZE,
                ResourceID.ACTION_BAR_LARGE_TITLE_AUTO_SIZE,
            ]
        )
        action_bar = self.device.find(
            resourceIdMatches=bar,
        )
        if not watching_stories and action_bar.exists(Timeout.LONG) or watching_stories:
            return action_bar
        # Fallback: look for profile header username/full name when action bar is missing
        header_name = self.device.find(
            resourceIdMatches=case_insensitive_re(
                f"{ResourceID.PROFILE_HEADER_FULL_NAME}|{ResourceID.USERNAME_TEXTVIEW}"
            )
        )
        if header_name.exists(Timeout.MEDIUM):
            return header_name
        # Last resort: try tab bar profile badge
        tab_badge = self.device.find(resourceIdMatches=ResourceID.TAB_AVATAR)
        if tab_badge.exists(Timeout.SHORT):
            tab_badge.click()
            random_sleep(0.5, 1.0, modulable=False)
            return self.device.find(resourceIdMatches=bar)
        logger.error(
            "Unable to find action bar or header username! (The element with the username at top)"
        )
        return None

    def _getSomeText(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get label strings from profile header for language check."""
        label_selectors = {
            "post": [
                dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_POST_COUNT_LABEL),
            ],
            "followers": [
                dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWERS_LABEL),
            ],
            "following": [
                dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWING_LABEL),
            ],
        }
        # Legacy fallback: use count text if labels missing
        count_selectors = {
            "post": [
                dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_POST_COUNT_VALUE),
                dict(resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_POST_COUNT),
            ],
            "followers": [
                dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWERS_VALUE),
                dict(resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWERS_COUNT),
            ],
            "following": [
                dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWING_VALUE),
                dict(resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWING_COUNT),
            ],
        }

        texts = {"post": None, "followers": None, "following": None}

        # Try labels first
        for key, options in label_selectors.items():
            for sel in options:
                view = self.device.find(**sel)
                if view.exists(Timeout.MEDIUM):
                    t = view.get_text()
                    if t:
                        texts[key] = t
                        break

        # Fallback to counts if any label missing
        for key in texts:
            if texts[key] is None:
                for sel in count_selectors[key]:
                    view = self.device.find(**sel)
                    if view.exists(Timeout.MEDIUM):
                        t = view.get_text()
                        if t:
                            texts[key] = t
                            break

        if any(v is None for v in texts.values()):
            logger.warning(
                "Can't get post/followers/following text for check the language! Save a crash to understand the reason."
            )
            save_crash(self.device)

        return tuple(t.casefold() if t else None for t in texts.values())

    def _new_ui_profile_button(self) -> bool:
        found = False
        buttons = self.device.find(className=ResourceID.BUTTON)
        for button in buttons:
            if button.get_desc() == "Profile":
                button.click()
                found = True
                break
        return found

    def _old_ui_profile_button(self) -> bool:
        """Try the legacy bottom-tab avatar; fall back to tab content-desc.

        On some IG builds/uiautomator2 combos, querying a missing selector raises
        a JsonRpcError instead of returning an object with exists()==False. That
        would previously crash the session before we could try other fallbacks."""
        try:
            obj = self.device.find(resourceIdMatches=ResourceID.TAB_AVATAR)
            if obj.exists(Timeout.MEDIUM):
                obj.click()
                return True
        except DeviceFacade.JsonRpcError as e:
            logger.debug(f"tab_avatar selector failed: {e}")

        # Newer UI exposes the profile tab with content-desc "Profile"
        alt = self.device.find(
            classNameMatches=ClassName.BUTTON_OR_FRAME_LAYOUT_REGEX,
            descriptionMatches=case_insensitive_re(TabBarText.PROFILE_CONTENT_DESC),
        )
        if alt.exists(Timeout.MEDIUM):
            alt.click()
            return True

        return False

    def click_on_avatar(self):
        attempts = 0
        while attempts < 5:
            if self._new_ui_profile_button():
                return
            if self._old_ui_profile_button():
                return
            self.device.back()
            attempts += 1
        logger.warning("Unable to find profile avatar from current screen, using tab bar fallback.")
        TabBarView(self.device).navigateToProfile()

    def wait_profile_header_loaded(self, retries: int = 3) -> bool:
        """Wait until any known profile metric is visible before reading counts."""
        selectors = [
            dict(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWERS_VALUE
                ),
                className=ClassName.TEXT_VIEW,
            ),
            dict(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWERS_COUNT
                ),
                className=ClassName.TEXT_VIEW,
            ),
        ]
        for attempt in range(retries):
            for sel in selectors:
                view = self.device.find(**sel)
                if view.exists(Timeout.LONG):
                    return True
            UniversalActions.close_keyboard(self.device)
            random_sleep(1, 2, modulable=False)
        logger.error("Profile header metrics not found after retries.")
        return False

    def getFollowButton(self):
        button_regex = f"{ClassName.BUTTON}|{ClassName.TEXT_VIEW}"
        following_regex_all = "^following|^requested|^follow back|^follow"
        following_or_follow_back_button = self.device.find(
            classNameMatches=button_regex,
            clickable=True,
            textMatches=case_insensitive_re(following_regex_all),
        )
        if following_or_follow_back_button.exists(Timeout.MEDIUM):
            button_text = following_or_follow_back_button.get_text().casefold()
            if button_text in ["following", "requested"]:
                button_status = FollowStatus.FOLLOWING
            elif button_text == "follow back":
                button_status = FollowStatus.FOLLOW_BACK
            else:
                button_status = FollowStatus.FOLLOW
            return following_or_follow_back_button, button_status
        else:
            logger.warning(
                "The follow button doesn't exist! Maybe the profile is not loaded!"
            )
            return None, FollowStatus.NONE

    def getUsername(self, watching_stories=False):
        action_bar = self._getActionBarTitleBtn(watching_stories)
        if action_bar is not None:
            return action_bar.get_text(error=not watching_stories).strip()
        # If we're not on a profile screen (e.g., search results), avoid noisy errors.
        try:
            if self.device.find(
                resourceIdMatches=case_insensitive_re(
                    f"{ResourceID.ACTION_BAR_SEARCH_EDIT_TEXT}|{ResourceID.SEARCH_TAB_BAR_LAYOUT}"
                )
            ).exists(Timeout.TINY):
                return None
        except Exception:
            pass
        # Fallback to profile header username/full name
        header_username = self.device.find(
            resourceIdMatches=case_insensitive_re(
                f"{ResourceID.PROFILE_HEADER_FULL_NAME}|{ResourceID.USERNAME_TEXTVIEW}"
            )
        )
        if header_username.exists(Timeout.SHORT):
            return header_username.get_text().strip()
        if not watching_stories:
            logger.error("Cannot get username.")
        return None

    def getLinkInBio(self):
        obj = self.device.find(resourceIdMatches=ResourceID.PROFILE_HEADER_WEBSITE)
        if obj.exists():
            website = obj.get_text()
            return website if website != "" else None
        return None

    def getMutualFriends(self) -> int:
        logger.debug("Looking for mutual friends tab.")
        follow_context = self.device.find(
            resourceIdMatches=ResourceID.PROFILE_HEADER_FOLLOW_CONTEXT_TEXT
        )
        if follow_context.exists():
            text = follow_context.get_text()
            mutual_friends = re.finditer(
                r"((?P<others>\s\d+\s)|(?P<extra>,))",
                text,
                re.IGNORECASE,
            )
            n_others = 0
            n_extra = 0
            for match in mutual_friends:
                if match.group("others"):
                    n_others = int(match.group("others"))
                if match.group("extra"):
                    n_extra = 2
            if n_others != 0:
                mutual_friends = n_others + n_extra if n_extra != 0 else n_others + 1
            else:
                mutual_friends = n_extra if n_extra != 0 else 1
        else:
            mutual_friends = 0
        return mutual_friends

    def _parseCounter(self, raw_text: str) -> Optional[int]:
        multiplier = 1
        regex = r"(?!(K|M|\.))\D+"
        subst = "."
        text = re.sub(regex, subst, raw_text)
        if "K" in text:
            value = float(text.replace("K", ""))
            multiplier = 1_000
        elif "M" in text:
            value = float(text.replace("M", ""))
            multiplier = 1_000_000
        else:
            try:
                value = int(text.replace(".", ""))
            except ValueError:
                logger.error(f"Cannot parse {repr(raw_text)}.")
                return None
        return int(value * multiplier)

    def _getFollowersTextView(self):
        # Newer IG builds (410+) use *familiar* ids; older builds keep row_profile_header_*
        selectors = [
            dict(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWERS_VALUE
                ),
                className=ClassName.TEXT_VIEW,
            ),
            dict(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWERS_COUNT
                ),
                className=ClassName.TEXT_VIEW,
            ),
        ]
        for sel in selectors:
            view = self.device.find(**sel)
            view.wait(Timeout.MEDIUM)
            if view.exists():
                return view
        # return last tried to keep type stable
        return view

    def getFollowersCount(self) -> Optional[int]:
        followers = None
        followers_text_view = self._getFollowersTextView()
        if followers_text_view.exists():
            followers_text = followers_text_view.get_text()
            if followers_text:
                followers = self._parseCounter(followers_text)
            else:
                logger.error("Cannot get followers count text.")
        else:
            logger.error("Cannot find followers count view.")

        return followers

    def _getFollowingTextView(self):
        selectors = [
            dict(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWING_VALUE
                ),
                className=ClassName.TEXT_VIEW,
            ),
            dict(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWING_COUNT
                ),
                className=ClassName.TEXT_VIEW,
            ),
        ]
        for sel in selectors:
            view = self.device.find(**sel)
            view.wait(Timeout.MEDIUM)
            if view.exists():
                return view
        return view

    def getFollowingCount(self) -> Optional[int]:
        following = None
        following_text_view = self._getFollowingTextView()
        if following_text_view.exists(Timeout.MEDIUM):
            following_text = following_text_view.get_text()
            if following_text:
                following = self._parseCounter(following_text)
            else:
                logger.error("Cannot get following count text.")
        else:
            logger.error("Cannot find following count view.")

        return following

    def getPostsCount(self) -> int:
        # Ensure header loaded
        self.wait_profile_header_loaded()
        selectors = [
            dict(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.PROFILE_HEADER_FAMILIAR_POST_COUNT_VALUE
                )
            ),
            dict(
                resourceIdMatches=case_insensitive_re(
                    ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_POST_COUNT
                )
            ),
        ]
        post_count_view = None
        for sel in selectors:
            post_count_view = self.device.find(**sel)
            if post_count_view.exists(Timeout.MEDIUM):
                break
        if post_count_view.exists(Timeout.LONG):
            count = post_count_view.get_text()
            if count is not None:
                return self._parseCounter(count)
        logger.error("Cannot get posts count text.")
        return None

    def count_photo_in_view(self) -> Tuple[int, int]:
        """return rows filled and the number of post in the last row"""
        views = f"({ClassName.RECYCLER_VIEW}|{ClassName.VIEW})"
        grid_post = self.device.find(
            classNameMatches=views, resourceIdMatches=ResourceID.LIST
        )
        if not grid_post.exists(Timeout.MEDIUM):
            return 0, 0
        for i in range(2, 6):
            lin_layout = grid_post.child(index=i, className=ClassName.LINEAR_LAYOUT)
            if i == 5 or not lin_layout.exists():
                last_index = i - 1
                last_lin_layout = grid_post.child(index=last_index)
                for n in range(1, 4):
                    if n == 3 or not last_lin_layout.child(index=n).exists():
                        if n == 3:
                            return last_index, 0
                        else:
                            return last_index - 1, n

    def getProfileInfo(self):
        username = self.getUsername()
        posts = self.getPostsCount()
        followers = self.getFollowersCount()
        following = self.getFollowingCount()

        return username, posts, followers, following

    def getProfileBiography(self) -> str:
        biography = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.PROFILE_HEADER_BIO_TEXT),
            className=ClassName.TEXT_VIEW,
        )
        if biography.exists():
            biography_text = biography.get_text()
            # If the biography is very long, blabla text and end with "...more" click the bottom of the text and get the new text
            is_long_bio = re.compile(
                r"{0}$".format("… more"), flags=re.IGNORECASE
            ).search(biography_text)
            if is_long_bio is not None:
                logger.debug('Found "… more" in bio - trying to expand')
                username = self.getUsername()
                biography.click(Location.BOTTOMRIGHT)
                if username != self.getUsername():
                    logger.debug(
                        "We're not in the same page - did we click a hashtag or a tag? Go back."
                    )
                    self.device.back()
                    logger.info("Failed to expand biography - checking short view.")
                return biography.get_text()
            return biography_text
        return ""

    def getFullName(self):
        full_name_view = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.PROFILE_HEADER_FULL_NAME),
            className=ClassName.TEXT_VIEW,
        )
        if full_name_view.exists(Timeout.SHORT):
            fullname_text = full_name_view.get_text()
            if fullname_text is not None:
                return fullname_text
        return ""

    def isPrivateAccount(self):
        private_profile_view = self.device.find(
            resourceIdMatches=case_insensitive_re(
                [
                    ResourceID.PRIVATE_PROFILE_EMPTY_STATE,
                    ResourceID.ROW_PROFILE_HEADER_EMPTY_PROFILE_NOTICE_TITLE,
                    ResourceID.ROW_PROFILE_HEADER_EMPTY_PROFILE_NOTICE_CONTAINER,
                ]
            )
        )
        return private_profile_view.exists()

    def StoryRing(self) -> DeviceFacade.View:
        return self.device.find(
            resourceId=ResourceID.REEL_RING,
        )

    def live_marker(self) -> DeviceFacade.View:
        return self.device.find(resourceId=ResourceID.LIVE_BADGE_VIEW)

    def profileImage(self):
        return self.device.find(
            resourceId=ResourceID.ROW_PROFILE_HEADER_IMAGEVIEW,
        )

    def navigateToFollowers(self):
        logger.info("Navigate to followers.")
        self._scroll_to_profile_header()
        selectors = [
            dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWERS_CONTAINER),
            dict(resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_FOLLOWERS_CONTAINER),
        ]
        followers_button = None
        for sel in selectors:
            followers_button = self.device.find(**sel)
            if followers_button.exists(Timeout.LONG):
                break
        if followers_button and followers_button.exists(Timeout.LONG):
            followers_button.click()
            followers_tab = self.device.find(
                resourceIdMatches=ResourceID.UNIFIED_FOLLOW_LIST_TAB_LAYOUT
            ).child(textContains="Followers")
            if followers_tab.exists(Timeout.LONG):
                if not followers_tab.get_property("selected"):
                    followers_tab.click()
                return True
        else:
            logger.error("Can't find followers tab!")
            return False

    def navigateToFollowing(self):
        logger.info("Navigate to following.")
        self._scroll_to_profile_header()
        selectors = [
            dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWING_CONTAINER),
            dict(resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_FOLLOWING_CONTAINER),
        ]
        following_button = None
        for sel in selectors:
            following_button = self.device.find(**sel)
            if following_button.exists(Timeout.LONG):
                break
        if following_button and following_button.exists(Timeout.LONG):
            following_button.click_retry()
            following_tab = self.device.find(
                resourceIdMatches=ResourceID.UNIFIED_FOLLOW_LIST_TAB_LAYOUT
            ).child(textContains="Following")
            if following_tab.exists(Timeout.LONG):
                if not following_tab.get_property("selected"):
                    following_tab.click()
                return True
        else:
            logger.error("Can't find following tab!")
            return False

    def _scroll_to_profile_header(self, attempts: int = 3):
        """Ensure profile header (metrics row) is visible."""
        metric_selectors = [
            dict(resourceIdMatches=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWERS_VALUE),
            dict(resourceIdMatches=ResourceID.ROW_PROFILE_HEADER_TEXTVIEW_FOLLOWERS_COUNT),
        ]
        for _ in range(attempts):
            for sel in metric_selectors:
                if self.device.find(**sel).exists(Timeout.TINY):
                    return
            UniversalActions(self.device)._swipe_points(Direction.DOWN, delta_y=550)
            random_sleep(0.3, 0.6, modulable=False)

    def navigateToMutual(self):
        logger.info("Navigate to mutual friends.")
        has_mutual = False
        follow_context = self.device.find(
            resourceIdMatches=ResourceID.PROFILE_HEADER_FOLLOW_CONTEXT_TEXT
        )
        if follow_context.exists():
            follow_context.click()
            has_mutual = True
        return has_mutual

    def swipe_to_fit_posts(self):
        """calculate the right swipe amount necessary to see 12 photos"""
        displayWidth = self.device.get_info()["displayWidth"]
        element_to_swipe_over_obj = self.device.find(
            resourceIdMatches=ResourceID.PROFILE_TABS_CONTAINER
        )
        for _ in range(2):
            if not element_to_swipe_over_obj.exists():
                UniversalActions(self.device)._swipe_points(
                    direction=Direction.DOWN, delta_y=randint(300, 350)
                )
                element_to_swipe_over_obj = self.device.find(
                    resourceIdMatches=ResourceID.PROFILE_TABS_CONTAINER
                )
                continue

            element_to_swipe_over = element_to_swipe_over_obj.get_bounds()["top"]
            try:
                bar_container = self.device.find(
                    resourceIdMatches=ResourceID.ACTION_BAR_CONTAINER
                ).get_bounds()["bottom"]

                logger.info("Scrolled down to see more posts.")
                self.device.swipe_points(
                    displayWidth / 2,
                    element_to_swipe_over,
                    displayWidth / 2,
                    bar_container,
                )
                return element_to_swipe_over - bar_container
            except Exception as e:
                logger.debug(f"Exception: {e}")
                logger.info("I'm not able to scroll down.")
                return 0
        logger.warning(
            "Maybe a private/empty profile in which check failed or after whatching stories the view moves down :S.. Skip"
        )
        return -1

    def navigateToPostsTab(self):
        self._navigateToTab(TabBarText.POSTS_CONTENT_DESC)
        return PostsGridView(self.device)

    def navigateToIgtvTab(self):
        self._navigateToTab(TabBarText.IGTV_CONTENT_DESC)
        raise Exception("Not implemented")

    def navigateToReelsTab(self):
        self._navigateToTab(TabBarText.REELS_CONTENT_DESC)
        raise Exception("Not implemented")

    def navigateToEffectsTab(self):
        self._navigateToTab(TabBarText.EFFECTS_CONTENT_DESC)
        raise Exception("Not implemented")

    def navigateToPhotosOfYouTab(self):
        self._navigateToTab(TabBarText.PHOTOS_OF_YOU_CONTENT_DESC)
        raise Exception("Not implemented")

    def _navigateToTab(self, tab: TabBarText):
        tabs_view = self.device.find(
            resourceIdMatches=case_insensitive_re(ResourceID.PROFILE_TAB_LAYOUT),
            className=ClassName.HORIZONTAL_SCROLL_VIEW,
        )
        button = tabs_view.child(
            descriptionMatches=case_insensitive_re(tab),
            resourceIdMatches=case_insensitive_re(ResourceID.PROFILE_TAB_ICON_VIEW),
            className=ClassName.IMAGE_VIEW,
        )

        attempts = 0
        while not button.exists():
            attempts += 1
            self.device.swipe(Direction.UP, scale=0.1)
            if attempts > 2:
                logger.error(f"Cannot navigate to tab '{tab}'")
                save_crash(self.device)
                return

        button.click()

    def _getRecyclerView(self):
        views = f"({ClassName.RECYCLER_VIEW}|{ClassName.VIEW})"

        return self.device.find(classNameMatches=views)


class FollowingView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def do_unfollow_from_list(self, username, user_row=None) -> bool:
        exists = False
        username_row = ""
        if user_row is None:
            user_row = self.device.find(
                resourceId=ResourceID.FOLLOW_LIST_CONTAINER,
                className=ClassName.LINEAR_LAYOUT,
            )
        if user_row.exists(Timeout.MEDIUM):
            exists = True
            username_row = user_row.child(index=1).child().child().get_text()
            following_button = user_row.child(index=2)
        if not exists or username_row != username:
            logger.error(f"Cannot find {username} in following list.")
            return False
        if following_button.exists(Timeout.SHORT):
            following_button.click()
            UNFOLLOW_REGEX = "^Unfollow$"
            confirm_unfollow_button = self.device.find(
                resourceId=ResourceID.PRIMARY_BUTTON, textMatches=UNFOLLOW_REGEX
            )
            if confirm_unfollow_button.exists(Timeout.SHORT):
                random_sleep(1, 2)
                confirm_unfollow_button.click()
            UniversalActions.detect_block(self.device)
            FOLLOW_REGEX = "^Follow$"
            follow_button = user_row.child(index=2, textMatches=FOLLOW_REGEX)
            if follow_button.exists(Timeout.SHORT):
                logger.info(
                    f"{username} unfollowed.",
                    extra={"color": f"{Style.BRIGHT}{Fore.GREEN}"},
                )
                return True
            if not confirm_unfollow_button.exists(Timeout.SHORT):
                logger.error(f"Cannot confirm unfollow for {username}.")
                save_crash(self.device)
                return False


class FollowersView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _find_user_to_remove(self, username):
        row = self.device.find(resourceId=ResourceID.FOLLOW_LIST_CONTAINER)
        return row if row.child(textMatches=username).exists() else None

    def _get_remove_button(self, row_obj):
        REMOVE_TEXT = "^Remove$"
        return row_obj.child(
            resourceId=ResourceID.BUTTON, textMatches=case_insensitive_re(REMOVE_TEXT)
        )

    def _click_button(self, obj, obj_name):
        if obj.exists(Timeout.SHORT):
            logger.info(f"Pressing on {obj_name} button.")
            obj.click()
            return True
        logger.info(f"Object {obj_name} doesn't exists. Can't press on it!")
        return False

    def _confirm_remove_follower(self):
        obj = self.device.find(resourceId=ResourceID.ACTION_SHEET_ROW_TEXT_VIEW)
        return self._click_button(obj, "remove confirmation")

    def remove_follower(self, username):
        user_row = self._find_user_to_remove(username)
        if user_row is not None and user_row.exists():
            if self._click_button(self._get_remove_button(user_row), "remove"):
                return self._confirm_remove_follower()
        return False


class CurrentStoryView:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def getStoryFrame(self) -> DeviceFacade.View:
        return self.device.find(
            resourceId=ResourceID.REEL_VIEWER_MEDIA_CONTAINER,
        )

    def getUsername(self) -> str:
        reel_viewer_title = self.device.find(
            resourceId=ResourceID.REEL_VIEWER_TITLE,
        )
        reel_exists = reel_viewer_title.exists(ignore_bug=True)
        if reel_exists == "BUG!":
            return reel_exists
        return (
            ""
            if not reel_exists
            else reel_viewer_title.get_text(error=False).replace(" ", "")
        )

    def getTimestamp(self) -> Optional[datetime.datetime]:
        reel_viewer_timestamp = self.device.find(
            resourceId=ResourceID.REEL_VIEWER_TIMESTAMP,
        )
        if reel_viewer_timestamp.exists():
            timestamp = reel_viewer_timestamp.get_text().strip()
            value = int(re.sub("[^0-9]", "", timestamp))
            if timestamp[-1] == "s":
                return datetime.timestamp(
                    datetime.datetime.now() - datetime.timedelta(seconds=value)
                )
            elif timestamp[-1] == "m":
                return datetime.timestamp(
                    datetime.datetime.now() - datetime.timedelta(minutes=value)
                )
            elif timestamp[-1] == "h":
                return datetime.timestamp(
                    datetime.datetime.now() - datetime.timedelta(hours=value)
                )
            else:
                return datetime.timestamp(
                    datetime.datetime.now() - datetime.timedelta(days=value)
                )
        return None


class UniversalActions:
    def __init__(self, device: DeviceFacade):
        self.device = device

    def _swipe_points(
        self,
        direction: Direction,
        start_point_x=-1,
        start_point_y=-1,
        delta_x=-1,
        delta_y=450,
    ) -> None:
        displayWidth = self.device.get_info()["displayWidth"]
        displayHeight = self.device.get_info()["displayHeight"]
        middle_point_x = displayWidth / 2
        if start_point_y == -1:
            start_point_y = displayHeight / 2
        if direction == Direction.UP:
            if start_point_y - delta_y < 0:
                delta = delta_y - start_point_y
                start_point_y = start_point_y + delta
            self.device.swipe_points(
                middle_point_x,
                start_point_y,
                middle_point_x,
                start_point_y - delta_y,
            )
        elif direction == Direction.DOWN:
            if start_point_y + delta_y > displayHeight:
                delta = start_point_y + delta_y - displayHeight
                start_point_y = start_point_y - delta
            self.device.swipe_points(
                middle_point_x,
                start_point_y,
                middle_point_x,
                start_point_y + delta_y,
            )
        elif direction == Direction.LEFT:
            if start_point_x == -1:
                start_point_x = displayWidth * 2 / 3
            if delta_x == -1:
                delta_x = uniform(0.95, 1.25) * (displayWidth / 2)
            self.device.swipe_points(
                start_point_x,
                start_point_y,
                start_point_x - delta_x,
                start_point_y,
            )

    def press_button_back(self) -> None:
        back_button = self.device.find(
            resourceIdMatches=ResourceID.ACTION_BAR_BUTTON_BACK
        )
        if back_button.exists():
            logger.info("Pressing on back button.")
            back_button.click()

    def _reload_page(self) -> None:
        logger.debug("Reload page.")
        self._swipe_points(direction=Direction.UP)
        random_sleep(inf=5, sup=8, modulable=False)

    @staticmethod
    def detect_block(device) -> bool:
        if not args.disable_block_detection:
            return False
        logger.debug("Checking for block...")
        if "blocked" in device.deviceV2.toast.get_message(1.0, 2.0, default=""):
            logger.warning("Toast detected!")
        serius_block = device.find(
            className=ClassName.IMAGE,
            textMatches=case_insensitive_re("Force reset password icon"),
        )
        if serius_block.exists():
            raise ActionBlockedError("Serius block detected :(")
        block_dialog = device.find(
            resourceIdMatches=ResourceID.BLOCK_POPUP,
        )
        popup_body = device.find(
            resourceIdMatches=ResourceID.IGDS_HEADLINE_BODY,
        )
        popup_appears = block_dialog.exists()
        if popup_appears:
            if popup_body.exists():
                regex = r".+deleted"
                is_post_deleted = re.match(regex, popup_body.get_text(), re.IGNORECASE)
                if is_post_deleted:
                    logger.info(f"{is_post_deleted.group()}")
                    logger.debug("Click on OK button.")
                    device.find(
                        resourceIdMatches=ResourceID.NEGATIVE_BUTTON,
                    ).click()
                    is_blocked = False
                else:
                    is_blocked = True
            else:
                is_blocked = True
        else:
            is_blocked = False

        if is_blocked:
            logger.error("Probably block dialog is shown.")
            raise ActionBlockedError(
                "Seems that action is blocked. Consider reinstalling Instagram app and be more careful with limits!"
            )

    def _check_if_no_posts(self) -> bool:
        obj = self.device.find(resourceId=ResourceID.IGDS_HEADLINE_EMPHASIZED_HEADLINE)
        return obj.exists(Timeout.MEDIUM)

    def search_text(self, username):
        search_row = self.device.find(resourceId=ResourceID.ROW_SEARCH_EDIT_TEXT)
        if search_row.exists(Timeout.MEDIUM):
            # FastInputIME is flaky on newer Android; prefer paste for reliability.
            for _ in range(2):
                search_row.set_text(username, Mode.PASTE)
                if search_row.get_text(error=False) == username:
                    return True
                random_sleep(0.3, 0.6, modulable=False)
            logger.warning("Search bar text mismatch after retries.")
            return False
        else:
            return False

    @staticmethod
    def close_keyboard(device):
        flag = DeviceFacade(device.device_id, device.app_id)._is_keyboard_show()
        if flag:
            logger.debug("The keyboard is currently open. Press back to close.")
            device.back()
        elif flag is None:
            tabbar_container = device.find(
                resourceId=ResourceID.FIXED_TABBAR_TABS_CONTAINER
            )
            if tabbar_container.exists():
                delta = tabbar_container.get_bounds()["bottom"]
            else:
                delta = 375
            logger.debug(
                "Failed to check if keyboard is open! Will do a little swipe up to prevent errors."
            )
            UniversalActions(device)._swipe_points(
                direction=Direction.UP,
                start_point_y=randint(delta + 10, delta + 150),
                delta_y=randint(50, 100),
            )
