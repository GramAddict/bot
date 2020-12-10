import logging
from enum import Enum, auto
from os import popen
from random import uniform
from re import search
from time import sleep
from GramAddict.core.utils import random_sleep

logger = logging.getLogger(__name__)

# How long we're waiting until UI element appears (loading content + animation)
UI_TIMEOUT_LONG = 5
UI_TIMEOUT_SHORT = 1


def create_device(device_id, version=2):
    logger.info(f"Using uiautomator v{version}")
    try:
        return DeviceFacade(version, device_id)
    except ImportError as e:
        logger.error(str(e))
        return None


class DeviceFacade:
    deviceV1 = None  # uiautomator
    deviceV2 = None  # uiautomator2

    def __init__(self, version, device_id):
        self.device_id = device_id
        if version == 1
            try:
                import uiautomator
                self.deviceV1 = uiautomator.device if device_id is None else uiautomator.Device(device_id)
            except ImportError:
                raise ImportError("Please install uiautomator: pip3 install uiautomator")
        else:
            try:
                import uiautomator2
                self.deviceV2 = (
                    uiautomator2.connect()
                    if device_id is None
                    else uiautomator2.connect(device_id)
                )
            except ImportError:
                raise ImportError("Please install uiautomator2: pip3 install uiautomator2")


    def find(self, *args, **kwargs):
        if self.deviceV1 is not None:
            import uiautomator
            try:
                view = self.deviceV1(*args, **kwargs)
            except uiautomator.JsonRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(version=1, view=view, device=self.deviceV1)
        else:
            import uiautomator2
            try:
                view = self.deviceV2(*args, **kwargs)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
            return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

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
        if self.deviceV1 is not None:
            xml_dump = self.deviceV1.dump()
        else:
            xml_dump = self.deviceV2.dump_hierarchy()

        with open(path, 'w', encoding="utf-8") as outfile:
            outfile.write(xml_dump)

    def press_power(self):
        if self.deviceV1 is not None:
            self.deviceV1.press.power()
        else:
            self.deviceV2.press("power")

    def is_screen_locked(self):
        status = popen(
            f"adb {'' if self.device_id is None else ('-s '+ self.device_id)} shell dumpsys window"
        )
        data = status.read()
        flag = search("mDreamingLockscreen=(true|false)", data)
        return True if flag.group(1) == "true" else False

    def is_alive(self):
        # v2 only - for atx_agent
        return self.deviceV2._is_alive()

    def wake_up(self):
        """ Make sure agent is alive or bring it back up before starting. """
        # v2 only - for atx_agent
        if self.deviceV2 is not None:
            attempts = 0
            while not self.is_alive() and attempts < 5:
                self.get_info()
                attempts += 1

    def unlock(self):
        self.swipe(DeviceFacade.Direction.TOP, 0.8)
        random_sleep(1, 1)
        if self.is_screen_locked():
            self.swipe(DeviceFacade.Direction.RIGHT, 0.8)

    def screen_off(self):
        if self.deviceV1 is not None:
            self.deviceV1.screen.off()
        else:
            self.deviceV2.screen_off()

    # TODO: uia1 only does swipe based on element. not sure how to handle
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
        self.deviceV2.swipe_ext(swipe_dir, scale=scale)

    def swipe_points(self, sx, sy, ex, ey):
        if self.deviceV1 is not None:
            import uiautomator
            try:
                self.deviceV1.swipe(sx, sy, ex, ey)
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
        else:
            import uiautomator2
            try:
                self.deviceV2.swipe_points([[sx, sy], [ex, ey]], uniform(0.2, 0.6))
            except uiautomator2.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)


    def get_info(self):
        # {'currentPackageName': 'net.oneplus.launcher', 'displayHeight': 1920, 'displayRotation': 0, 'displaySizeDpX': 411,
        # 'displaySizeDpY': 731, 'displayWidth': 1080, 'productName': 'OnePlus5', '
        #  screenOn': True, 'sdkInt': 27, 'naturalOrientation': True}
        if self.deviceV1 is not None:
            return self.deviceV1.info
        else:
            return self.deviceV2.info
        

    class View:
        deviceV1: Device = None  # uiautomator
        deviceV2: Device = None  # uiautomator2
        viewV1 = None  # uiautomator
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
            if self.viewV1 is not None:
                import uiautomator
                try:
                    for item in self.viewV1:
                        children.append(DeviceFacade.View(version=1, view=item, device=self.deviceV1))
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                import uiautomator2
                try:
                    for item in self.viewV2:
                        children.append(DeviceFacade.View(version=2, view=item, device=self.deviceV2))
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
                return DeviceFacade.View(version=1, view=view, device=self.deviceV1)
            else:
                import uiautomator2
                try:
                    view = self.viewV2.child(*args, **kwargs)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def left(self, *args, **kwargs):
            if self.viewV1 is not None:
                import uiautomator
                try:
                    view = self.viewV1.left(*args, **kwargs)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=1, view=view, device=self.deviceV1)
            else:
                import uiautomator2
                try:
                    view = self.viewV2.left(*args, **kwargs)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def right(self, *args, **kwargs):
            if self.viewV1 is not None:
                import uiautomator
                try:
                    view = self.viewV1.right(*args, **kwargs)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=1, view=view, device=self.deviceV1)
            else:
                import uiautomator2
                try:
                    view = self.viewV2.right(*args, **kwargs)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def up(self, *args, **kwargs):
            if self.viewV1 is not None:
                import uiautomator
                try:
                    view = self.viewV1.up(*args, **kwargs)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=1, view=view, device=self.deviceV1)
            else:
                import uiautomator2
                try:
                    view = self.viewV2.up(*args, **kwargs)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=2, view=view, device=self.deviceV2)

        def down(self, *args, **kwargs):
            if self.viewV1 is not None:
                import uiautomator
                try:
                    view = self.viewV1.down(*args, **kwargs)
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=1, view=view, device=self.deviceV1)
            else:
                import uiautomator2
                try:
                    view = self.viewV2.down(*args, **kwargs)
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                return DeviceFacade.View(version=2, view=view, device=self.deviceV2)


        def click(self, mode=None):
            if self.viewV1 is not None:
                import uiautomator
                try:
                    self.viewV1.click.wait()
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
            else:
                mode = self.Location.WHOLE if mode == None else mode
                x_abs = -1
                y_abs = -1
                if mode == self.Location.WHOLE:
                    x_offset = uniform(0.15, 0.85)
                    y_offset = uniform(0.15, 0.85)

                elif mode == self.Location.LEFT:
                    x_offset = uniform(0.15, 0.4)
                    y_offset = uniform(0.15, 0.85)

                elif mode == self.Location.CENTER:
                    x_offset = uniform(0.4, 0.6)
                    y_offset = uniform(0.15, 0.85)

                elif mode == self.Location.RIGHT:
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
            if self.viewV1 is not None:
                import uiautomator
                config = self.deviceV1.server.jsonrpc.getConfigurator()
                config['actionAcknowledgmentTimeout'] = 40
                self.deviceV1.server.jsonrpc.setConfigurator(config)
                try:
                    self.viewV1.click()
                    self.viewV1.click()
                except uiautomator.JsonRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)
                config['actionAcknowledgmentTimeout'] = 3000
                self.deviceV1.server.jsonrpc.setConfigurator(config)
            else:
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

        def fling(self, direction):
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
                    return self.viewV2.info['bounds']
                except uiautomator2.JSONRPCError as e:
                    raise DeviceFacade.JsonRpcError(e)

        def get_text(self, retry=True):
            max_attempts = 1 if not retry else 3
            attempts = 0
            while attempts < max_attempts:
                attempts += 1
                if self.viewV1 is not None:
                    import uiautomator
                    try:
                        text = self.viewV1.text
                        if text == None:
                            logger.debug(
                                "Could not get text. Waiting 2 seconds and trying again..."
                            )
                            sleep(2)  # wait 2 seconds and retry
                        else:
                            return text
                    except uiautomator.JsonRPCError as e:
                        raise DeviceFacade.JsonRpcError(e)
                else:
                    import uiautomator2
                    try:
                        text = self.viewV2.info['text']
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
            return ""

        def get_selected(self) -> bool:

        if self.viewV1 is not None:
            try:
                return self.viewV1.info["selected"]
            except uiautomator.JSONRPCError as e:
                raise DeviceFacade.JsonRpcError(e)
        else:
            try:
                return self.viewV2.info["selected"]
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

        class Location(Enum):
            WHOLE = auto()
            CENTER = auto()
            BOTTOM = auto()
            RIGHT = auto()
            LEFT = auto()

    class Direction(Enum):
        TOP = auto()
        BOTTOM = auto()
        RIGHT = auto()
        LEFT = auto()

    class JsonRpcError(Exception):
        pass
