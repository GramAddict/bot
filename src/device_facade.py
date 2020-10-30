from enum import Enum, unique
import random
from src.utils import *

# How long we're waiting until UI element appears (loading content + animation)
UI_TIMEOUT_LONG = 5
UI_TIMEOUT_SHORT = 1


def create_device(is_old, device_id):
    print("Using uiautomator v" + ("1" if is_old else "2"))
    try:
        return DeviceFacade(is_old, device_id)
    except ImportError as e:
        print(COLOR_FAIL + str(e) + COLOR_ENDC)
        return None


class DeviceFacade:
    deviceV1 = None  # uiautomator
    deviceV2 = None  # uiautomator2

    def __init__(self, is_old, device_id):
        if is_old:
            try:
                import uiautomator

                self.deviceV1 = (
                    uiautomator.device
                    if device_id is None
                    else uiautomator.Device(device_id)
                )
            except ImportError:
                raise ImportError(
                    "Please install uiautomator: pip3 install uiautomator"
                )
        else:
            try:
                import uiautomator2

                self.deviceV2 = (
                    uiautomator2.connect()
                    if device_id is None
                    else uiautomator2.connect(device_id)
                )
            except ImportError:
                raise ImportError(
                    "Please install uiautomator2: pip3 install uiautomator2"
                )

    def is_old(self):
        return self.deviceV1 is not None

    def find(self, *args, **kwargs):
        if self.deviceV1 is not None:
            import uiautomator

            try:
                view = self.deviceV1(*args, **kwargs)
            except uiautomator.JsonRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(is_old=True, view=view, device=self.deviceV1)
        else:
            import uiautomator2

            try:
                view = self.deviceV2(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(is_old=False, view=view, device=self.deviceV2)

    def back(self):
        if self.deviceV1 is not None:
            self.deviceV1.press.back()
        else:
            self.deviceV2.press("back")

    def screenshot(self, path):
        if self.deviceV1 is not None:
            self.deviceV1.screenshot(path)
        else:
            self.deviceV2.screenshot(path)

    def dump_hierarchy(self, path):
        xml_dump = ""
        if self.deviceV1 is not None:
            xml_dump = self.deviceV1.dump()
        else:
            xml_dump = self.deviceV2.dump_hierarchy()

        with open(path, "w") as outfile:
            outfile.write(xml_dump)

    class View:
        deviceV1 = None  # uiautomator
        viewV1 = None  # uiautomator
        deviceV2 = None  # uiautomator2
        viewV2 = None  # uiautomator2

        def __init__(self, is_old, view, device):
            if is_old:
                self.viewV1 = view
                self.deviceV1 = device
            else:
                self.viewV2 = view
                self.deviceV2 = device

        def __iter__(self):
            children = []
            if self.viewV1 is not None:
                import uiautomator

                try:
                    for item in self.viewV1:
                        children.append(
                            DeviceFacade.View(
                                is_old=True, view=item, device=self.deviceV1
                            )
                        )
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2

                try:
                    for item in self.viewV2:
                        children.append(
                            DeviceFacade.View(
                                is_old=False, view=item, device=self.deviceV2
                            )
                        )
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            return iter(children)

        def child(self, *args, **kwargs):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    view = self.viewV1.child(*args, **kwargs)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(is_old=True, view=view, device=self.deviceV1)
            else:
                import uiautomator2

                try:
                    view = self.viewV2.child(*args, **kwargs)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(is_old=False, view=view, device=self.deviceV2)

        def right(self, *args, **kwargs):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    view = self.viewV1.right(*args, **kwargs)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(is_old=True, view=view, device=self.deviceV1)
            else:
                import uiautomator2

                try:
                    view = self.viewV2.right(*args, **kwargs)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(is_old=False, view=view, device=self.deviceV2)

        def click(self, mode="whole"):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    self.viewV1.click.wait()
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2

                try:
                    if mode == "whole":
                        self.viewV2.click(
                            UI_TIMEOUT_LONG,
                            offset=(random.uniform(0.1, 0.9), random.uniform(0.1, 0.9)),
                        )
                    elif mode == "left":
                        self.viewV2.click(
                            UI_TIMEOUT_LONG,
                            offset=(random.uniform(0.1, 0.4), random.uniform(0.1, 0.9)),
                        )
                    elif mode == "center":
                        self.viewV2.click(
                            UI_TIMEOUT_LONG,
                            offset=(random.uniform(0.4, 0.6), random.uniform(0.1, 0.9)),
                        )
                    elif mode == "right":
                        self.viewV2.click(
                            UI_TIMEOUT_LONG,
                            offset=(random.uniform(0.6, 0.9), random.uniform(0.1, 0.9)),
                        )
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def double_click(self):
            if self.viewV1 is not None:
                self._double_click_v1()
            else:
                self._double_click_v2()

        def scroll(self, direction):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    if direction == DeviceFacade.Direction.TOP:
                        self.viewV1.scroll.toBeginning(max_swipes=1)
                    else:
                        self.viewV1.scroll.toEnd(max_swipes=1)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2

                try:
                    if direction == DeviceFacade.Direction.TOP:
                        self.viewV2.scroll.toBeginning(max_swipes=1)
                    else:
                        self.viewV2.scroll.toEnd(max_swipes=1)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def swipe(self, direction):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    if direction == DeviceFacade.Direction.TOP:
                        self.viewV1.fling.toBeginning(max_swipes=5)
                    else:
                        self.viewV1.fling.toEnd(max_swipes=5)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2

                try:
                    if direction == DeviceFacade.Direction.TOP:
                        self.viewV2.fling.toBeginning(max_swipes=5)
                    else:
                        self.viewV2.fling.toEnd(max_swipes=5)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def exists(self, quick=False):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    return self.viewV1.exists
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2

                try:
                    return self.viewV2.exists(
                        UI_TIMEOUT_SHORT if quick else UI_TIMEOUT_LONG
                    )
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def wait(self):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    self.deviceV1.wait.idle()
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return True
            else:
                import uiautomator2

                try:
                    return self.viewV2.wait(timeout=UI_TIMEOUT_LONG)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def get_bounds(self):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    return self.viewV1.bounds
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2

                try:
                    return self.viewV2.info["bounds"]
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def get_text(self):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    return self.viewV1.text
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2

                try:
                    return self.viewV2.info["text"]
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def set_text(self, text):
            if self.viewV1 is not None:
                import uiautomator

                try:
                    self.viewV1.set_text(text)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2

                try:
                    self.viewV2.set_text(text)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def _double_click_v1(self):
            import uiautomator

            config = self.deviceV1.server.jsonrpc.getConfigurator()
            config["actionAcknowledgmentTimeout"] = 40
            self.deviceV1.server.jsonrpc.setConfigurator(config)
            try:
                self.viewV1.click()
                self.viewV1.click()
            except uiautomator.JsonRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            config["actionAcknowledgmentTimeout"] = 3000
            self.deviceV1.server.jsonrpc.setConfigurator(config)

        def _double_click_v2(self):
            import uiautomator2

            visible_bounds = self.get_bounds()
            center_x = (visible_bounds["right"] - visible_bounds["left"]) / 2
            center_y = (visible_bounds["bottom"] - visible_bounds["top"]) / 2
            try:
                self.deviceV2.double_click(center_x, center_y, duration=0)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)

    @unique
    class Direction(Enum):
        TOP = 0
        BOTTOM = 1

    class JsonRpcError(Exception):
        pass
