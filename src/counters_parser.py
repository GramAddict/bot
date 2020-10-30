from src.navigation import switch_to_english, LanguageChangedException
from src.utils import *


def parse(device, text):
    multiplier = 1
    text = text.replace(",", "")
    text = text.replace(".", "")
    if "K" in text:
        text = text.replace("K", "")
        multiplier = 1000
    if "M" in text:
        text = text.replace("M", "")
        multiplier = 1000000
    try:
        count = int(float(text) * multiplier)
    except ValueError:
        print_timeless(
            COLOR_FAIL
            + 'Cannot parse "'
            + text
            + '". Probably wrong language, will set English now.'
            + COLOR_ENDC
        )
        save_crash(device)
        switch_to_english(device)
        raise LanguageChangedException()
    return count
