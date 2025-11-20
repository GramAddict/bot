"""
GramAddict Plugin Template

This template shows how to create a new plugin for GramAddict.
Copy this file and modify it to add new bot functionality.

Plugin Basics:
1. All plugins must inherit from the Plugin base class
2. Define arguments in the arguments list
3. Implement the run() method with your bot logic
4. Save the file as interact_<name>.py or action_<name>.py
"""

from GramAddict.core.plugin_loader import Plugin


class MyCustomPlugin(Plugin):
    """
    Example plugin that demonstrates the basic structure.

    Replace this with your plugin description.
    """

    def __init__(self):
        super().__init__()
        # Define plugin name
        self.description = "Example plugin template"
        # Define CLI arguments for this plugin
        self.arguments = [
            {
                # Argument name (will be accessible as --my-action)
                "arg": "--my-action",
                # Number of arguments: "?" for optional, "+" for one or more, "*" for zero or more
                "nargs": None,
                # Help text shown in CLI
                "help": "example action that does something cool",
                # Metadata key (optional)
                "metavar": "value",
                # Default value
                "default": None,
                # Mark as an operation (makes it show up as a main bot action)
                "operation": True,
            }
        ]

    def run(self, config, plugin, followers_now, following_now, time_left):
        """
        Main plugin execution method.

        This method is called when the plugin is activated.

        Args:
            config: Configuration object with all settings
            plugin: The plugin instance (self)
            followers_now: Current follower count
            following_now: Current following count
            time_left: Time remaining in session

        Returns:
            None
        """
        # Get the argument value from config
        action_value = config.args.my_action  # Note: dashes become underscores

        if action_value is None:
            # Plugin not activated
            return

        # Your plugin logic goes here
        print(f"Running MyCustomPlugin with value: {action_value}")

        # Example: Interact with device
        # device = config.device
        # device.click(x=500, y=500)

        # Example: Access storage
        # from GramAddict.core.storage import Storage
        # storage = Storage(config.username)
        # storage.add_interacted_user("username123")

        # Example: Log information
        # logger.info("Doing something cool...")

        pass


# EXAMPLES OF COMMON PLUGIN PATTERNS
# -----------------------------------

# 1. INTERACTION PLUGIN
# Interacts with users, posts, hashtags, etc.
class InteractExamplePlugin(Plugin):
    """Example interaction plugin."""

    def __init__(self):
        super().__init__()
        self.description = "Interact with example target"
        self.arguments = [
            {
                "arg": "--interact-example",
                "nargs": "+",
                "help": "list of targets to interact with",
                "metavar": ("target1", "target2"),
                "default": None,
                "operation": True,
            }
        ]

    def run(self, config, plugin, followers_now, following_now, time_left):
        targets = config.args.interact_example
        if targets is None:
            return

        for target in targets:
            print(f"Interacting with {target}...")
            # Your interaction logic here
            pass


# 2. ACTION PLUGIN
# Performs actions like unfollowing, removing followers, etc.
class ActionExamplePlugin(Plugin):
    """Example action plugin."""

    def __init__(self):
        super().__init__()
        self.description = "Perform example action"
        self.arguments = [
            {
                "arg": "--action-example",
                "nargs": None,
                "help": "perform example action",
                "metavar": None,
                "default": None,
                "operation": True,
            }
        ]

    def run(self, config, plugin, followers_now, following_now, time_left):
        if config.args.action_example is None:
            return

        print("Performing action...")
        # Your action logic here
        pass


# 3. FILTER PLUGIN
# Adds filtering capabilities
class FilterExamplePlugin(Plugin):
    """Example filter plugin."""

    def __init__(self):
        super().__init__()
        self.description = "Example filter"
        self.arguments = [
            {
                "arg": "--filter-example",
                "nargs": None,
                "help": "enable example filter",
                "metavar": "value",
                "default": None,
                "operation": False,  # Not a main operation
            }
        ]

    def run(self, config, plugin, followers_now, following_now, time_left):
        # Filters typically don't have run() logic
        # They're checked during interactions
        pass


# PLUGIN NAMING CONVENTIONS
# -------------------------
# interact_*.py  - Interaction plugins (follow, like, comment)
# action_*.py    - Action plugins (unfollow, remove, scrape)
# core_*.py      - Core functionality (filters, arguments)
# *_analytics.py - Analytics and reporting
# *.py           - Utility plugins

# HOW TO USE YOUR PLUGIN
# -----------------------
# 1. Save this file in GramAddict/plugins/
# 2. Name it according to convention (e.g., interact_my_feature.py)
# 3. Run: gramaddict run --config config.yml --my-action value
# 4. The plugin will be automatically discovered and loaded!

# TIPS
# ----
# - Look at existing plugins in GramAddict/plugins/ for examples
# - Use logger for output instead of print()
# - Access device via config.device
# - Access storage via Storage(config.username)
# - Test with --debug flag for verbose logging
# - Use filters from config.args to respect user preferences
