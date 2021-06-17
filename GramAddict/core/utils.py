from GramAddict import __file__
from GramAddict.core.storage import ACCOUNTS
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
from os import getcwd, walk, rename
from pathlib import Path
from datetime import datetime
from random import randint, shuffle, uniform
from subprocess import PIPE
from time import sleep
from urllib.parse import urlparse
from requests import get

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
    urllib3.disable_warnings()
    logger.info("Checking for updates...")
    if "b" not in __version__:
        version_request = "https://raw.githubusercontent.com/GramAddict/bot/master/GramAddict/version.py"
    else:
        version_request = "https://raw.githubusercontent.com/GramAddict/bot/develop/GramAddict/version.py"
    try:
        r = get(version_request, verify=False)
        online_version_raw = r.text.split('"')[1]

    except Exception as e:
        logger.error(
            f"There was an error retrieving the latest version of GramAddict: {e}"
        )
        return False, False
    if "b" not in __version__:
        local_version = __version__.split(".")
        online_version = online_version_raw.split(".")
    else:
        local_version = __version__.split(".")[:-1] + __version__.split(".")[-1].split(
            "b"
        )
        online_version = online_version_raw.split(".")[:-1] + online_version_raw.split(
            "."
        )[-1].split("b")
    for n in range(len(online_version)):
        if int(online_version[n]) > int(local_version[n]):
            return True, online_version_raw
        else:
            if int(online_version[n]) == int(local_version[n]):
                continue
            break
    return False, online_version_raw


def move_usernames_to_accounts():
    Path(ACCOUNTS).mkdir(parents=True, exist_ok=True)
    ls = next(walk("."))[1]
    ignored_dir = [
        "build",
        "accounts",
        "GramAddict",
        "config-examples",
        ".git",
        ".venv",
        "dist",
        ".vscode",
        ".github",
        "crashes",
        "gramaddict.egg-info",
        "logs",
        "res",
        "test",
    ]
    for n in ignored_dir:
        try:
            ls.remove(n)
        except ValueError:
            pass

    for dir in ls:
        try:
            if dir != dir.strip():
                rename(f"{dir}", dir.strip())
            shutil.move(dir.strip(), ACCOUNTS)
        except Exception as e:
            logger.error(
                f"Folder {dir.strip()} already exists! Won't overwrite it, please check which is the correct one and delete the other! Exception: {e}"
            )
            sleep(3)
    if len(ls) > 0:
        logger.warning(
            f"Username folders {', '.join(ls)} have been moved to main folder 'accounts'. Remember that your config file must point there! Example: '--config accounts/yourusername/config.yml'"
        )


def config_examples():
    if getcwd() == __file__[:-23]:
        logger.debug("Installed via git, config-examples is in the local folder.")
    else:
        logger.debug("Installed via pip.")
        logger.info(
            "Do you want to update/create your config-examples folder in local? Do the following: \n\t\t\t\tpip3 install --user gitdir (only the first time)\n\t\t\t\tpython3 -m gitdir https://github.com/GramAddict/bot/tree/master/config-examples (python on Windows)",
            extra={"color": Fore.GREEN},
        )
        sleep(3)


def check_adb_connection():
    is_device_id_provided = configs.device_id is not None
    # sometimes it needs two requests to wake up..
    stream = os.popen("adb devices")
    stream.close()
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
        message = "Use '--device devicename' to specify a device."

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
    FastInputIME = "com.github.uiautomator/.FastInputIME"
    nl = "\n"
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
            f"{err[9:].capitalize()}, specify only one by using '--device devicename'"
        )
        return False
    elif err == "":
        logger.debug("Instagram called succesfully.")
    else:
        logger.debug(f"{err.replace('Warning: ', '')}.")
    success = False
    for _ in range(3):
        if device.deviceV2.info["currentPackageName"] == app_id:
            success = True
            break
        logger.debug("Wait for Instagram to open.")
        sleep(3)
    if success:
        logger.info(
            "Ready for botting!🤫", extra={"color": f"{Style.BRIGHT}{Fore.GREEN}"}
        )
    else:
        logger.error("Unabled to open Instagram. Try again..")
        return False
    random_sleep()
    if close_apps:
        logger.info("Close all the other apps, for avoid interferece..")
        device.deviceV2.app_stop_all(excludes=[app_id])
        random_sleep()
    logger.debug("Setting FastInputIME as default keyboard.")
    device.deviceV2.set_fastinput_ime(True)
    cmd = (
        "adb"
        + ("" if configs.device_id is None else " -s " + configs.device_id)
        + " shell settings get secure default_input_method"
    )
    cmd_res = subprocess.run(cmd, stdout=PIPE, stderr=PIPE, shell=True, encoding="utf8")
    if cmd_res.stdout.replace(nl, "") != FastInputIME:
        logger.warning(
            f"FastInputIME is not the default keyboard! Default is: {cmd_res.stdout.replace(nl, '')}. Changing it via adb.."
        )
        cmd = (
            "adb"
            + ("" if configs.device_id is None else " -s " + configs.device_id)
            + f" shell ime set {FastInputIME}"
        )
        cmd_res = subprocess.run(
            cmd, stdout=PIPE, stderr=PIPE, shell=True, encoding="utf8"
        )
        if cmd_res.stdout.startswith("Error:"):
            logger.warning(
                f"{cmd_res.stdout.replace(nl, '')}. It looks like you don't have FastInputIME installed :S"
            )
        else:
            logger.info("FastInputIME is the default keyboard.")
    else:
        logger.info("FastInputIME is the default keyboard.")
    if screen_record:
        try:
            device.start_screenrecord()
        except Exception as e:
            logger.error(
                f"For use the screen-record feature you have to install the requirements package! Run in the console: 'pip3 install -U 'uiautomator2[image]' -i https://pypi.doubanio.com/simple' Exception: {e}"
            )
    return True


def close_instagram(device, screen_record):
    logger.info("Close Instagram app.")
    device.deviceV2.app_stop(app_id)
    if screen_record:
        try:
            device.stop_screenrecord()
        except Exception as e:
            logger.error(
                f"For use the screen-record feature you have to install the requirements package! Run in the console: 'pip3 install -U 'uiautomator2[image]' -i https://pypi.doubanio.com/simple' Exception: {e}"
            )


def kill_atx_agent(device):
    logger.debug("Back to default keyboard!")
    device.deviceV2.set_fastinput_ime(False)
    logger.info("Kill atx agent.")
    os.popen(
        "adb"
        + ("" if configs.device_id is None else " -s " + configs.device_id)
        + " shell pkill atx-agent"
    ).close()


def random_sleep(inf=0.5, sup=3.0, modulable=True, logging=True):
    MIN_INF = 0.3
    multiplier = float(args.speed_multiplier)
    delay = uniform(inf, sup) / (multiplier if modulable else 1.0)
    if delay < MIN_INF:
        delay = MIN_INF
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
    logger.info("https://discord.gg/66zWWCDM7x\n", extra={"color": Fore.GREEN})


def stop_bot(device, sessions, session_state, screen_record, was_sleeping=False):
    close_instagram(device, screen_record)
    kill_atx_agent(device)
    logger.info(
        f"-------- FINISH: {datetime.now().strftime('%H:%M:%S')} --------",
        extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
    )
    if session_state is not None:
        print_full_report(sessions, configs.args.scrape_to_file)
        if not was_sleeping:
            sessions.persist(directory=session_state.my_username)
    sys.exit(0)


def can_repeat(current_session, max_sessions):
    if max_sessions != -1:
        logger.info(
            f"You completed {current_session} session(s). {max_sessions-current_session} session(s) left.",
            extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
        )
        if current_session >= max_sessions:
            logger.info(
                "You reached the total-sessions limit! Finish.",
                extra={"color": f"{Style.BRIGHT}{Fore.YELLOW}"},
            )
            return False
        else:
            return True
    else:
        return True


def get_value(count, name, default, its_time=False):
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
            if not its_time:
                value = randint(int(parts[0]), int(parts[1]))
            else:
                value = round(uniform(int(parts[0]), int(parts[1])), 2)

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
        with open(filename, "a+", encoding="utf-8") as file:
            file.write(username + "\n")
    except Exception as e:
        logger.error(f"Failed to append {username} to: {filename}. Exception: {e}")


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

    likes_percentage = get_value(args.likes_percentage, "Chance of liking: {}%", 100)
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
        likes_percentage,
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
        f"Time delta has set to {'' if args.time_delta_session >0 else '-'}{h:02d}:{m:02d}:{s:02d}."
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
        stop_bot(device, sessions, session_state, screen_record, was_sleeping=True)


class ActionBlockedError(Exception):
    pass


class Square:
    def __init__(self, x0, y0, x1, y1):
        self.delta = 7
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def point(self):
        """return safe point to click"""
        if (self.x1 - self.x0) <= (2 * self.delta) or (self.y1 - self.y0) <= (
            2 * self.delta
        ):
            return nan
        else:
            return [
                randint(self.x0 + self.delta, self.x1 - self.delta),
                randint(self.y0 + self.delta, self.y1 - self.delta),
            ]
