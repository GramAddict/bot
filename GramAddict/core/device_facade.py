import logging
from enum import Enum, auto
from random import uniform

import uiautomator2

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
        return self.deviceV2.info

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

            try:
                x_abs = -1
                y_abs = -1
                visible_bounds = self.get_bounds()
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

        def double_click(self):
            visible_bounds = self.get_bounds()
            random_x = int(
                uniform(visible_bounds["left"] + 1, visible_bounds["right"] - 1)
            )
            random_y = int(
                uniform(visible_bounds["top"] + 1, visible_bounds["bottom"] - 1)
            )
            try:
                logger.debug(f"Double click in x={random_x}; y={random_y}")
                self.deviceV2.double_click(
                    random_x, random_y, duration=uniform(0, 0.200)
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

        def get_text(self):

            try:
                return self.viewV2.info["text"]
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

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
