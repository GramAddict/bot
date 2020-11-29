import logging
from enum import Enum, auto
from random import uniform
from time import sleep

import uiautomator2
from uiautomator2 import Device

logger = logging.getLogger(__name__)

# How long we're waiting until UI element appears (loading content + animation)
UI_TIMEOUT_LONG = 5
UI_TIMEOUT_SHORT = 1


def create_device(device_id):
    logger.debug("Using uiautomator v2")
    try:
        return DeviceFacade(device_id)
    except ImportError as e:
        logger.error(str(e))
        return None


class DeviceFacade:
    deviceV2 = None  # uiautomator2

    def __init__(self, device_id):
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
        return DeviceFacade.View(view=view, device=self.deviceV2)

    def back(self):
        self.deviceV2.press("back")

    def screenshot(self, path):
        self.deviceV2.screenshot(path)

    def dump_hierarchy(self, path):
        xml_dump = ""
        xml_dump = self.deviceV2.dump_hierarchy()

        with open(path, "w", encoding="utf-8") as outfile:
            outfile.write(xml_dump)

    def swipe(self, direction: "DeviceFacade.Direction", scale=0.5):
        """Swipe finger in the `direction`.
        Scale is the sliding distance. Default to 50% of the screen width
        """
        swipe_dir = ""
        if direction == DeviceFacade.Direction.TOP:
            swipe_dir = "up"
        elif direction == DeviceFacade.Direction.BOTTOM:
            swipe_dir = "up"
        elif direction == DeviceFacade.Direction.LEFT:
            swipe_dir = "left"
        elif direction == DeviceFacade.Direction.BOTTOM:
            swipe_dir = "down"

        logger.debug(f"Swipe {swipe_dir}, scale={scale}")
        self.deviceV2.swipe_ext(swipe_dir, scale=scale)

    def get_info(self):
        # {'currentPackageName': 'net.oneplus.launcher', 'displayHeight': 1920, 'displayRotation': 0, 'displaySizeDpX': 411,
        # 'displaySizeDpY': 731, 'displayWidth': 1080, 'productName': 'OnePlus5', '
        #  screenOn': True, 'sdkInt': 27, 'naturalOrientation': True}
        window = self.deviceV2.window_size()
        d = self.deviceV2.info
        d["windowWidth"] = window[0]
        d["windowHeight"] = window[1]
        return d

    class View:
        deviceV2: Device = None  # uiautomator2
        viewV2 = None  # uiautomator2

        def __init__(self, view, device):
            self.viewV2 = view
            self.deviceV2 = device

        def __iter__(self):
            children = []

            try:
                for item in self.viewV2:
                    children.append(DeviceFacade.View(view=item, device=self.deviceV2))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return iter(children)

        def child(self, *args, **kwargs):

            try:
                view = self.viewV2.child(*args, **kwargs)
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

        def click(self, mode="whole"):
            x_abs = -1
            y_abs = -1
            if mode == "whole":
                x_offset = uniform(0.15, 0.85)
                y_offset = uniform(0.15, 0.85)

            elif mode == "left":
                x_offset = uniform(0.15, 0.4)
                y_offset = uniform(0.15, 0.85)

            elif mode == "center":
                x_offset = uniform(0.4, 0.6)
                y_offset = uniform(0.15, 0.85)

            elif mode == "right":
                x_offset = uniform(0.6, 0.85)
                y_offset = uniform(0.15, 0.85)
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
                logger.debug(f"Single click ({x_abs}, {y_abs})")
                self.viewV2.click(UI_TIMEOUT_LONG, offset=(x_offset, y_offset))

            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def double_click(self, padding=0.3):
            """Double click randomly in the selected view using padding
            padding: % of how far from the borders we want the double
                    click to happen.
            """
            visible_bounds = self.get_bounds()
            horizontal_len = visible_bounds["right"] - visible_bounds["left"]
            vertical_len = visible_bounds["bottom"] - visible_bounds["top"]
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
            time_between_clicks = uniform(0.050, 0.200)

            try:
                logger.debug(
                    f"Double click in x={random_x}; y={random_y} with t={int(time_between_clicks*1000)}ms"
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

        def exists(self, quick=False):

            try:
                # Currently the methods left, rigth, up and down from
                # uiautomator2 return None when a Selector does not exist.
                # All other selectors return an UiObject with exists() == False.
                # We will open a ticket to uiautomator2 to fix this incosistency.
                if self.viewV2 == None:
                    return False

                return self.viewV2.exists(
                    UI_TIMEOUT_SHORT if quick else UI_TIMEOUT_LONG
                )
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def wait(self):

            try:
                return self.viewV2.wait(timeout=UI_TIMEOUT_LONG)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def get_bounds(self):

            try:
                return self.viewV2.info["bounds"]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def get_text(self, retry=True):
            max_attempts = 1 if not retry else 3
            attempts = 0
            while attempts < max_attempts:
                attempts += 1
                try:
                    text = self.viewV2.info["text"]
                    if text == None:
                        logger.debug(
                            "Could not get text. Waiting 2 seconds and trying again..."
                        )
                        sleep(2)  # wait 2 seconds and retry
                    else:
                        return text
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            logger.error(
                f"Attempted to get text {attempts} times. You may have a slow network or are experiencing another problem."
            )
            return 0

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

    class Direction(Enum):
        TOP = auto()
        BOTTOM = auto()
        RIGHT = auto()
        LEFT = auto()

    class JsonRpcError(Exception):
        pass
