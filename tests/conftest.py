"""Pytest fixtures for eidolon offline tests.

Critical: scripts/generate.py refuses to import from the source repo unless
EIDOLON_HOME is set. We force a per-session tmp dir BEFORE any test imports
generate or setup.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest


# Set EIDOLON_HOME to a session-temp dir BEFORE any test imports generate/setup.
# This must happen at conftest import time, not in a fixture, because
# generate.py runs _resolve_state_dir() at module import.
_SESSION_STATE_DIR = Path(tempfile.mkdtemp(prefix="eidolon-pytest-state-"))
os.environ.setdefault("EIDOLON_HOME", str(_SESSION_STATE_DIR))

# Make `import generate` / `import setup` work from tests.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Per-test isolated state dir via EIDOLON_HOME override."""
    state = tmp_path / "eidolon"
    monkeypatch.setenv("EIDOLON_HOME", str(state))
    return state


@pytest.fixture
def clear_image_env(monkeypatch):
    """Clear EIDOLON_* env vars that affect generation knobs / output paths.

    eid0l0n 0.8+ does not detect any image-API env vars itself — the host
    agent's own tool handles those. We only clear knobs that affect the
    skill's own behavior (output dir override, codex tuning).
    """
    for var in (
        "EIDOLON_IMAGE_QUALITY",
        "EIDOLON_IMAGE_ASPECT",
        "EIDOLON_OUTPUT_DIR",
    ):
        monkeypatch.delenv(var, raising=False)
