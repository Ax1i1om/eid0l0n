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
def clear_backend_env(monkeypatch):
    """Clear all backend-related env vars so tests start from a known state."""
    for var in (
        "EIDOLON_IMAGE_BACKEND",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_AI_STUDIO_KEY",
        "FAL_KEY",
        "FAL_API_KEY",
        "REPLICATE_API_TOKEN",
        "IMAGE_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
