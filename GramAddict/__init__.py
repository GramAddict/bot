"""Human-like Instagram bot powered by UIAutomator2"""

__version__ = "3.2.12"
__tested_ig_version__ = "410.1.0.63.71"

from GramAddict.core.bot_flow import start_bot


def run(**kwargs):
    start_bot(**kwargs)
