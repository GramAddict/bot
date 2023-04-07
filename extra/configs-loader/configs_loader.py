import logging
from enum import Enum, auto
from itertools import cycle
from subprocess import Popen

import yaml


class Mode(Enum):
    REPEAT = auto()
    SINGLE = auto()


logger = logging.getLogger("configs-loader")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)-12s ==> %(message)s",
    datefmt="%m/%d %H:%M:%S",
)

mode = Mode.REPEAT

if __name__ == "__main__":
    bot_run = "gramaddict run --config".split(" ")

    def process_config():
        cur_conf = bot_run + [configs.get(config, {}).get("path", "")]
        logger.info(f"Starting `{config}` - {configs[config].get('path')}")
        with Popen(cur_conf, text=True, shell=True) as p:
            p.wait()

    with open("configs-list.yml", "r") as stream:
        try:
            configs = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.error(exc)
            exit(1)

    if mode == Mode.REPEAT:
        for config in cycle(configs):
            process_config()
    elif mode == Mode.SINGLE:
        for config in configs:
            process_config()
    logger.info("Finish!")
