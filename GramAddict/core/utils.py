from math import nan
import random
import sys

from GramAddict.core.report import print_full_report
import logging
import os
import subprocess
import re
import shutil
import urllib3
import emoji
from datetime import datetime
from random import randint, shuffle, uniform
from subprocess import PIPE
from time import sleep
from urllib.parse import urlparse

from colorama import Fore, Style
from GramAddict.core.log import get_log_file_config
from GramAddict.core.resources import ResourceID as resources
from GramAddict.version import __version__

http = urllib3.PoolManager()
logger = logging.getLogger(__name__)


def load_config(config):
    global app_id
    global args
    global configs
    global ResourceID
    app_id = config.args.app_id
    args = config.args
    configs = config
    ResourceID = resources(app_id)


def update_available():
    if "b" not in __version__:
        version_request = "https://raw.githubusercontent.com/GramAddict/bot/master/GramAddict/version.py"
    else:
        version_request = "https://raw.githubusercontent.com/GramAddict/bot/develop/GramAddict/version.py"
    try:
        r = http.request(
            "GET",
            version_request,
        )
        version_number = r.data.decode("utf-8").split('"')[1]
        return (
            version_number.replace("b", "") > __version__.replace("b", ""),
            version_number,
        )
    except Exception as e:
        logger.error(
            f"There was an error retreiving the latest version of GramAddict: {e}"
        )
        return False, False


def check_adb_connection():
    is_device_id_provided = configs.device_id is not None
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
        message = "Use --device devicename to specify a device."

    if is_ok:
        logger.debug(f"Connected devices via adb: {devices_count}. {message}")
    else:
        logger.error(f"Connected devices via adb: {devices_count}. {message}")

    return is_ok


def get_instagram_version():
    stream = os.popen(
        "adb"
        + ("" if configs.device_id is None else " -s " + configs.device_id)
        + f" shell dumpsys package {app_id}"
    )
    output = stream.read()
    version_match = re.findall("versionName=(\\S+)", output)
    if len(version_match) == 1:
        version = version_match[0]
    else:
        version = "not found"
    stream.close()
    return version


def open_instagram_with_url(url):
    logger.info("Open Instagram app with url: {}".format(url))
    cmd = (
        "adb"
        + ("" if configs.device_id is None else " -s " + configs.device_id)
        + " shell am start -a android.intent.action.VIEW -d {}".format(url)
    )
    cmd_res = subprocess.run(cmd, stdout=PIPE, stderr=PIPE, shell=True, encoding="utf8")
    err = cmd_res.stderr.strip()
    random_sleep()
    if err:
        logger.debug(err)
        return False
    return True


def open_instagram(device, screen_record, close_apps):
    logger.info("Open Instagram app.")
    cmd = (
        "adb"
        + ("" if configs.device_id is None else " -s " + configs.device_id)
        + f" shell am start -n {app_id}/com.instagram.mainactivity.MainActivity"
    )
    cmd_res = subprocess.run(cmd, stdout=PIPE, stderr=PIPE, shell=True, encoding="utf8")
    err = cmd_res.stderr.strip()
    if "Error" in err:
        logger.error(err.replace("\n", ". "))
        return False
    elif "more than one device/emulator" in err:
        logger.error(
            f"{err[9:].capitalize()}, specify only one by using --device devicename"
        )
        return False
    elif err == "":
        logger.debug("Instagram app opened successfully.")
    else:
        logger.debug(err.replace("Warning: ", ""))
    random_sleep()
    if close_apps:
        logger.info("Close all the other apps, for avoid interfereces..")
        device.deviceV2.app_stop_all(excludes=[app_id])
        random_sleep()

    device.deviceV2.set_fastinput_ime(True)
    ime = device.find(
        classNameMatches="android.widget.TextView", textMatches="FastInputIME"
    )
    if ime.exists():
        logger.debug("Keyboard switch dialog is open. Closing it.")
        ime.click()
    if screen_record:
        try:
            device.start_screenrecord()
        except:
            logger.warning(
                "For use the screen-record feature you have to install the requirments package! Run in the console: 'pip3 install -U 'uiautomator2[image]' -i https://pypi.doubanio.com/simple'"
            )
    return True


def close_instagram(device, screen_record):
    logger.info("Close Instagram app.")
    device.deviceV2.app_stop(app_id)
    if screen_record:
        try:
            device.stop_screenrecord()
        except:
            logger.warning(
                "For use the screen-record feature you have to install the requirments package! Run in the console: 'pip3 install -U 'uiautomator2[image]' -i https://pypi.doubanio.com/simple'"
            )


def kill_atx_agent(device):
    logger.info("Kill atx agent.")
    os.popen(
        "adb"
        + ("" if configs.device_id is None else " -s " + configs.device_id)
        + " shell pkill atx-agent"
    ).close()
    logger.debug("Back to default keyboard!")
    device.deviceV2.set_fastinput_ime(False)


def random_sleep(inf=1.0, sup=3.0, modulable=True, logging=True):
    multiplier = float(args.speed_multiplier)
    delay = uniform(inf, sup) / (multiplier if modulable else 1.0)
    if logging:
        logger.debug(f"{str(delay)[0:4]}s sleep")
    sleep(delay)


def save_crash(device):
    directory_name = __version__ + "_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
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

    g_log_file_name, g_logs_dir, _, _ = get_log_file_config()
    src_file = f"{g_logs_dir}/{g_log_file_name}"
    target_file = f"crashes/{directory_name}/logs.txt"
    shutil.copy(src_file, target_file)

    shutil.make_archive(
        "crashes/" + directory_name, "zip", "crashes/" + directory_name + "/"
    )
    shutil.rmtree("crashes/" + directory_name + "/")

    logger.info(
        'Crash saved as "crashes/' + directory_name + '.zip".',
        extra={"color": Fore.GREEN},
    )
    logger.info(
        "If you want to report this crash, please upload the dump file via a ticket in the #lobby channel on discord ",
        extra={"color": Fore.GREEN},
    )
    logger.info("https://discord.gg/9MTjgs8g5R\n", extra={"color": Fore.GREEN})


def stop_bot(device, sessions, session_state, screen_record):
    close_instagram(device, screen_record)
    kill_atx_agent(device)
    logger.info(
        f"-------- FINISH: {datetime.now().strftime('%H:%M:%S')} --------",
        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
    )
    if session_state is not None:
        print_full_report(sessions, configs.args.scrape_to_file)
        sessions.persist(directory=session_state.my_username)
    sys.exit(0)


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
            if name is not None:
                logger.info(name.format(value), extra={"color": Style.BRIGHT})
        except ValueError:
            value = default
            print_error()
    elif len(parts) == 2:
        try:
            value = randint(int(parts[0]), int(parts[1]))
            if name is not None:
                logger.info(name.format(value), extra={"color": Style.BRIGHT})
        except ValueError:
            value = default
            print_error()
    else:
        value = default
        print_error()
    return value


def validate_url(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc, result.path])
    except Exception as e:
        logger.error(f"Error validating URL {x}. Error: {e}")
        return False


def append_to_file(filename, username):
    try:
        if not filename.lower().endswith(".txt"):
            filename = filename + ".txt"
        with open(filename, "a+", encoding="UTF-8") as file:
            file.write(username + "\n")
    except:
        logger.error(f"Failed to append {username} to: {filename}")


def sample_sources(sources, n_sources):
    from random import sample

    sources_limit_input = n_sources.split("-")
    if len(sources_limit_input) > 1:
        sources_limit = randint(
            int(sources_limit_input[0]), int(sources_limit_input[1])
        )
    else:
        sources_limit = int(sources_limit_input[0])
    if len(sources) < sources_limit:
        sources_limit = len(sources)
    if sources_limit == 0:
        truncaded = sources
        shuffle(truncaded)
    else:
        truncaded = sample(sources, sources_limit)
        logger.info(
            f"Source list truncated at {len(truncaded)} {'item' if len(truncaded)<=1 else 'items'}."
        )
    logger.info(
        f"In this session, {'that source' if len(truncaded)<=1 else 'these sources'} will be handled: {', '.join(emoji.emojize(str(x), use_aliases=True) for x in truncaded)}"
    )
    return truncaded


def init_on_things(source, args, sessions, session_state):
    from functools import partial
    from GramAddict.core.interaction import (
        _on_interaction,
    )

    on_interaction = partial(
        _on_interaction,
        likes_limit=int(args.total_likes_limit),
        source=source,
        interactions_limit=get_value(
            args.interactions_count, "Interactions count: {}", 70
        ),
        sessions=sessions,
        session_state=session_state,
        args=args,
    )

    if args.stories_count != "0":
        stories_percentage = get_value(
            args.stories_percentage, "Chance of watching stories: {}%", 40
        )
    else:
        stories_percentage = 0

    follow_percentage = get_value(
        args.follow_percentage, "Chance of following: {}%", 40
    )
    comment_percentage = get_value(
        args.comment_percentage, "Chance of commenting: {}%", 0
    )
    interact_percentage = get_value(
        args.interact_percentage, "Chance of interacting: {}%", 40
    )
    pm_percentage = get_value(args.pm_percentage, "Chance of send PM: {}%", 0)

    return (
        on_interaction,
        stories_percentage,
        follow_percentage,
        comment_percentage,
        pm_percentage,
        interact_percentage,
    )


def set_time_delta(args):
    args.time_delta_session = (
        get_value(args.time_delta, None, 0) * (1 if random.random() < 0.5 else -1) * 60
    ) + random.randint(0, 59)
    m, s = divmod(abs(args.time_delta_session), 60)
    h, m = divmod(m, 60)
    logger.info(
        f"Time delta has setted to {'' if args.time_delta_session >0 else '-'}{h:02d}:{m:02d}:{s:02d}."
    )


def wait_for_next_session(time_left, session_state, sessions, device, screen_record):
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    kill_atx_agent(device)
    logger.info(
        f'Next session will start at: {(datetime.now()+ time_left).strftime("%H:%M:%S (%Y/%m/%d)")}.',
        extra={"color": f"{Fore.GREEN}"},
    )
    logger.info(
        f"Time left: {hours:02d}:{minutes:02d}:{seconds:02d}.",
        extra={"color": f"{Fore.GREEN}"},
    )
    try:
        sleep(time_left.total_seconds())
    except KeyboardInterrupt:
        stop_bot(device, sessions, session_state, screen_record)


class ActionBlockedError(Exception):
    pass


class Square:
    def __init__(self, x, y, span_x, span_y):
        self.x = x + 10
        self.y = y + 10
        self.x1 = (x + span_x - 10) if span_x != 0 else 0
        self.y1 = (y + span_y - 10) if span_y != 0 else 0

    def point(self):
        """return safe point to click"""
        if self.x1 != 0 and self.y1 != 0:
            return [randint(self.x, self.x1), randint(self.y, self.y1)]
        else:
            return nan
