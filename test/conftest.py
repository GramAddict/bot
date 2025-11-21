import os
import sys
from contextlib import ExitStack
from unittest import mock

import pytest

# Ensure the project root is on sys.path so that the GramAddict package can be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def mocker():
    """A lightweight substitute for pytest-mock's mocker fixture."""

    class SimpleMocker:
        def __init__(self):
            self._exit_stack = ExitStack()

        def patch(self, target, *args, **kwargs):
            patcher = mock.patch(target, *args, **kwargs)
            mocked = self._exit_stack.enter_context(patcher)
            return mocked

        def stop(self):
            self._exit_stack.close()

    instance = SimpleMocker()
    try:
        yield instance
    finally:
        instance.stop()
