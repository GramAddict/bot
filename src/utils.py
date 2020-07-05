import hashlib
import os
import re
from datetime import datetime
from random import randint
from time import sleep

COLOR_HEADER = '\033[95m'
COLOR_OKBLUE = '\033[94m'
COLOR_OKGREEN = '\033[92m'
COLOR_WARNING = '\033[93m'
COLOR_FAIL = '\033[91m'
COLOR_ENDC = '\033[0m'
COLOR_BOLD = '\033[1m'
COLOR_UNDERLINE = '\033[4m'


def get_version():
    stream = os.popen('git describe --tags')
    output = stream.read()
    version_match = re.match('(v\\d+.\\d+.\\d+)', output)
    version = (version_match is None) and "(Work In Progress)" or version_match.group(1)
    stream.close()
    return version


def check_adb_connection(is_device_id_provided):
    stream = os.popen('adb devices')
    output = stream.read()
    devices_count = len(re.findall('device\n', output))
    stream.close()

    is_ok = True
    message = "That's ok."
    if devices_count == 0:
        is_ok = False
        message = "Cannot proceed."
    elif devices_count > 1 and not is_device_id_provided:
        is_ok = False
        message = "Use --device to specify a device."

    print(("" if is_ok else COLOR_FAIL) + "Connected devices via adb: " + str(devices_count) + ". " + message +
          COLOR_ENDC)
    return is_ok


def double_click(device, *args, **kwargs):
    config = device.server.jsonrpc.getConfigurator()
    config['actionAcknowledgmentTimeout'] = 40
    device.server.jsonrpc.setConfigurator(config)
    device(*args, **kwargs).click()
    device(*args, **kwargs).click()
    config['actionAcknowledgmentTimeout'] = 3000
    device.server.jsonrpc.setConfigurator(config)


def random_sleep():
    delay = randint(1, 4)
    print("Sleep for " + str(delay) + (delay == 1 and " second" or " seconds"))
    sleep(delay)


def open_instagram(device_id):
    print("Open Instagram app")
    os.popen("adb" + ("" if device_id is None else " -s " + device_id) +
             " shell am start -n com.instagram.android/com.instagram.mainactivity.MainActivity").close()
    random_sleep()


def close_instagram():
    print("Close Instagram app")
    os.popen("adb shell am force-stop com.instagram.android").close()


def stringify_interactions(interactions):
    if len(interactions) == 0:
        return "0"

    result = ""
    for blogger, count in interactions.items():
        result += str(count) + " for @" + blogger + ", "
    result = result[:-2]
    return result


def take_screenshot(device):
    os.makedirs("screenshots/", exist_ok=True)
    filename = "Crash-" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + ".png"
    device.screenshot("screenshots/" + filename)
    print(COLOR_OKGREEN + "Screenshot taken and saved as " + filename + COLOR_ENDC)


def print_copyright(username):
    copyright_blacklist = (
        '2a978d696a5bbc8536fe2859a61ee01d86e7a20f',
        'ab1d65a93ec9b6fb90a67dec1ca1480ff71ef725'
    )

    if hashlib.sha1(username.encode('utf-8')).hexdigest() not in copyright_blacklist:
        print_timeless("\nIf you like this script and want it to be improved, " + COLOR_BOLD + "donate please"
                       + COLOR_ENDC + ".")
        print_timeless(COLOR_BOLD + "$1" + COLOR_ENDC + " - support this project")
        print_timeless(COLOR_BOLD + "$5" + COLOR_ENDC + " - unblock hidden features")
        print_timeless(COLOR_BOLD + "$50" + COLOR_ENDC + " - order the feature you want")
        print_timeless("https://www.patreon.com/insomniac_bot\n")


def _print_with_time_decorator(standard_print, print_time):
    def wrapper(*args, **kwargs):
        if print_time:
            time = datetime.now().strftime("%m/%d %H:%M:%S")
            return standard_print("[" + time + "]", *args, **kwargs)
        else:
            return standard_print(*args, **kwargs)

    return wrapper


print_timeless = _print_with_time_decorator(print, False)
print = _print_with_time_decorator(print, True)
