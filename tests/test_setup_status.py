"""Tests for setup.cmd_status — JSON state dump emitted by `setup.py status`."""
from __future__ import annotations

import argparse
import json

import pytest

import backends
import setup
import state


# Keys actually emitted by cmd_status (scripts/setup.py lines 139-155).
# Spec called for 14; current source emits 15. Test pins actual behavior.
EXPECTED_KEYS = {
    "anchor_exists",
    "reference_exists",
    "api_key_set",
    "anchor_path",
    "reference_path",
    "register_locked_until",
    "register_max",
    "backend_available",
    "backends_available",
    "backend_selected",
    "backend_forced",
    "state_dir",
    "workspace_cwd",
    "legacy_state_present",
    "legacy_config_dir",
}


@pytest.fixture
def isolated_state(tmp_path, monkeypatch, clear_backend_env):
    """Redirect state + setup paths into tmp_path, also block codex auth.

    Post-refactor: paths live canonically in `state` module; `setup` re-binds
    them at import, and helpers like find_existing_reference / legacy_state_present
    execute in `state`'s scope. We patch BOTH modules so every reader sees tmp_path,
    and patch CODEX_AUTH_PATH on `backends` (canonical home).
    """
    state_dir = tmp_path / "eidolon"
    state_dir.mkdir()
    legacy = tmp_path / "legacy-config-eidolon"  # never auto-created → legacy_state_present=False

    # `state` module is the canonical home of these paths; functions like
    # find_existing_reference() and legacy_state_present() read state.CONFIG_DIR
    # and state.LEGACY_CONFIG_DIR from their own globals.
    monkeypatch.setattr(state, "CONFIG_DIR", state_dir)
    monkeypatch.setattr(state, "ANCHOR_PATH", state_dir / "visual_anchor.md")
    monkeypatch.setattr(state, "ENV_PATH", state_dir / "env")
    monkeypatch.setattr(state, "PREFS_PATH", state_dir / "preferences.json")
    monkeypatch.setattr(state, "LOCK_PATH", state_dir / ".lock")
    monkeypatch.setattr(state, "LEGACY_CONFIG_DIR", legacy)

    # `backends` owns CODEX_AUTH_PATH after the refactor.
    monkeypatch.setattr(backends, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")

    # `setup` re-binds the path names at import time; cmd_status reads its OWN
    # ANCHOR_PATH global (not state.ANCHOR_PATH), so patch those bindings too.
    monkeypatch.setattr(setup, "CONFIG_DIR", state_dir)
    monkeypatch.setattr(setup, "ANCHOR_PATH", state_dir / "visual_anchor.md")
    monkeypatch.setattr(setup, "ENV_PATH", state_dir / "env")
    monkeypatch.setattr(setup, "PREFS_PATH", state_dir / "preferences.json")
    monkeypatch.setattr(setup, "LOCK_PATH", state_dir / ".lock")
    monkeypatch.setattr(setup, "LEGACY_CONFIG_DIR", legacy)

    return state_dir


def _run_status_capture(capsys) -> dict:
    """Invoke cmd_status and return the parsed JSON dict from stdout."""
    rc = setup.cmd_status(argparse.Namespace())
    assert rc == 0
    out = capsys.readouterr().out.strip()
    return json.loads(out)


def test_status_empty_state_dir_all_keys_false(isolated_state, capsys):
    """Empty state → all booleans False, all paths empty strings."""
    payload = _run_status_capture(capsys)

    assert set(payload.keys()) == EXPECTED_KEYS
    assert payload["anchor_exists"] is False
    assert payload["reference_exists"] is False
    assert payload["backend_available"] is False
    assert payload["legacy_state_present"] is False
    assert payload["anchor_path"] == ""
    assert payload["reference_path"] == ""
    assert payload["register_locked_until"] == ""
    assert payload["register_max"] == ""


def test_status_reports_anchor_and_reference_when_present(isolated_state, capsys):
    """Anchor + reference files in the state dir → exists flags True with absolute paths."""
    anchor = isolated_state / "visual_anchor.md"
    anchor.write_text("# Visual Anchor — Test\n\nbody\n")
    ref = isolated_state / "reference.png"
    ref.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes — file just needs to exist

    payload = _run_status_capture(capsys)

    assert payload["anchor_exists"] is True
    assert payload["reference_exists"] is True
    assert payload["anchor_path"] == str(anchor)
    assert payload["reference_path"] == str(ref)


def test_status_with_openai_key_marks_backend_available(
    isolated_state, capsys, monkeypatch
):
    """OPENAI_API_KEY=fake → backend_available True, backend_selected='openai'."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")

    payload = _run_status_capture(capsys)

    assert payload["backend_available"] is True
    assert "openai" in payload["backends_available"]
    assert payload["backend_selected"] == "openai"
    assert payload["backend_forced"] is False


def test_status_reflects_register_lock_after_set(isolated_state, capsys):
    """cmd_set_register_lock(--until X --max intimate) → status reports both."""
    args = argparse.Namespace(
        until="2099-01-01T00:00:00Z",
        max="intimate",
        clear=False,
    )
    rc = setup.cmd_set_register_lock(args)
    assert rc == 0
    capsys.readouterr()  # discard the lock-set print

    payload = _run_status_capture(capsys)

    assert payload["register_locked_until"] == "2099-01-01T00:00:00Z"
    assert payload["register_max"] == "intimate"


def test_status_register_lock_cleared_returns_empty_strings(isolated_state, capsys):
    """After --clear, register_locked_until + register_max are empty strings."""
    setup.cmd_set_register_lock(argparse.Namespace(
        until="2099-01-01T00:00:00Z", max="intimate", clear=False))
    capsys.readouterr()
    setup.cmd_set_register_lock(argparse.Namespace(
        until=None, max=None, clear=True))
    capsys.readouterr()

    payload = _run_status_capture(capsys)

    assert payload["register_locked_until"] == ""
    assert payload["register_max"] == ""


def test_status_eidolon_image_backend_env_marks_forced(
    isolated_state, capsys, monkeypatch
):
    """EIDOLON_IMAGE_BACKEND=gemini → backend_forced True, backend_selected='gemini'."""
    monkeypatch.setenv("EIDOLON_IMAGE_BACKEND", "gemini")

    payload = _run_status_capture(capsys)

    assert payload["backend_forced"] is True
    assert payload["backend_selected"] == "gemini"
