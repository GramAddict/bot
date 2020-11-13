import logging
from io import StringIO
from logging import LogRecord

from colorama import Fore, Style
from colorama import init as init_colorama

COLORS = {
    "DEBUG": Style.DIM,
    "INFO": Fore.WHITE,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.MAGENTA,
}


class ColoredFormatter(logging.Formatter):
    def __init__(self, *, fmt, datefmt=None):
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt)

    def format(self, record):
        msg = super().format(record)
        levelname = record.levelname
        if hasattr(record, "color"):
            return f"{record.color}{msg}{Style.RESET_ALL}"
        if levelname in COLORS:
            return f"{COLORS[levelname]}{msg}{Style.RESET_ALL}"
        return msg


def configure_logger():
    init_colorama()
    logger = logging.getLogger()  # root logger
    logger.setLevel(logging.DEBUG)

    # Formatters
    datefmt = r"[%m/%d %H:%M:%S]"
    console_fmt = "%(asctime)s %(levelname)8s | %(message)s (%(filename)s:%(lineno)d)"
    console_formatter = ColoredFormatter(fmt=console_fmt, datefmt=datefmt)
    crash_report_fmt = (
        "%(asctime)s %(levelname)8s | %(message)s (%(filename)s:%(lineno)d)"
    )
    crash_report_formatter = logging.Formatter(fmt=crash_report_fmt, datefmt=datefmt)

    # Filters
    class FilterGramAddictOnly(logging.Filter):
        def filter(self, record: LogRecord):
            return record.name.startswith("GramAddict")

    # Console handler (limited colored log)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(FilterGramAddictOnly())

    # Crash report handler (full raw log)
    global log_stream
    log_stream = StringIO()
    crash_report_handler = logging.StreamHandler(log_stream)
    crash_report_handler.setLevel(logging.DEBUG)
    crash_report_handler.setFormatter(crash_report_formatter)
    crash_report_handler.addFilter(FilterGramAddictOnly())

    logger.addHandler(console_handler)
    logger.addHandler(crash_report_handler)


def get_logs():
    # log_stream is a StringIO() created when configure_logger() is called
    global log_stream

    return log_stream.getvalue()
