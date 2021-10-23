import logging
import string
from datetime import datetime
from enum import Enum, auto
from os import getcwd, listdir
from random import randint, uniform
from re import search
from subprocess import PIPE, run
from time import sleep

import uiautomator2

from GramAddict.core.utils import random_sleep

logger = logging.getLogger(__name__)


def create_device(device_id):
    try:
        return DeviceFacade(device_id)
    except ImportError as e:
        logger.error(str(e))
        return None


def get_device_info(device):
    logger.debug(
        f"Phone Name: {device.get_info()['productName']}, SDK Version: {device.get_info()['sdkInt']}"
    )
    if int(device.get_info()["sdkInt"]) < 19:
        logger.warning("Only Android 4.4+ (SDK 19+) devices are supported!")
    logger.debug(
        f"Screen dimension: {device.get_info()['displayWidth']}x{device.get_info()['displayHeight']}"
    )
    logger.debug(
        f"Screen resolution: {device.get_info()['displaySizeDpX']}x{device.get_info()['displaySizeDpY']}"
    )
    logger.debug(f"Device ID: {device.deviceV2.serial}")


class Timeout(Enum):
    ZERO = auto()
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
    RIGHTEDGE = auto()
    TOPLEFT = auto()


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    RIGHT = auto()
    LEFT = auto()


class DeviceFacade:
    deviceV2 = None  # uiautomator2

    def __init__(self, device_id):
        self.device_id = device_id
        device_ip = None
        try:
            if "." not in device_id:
                self.deviceV2 = (
                    uiautomator2.connect()
                    if device_id is None
                    else uiautomator2.connect(device_id)
                )
            else:
                splitted = device_id.split(":")
                port = splitted[1] if len(splitted) == 2 else "7912"
                self.deviveV2 = uiautomator2.connect_adb_wifi(f"{device_ip}:{port}")
        except ImportError:
            raise ImportError("Please install uiautomator2: pip3 install uiautomator2")

    def find(
        self,
        index=None,
        *args,
        **kwargs,
    ):
        try:
            view = self.deviceV2(*args, **kwargs)
            if index is not None and view.count > 1:
                view = self.deviceV2(*args, **kwargs)[index]
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)
        return DeviceFacade.View(view=view, device=self.deviceV2)

    def back(self):
        logger.debug("Press back button.")
        self.deviceV2.press("back")
        random_sleep()

    def start_screenrecord(self, output="debug_0000.mp4", fps=20):
        mp4_files = [f for f in listdir(getcwd()) if f.endswith(".mp4")]
        if mp4_files != []:
            last_mp4 = mp4_files[-1]
            debug_number = "{0:0=4d}".format(int(last_mp4[-8:-4]) + 1)
            output = f"debug_{debug_number}.mp4"
        self.deviceV2.screenrecord(output, fps)
        logger.warning("Screen recording has been started.")

    def stop_screenrecord(self, crash=True):
        if self.deviceV2.screenrecord.stop(crash=crash):
            logger.warning("Screen recorder has been stopped succesfully!")

    def screenshot(self, path):
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
            return True if flag is not None and flag.group(1) == "true" else False
        else:
            logger.debug(
                f"'adb -s {self.deviceV2.serial} shell dumpsys window' returns nothing!"
            )
            return None

    def is_keyboard_show(serial):
        data = run(
            f"adb -s {serial} shell dumpsys input_method",
            encoding="utf-8",
            stdout=PIPE,
            stderr=PIPE,
            shell=True,
        )
        if data != "":
            flag = search("mInputShown=(true|false)", data.stdout)
            return True if flag.group(1) == "true" else False
        else:
            logger.debug(
                f"'adb -s {serial} shell dumpsys input_method' returns nothing!"
            )
            return None

    def is_alive(self):
        return self.deviceV2._is_alive()

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

    def swipe(self, direction: "Direction", scale=0.5):
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
                for item in self.viewV2:
                    children.append(DeviceFacade.View(view=item, device=self.deviceV2))
                return iter(children)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def ui_info(self):
            try:
                return self.viewV2.info
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

        def click(self, mode=None, sleep=None, coord=[], crash_report_if_fails=True):
            mode = Location.WHOLE if mode is None else mode
            x_abs = -1
            y_abs = -1
            if mode == Location.WHOLE:
                x_offset = uniform(0.15, 0.85)
                y_offset = uniform(0.15, 0.85)

            elif mode == Location.LEFT:
                x_offset = uniform(0.15, 0.4)
                y_offset = uniform(0.15, 0.85)

            elif mode == Location.CENTER:
                x_offset = uniform(0.4, 0.6)
                y_offset = uniform(0.15, 0.85)

            elif mode == Location.RIGHT:
                x_offset = uniform(0.6, 0.85)
                y_offset = uniform(0.15, 0.85)

            elif mode == Location.RIGHTEDGE:
                x_offset = uniform(0.8, 0.9)
                y_offset = uniform(0.30, 0.70)

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

        def click_retry(self, mode=None, sleep=None, coord=[], maxretry=2):
            """return True if successfully open the element, else False"""
            self.click(mode, sleep, coord)

            while maxretry > 0:
                # we wait a little bit more before try again
                random_sleep(2, 4, modulable=False)
                if not self.exists():
                    return True
                logger.debug("UI element didn't open! Try again..")
                self.click(mode, sleep, coord)
                maxretry -= 1
            if not self.exists():
                return True
            else:
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

            time_between_clicks = uniform(0.050, 0.140)

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

        def exists(self, ui_timeout=None):
            try:
                # Currently the methods left, right, up and down from
                # uiautomator2 return None when a Selector does not exist.
                # All other selectors return an UiObject with exists() == False.
                # We will open a ticket to uiautomator2 to fix this inconsistency.
                if self.viewV2 is None:
                    return False
                exists = self.viewV2.exists(self.get_ui_timeout(ui_timeout))
                if hasattr(self.viewV2, "count"):
                    if not exists and self.viewV2.count >= 1:
                        logger.debug(
                            f"BUG: exists return False, but there is/are {self.viewV2.count} element(s)!"
                        )
                        # More info about that: https://github.com/openatx/uiautomator2/issues/689"
                        return False
                return exists
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def count_items(self):
            try:
                return self.viewV2.count
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def wait(self, ui_timeout=None):
            try:
                return self.viewV2.wait(timeout=self.get_ui_timeout(ui_timeout))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def wait_gone(self, ui_timeout=None):
            try:
                return self.viewV2.wait_gone(timeout=self.get_ui_timeout(ui_timeout))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def get_bounds(self):
            try:
                return self.viewV2.info["bounds"]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def get_property(self, property):
            try:
                return self.viewV2.info[property]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        @staticmethod
        def get_ui_timeout(ui_timeout):
            ui_timeout = Timeout.ZERO if ui_timeout is None else ui_timeout
            if ui_timeout == Timeout.ZERO:
                ui_timeout = 0
            elif ui_timeout == Timeout.SHORT:
                ui_timeout = 3
            elif ui_timeout == Timeout.MEDIUM:
                ui_timeout = 5
            elif ui_timeout == Timeout.LONG:
                ui_timeout = 8
            return ui_timeout

        def get_text(self, retry=True, error=True, index=None):
            max_attempts = 1 if not retry else 3
            attempts = 0
            while attempts < max_attempts:
                attempts += 1
                try:
                    text = (
                        self.viewV2.info["text"]
                        if index is None
                        else self.viewV2[index].info["text"]
                    )
                    if text is None:
                        logger.debug(
                            "Could not get text. Waiting 2 seconds and trying again..."
                        )
                        sleep(2)  # wait 2 seconds and retry
                    else:
                        return text
                except uiautomator2.JSONRPCError as e:
                    if error:
                        raise DeviceFacade.JsonRpcError(e)
                    else:
                        return ""
            logger.error(
                f"Attempted to get text {attempts} times. You may have a slow network or are experiencing another problem."
            )
            return ""

        def get_selected(self) -> bool:
            try:
                return self.viewV2.info["selected"]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def set_text(self, text):
            punct_list = string.punctuation
            try:
                self.click(sleep=SleepTime.SHORT)
                self.deviceV2.clear_text()
                start = datetime.now()
                random_sleep(0.3, 1, modulable=False)
                word_list = text.split()
                n_words = len(word_list)
                i = 0
                n = 1
                for word in word_list:
                    n_single_letters = randint(1, 3)
                    for char in word:
                        if i < n_single_letters:
                            self.deviceV2.send_keys(char, clear=False)
                            random_sleep(0.01, 0.1, modulable=False, logging=False)
                            i += 1
                        else:
                            if word[-1] in punct_list:
                                self.deviceV2.send_keys(word[i:-1], clear=False)
                                random_sleep(0.01, 0.1, modulable=False, logging=False)
                                self.deviceV2.send_keys(word[-1], clear=False)
                                random_sleep(0.01, 0.1, modulable=False, logging=False)
                            else:
                                self.deviceV2.send_keys(word[i:], clear=False)
                                random_sleep(0.01, 0.1, modulable=False, logging=False)
                            break
                    if n < n_words:
                        self.deviceV2.send_keys(" ", clear=False)
                        random_sleep(0.01, 0.1, modulable=False, logging=False)

                    i = 0
                    n += 1
                typed_text = self.viewV2.get_text()
                if (
                    typed_text is None
                    or typed_text == "Add a comment…"
                    or typed_text == "Message…"
                    or typed_text == ""
                    or typed_text.startswith("Comment as ")
                ):
                    logger.warning(
                        "Failed to write in text field, let's try in the old way.."
                    )
                    self.viewV2.set_text(text)
                else:
                    logger.debug(
                        f"Text typed in: {(datetime.now()-start).total_seconds():.2f}s"
                    )
                DeviceFacade.sleep_mode(SleepTime.SHORT)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

    class JsonRpcError(Exception):
        pass
