import logging
import os
from functools import partial
from GramAddict.core.decorators import run_safely
from GramAddict.core.interaction import _on_like, do_like
from GramAddict.core.plugin_loader import Plugin
from GramAddict.core.utils import (
    random_sleep,
    open_instagram_with_url,
    validate_url,
    read_file,
    delete_line_in_file,
)

logger = logging.getLogger(__name__)

from GramAddict.core.views import OpenedPostView


class LikeFromURLs(Plugin):
    """Likes a post from url. The urls are read from a plaintext file"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Likes a post from url. The urls are read from a plaintext file"
        )
        self.arguments = [
            {
                "arg": "--posts-from-file",
                "nargs": None,
                "help": "full path of plaintext file contains urls to likes",
                "metavar": None,
                "default": None,
                "operation": True,
            }
        ]

    def run(self, device, config, storage, sessions, plugin):
        class State:
            def __init__(self):
                pass

            is_job_completed = False

        self.args = config.args
        self.device_id = config.args.device
        self.state = None
        self.sessions = sessions
        self.session_state = sessions[-1]
        self.current_mode = plugin

        self.urls = []
        self.urls = read_file(self.args.posts_from_file)
        if self.urls is False:
            logger.warning(f"File {self.args.posts_from_file} not found.")
            return
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
                delete_line_in_file(url, self.args.posts_from_file)
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
