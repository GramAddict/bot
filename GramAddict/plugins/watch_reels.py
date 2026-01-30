import logging
from random import randint, uniform
from time import sleep, time
from typing import Tuple

from GramAddict.core.decorators import run_safely
from GramAddict.core.device_facade import Timeout
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.resources import ResourceID as resources
from GramAddict.core.utils import get_value, random_sleep
from GramAddict.core.utils import stop_bot
from GramAddict.core.views import (
    Direction,
    PostsViewList,
    TabBarView,
    UniversalActions,
    _click_reel_like_button,
    _double_tap_reel_media,
    _is_reel_liked,
    _reel_like_use_double_tap,
    case_insensitive_re,
)

logger = logging.getLogger(__name__)


class WatchReels(Plugin):
    """Watches reels in the Reels tab with optional auto-like"""

    def __init__(self):
        super().__init__()
        self.description = "Watch reels in the Reels tab with optional auto-like"
        self.arguments = [
            {
                "arg": "--watch-reels",
                "nargs": None,
                "help": "watch reels tab for the given amount (number or range). Disabled by default",
                "metavar": "5-10",
                "default": None,
                "operation": True,
            },
            {
                "arg": "--reels-like-percentage",
                "nargs": None,
                "help": "chance of liking a reel while watching, 0 by default",
                "metavar": "10-40",
                "default": "0",
            },
            {
                "arg": "--reels-watch-time",
                "nargs": None,
                "help": "seconds to stay on each reel before swiping (number or range)",
                "metavar": "5-8",
                "default": "5-8",
            },
            {
                "arg": "--reels-ad-watch-time",
                "nargs": None,
                "help": "seconds to stay on ad reels before swiping (number or range). Defaults to reels-watch-time if not set.",
                "metavar": "3-6",
                "default": None,
            },
            {
                "arg": "--reels-like-ads",
                "help": "allow likes on reels detected as ads (default: false)",
                "action": "store_true",
            },
        ]

    def run(self, device, configs, storage, sessions, profile_filter, plugin):
        self.device_id = configs.args.device
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.args = configs.args
        self.storage = storage
        self.current_mode = plugin
        self.ResourceID = resources(self.args.app_id)

        reels_count = get_value(self.args.watch_reels, "Reels to watch: {}", 0)
        if not reels_count:
            logger.info("No reels count provided, skipping reels watcher.")
            return
        like_percentage = get_value(self.args.reels_like_percentage, None, 0)
        dwell_seconds = get_value(self.args.reels_watch_time, None, 6, its_time=True)
        if dwell_seconds is None:
            dwell_seconds = 6
        dwell_seconds_ads = get_value(
            self.args.reels_ad_watch_time, None, dwell_seconds, its_time=True
        )
        if dwell_seconds_ads is None:
            dwell_seconds_ads = dwell_seconds
        doubletap_pct = get_value(self.args.reels_like_doubletap_percentage, None, 0)

        @run_safely(
            device=device,
            device_id=self.device_id,
            sessions=self.sessions,
            session_state=self.session_state,
            screen_record=self.args.screen_record,
            configs=configs,
        )
        def job():
            self._watch_reels(
                device,
                reels_count,
                like_percentage,
                dwell_seconds,
                dwell_seconds_ads,
                doubletap_pct,
            )

        job()

    def _watch_reels(
        self,
        device,
        reels_count: int,
        like_percentage: int,
        dwell_regular: int,
        dwell_ads: int,
        doubletap_pct: int,
    ):
        tab_bar = TabBarView(device)
        tab_bar.navigateToReels()
        random_sleep(inf=1, sup=2, modulable=False)

        watched = 0
        likes_limit_logged = False
        reel_likes_limit_logged = False
        reel_watch_limit_logged = False
        extra_watch_logged = False
        extra_watch_remaining = None
        reels_likes_limit = int(self.session_state.args.current_reels_likes_limit)
        reels_watches_limit = int(self.session_state.args.current_reels_watches_limit)
        extra_watch_limit = int(
            self.session_state.args.current_reels_watch_after_like_limit
        )
        if reels_watches_limit == 0:
            logger.info("Reel watch limit is 0; skipping reels.")
            return
        while watched < reels_count:
            reel_start = time()
            if (
                reels_watches_limit > 0
                and self.session_state.totalReelWatched >= reels_watches_limit
            ):
                if not reel_watch_limit_logged:
                    logger.info("Reel watch limit reached; stopping session.")
                    reel_watch_limit_logged = True
                stop_bot(device, self.sessions, self.session_state)
                return
            username = PostsViewList(device)._get_reel_author_username()
            if not username:
                logger.debug("Reel author not detected; cannot check interacted history.")
            skip_like_for_user = False
            if self.storage is not None and username:
                if self.storage.is_user_in_blacklist(username):
                    logger.info(f"@{username} is in blacklist. Skip reel interaction.")
                    skip_like_for_user = True
                else:
                    interacted, interacted_when = self.storage.check_user_was_interacted(
                        username
                    )
                    if interacted:
                        can_reinteract = self.storage.can_be_reinteract(
                            interacted_when,
                            get_value(self.args.can_reinteract_after, None, 0),
                        )
                        logger.info(
                            f"@{username}: already interacted on {interacted_when:%Y/%m/%d %H:%M:%S}. {'Interacting again now' if can_reinteract else 'Skip'}."
                        )
                        if not can_reinteract:
                            skip_like_for_user = True
            already_liked = _is_reel_liked(device)
            if already_liked:
                logger.info("Reel already liked; skipping like.")
                skip_like_for_user = True
                if self.storage is not None and username:
                    self.storage.add_interacted_user(
                        username,
                        session_id=self.session_state.id,
                        liked=1,
                        job_name=self.current_mode,
                        target=None,
                    )
            likes_limit = int(self.session_state.args.current_likes_limit)
            global_likes_reached = (
                likes_limit > 0 and self.session_state.totalLikes >= likes_limit
            )
            reel_likes_reached = (
                reels_likes_limit > 0
                and self.session_state.totalReelLikes >= reels_likes_limit
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

            if self.session_state.check_limit(
                limit_type=self.session_state.Limit.ALL, output=True
            )[0]:
                logger.info("Session limits reached while watching reels; stopping session.")
                stop_bot(device, self.sessions, self.session_state)

            # Detect ad reel (but still watch); gate likes on ads by config
            is_ad, ad_reason = self._is_reel_ad(device)
            if is_ad and not self.args.reels_like_ads:
                logger.debug(
                    f"Reel marked as ad ({ad_reason}); skipping immediately (no watch/like)."
                )
                UniversalActions(device)._swipe_points(direction=Direction.UP, delta_y=800)
                random_sleep(inf=0.5, sup=1.2, modulable=False)
                watched += 1
                self.session_state.totalWatched += 1
                self.session_state.totalReelWatched += 1
                if extra_watch_remaining is not None:
                    extra_watch_remaining -= 1
                    if extra_watch_remaining <= 0:
                        logger.info(
                            "Like limit reached; extra reels watched, exiting."
                        )
                        break
                continue

            if (
                like_percentage
                and not likes_limit_reached
                and not skip_like_for_user
                and (self.args.reels_like_ads or not is_ad)
                and randint(1, 100) <= like_percentage
            ):
                used_doubletap = _reel_like_use_double_tap(doubletap_pct)
                liked = None
                method = None
                if used_doubletap and _double_tap_reel_media(device):
                    random_sleep(inf=0.3, sup=0.7, modulable=False)
                    liked = _is_reel_liked(device)
                    if not liked:
                        logger.info(
                            "Double-tap did not confirm like; trying heart."
                        )
                        liked = _click_reel_like_button(device)
                        if liked:
                            method = "heart"
                    else:
                        method = "double-tap"
                else:
                    liked = _click_reel_like_button(device)
                    if liked:
                        method = "heart"
                if liked:
                    self.session_state.totalLikes += 1
                    self.session_state.totalReelLikes += 1
                    logger.info(
                        f"Liked reel #{watched + 1}{' (ad)' if is_ad else ''} ({method})."
                    )
                    if self.storage is not None and username:
                        self.storage.add_interacted_user(
                            username,
                            session_id=self.session_state.id,
                            liked=1,
                            job_name=self.current_mode,
                            target=None,
                        )
                elif liked is None:
                    logger.warning("Reel like could not be confirmed.")

            dwell = dwell_ads if is_ad else dwell_regular
            stay_time = max(1, dwell)
            watch_for = max(1, uniform(stay_time - 0.5, stay_time + 1))
            elapsed = time() - reel_start
            remaining = max(0.0, watch_for - elapsed)
            if remaining <= 0.2:
                logger.info(
                    f"Watching reel #{watched + 1} for ~{watch_for:.1f}s (elapsed {elapsed:.1f}s; no extra wait)."
                )
            else:
                logger.info(
                    f"Watching reel #{watched + 1} for ~{watch_for:.1f}s (elapsed {elapsed:.1f}s, remaining {remaining:.1f}s)."
                )
                sleep(remaining)

            watched += 1
            self.session_state.totalWatched += 1
            self.session_state.totalReelWatched += 1
            if extra_watch_remaining is not None:
                extra_watch_remaining -= 1
                if extra_watch_remaining <= 0:
                    logger.info(
                        "Like limit reached; extra reels watched, exiting."
                    )
                    break

            UniversalActions(device)._swipe_points(direction=Direction.UP, delta_y=800)
            random_sleep(inf=1, sup=2, modulable=False)

        if self.session_state.check_limit(limit_type=self.session_state.Limit.ALL)[0]:
            logger.info("Session limits reached after reels; stopping session.")
            stop_bot(device, self.sessions, self.session_state)

    def _is_reel_ad(self, device) -> Tuple[bool, str]:
        # Reuse feed ad heuristics: sponsored root, ad badge, or localized labels
        sponsored_txts = [
            "sponsored",
            "gesponsert",
            "pubblicité",
            "publicidad",
            "sponsorisé",
            "advertisement",
            "ad",
        ]
        if device.find(
            resourceIdMatches=self.ResourceID.SPONSORED_CONTENT_SERVER_RENDERED_ROOT
        ).exists(Timeout.TINY):
            return True, "sponsored_root"
        ad_badge = device.find(resourceId=self.ResourceID.AD_BADGE)
        if ad_badge.exists(Timeout.TINY):
            return True, "ad_badge"
        label = device.find(textMatches=case_insensitive_re("|".join(sponsored_txts)))
        if label.exists(Timeout.TINY):
            return True, "label_text"
        desc_label = device.find(
            descriptionMatches=case_insensitive_re("|".join(sponsored_txts))
        )
        if desc_label.exists(Timeout.TINY):
            return True, "label_desc"
        return False, ""
