import configargparse
import logging
import sys
import yaml

from GramAddict.core.plugin_loader import PluginLoader

logger = logging.getLogger(__name__)


class Config:
    def __init__(self, first_run=False):
        self.args = sys.argv
        self.config = None
        self.config_list = None
        self.debug = False
        self.device_id = None
        self.first_run = first_run
        self.username = False

        # Pre-Load Variables Needed for Script Init
        if "--config" in self.args:
            try:
                file_name = self.args[self.args.index("--config") + 1]
                with open(file_name) as fin:
                    # preserve order of yaml
                    self.config_list = [line.strip() for line in fin]
                    fin.seek(0)
                    # pre-load config for debug and username
                    self.config = yaml.safe_load(fin)
            except IndexError:
                print("Please provide a filename with your --config argument.")
                exit(0)

            self.username = self.config.get("username", False)
            self.debug = self.config.get("debug", False)

        if "--debug":
            self.debug = True
        if "--username" in self.args:
            try:
                self.username = self.args[self.args.index("--username") + 1]
            except IndexError:
                print("Please provide a username with your --username argument.")
                exit(0)

        # Configure ArgParse
        self.parser = configargparse.ArgumentParser(
            description="GramAddict Instagram Bot"
        )
        self.parser.add(
            "-c",
            "--config",
            required=False,
            is_config_file=True,
            help="config file path",
        )

        # on first run, we must wait to proceed with loading
        if not self.first_run:
            self.load_plugins()
            self.parse_args()

    def load_plugins(self):
        self.plugins = PluginLoader("GramAddict.plugins", self.first_run).plugins
        self.actions = {}
        for plugin in self.plugins:
            if plugin.arguments:
                for arg in plugin.arguments:
                    try:
                        action = arg.get("action", None)
                        if action:
                            self.parser.add_argument(
                                arg["arg"],
                                help=arg["help"],
                                action=arg.get("action", None),
                            )
                        else:
                            self.parser.add_argument(
                                arg["arg"],
                                nargs=arg["nargs"],
                                help=arg["help"],
                                metavar=arg["metavar"],
                                default=arg["default"],
                            )
                        if arg.get("operation", False):
                            self.actions[arg["arg"][2:]] = plugin
                    except Exception as e:
                        logger.error(
                            f"Error while importing arguments of plugin {plugin.__class__.__name__}. Error: Missing key from arguments dictionary - {e}"
                        )

    def parse_args(self):
        def _is_legacy_arg(arg):
            if arg == "interact" or arg == "hashtag-likers":
                if self.first_run:
                    logger.warn(
                        f"You are using a legacy argument {arg} that is no longer supported. It will not be used. Please refer to https://docs.gramaddict.org/#/configuration?id=arguments."
                    )
                return True
            return False

        self.enabled = []
        if self.first_run:
            logger.debug(f"Arguments used: {' '.join(sys.argv[1:])}")
            if self.config:
                logger.debug(f"Config used: {self.config}")
            if not len(sys.argv) > 1:
                self.parser.print_help()
                exit(0)

        self.args, self.unknown_args = self.parser.parse_known_args()

        if self.unknown_args and self.first_run:
            logger.error(
                "Unknown arguments: " + ", ".join(str(arg) for arg in self.unknown_args)
            )
            self.parser.print_help()
            exit(0)

        self.device_id = self.args.device

        # We need to maintain the order of plugins as defined
        # in config or sys.argv
        if self.config_list:
            for item in self.config_list:
                item = item.split(":")[0]
                if (
                    item in self.actions
                    and getattr(self.args, item.replace("-", "_")) != None
                    and not _is_legacy_arg(item)
                ):
                    self.enabled.append(item)
        else:
            for item in sys.argv:
                nitem = item[2:]
                if (
                    nitem in self.actions
                    and getattr(self.args, nitem.replace("-", "_")) != None
                    and not _is_legacy_arg(nitem)
                ):
                    self.enabled.append(nitem)
