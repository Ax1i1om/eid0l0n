"""Tests for setup.cmd_status — JSON state dump emitted by `setup.py status`."""
from __future__ import annotations

import argparse
import json

import pytest

import codex_backend
import setup
import state


# Keys actually emitted by cmd_status in 0.8+. The shape changed: image-API
# detection fields (api_key_set, backend_*, backends_available) are gone;
# codex-specific fields and an output_dir field were added.
EXPECTED_KEYS = {
    "anchor_exists",
    "reference_exists",
    "anchor_path",
    "reference_path",
    "register_locked_until",
    "register_max",
    "codex_available",
    "codex_credit",
    "codex_missing",
    "state_dir",
    "output_dir",
    "workspace_cwd",
    "legacy_state_present",
    "legacy_config_dir",
}


@pytest.fixture
def isolated_state(tmp_path, monkeypatch, clear_image_env):
    """Redirect state + setup paths into tmp_path, also block codex auth.

    Paths live canonically in `state` module; `setup` re-binds them at import,
    and helpers like find_existing_reference / legacy_state_present execute in
    `state`'s scope. We patch BOTH modules so every reader sees tmp_path, and
    patch CODEX_AUTH_PATH on `codex_backend` to a non-existent path so codex
    is reported unavailable by default.
    """
    state_dir = tmp_path / "eidolon"
    state_dir.mkdir()
    legacy = tmp_path / "legacy-config-eidolon"  # never auto-created → legacy_state_present=False

    # `state` module is the canonical home of these paths.
    monkeypatch.setattr(state, "CONFIG_DIR", state_dir)
    monkeypatch.setattr(state, "ANCHOR_PATH", state_dir / "visual_anchor.md")
    monkeypatch.setattr(state, "ENV_PATH", state_dir / "env")
    monkeypatch.setattr(state, "PREFS_PATH", state_dir / "preferences.json")
    monkeypatch.setattr(state, "LOCK_PATH", state_dir / ".lock")
    monkeypatch.setattr(state, "LEGACY_CONFIG_DIR", legacy)

    # `codex_backend` owns CODEX_AUTH_PATH after the 0.8 refactor.
    monkeypatch.setattr(codex_backend, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")

    # `setup` re-binds the path names at import time; cmd_status reads its OWN
    # ANCHOR_PATH global (not state.ANCHOR_PATH), so patch those bindings too.
    monkeypatch.setattr(setup, "CONFIG_DIR", state_dir)
    monkeypatch.setattr(setup, "ANCHOR_PATH", state_dir / "visual_anchor.md")
    monkeypatch.setattr(setup, "PREFS_PATH", state_dir / "preferences.json")
    monkeypatch.setattr(setup, "LEGACY_CONFIG_DIR", legacy)

    # cmd_status calls resolve_output_dir() at runtime, which reads EIDOLON_HOME
    # from the env (not state.CONFIG_DIR). Align the env var with the patched
    # state dir so output_dir reflects the per-test isolated dir, not the
    # session-level conftest tmp dir.
    monkeypatch.setenv("EIDOLON_HOME", str(state_dir))

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
    assert payload["codex_available"] is False
    assert payload["legacy_state_present"] is False
    assert payload["anchor_path"] == ""
    assert payload["reference_path"] == ""
    assert payload["register_locked_until"] == ""
    assert payload["register_max"] == ""
    assert payload["codex_credit"] == ""
    # codex_missing is populated when codex is unavailable
    assert payload["codex_missing"] != ""


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


def test_status_reports_state_and_output_dir_match_by_default(isolated_state, capsys):
    """state_dir == output_dir when EIDOLON_OUTPUT_DIR is unset."""
    payload = _run_status_capture(capsys)

    assert payload["state_dir"] == str(isolated_state)
    assert payload["output_dir"] == str(isolated_state)


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


def test_status_codex_available_when_auth_present(isolated_state, capsys, monkeypatch, tmp_path):
    """Plant a synthetic codex auth.json (non-expired JWT) → codex_available True."""
    import base64
    import json as _json
    import time

    payload = {
        "exp": int(time.time()) + 3600,  # 1 hour from now
        "https://api.openai.com/auth": {"chatgpt_account_id": "test-acct-uuid"},
    }
    payload_b64 = base64.urlsafe_b64encode(_json.dumps(payload).encode()).rstrip(b"=").decode()
    fake_token = f"header.{payload_b64}.sig"

    auth_path = tmp_path / "fake-codex-auth.json"
    auth_path.write_text(_json.dumps({"tokens": {"access_token": fake_token}}))
    monkeypatch.setattr(codex_backend, "CODEX_AUTH_PATH", auth_path)

    payload_out = _run_status_capture(capsys)

    assert payload_out["codex_available"] is True
    assert payload_out["codex_credit"] != ""
    assert payload_out["codex_missing"] == ""
