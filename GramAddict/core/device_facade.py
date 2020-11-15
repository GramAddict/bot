import logging
from enum import Enum, unique
from random import uniform
from time import sleep

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

        def right(self, *args, **kwargs):

            try:
                view = self.viewV2.right(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(view=view, device=self.deviceV2)  # is_old =false

        def click(self, mode="whole"):

            try:
                if mode == "whole":
                    self.viewV2.click(
                        UI_TIMEOUT_LONG,
                        offset=(uniform(0.15, 0.85), uniform(0.15, 0.85)),
                    )
                elif mode == "left":
                    self.viewV2.click(
                        UI_TIMEOUT_LONG,
                        offset=(uniform(0.15, 0.4), uniform(0.15, 0.85)),
                    )
                elif mode == "center":
                    self.viewV2.click(
                        UI_TIMEOUT_LONG, offset=(uniform(0.4, 0.6), uniform(0.15, 0.85))
                    )
                elif mode == "right":
                    self.viewV2.click(
                        UI_TIMEOUT_LONG,
                        offset=(uniform(0.6, 0.85), uniform(0.15, 0.85)),
                    )
                elif mode == "bottom":
                    self.viewV2.click(
                        UI_TIMEOUT_LONG,
                        offset=(uniform(0.15, 0.85), uniform(0.6, 0.85)),
                    )
                elif mode == "top":
                    self.viewV2.click(
                        UI_TIMEOUT_LONG,
                        offset=(uniform(0.15, 0.85), uniform(0.15, 0.4)),
                    )
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def double_click(self):
            self._double_click_v2()

        def scroll(self, direction):

            try:
                if direction == DeviceFacade.Direction.TOP:
                    self.viewV2.scroll.toBeginning(max_swipes=1)
                else:
                    self.viewV2.scroll.toEnd(max_swipes=1)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

        def swipe(self, direction):

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

        def _double_click_v2(self):
            offset_x = uniform(0.15, 0.85)
            offset_y = uniform(0.15, 0.85)
            sleep_between_clicks = uniform(0.0, 0.2)
            try:
                self.viewV2.click(offset=(offset_x, offset_y))
                sleep(sleep_between_clicks)
                self.viewV2.click(offset=(offset_x, offset_y))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

    @unique
    class Direction(Enum):
        TOP = 0
        BOTTOM = 1

    class JsonRpcError(Exception):
        pass
