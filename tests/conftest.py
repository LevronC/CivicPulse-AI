"""
Shared test fixtures.

Tests run against isolated in-memory state or test database instances.
No test should depend on external services or persistent state from
another test — each test gets its own clean context.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))
