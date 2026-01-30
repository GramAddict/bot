import logging
import string
from datetime import datetime
from enum import Enum, auto
from inspect import stack
from os import getcwd, listdir
from random import randint, uniform
from re import search
from subprocess import PIPE, run
from time import sleep, time
from typing import Optional, Tuple

import uiautomator2

from GramAddict.core.utils import random_sleep

logger = logging.getLogger(__name__)

DOUBLE_CLICK_INTERVAL_RANGE: Tuple[float, float] = (0.030, 0.090)


def _parse_double_click_interval(value) -> Optional[Tuple[float, float]]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        val = float(value)
        return (val, val)
    if isinstance(value, str):
        parts = [part.strip() for part in value.split("-") if part.strip()]
        if len(parts) == 1:
            try:
                val = float(parts[0])
            except ValueError:
                return None
            return (val, val)
        if len(parts) == 2:
            try:
                low = float(parts[0])
                high = float(parts[1])
            except ValueError:
                return None
            if low > high:
                low, high = high, low
            return (low, high)
    return None


def load_config(config) -> None:
    global DOUBLE_CLICK_INTERVAL_RANGE
    args = getattr(config, "args", None)
    if args is None:
        return
    interval_raw = getattr(args, "double_click_interval", None)
    if interval_raw is None:
        return
    parsed = _parse_double_click_interval(interval_raw)
    if parsed is None or parsed[0] <= 0 or parsed[1] <= 0:
        logger.warning(
            f"Invalid double-click-interval '{interval_raw}', using default "
            f"{DOUBLE_CLICK_INTERVAL_RANGE[0]}-{DOUBLE_CLICK_INTERVAL_RANGE[1]}."
        )
        return
    DOUBLE_CLICK_INTERVAL_RANGE = parsed


def create_device(device_id, app_id):
    try:
        return DeviceFacade(device_id, app_id)
    except ImportError as e:
        logger.error(str(e))
        return None


def get_device_info(device):
    info = device.get_info()
    logger.debug(
        f"Phone Name: {info['productName']}, SDK Version: {info['sdkInt']}"
    )
    if int(info["sdkInt"]) < 19:
        logger.warning("Only Android 4.4+ (SDK 19+) devices are supported!")
    logger.debug(
        f"Screen dimension: {info['displayWidth']}x{info['displayHeight']}"
    )
    logger.debug(
        f"Screen resolution: {info['displaySizeDpX']}x{info['displaySizeDpY']}"
    )
    logger.debug(f"Device ID: {device.deviceV2.serial}")


class Timeout(Enum):
    ZERO = auto()
    TINY = auto()
    SHORT = auto()
    MEDIUM = auto()
    LONG = auto()


class SleepTime(Enum):
    ZERO = auto()
    TINY = auto()
    SHORT = auto()
    DEFAULT = auto()


class Location(Enum):
    CUSTOM = auto()
    WHOLE = auto()
    CENTER = auto()
    BOTTOM = auto()
    RIGHT = auto()
    LEFT = auto()
    BOTTOMRIGHT = auto()
    LEFTEDGE = auto()
    RIGHTEDGE = auto()
    TOPLEFT = auto()


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    RIGHT = auto()
    LEFT = auto()


class Mode(Enum):
    TYPE = auto()
    PASTE = auto()


class DeviceFacade:
    def __init__(self, device_id, app_id):
        self.device_id = device_id
        self.app_id = app_id
        try:
            # Always prefer a USB connection; only use Wi-Fi when an explicit host:port is provided.
            if device_id is None:
                self.deviceV2 = uiautomator2.connect()
            elif "." in device_id:
                self.deviceV2 = uiautomator2.connect_adb_wifi(f"{device_id}")
            else:
                # explicit serial over USB
                self.deviceV2 = uiautomator2.connect_usb(device_id)

            # Make sure atx-agent/uiautomator is up before doing anything else.
            self._ensure_uiautomator_started()

            # FastInputIME is unreliable on Android 15/16; disable it so set_text uses
            # the standard IME and avoids warnings/timeouts.
            try:
                self.deviceV2.set_fastinput_ime(False)
            except Exception:
                pass

            # Android 15 (SDK 35/36) + uiautomator2 2.16.x can crash when
            # compressed layout hierarchy is enabled (NullPointerException in
            # setCompressedLayoutHeirarchy). Disable it up front to keep dumps
            # and selector lookups stable. See
            # https://github.com/openatx/uiautomator2/issues/1393
            try:
                self.deviceV2.settings["compressedLayoutHierarchy"] = False
            except Exception:
                pass

            # Remove default per-action delay to speed up startup interactions.
            try:
                self.deviceV2.settings["operation_delay"] = (0, 0)
                self.deviceV2.settings["operation_delay_range"] = (0, 0)
            except Exception:
                pass
        except ImportError:
            raise ImportError("Please install uiautomator2: pip3 install uiautomator2")

    def _ensure_uiautomator_started(self, timeout: int = 12):
        """Start uiautomator service if it's stopped and wait until it's ready."""
        # New API (uiautomator2 >= 3.0): device.uiautomator.start()
        self.deviceV2.uiautomator.start()
        start = time()
        while not self.deviceV2.uiautomator.running():
            if time() - start > timeout:
                raise RuntimeError("uiautomator service did not start in time")
            sleep(0.4)
        # Warm up one info call so later queries are instant
        try:
            _ = self.deviceV2.info
        except Exception:
            pass

    def _get_current_app(self):
        try:
            return self.deviceV2.app_current()["package"]
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    def _ig_is_opened(self) -> bool:
        return self._get_current_app() == self.app_id

    def check_if_ig_is_opened(func):
        def wrapper(self, **kwargs):
            avoid_lst = ["choose_cloned_app", "check_if_crash_popup_is_there"]
            caller = stack()[1].function
            if not self._ig_is_opened() and caller not in avoid_lst:
                raise DeviceFacade.AppHasCrashed("App has crashed / has been closed!")
            return func(self, **kwargs)

        return wrapper

    @check_if_ig_is_opened
    def find(
        self,
        index=None,
        **kwargs,
    ):
        try:
            view = self.deviceV2(**kwargs)
            if index is not None and view.count > 1:
                view = self.deviceV2(**kwargs)[index]
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)
        return DeviceFacade.View(view=view, device=self.deviceV2)

    def back(self, modulable: bool = True):
        logger.debug("Press back button.")
        self.deviceV2.press("back")
        random_sleep(modulable=modulable)

    def start_screenrecord(self, output="debug_0000.mp4", fps=20):
        import imageio

        def _run_MOD(self):
            from collections import deque

            pipelines = [self._pipe_limit, self._pipe_convert, self._pipe_resize]
            _iter = self._iter_minicap()
            for p in pipelines:
                _iter = p(_iter)

            with imageio.get_writer(self._filename, fps=self._fps) as wr:
                frames = deque(maxlen=self._fps * 30)
                for im in _iter:
                    frames.append(im)
                if self.crash:
                    for frame in frames:
                        wr.append_data(frame)
            self._done_event.set()

        def stop_MOD(self, crash=True):
            """
            stop record and finish write video
            Returns:
                bool: whether video is recorded.
            """
            if self._running:
                self.crash = crash
                self._stop_event.set()
                ret = self._done_event.wait(10.0)

                # reset
                self._stop_event.clear()
                self._done_event.clear()
                self._running = False
                return ret

        from uiautomator2 import screenrecord as _sr

        _sr.Screenrecord._run = _run_MOD
        _sr.Screenrecord.stop = stop_MOD
        mp4_files = [f for f in listdir(getcwd()) if f.endswith(".mp4")]
        if mp4_files:
            last_mp4 = mp4_files[-1]
            debug_number = "{0:0=4d}".format(int(last_mp4[-8:-4]) + 1)
            output = f"debug_{debug_number}.mp4"
        self.deviceV2.screenrecord(output, fps)
        logger.warning("Screen recording has been started.")

    def stop_screenrecord(self, crash=True):
        if self.deviceV2.screenrecord.stop(crash=crash):
            logger.warning("Screen recorder has been stopped successfully!")

    def screenshot(self, path=None):
        if path is None:
            return self.deviceV2.screenshot()
        else:
            self.deviceV2.screenshot(path)

    def dump_hierarchy(self, path):
        xml_dump = self.deviceV2.dump_hierarchy()
        with open(path, "w", encoding="utf-8") as outfile:
            outfile.write(xml_dump)

    def press_power(self):
        self.deviceV2.press("power")
        sleep(2)

    def is_screen_locked(self):
        data = run(
            f"adb -s {self.deviceV2.serial} shell dumpsys window",
            encoding="utf-8",
            stdout=PIPE,
            stderr=PIPE,
            shell=True,
        )
        if data != "":
            flag = search("mDreamingLockscreen=(true|false)", data.stdout)
            return flag is not None and flag.group(1) == "true"
        else:
            logger.debug(
                f"'adb -s {self.deviceV2.serial} shell dumpsys window' returns nothing!"
            )
            return None

    def _is_keyboard_show(self):
        data = run(
            f"adb -s {self.deviceV2.serial} shell dumpsys input_method",
            encoding="utf-8",
            stdout=PIPE,
            stderr=PIPE,
            shell=True,
        )
        if data != "":
            flag = search("mInputShown=(true|false)", data.stdout)
            return flag.group(1) == "true"
        else:
            logger.debug(
                f"'adb -s {self.deviceV2.serial} shell dumpsys input_method' returns nothing!"
            )
            return None

    def is_alive(self):
        try:
            return self.deviceV2._is_alive()  # deprecated method
        except AttributeError:
            return self.deviceV2.server.alive

    def wake_up(self):
        """Make sure agent is alive or bring it back up before starting."""
        if self.deviceV2 is not None:
            attempts = 0
            while not self.is_alive() and attempts < 5:
                self.get_info()
                attempts += 1

    def unlock(self):
        self.swipe(Direction.UP, 0.8)
        sleep(2)
        logger.debug(f"Screen locked: {self.is_screen_locked()}")
        if self.is_screen_locked():
            self.swipe(Direction.RIGHT, 0.8)
            sleep(2)
            logger.debug(f"Screen locked: {self.is_screen_locked()}")

    def screen_off(self):
        self.deviceV2.screen_off()

    def get_orientation(self):
        try:
            return self.deviceV2._get_orientation()
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    def window_size(self):
        """return (width, height)"""
        try:
            self.deviceV2.window_size()
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    def swipe(self, direction: Direction, scale=0.5):
        """Swipe finger in the `direction`.
        Scale is the sliding distance. Default to 50% of the screen width
        """
        swipe_dir = ""
        if direction == Direction.UP:
            swipe_dir = "up"
        elif direction == Direction.RIGHT:
            swipe_dir = "right"
        elif direction == Direction.LEFT:
            swipe_dir = "left"
        elif direction == Direction.DOWN:
            swipe_dir = "down"

        logger.debug(f"Swipe {swipe_dir}, scale={scale}")

        try:
            self.deviceV2.swipe_ext(swipe_dir, scale=scale)
            DeviceFacade.sleep_mode(SleepTime.TINY)
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    def swipe_points(self, sx, sy, ex, ey, random_x=True, random_y=True):
        if random_x:
            sx = int(sx * uniform(0.85, 1.15))
            ex = int(ex * uniform(0.85, 1.15))
        if random_y:
            ey = int(ey * uniform(0.98, 1.02))
        sy = int(sy)
        try:
            logger.debug(f"Swipe from: ({sx},{sy}) to ({ex},{ey}).")
            self.deviceV2.swipe_points([[sx, sy], [ex, ey]], uniform(0.2, 0.5))
            DeviceFacade.sleep_mode(SleepTime.TINY)
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    def get_info(self):
        # {'currentPackageName': 'net.oneplus.launcher', 'displayHeight': 1920, 'displayRotation': 0, 'displaySizeDpX': 411,
        # 'displaySizeDpY': 731, 'displayWidth': 1080, 'productName': 'OnePlus5', '
        #  screenOn': True, 'sdkInt': 27, 'naturalOrientation': True}
        try:
            return self.deviceV2.info
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    @staticmethod
    def sleep_mode(mode):
        mode = SleepTime.DEFAULT if mode is None else mode
        if mode == SleepTime.DEFAULT:
            random_sleep()
        elif mode == SleepTime.TINY:
            random_sleep(0, 1)
        elif mode == SleepTime.SHORT:
            random_sleep(1, 2)
        elif mode == SleepTime.ZERO:
            pass

    class View:
        deviceV2 = None  # uiautomator2
        viewV2 = None  # uiautomator2

        def __init__(self, view, device):
            self.viewV2 = view
            self.deviceV2 = device

        def __iter__(self):
            children = []
            try:
                children.extend(
                    DeviceFacade.View(view=item, device=self.deviceV2)
                    for item in self.viewV2
                )
                return iter(children)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def ui_info(self):
            try:
                return self.viewV2.info
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def get_desc(self):
            try:
                return self.viewV2.info["contentDescription"]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def child(self, *args, **kwargs):
            try:
                view = self.viewV2.child(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(view=view, device=self.deviceV2)

        def sibling(self, *args, **kwargs):
            try:
                view = self.viewV2.sibling(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(view=view, device=self.deviceV2)

        def left(self, *args, **kwargs):
            try:
                view = self.viewV2.left(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(view=view, device=self.deviceV2)

        def right(self, *args, **kwargs):
            try:
                view = self.viewV2.right(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(view=view, device=self.deviceV2)

        def up(self, *args, **kwargs):
            try:
                view = self.viewV2.up(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(view=view, device=self.deviceV2)

        def down(self, *args, **kwargs):
            try:
                view = self.viewV2.down(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(view=view, device=self.deviceV2)

        def click_gone(self, maxretry=3, interval=1.0):
            try:
                self.viewV2.click_gone(maxretry, interval)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def click(self, mode=None, sleep=None, coord=None, crash_report_if_fails=True):
            if coord is None:
                coord = []
            mode = Location.WHOLE if mode is None else mode
            if mode == Location.WHOLE:
                x_offset = uniform(0.15, 0.85)
                y_offset = uniform(0.15, 0.85)

            elif mode == Location.LEFT:
                x_offset = uniform(0.15, 0.4)
                y_offset = uniform(0.15, 0.85)

            elif mode == Location.LEFTEDGE:
                x_offset = uniform(0.1, 0.2)
                y_offset = uniform(0.40, 0.60)

            elif mode == Location.CENTER:
                x_offset = uniform(0.4, 0.6)
                y_offset = uniform(0.15, 0.85)

            elif mode == Location.RIGHT:
                x_offset = uniform(0.6, 0.85)
                y_offset = uniform(0.15, 0.85)

            elif mode == Location.RIGHTEDGE:
                x_offset = uniform(0.8, 0.9)
                y_offset = uniform(0.40, 0.60)

            elif mode == Location.BOTTOMRIGHT:
                x_offset = uniform(0.8, 0.9)
                y_offset = uniform(0.8, 0.9)

            elif mode == Location.TOPLEFT:
                x_offset = uniform(0.05, 0.15)
                y_offset = uniform(0.05, 0.25)
            elif mode == Location.CUSTOM:
                try:
                    logger.debug(f"Single click ({coord[0]},{coord[1]})")
                    self.deviceV2.click(coord[0], coord[1])
                    DeviceFacade.sleep_mode(sleep)
                    return
                except uiautomator2.JSONRPCError as e:
                    if crash_report_if_fails:
                        raise DeviceFacade.JsonRpcError(e)
                    else:
                        logger.debug("Trying to press on a obj which is gone.")

            else:
                x_offset = 0.5
                y_offset = 0.5

            try:
                visible_bounds = self.get_bounds()
                x_abs = int(
                    visible_bounds["left"]
                    + (visible_bounds["right"] - visible_bounds["left"]) * x_offset
                )
                y_abs = int(
                    visible_bounds["top"]
                    + (visible_bounds["bottom"] - visible_bounds["top"]) * y_offset
                )

                logger.debug(
                    f"Single click in ({x_abs},{y_abs}). Surface: ({visible_bounds['left']}-{visible_bounds['right']},{visible_bounds['top']}-{visible_bounds['bottom']})"
                )
                self.viewV2.click(
                    self.get_ui_timeout(Timeout.LONG),
                    offset=(x_offset, y_offset),
                )
                DeviceFacade.sleep_mode(sleep)

            except uiautomator2.JSONRPCError as e:
                if crash_report_if_fails:
                    raise DeviceFacade.JsonRpcError(e)
                else:
                    logger.debug("Trying to press on a obj which is gone.")

        def click_retry(self, mode=None, sleep=None, coord=None, maxretry=2):
            """return True if successfully open the element, else False"""
            if coord is None:
                coord = []
            self.click(mode, sleep, coord)

            while maxretry > 0:
                # we wait a little more before try again
                random_sleep(2, 4, modulable=False)
                if not self.exists():
                    return True
                logger.debug("UI element didn't open! Try again..")
                self.click(mode, sleep, coord)
                maxretry -= 1
            if not self.exists():
                return True
            logger.warning("Failed to open the UI element!")
            return False

        def double_click(self, padding=0.3, obj_over=0):
            """Double click randomly in the selected view using padding
            padding: % of how far from the borders we want the double
                    click to happen.
            """
            visible_bounds = self.get_bounds()
            horizontal_len = visible_bounds["right"] - visible_bounds["left"]
            vertical_len = visible_bounds["bottom"] - max(
                visible_bounds["top"], obj_over
            )
            horizontal_padding = int(padding * horizontal_len)
            vertical_padding = int(padding * vertical_len)
            random_x = int(
                uniform(
                    visible_bounds["left"] + horizontal_padding,
                    visible_bounds["right"] - horizontal_padding,
                )
            )
            random_y = int(
                uniform(
                    visible_bounds["top"] + vertical_padding,
                    visible_bounds["bottom"] - vertical_padding,
                )
            )

            time_between_clicks = uniform(
                DOUBLE_CLICK_INTERVAL_RANGE[0], DOUBLE_CLICK_INTERVAL_RANGE[1]
            )

            try:
                logger.debug(
                    f"Double click in ({random_x},{random_y}) with t={int(time_between_clicks*1000)}ms. Surface: ({visible_bounds['left']}-{visible_bounds['right']},{visible_bounds['top']}-{visible_bounds['bottom']})."
                )
                self.deviceV2.double_click(
                    random_x, random_y, duration=time_between_clicks
                )
                DeviceFacade.sleep_mode(SleepTime.DEFAULT)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def scroll(self, direction):
            try:
                if direction == Direction.UP:
                    self.viewV2.scroll.toBeginning(max_swipes=1)
                else:
                    self.viewV2.scroll.toEnd(max_swipes=1)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def fling(self, direction):
            try:
                if direction == Direction.UP:
                    self.viewV2.fling.toBeginning(max_swipes=5)
                else:
                    self.viewV2.fling.toEnd(max_swipes=5)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def exists(self, ui_timeout=None, ignore_bug: bool = False) -> bool:
            try:
                # Currently, the methods left, right, up and down from
                # uiautomator2 return None when a Selector does not exist.
                # All other selectors return an UiObject with exists() == False.
                # We will open a ticket to uiautomator2 to fix this inconsistency.
                if self.viewV2 is None:
                    return False
                exists: bool = self.viewV2.exists(self.get_ui_timeout(ui_timeout))
                if (
                    hasattr(self.viewV2, "count")
                    and not exists
                    and self.viewV2.count >= 1
                ):
                    logger.debug(
                        f"UIA2 BUG: exists return False, but there is/are {self.viewV2.count} element(s)!"
                    )
                    if ignore_bug:
                        return "BUG!"
                    # More info about that: https://github.com/openatx/uiautomator2/issues/689"
                    return False
                return exists
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def count_items(self) -> int:
            try:
                return self.viewV2.count
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def wait(self, ui_timeout=Timeout.MEDIUM):
            try:
                return self.viewV2.wait(timeout=self.get_ui_timeout(ui_timeout))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def wait_gone(self, ui_timeout=None):
            try:
                return self.viewV2.wait_gone(timeout=self.get_ui_timeout(ui_timeout))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def is_above_this(self, obj2) -> Optional[bool]:
            obj1 = self.viewV2
            obj2 = obj2.viewV2
            try:
                if obj1.exists() and obj2.exists():
                    return obj1.info["bounds"]["top"] < obj2.info["bounds"]["top"]
                else:
                    return None
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def get_bounds(self) -> dict:
            try:
                return self.viewV2.info["bounds"]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def get_height(self) -> int:
            bounds = self.get_bounds()
            return bounds["bottom"] - bounds["top"]

        def get_width(self):
            bounds = self.get_bounds()
            return bounds["right"] - bounds["left"]

        def get_property(self, prop: str):
            try:
                return self.viewV2.info[prop]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def is_scrollable(self):
            try:
                if self.viewV2.exists():
                    return self.viewV2.info["scrollable"]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        @staticmethod
        def get_ui_timeout(ui_timeout: Timeout) -> int:
            ui_timeout = Timeout.ZERO if ui_timeout is None else ui_timeout
            if ui_timeout == Timeout.ZERO:
                ui_timeout = 0
            elif ui_timeout == Timeout.TINY:
                ui_timeout = 1
            elif ui_timeout == Timeout.SHORT:
                ui_timeout = 3
            elif ui_timeout == Timeout.MEDIUM:
                ui_timeout = 5
            elif ui_timeout == Timeout.LONG:
                ui_timeout = 8
            return ui_timeout

        def get_text(self, error=True, index=None):
            try:
                text = (
                    self.viewV2.info["text"]
                    if index is None
                    else self.viewV2[index].info["text"]
                )
                if text is not None:
                    return text
            except uiautomator2.JSONRPCError as e:
                if error:
                    raise DeviceFacade.JsonRpcError(e)
                else:
                    return ""
            logger.debug("Object exists but doesn't contain any text.")
            return ""

        def get_selected(self) -> bool:
            try:
                if self.viewV2.exists():
                    return self.viewV2.info["selected"]
                logger.debug(
                    "Object has disappeared! Probably too short video which has been liked!"
                )
                return True
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def set_text(self, text: str, mode: Mode = Mode.TYPE) -> None:
            punct_list = string.punctuation
            try:
                # Always start with fast, non-FastIME set_text
                try:
                    self.deviceV2.set_fastinput_ime(False)
                except Exception:
                    pass

                self.viewV2.set_text(text)
                typed_text = self.viewV2.get_text()
                if typed_text == text:
                    DeviceFacade.sleep_mode(SleepTime.SHORT)
                    return

                # If TYPE requested, fall back to slow send_keys once
                if mode == Mode.TYPE:
                    self.click(sleep=SleepTime.TINY)
                    self.deviceV2.clear_text()
                    random_sleep(0.1, 0.3, modulable=False)
                    start = datetime.now()
                    sentences = text.splitlines()
                    for j, sentence in enumerate(sentences, start=1):
                        word_list = sentence.split()
                        n_words = len(word_list)
                        for n, word in enumerate(word_list, start=1):
                            i = 0
                            n_single_letters = randint(1, 2)
                            for char in word:
                                if i < n_single_letters:
                                    self.deviceV2.send_keys(char, clear=False)
                                    i += 1
                                else:
                                    if word[-1] in punct_list:
                                        self.deviceV2.send_keys(word[i:-1], clear=False)
                                        self.deviceV2.send_keys(word[-1], clear=False)
                                    else:
                                        self.deviceV2.send_keys(word[i:], clear=False)
                                    break
                            if n < n_words:
                                self.deviceV2.send_keys(" ", clear=False)
                        if j < len(sentences):
                            self.deviceV2.send_keys("\n")

                    typed_text = self.viewV2.get_text()
                    if typed_text == text:
                        logger.debug(
                            f"Text typed in: {(datetime.now()-start).total_seconds():.2f}s"
                        )
                        DeviceFacade.sleep_mode(SleepTime.TINY)
                        return

                # Final fallback: direct set_text again
                logger.warning("Failed to write in text field, retrying set_text.")
                self.viewV2.set_text(text)
                DeviceFacade.sleep_mode(SleepTime.TINY)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

    class JsonRpcError(Exception):
        pass

    class AppHasCrashed(Exception):
        pass
