import hashlib
import os
import platform
import re
import shutil
from datetime import datetime
from random import randint
from time import sleep

COLOR_HEADER = "\033[95m"
COLOR_OKBLUE = "\033[94m"
COLOR_OKGREEN = "\033[92m"
COLOR_WARNING = "\033[93m"
COLOR_FAIL = "\033[91m"
COLOR_ENDC = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_UNDERLINE = "\033[4m"


def get_version():
    stream = os.popen("git describe --tags")
    output = stream.read()
    version_match = re.match("(v\\d+.\\d+.\\d+)", output)
    version = (version_match is None) and "(Work In Progress)" or version_match.group(1)
    stream.close()
    return version


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

    print(
        ("" if is_ok else COLOR_FAIL)
        + "Connected devices via adb: "
        + str(devices_count)
        + ". "
        + message
        + COLOR_ENDC
    )
    return is_ok


def random_sleep():
    delay = randint(1, 4)
    print("Sleep for " + str(delay) + (delay == 1 and " second" or " seconds"))
    sleep(delay)


def open_instagram(device_id):
    print("Open Instagram app")
    os.popen(
        "adb"
        + ("" if device_id is None else " -s " + device_id)
        + " shell am start -n com.instagram.android/com.instagram.mainactivity.MainActivity"
    ).close()
    random_sleep()


def close_instagram(device_id):
    print("Close Instagram app")
    os.popen(
        "adb"
        + ("" if device_id is None else " -s " + device_id)
        + " shell am force-stop com.instagram.android"
    ).close()


def random_sleep():
    delay = randint(1, 4)
    print("Sleep for " + str(delay) + (delay == 1 and " second" or " seconds"))
    sleep(delay)


def screen_care():
    System_OS = platform.system()
    print(f"You're on {System_OS}!")
    if "Linux" == System_OS:
        status = os.popen("adb shell dumpsys input_method | grep mInteractive=")
    else:
        status = os.popen("adb shell dumpsys input_method | findstr mInteractive=")

    data = status.read()
    flag = re.search("mInteractive=(true|false)", data)
    if flag is not None:
        if flag.group(1) == "false":
            print("Turning ON device screen")
            os.popen("adb shell input keyevent 26")
    else:
        print("Screen care off")
        print("You're using an emulator!")


def save_crash(device):
    global print_log

    directory_name = "Crash-" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    try:
        os.makedirs("crashes/" + directory_name + "/", exist_ok=False)
    except OSError:
        print(
            COLOR_FAIL + "Directory " + directory_name + " already exists." + COLOR_ENDC
        )
        return

    screenshot_format = ".png" if device.is_old() else ".jpg"
    try:
        device.screenshot(
            "crashes/" + directory_name + "/screenshot" + screenshot_format
        )
    except RuntimeError:
        print(COLOR_FAIL + "Cannot save screenshot." + COLOR_ENDC)

    view_hierarchy_format = ".xml"
    try:
        device.dump_hierarchy(
            "crashes/" + directory_name + "/view_hierarchy" + view_hierarchy_format
        )
    except RuntimeError:
        print(COLOR_FAIL + "Cannot save view hierarchy." + COLOR_ENDC)

    with open("crashes/" + directory_name + "/logs.txt", "w") as outfile:
        outfile.write(print_log)

    shutil.make_archive(
        "crashes/" + directory_name, "zip", "crashes/" + directory_name + "/"
    )
    shutil.rmtree("crashes/" + directory_name + "/")

    print(
        COLOR_OKGREEN
        + 'Crash saved as "crashes/'
        + directory_name
        + '.zip".'
        + COLOR_ENDC
    )
    print(
        COLOR_OKGREEN
        + "Please attach this file if you gonna report the crash at"
        + COLOR_ENDC
    )
    print(
        COLOR_OKGREEN
        + "https://github.com/GramAddict/bot/issues\n"
        + COLOR_ENDC
    )


def detect_block(device):
    block_dialog = device.find(
        resourceId="com.instagram.android:id/dialog_root_view",
        className="android.widget.FrameLayout",
    )
    is_blocked = block_dialog.exists()
    if is_blocked:
        print(COLOR_FAIL + "Probably block dialog is shown." + COLOR_ENDC)
        raise ActionBlockedError(
            "Seems that action is blocked. Consider reinstalling Instagram app and be more careful"
            " with limits!"
        )


def print_copyright(username):
    print_timeless(
        "\nIf you like this script and want it to be improved, "
        + COLOR_BOLD
        + "donate please"
        + COLOR_ENDC
        + "."
    )
    print_timeless(COLOR_BOLD + "$3" + COLOR_ENDC + " - support this project")


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
        print(
            COLOR_FAIL
            + name.format(default)
            + f'. Using default value instead of "{count}", because it must be '
            "either a number (e.g. 2) or a range (e.g. 2-4)." + COLOR_ENDC
        )

    parts = count.split("-")
    if len(parts) <= 0:
        value = default
        print_error()
    elif len(parts) == 1:
        try:
            value = int(count)
            print(COLOR_BOLD + name.format(value) + COLOR_ENDC)
        except ValueError:
            value = default
            print_error()
    elif len(parts) == 2:
        try:
            value = randint(int(parts[0]), int(parts[1]))
            print(COLOR_BOLD + name.format(value) + COLOR_ENDC)
        except ValueError:
            value = default
            print_error()
    else:
        value = default
        print_error()
    return value


print_log = ""
print_timeless = _print_with_time_decorator(print, False)
print = _print_with_time_decorator(print, True)


class ActionBlockedError(Exception):
    pass
