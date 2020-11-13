from GramAddict.core.plugin_loader import Plugin

# Note: this is mainly here to house old arguments until we figure out args better


class CoreArguments(Plugin):
    """This plugin simply adds core arguments"""

    def __init__(self):
        super().__init__()
        self.description = "Adds legacy arguments"
        self.arguments = [
            {
                "arg": "--device",
                "nargs": None,
                "help": "device identifier. Should be used only when multiple devices are connected at once",
                "metavar": "2443de990e017ece",
                "default": None,
            },
            {
                "arg": "--likes-count",
                "nargs": None,
                "help": "number of likes for each interacted user, 2 by default. It can be a number (e.g. 2) or a range (e.g. 2-4)",
                "metavar": "2-4",
                "default": "1-2",
            },
            {
                "arg": "--total-likes-limit",
                "nargs": None,
                "help": "limit on total amount of likes during the session, 300 by default",
                "metavar": "300",
                "default": "300",
            },
            {
                "arg": "--stories-count",
                "nargs": None,
                "help": "number of stories to watch for each user, 2 by default. It can be a number (e.g. 2) or a range (e.g. 2-4)",
                "metavar": "2-4",
                "default": "1-2",
            },
            {
                "arg": "--interactions-count",
                "nargs": None,
                "help": "number of interactions per each blogger, 70 by default. It can be a number (e.g. 70) or a range (e.g. 60-80). Only successful interactions count",
                "metavar": "60-80",
                "default": "30-50",
            },
            {
                "arg": "--repeat",
                "nargs": None,
                "help": "repeat the same session again after N minutes after completion, disabled by default. It can be a number of minutes (e.g. 180) or a range (e.g. 120-180)",
                "metavar": "220-300",
                "default": None,
            },
            {
                "arg": "--follow-percentage",
                "nargs": None,
                "help": "follow given percentage of interacted users, 0 by default",
                "metavar": "50",
                "default": "0",
            },
            {
                "arg": "--follow-limit",
                "nargs": None,
                "help": "limit on amount of follows during interaction with each one user's followers, disabled by default",
                "metavar": "0",
                "default": None,
            },
            {
                "arg": "--screen-sleep",
                "help": "save your screen by turning it off during the inactive time, disabled by default",
                "action": "store_true",
            },
            {
                "arg": "--interact",
                "nargs": "+",
                "help": "list of @usernames or #hashtags with whose followers you want to interact",
                "metavar": ("@username1", "@username2"),
                "default": None,
                "operation": True,
            },
        ]
