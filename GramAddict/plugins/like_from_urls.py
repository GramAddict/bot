import logging
import os
from functools import partial
from GramAddict.core.decorators import run_safely
from GramAddict.core.interaction import _on_like, do_like
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.utils import random_sleep, open_instagram_with_url, validate_url

logger = logging.getLogger(__name__)

from GramAddict.core.views import OpenedPostView


class LikeFromURLs(Plugin):
    """This plugin handles the functionality to likes all post from url reading a plaintext file"""

    def __init__(self):
        super().__init__()
        self.description = "This plugin handles the functionality to likes all post from url reading a plaintext file"
        self.arguments = [
            {
                "arg": "--urls-file",
                "nargs": None,
                "help": "full path of plaintext file contains urls to likes",
                "metavar": None,
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, device_id, args, enabled, storage, sessions):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.device_id = device_id
        self.state = None
        self.sessions = sessions
        self.session_state = sessions[-1]

        self.urls = []
        if os.path.isfile(args.urls_file):
            with open(args.urls_file, "r") as f:
                self.urls = f.readlines()

        self.state = State()
        on_like = partial(
            _on_like, sessions=self.sessions, session_state=self.session_state
        )

        @run_safely(
            device=device,
            device_id=self.device_id,
            sessions=self.sessions,
            session_state=self.session_state,
        )
        def job():
            for url in self.urls:
                url = url.strip().replace("\n", "")
                if validate_url(url) and "instagram.com/p/" in url:
                    if open_instagram_with_url(self.device_id, url) is True:
                        opened_post_view = OpenedPostView(device)
                        like_succeed = do_like(opened_post_view, device, on_like)
                        logger.info(
                            "Like for: {}, status: {}".format(url, like_succeed)
                        )

                        if like_succeed:
                            logger.info("Back to profile")
                            device.back()
                            random_sleep()

        job()
