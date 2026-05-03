"""Pytest fixtures for eidolon offline tests."""
import os
import sys
import tempfile
from pathlib import Path

import pytest


# Set EIDOLON_HOME to a session-temp dir BEFORE any test imports state/eidolon.
_SESSION_STATE_DIR = Path(tempfile.mkdtemp(prefix="eidolon-pytest-state-"))
os.environ.setdefault("EIDOLON_HOME", str(_SESSION_STATE_DIR))

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Per-test isolated state dir via EIDOLON_HOME override."""
    state = tmp_path / "eidolon"
    monkeypatch.setenv("EIDOLON_HOME", str(state))
    return state
