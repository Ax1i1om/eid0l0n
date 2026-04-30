"""Tests for state.resolve_output_dir — picks where finished images land.

Output mirrors the state-dir contract: whichever host defines cwd is also
where PNGs land. EIDOLON_OUTPUT_DIR is a per-call override; EIDOLON_HOME
re-routes both state and output together.
"""
from __future__ import annotations

from pathlib import Path

import state


def test_env_var_wins(tmp_path, monkeypatch):
    """EIDOLON_OUTPUT_DIR=<path> → returns that path verbatim."""
    target = tmp_path / "foo"
    monkeypatch.setenv("EIDOLON_OUTPUT_DIR", str(target))

    out = state.resolve_output_dir()

    assert out == target.resolve()


def test_env_output_dir_overrides_eidolon_home(tmp_path, monkeypatch):
    """EIDOLON_OUTPUT_DIR wins even when EIDOLON_HOME is also set."""
    home = tmp_path / "home"
    out_target = tmp_path / "elsewhere"
    monkeypatch.setenv("EIDOLON_HOME", str(home))
    monkeypatch.setenv("EIDOLON_OUTPUT_DIR", str(out_target))

    assert state.resolve_output_dir() == out_target.resolve()


def test_eidolon_home_drives_output(tmp_path, monkeypatch):
    """No EIDOLON_OUTPUT_DIR + EIDOLON_HOME=<path> → output = EIDOLON_HOME."""
    monkeypatch.delenv("EIDOLON_OUTPUT_DIR", raising=False)
    target = tmp_path / "custom"
    monkeypatch.setenv("EIDOLON_HOME", str(target))

    assert state.resolve_output_dir() == target.resolve()


def test_falls_back_to_cwd_eidolon(tmp_path, monkeypatch):
    """No env vars → output follows the state dir at <cwd>/eidolon/."""
    monkeypatch.delenv("EIDOLON_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("EIDOLON_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    out = state.resolve_output_dir()

    assert out.resolve() == (tmp_path / "eidolon").resolve()


def test_openclaw_cwd_routes_output_to_openclaw(tmp_path, monkeypatch):
    """When cwd is OpenClaw's workspace, output lands in that workspace."""
    monkeypatch.delenv("EIDOLON_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("EIDOLON_HOME", raising=False)
    openclaw_ws = tmp_path / ".openclaw" / "workspace"
    openclaw_ws.mkdir(parents=True)
    monkeypatch.chdir(openclaw_ws)

    out = state.resolve_output_dir()

    assert out.resolve() == (openclaw_ws / "eidolon").resolve()


def test_hermes_cwd_routes_output_to_hermes_even_when_openclaw_exists(tmp_path, monkeypatch):
    """Regression: when cwd is Hermes and ~/.openclaw also exists on disk,
    output MUST land under Hermes — not silently fall through to OpenClaw.

    Pre-fix, resolve_output_dir() probed hardcoded ``~/.openclaw/workspace``
    first and returned it whenever it existed, hijacking Hermes-generated
    images. The new contract derives output from cwd via _resolve_state_dir().
    """
    monkeypatch.delenv("EIDOLON_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("EIDOLON_HOME", raising=False)
    hermes_dir = tmp_path / ".hermes"
    openclaw_ws = tmp_path / ".openclaw" / "workspace"
    hermes_dir.mkdir(parents=True)
    openclaw_ws.mkdir(parents=True)  # both on disk; the bug case
    monkeypatch.chdir(hermes_dir)

    out = state.resolve_output_dir()

    assert out.resolve() == (hermes_dir / "eidolon").resolve()
    assert ".openclaw" not in str(out.resolve())
