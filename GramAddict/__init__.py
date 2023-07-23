"""Human-like Instagram bot powered by UIAutomator2"""
__version__ = "3.2.5"
__tested_ig_version__ = "226.1.0.16.117"

from GramAddict.core.bot_flow import start_bot


def run(**kwargs):
    start_bot(**kwargs)
