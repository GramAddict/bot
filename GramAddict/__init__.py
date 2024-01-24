"""Human-like Instagram bot powered by UIAutomator2"""
__version__ = "3.2.8"
__tested_ig_version__ = "263.2.0.19.104"

from GramAddict.core.bot_flow import start_bot


def run(**kwargs):
    start_bot(**kwargs)
