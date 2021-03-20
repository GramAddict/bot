import logging
from enum import Enum, auto
from os import popen, listdir, getcwd
from random import uniform
from re import search
from subprocess import run
from time import sleep
from GramAddict.core.utils import random_sleep
import uiautomator2

logger = logging.getLogger(__name__)


def create_device(device_id):
    logger.info(f"Using uiautomator v2")
    try:
        return DeviceFacade(device_id)
    except ImportError as e:
        logger.error(str(e))
        return None


class DeviceFacade:
    deviceV2 = None  # uiautomator2

    def __init__(self, device_id):
        self.device_id = device_id
        try:
            self.deviceV2 = (
                uiautomator2.connect()
                if device_id is None
                else uiautomator2.connect(device_id)
            )
        except ImportError:
            raise ImportError("Please install uiautomator2: pip3 install uiautomator2")

    def find(self, *args, **kwargs):
        try:
            view = self.deviceV2(*args, **kwargs)
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)
        return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

    def back(self):
        logger.debug("Press back button.")
        self.deviceV2.press("back")

    def start_screenrecord(self, output="debug_0000.mp4", fps=10):
        mp4_files = [f for f in listdir(getcwd()) if f.endswith(".mp4")]
        if mp4_files != []:
            last_mp4 = mp4_files[-1]
            debug_number = "{0:0=4d}".format(int(last_mp4[-8:-4]) + 1)
            output = f"debug_{debug_number}.mp4"
        self.deviceV2.screenrecord(output, fps)
        logger.warning(
            f"Start screen recording: it will be saved as '{output}' in '{getcwd()}'"
        )

    def stop_screenrecord(self):
        if self.deviceV2.screenrecord.stop():
            mp4_files = [f for f in listdir(getcwd()) if f.endswith(".mp4")]
            if mp4_files != []:
                last_mp4 = mp4_files[-1]
                logger.warning(
                    f"Screen recorder has been stoped succesfully! File '{last_mp4}' available in '{getcwd()}'"
                )

    def screenshot(self, path):
        self.deviceV2.screenshot(path)

    def dump_hierarchy(self, path):
        xml_dump = self.deviceV2.dump_hierarchy()
        with open(path, "w", encoding="utf-8") as outfile:
            outfile.write(xml_dump)

    def press_power(self):
        self.deviceV2.press("power")

    def is_screen_locked(self):
        data = run(
            f"adb -s {self.deviceV2.serial} shell dumpsys window",
            encoding="utf-8",
            capture_output=True,
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
            capture_output=True,
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
        """ Make sure agent is alive or bring it back up before starting. """
        if self.deviceV2 is not None:
            attempts = 0
            while not self.is_alive() and attempts < 5:
                self.get_info()
                attempts += 1

    def unlock(self):
        self.swipe(DeviceFacade.Direction.TOP, 0.8)
        random_sleep(1, 1, False)
        if self.is_screen_locked():
            self.swipe(DeviceFacade.Direction.RIGHT, 0.8)

    def screen_off(self):
        self.deviceV2.screen_off()

    def get_orientation(self):
        try:
            return self.deviceV2._get_orientation()
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    def window_size(self):
        """ return (width, height) """
        try:
            self.deviceV2.window_size()
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    def swipe(self, direction: "DeviceFacade.Direction", scale=0.5):
        """Swipe finger in the `direction`.
        Scale is the sliding distance. Default to 50% of the screen width
        """
        swipe_dir = ""
        if direction == DeviceFacade.Direction.TOP:
            swipe_dir = "up"
        elif direction == DeviceFacade.Direction.RIGHT:
            swipe_dir = "right"
        elif direction == DeviceFacade.Direction.LEFT:
            swipe_dir = "left"
        elif direction == DeviceFacade.Direction.BOTTOM:
            swipe_dir = "down"

        logger.debug(f"Swipe {swipe_dir}, scale={scale}")

        try:
            self.deviceV2.swipe_ext(swipe_dir, scale=scale)
        except uiautomator2.JSONRPCError as e:
            raise DeviceFacade.JsonRpcError(e)

    def swipe_points(self, sx, sy, ex, ey, random_x=True, random_y=True):
        if random_x:
            sx = sx * uniform(0.60, 1.40)
            ex = ex * uniform(0.85, 1.15)
        if random_y:
            ey = ey * uniform(0.98, 1.02)
        try:
            self.deviceV2.swipe_points([[sx, sy], [ex, ey]], uniform(0.4, 0.6))
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

    class View:
        deviceV2 = None  # uiautomator2
        viewV2 = None  # uiautomator2

        def __init__(self, version, view, device):
            if version == 1:
                self.viewV1 = view
                self.deviceV1 = device
            else:
                self.viewV2 = view
                self.deviceV2 = device

        def __iter__(self):
            children = []
            try:
                for item in self.viewV2:
                    children.append(
                        DeviceFacade.View(version=2, view=item, device=self.deviceV2)
                    )
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
            return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def sibling(self, *args, **kwargs):
            try:
                view = self.viewV2.sibling(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def left(self, *args, **kwargs):
            try:
                view = self.viewV2.left(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def right(self, *args, **kwargs):
            try:
                view = self.viewV2.right(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def up(self, *args, **kwargs):
            try:
                view = self.viewV2.up(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def down(self, *args, **kwargs):
            try:
                view = self.viewV2.down(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def click_gone(self, maxretry=3, interval=1.0):
            try:
                self.viewV2.click_gone(maxretry, interval)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def click(self, mode=None):
            mode = DeviceFacade.Location.WHOLE if mode is None else mode
            x_abs = -1
            y_abs = -1
            if mode == DeviceFacade.Location.WHOLE:
                x_offset = uniform(0.15, 0.85)
                y_offset = uniform(0.15, 0.85)

            elif mode == DeviceFacade.Location.LEFT:
                x_offset = uniform(0.15, 0.4)
                y_offset = uniform(0.15, 0.85)

            elif mode == DeviceFacade.Location.CENTER:
                x_offset = uniform(0.4, 0.6)
                y_offset = uniform(0.15, 0.85)

            elif mode == DeviceFacade.Location.RIGHT:
                x_offset = uniform(0.6, 0.85)
                y_offset = uniform(0.15, 0.85)

            elif mode == DeviceFacade.Location.RIGHTEDGE:
                x_offset = uniform(0.8, 0.9)
                y_offset = uniform(0.30, 0.70)

            elif mode == DeviceFacade.Location.BOTTOMRIGHT:
                x_offset = uniform(0.8, 0.9)
                y_offset = uniform(0.8, 0.9)

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
                logger.debug(f"Single click ({x_abs},{y_abs})")
                self.viewV2.click(
                    self.get_ui_timeout(DeviceFacade.Timeout.LONG),
                    offset=(x_offset, y_offset),
                )

            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

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
            horizintal_padding = int(padding * horizontal_len)
            vertical_padding = int(padding * vertical_len)
            random_x = int(
                uniform(
                    visible_bounds["left"] + horizintal_padding,
                    visible_bounds["right"] - horizintal_padding,
                )
            )
            random_y = int(
                uniform(
                    visible_bounds["top"] + vertical_padding,
                    visible_bounds["bottom"] - vertical_padding,
                )
            )

            logger.debug(
                f"Available surface for double click ({visible_bounds['left']}-{visible_bounds['right']},{visible_bounds['top']}-{visible_bounds['bottom']})"
            )
            time_between_clicks = uniform(0.050, 0.170)

            try:
                logger.debug(
                    f"Double click in ({random_x},{random_y}) with t={int(time_between_clicks*1000)}ms"
                )
                self.deviceV2.double_click(
                    random_x, random_y, duration=time_between_clicks
                )
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def scroll(self, direction):
            try:
                if direction == DeviceFacade.Direction.TOP:
                    self.viewV2.scroll.toBeginning(max_swipes=1)
                else:
                    self.viewV2.scroll.toEnd(max_swipes=1)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def fling(self, direction):
            try:
                if direction == DeviceFacade.Direction.TOP:
                    self.viewV2.fling.toBeginning(max_swipes=5)
                else:
                    self.viewV2.fling.toEnd(max_swipes=5)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def exists(self, ui_timeout=None):
            try:
                # Currently the methods left, rigth, up and down from
                # uiautomator2 return None when a Selector does not exist.
                # All other selectors return an UiObject with exists() == False.
                # We will open a ticket to uiautomator2 to fix this incosistency.
                if self.viewV2 is None:
                    return False
                return self.viewV2.exists(self.get_ui_timeout(ui_timeout))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def wait(self, ui_timeout=None):
            try:
                return self.viewV2.wait(timeout=self.get_ui_timeout(ui_timeout))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def get_bounds(self):
            try:
                return self.viewV2.info["bounds"]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        @staticmethod
        def get_ui_timeout(ui_timeout):
            ui_timeout = DeviceFacade.Timeout.ZERO if ui_timeout is None else ui_timeout
            if ui_timeout == DeviceFacade.Timeout.ZERO:
                ui_timeout = 0
            elif ui_timeout == DeviceFacade.Timeout.SHORT:
                ui_timeout = 3
            elif ui_timeout == DeviceFacade.Timeout.MEDIUM:
                ui_timeout = 5
            elif ui_timeout == DeviceFacade.Timeout.LONG:
                ui_timeout = 8
            return ui_timeout

        def get_text(self, retry=True, error=True):
            max_attempts = 1 if not retry else 3
            attempts = 0
            while attempts < max_attempts:
                attempts += 1
                try:
                    text = self.viewV2.info["text"]
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
            try:
                self.viewV2.set_text(text)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

    class Location(Enum):
        WHOLE = auto()
        CENTER = auto()
        BOTTOM = auto()
        RIGHT = auto()
        LEFT = auto()
        BOTTOMRIGHT = auto()
        RIGHTEDGE = auto()

    class Timeout(Enum):
        ZERO = auto()
        SHORT = auto()
        MEDIUM = auto()
        LONG = auto()

    class Direction(Enum):
        TOP = auto()
        BOTTOM = auto()
        RIGHT = auto()
        LEFT = auto()

    class JsonRpcError(Exception):
        pass
