import inspect
import logging
import pkgutil

logger = logging.getLogger(__name__)


class Plugin(object):
    def __init__(self):
        self.description = None
        self.arguments = None
        self.action = False

    def run(self):
        raise NotImplementedError


class PluginLoader(object):
    def __init__(self, plugin_package):
        self.plugin_package = plugin_package
        self.reload_plugins()

    def reload_plugins(self):
        self.plugins = []
        self.seen_paths = []
        logger.debug("Loading plugins . . .")
        self.walk_package(self.plugin_package)

    def walk_package(self, package):
        imported_package = __import__(package, fromlist=["plugins"])

        for _, pluginname, ispkg in pkgutil.iter_modules(
            imported_package.__path__, imported_package.__name__ + "."
        ):
            if not ispkg:
                plugin_module = __import__(pluginname, fromlist=["plugins"])
                clsmembers = inspect.getmembers(plugin_module, inspect.isclass)
                for (_, c) in clsmembers:
                    if issubclass(c, Plugin) & (c is not Plugin):
                        logger.debug(f"  - {c.__name__}: {c.__doc__}")
                        self.plugins.append(c())
