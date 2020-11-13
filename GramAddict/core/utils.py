import logging
import os
import subprocess
import re
import shutil
import sys
from datetime import datetime
from random import randint, uniform
from time import sleep

from colorama import Fore, Style
from GramAddict.core.log import get_logs

logger = logging.getLogger(__name__)

COLOR_HEADER = "\033[95m"
COLOR_OKBLUE = "\033[94m"
COLOR_OKGREEN = "\033[92m"
COLOR_WARNING = "\033[93m"
COLOR_DBG = "\033[90m"  # dark gray
COLOR_FAIL = "\033[91m"
COLOR_ENDC = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_UNDERLINE = "\033[4m"


def get_version():
    fin = open("GramAddict/version.txt")
    version = fin.readline().strip()
    fin.close()
    return version


def check_adb_connection(is_device_id_provided):
    stream = os.popen("adb devices")
    output = stream.read()
    devices_count = len(re.findall("device\n", output))
    stream.close()

    is_ok = True
    message = "That's ok."
    if devices_count == 0:
        is_ok = False
        message = "Cannot proceed."
    elif devices_count > 1 and not is_device_id_provided:
        is_ok = False
        message = "Use --device to specify a device."

    if is_ok:
        logger.debug(f"Connected devices via adb: {devices_count}. {message}")
    else:
        logger.error(f"Connected devices via adb: {devices_count}. {message}")

    return is_ok


def get_instagram_version():
    stream = os.popen("adb shell dumpsys package com.instagram.android")
    output = stream.read()
    version_match = re.findall("versionName=(\\S+)", output)
    if len(version_match) == 1:
        version = version_match[0]
    else:
        version = "not found"
    stream.close()
    return version


def open_instagram(device_id):
    logger.info("Open Instagram app")
    cmd = (
        "adb"
        + ("" if device_id is None else " -s " + device_id)
        + " shell am start -n com.instagram.android/com.instagram.mainactivity.MainActivity"
    )
    cmd_res = subprocess.run(cmd, capture_output=True, shell=True, encoding="utf8")
    err = cmd_res.stderr.strip()
    if err:
        logger.debug(err)
    random_sleep()


def close_instagram(device_id):
    logger.info("Close Instagram app")
    os.popen(
        "adb"
        + ("" if device_id is None else " -s " + device_id)
        + " shell am force-stop com.instagram.android"
    ).close()


def random_sleep():
    delay = uniform(1.0, 4.0)
    logger.debug(f"{str(delay)[0:4]}s sleep")
    sleep(delay)


def check_screen_on(device_id):
    status = os.popen(
        f"adb {''if device_id is None else ('-s '+ device_id)} shell dumpsys power"
    )
    data = status.read()
    flag = re.search("mWakefulness=(Awake|Asleep)", data)
    if flag.group(1) == "Asleep":
        return True
    else:
        return False


def check_screen_locked(device_id):
    status = os.popen(
        f"adb {''if device_id is None else ('-s '+ device_id)} shell dumpsys window"
    )
    data = status.read()
    flag = re.search("mDreamingLockscreen=(true|false)", data)
    if flag.group(1) == "true":
        return True
    else:
        return False


def screen_unlock(device_id, MENU_BUTTON):
    is_locked = check_screen_locked(device_id)
    if is_locked:
        logger.info("Device is locked! I'll try to unlock it!")
        os.popen(
            f"adb {''if device_id is None else ('-s '+ device_id)} shell input keyevent {MENU_BUTTON}"
        )
        sleep(2)
        if check_screen_locked(device_id):
            sys.exit(
                "Can't unlock your screen.. Maybe you've set a passcode.. Disable it or don't use this function!"
            )


def screen_sleep(device_id, mode):
    POWER_BUTTON = 26
    MENU_BUTTON = 82
    if mode == "on":
        is_not_awake = check_screen_on(device_id)
        if is_not_awake:
            os.popen(
                f"adb {''if device_id is None else ('-s '+ device_id)} shell input keyevent {POWER_BUTTON}"
            )
            logger.info("Device screen turned ON!")
            sleep(2)
            screen_unlock(device_id, MENU_BUTTON)
        else:
            logger.debug("Device screen already turned ON!")
            sleep(2)
            screen_unlock(device_id, MENU_BUTTON)
    else:
        os.popen(
            f"adb {''if device_id is None else ('-s '+ device_id)} shell input keyevent {POWER_BUTTON}"
        )
        logger.debug("Device screen turned OFF!")


def save_crash(device):
    global print_log

    directory_name = "Crash-" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    try:
        os.makedirs("crashes/" + directory_name + "/", exist_ok=False)
    except OSError:
        logger.error("Directory " + directory_name + " already exists.")
        return

    screenshot_format = ".png"
    try:
        device.screenshot(
            "crashes/" + directory_name + "/screenshot" + screenshot_format
        )
    except RuntimeError:
        logger.error("Cannot save screenshot.")

    view_hierarchy_format = ".xml"
    try:
        device.dump_hierarchy(
            "crashes/" + directory_name + "/view_hierarchy" + view_hierarchy_format
        )
    except RuntimeError:
        logger.error("Cannot save view hierarchy.")

    with open(
        "crashes/" + directory_name + "/logs.txt", "w", encoding="utf-8"
    ) as outfile:
        outfile.write(get_logs())

    shutil.make_archive(
        "crashes/" + directory_name, "zip", "crashes/" + directory_name + "/"
    )
    shutil.rmtree("crashes/" + directory_name + "/")

    logger.info(
        'Crash saved as "crashes/' + directory_name + '.zip".',
        extra={"color": Fore.GREEN},
    )
    logger.info(
        "Please attach this file if you gonna report the crash at",
        extra={"color": Fore.GREEN},
    )
    logger.info(
        "https://github.com/GramAddict/bot/issues\n",
        extra={"color": Fore.GREEN},
    )


def detect_block(device):
    block_dialog = device.find(
        resourceId="com.instagram.android:id/dialog_root_view",
        className="android.widget.FrameLayout",
    )
    is_blocked = block_dialog.exists()
    if is_blocked:
        logger.error("Probably block dialog is shown.")
        raise ActionBlockedError(
            "Seems that action is blocked. Consider reinstalling Instagram app and be more careful"
            " with limits!"
        )


def _print_with_time_decorator(standard_print, print_time):
    def wrapper(*args, **kwargs):
        global print_log
        if print_time:
            time = datetime.now().strftime("%m/%d %H:%M:%S")
            print_log += re.sub(
                r"\[\d+m", "", ("[" + time + "] " + str(*args, **kwargs) + "\n")
            )
            return standard_print("[" + time + "]", *args, **kwargs)
        else:
            print_log += re.sub(r"\[\d+m", "", (str(*args, **kwargs) + "\n"))
            return standard_print(*args, **kwargs)

    return wrapper


def get_value(count, name, default):
    def print_error():
        logger.error(
            name.format(default)
            + f'. Using default value instead of "{count}", because it must be '
            "either a number (e.g. 2) or a range (e.g. 2-4)."
        )

    parts = count.split("-")
    if len(parts) <= 0:
        value = default
        print_error()
    elif len(parts) == 1:
        try:
            value = int(count)
            logger.info(name.format(value), extra={"color": Style.BRIGHT})
        except ValueError:
            value = default
            print_error()
    elif len(parts) == 2:
        try:
            value = randint(int(parts[0]), int(parts[1]))
            logger.info(name.format(value), extra={"color": Style.BRIGHT})
        except ValueError:
            value = default
            print_error()
    else:
        value = default
        print_error()
    return value


print_log = ""


class ActionBlockedError(Exception):
    pass
