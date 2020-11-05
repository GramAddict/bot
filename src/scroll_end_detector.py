from src.utils import *


class ScrollEndDetector:
    # Specify how many times we'll have to iterate over same users to decide that it's the end of the list
    repeats_to_end = 0
    pages = []

    def __init__(self, repeats_to_end=5):
        self.repeats_to_end = repeats_to_end

    def notify_new_page(self):
        self.pages.append([])

    def notify_username_iterated(self, username):
        last_page = self.pages[-1]
        last_page.append(username)

    def is_the_end(self):
        if len(self.pages) < 2:
            return False

        is_the_end = True
        last_page = self.pages[-1]
        repeats = 1
        for i in range(2, min(self.repeats_to_end + 1, len(self.pages) + 1)):
            page = self.pages[-i]
            if page != last_page:
                is_the_end = False
                break
            repeats += 1

        if is_the_end:
            print(
                COLOR_OKBLUE
                + f"Same users iterated {repeats} times. End of the list, finish."
                + COLOR_ENDC
            )
        elif repeats > 1:
            print(
                COLOR_OKBLUE
                + f"Same users iterated {repeats} times. Continue."
                + COLOR_ENDC
            )

        return is_the_end
