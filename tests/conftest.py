import os
import sys
from types import SimpleNamespace

import pytest

# Make the project packages (engine, features, storage) importable from the tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class FakeClock:
    """Replaces time.time() so time-based logic can be tested instantly and exactly."""

    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr("time.time", fake)
    return fake


def point(x, y, z=0.0):
    """A stand-in for a MediaPipe landmark (only .x, .y, .z are used)."""
    return SimpleNamespace(x=x, y=y, z=z)
