"""Tests for state.resolve_output_dir — picks where finished images land."""
from __future__ import annotations

from pathlib import Path

import state


def _patch_home(monkeypatch, tmp_home: Path) -> None:
    """Make Path.home() resolve to tmp_home for the duration of one test."""
    monkeypatch.setattr(Path, "home", lambda: tmp_home)


def test_env_var_wins(tmp_path, monkeypatch):
    """EIDOLON_OUTPUT_DIR=/tmp/foo → returns Path('/tmp/foo')."""
    target = tmp_path / "foo"
    monkeypatch.setenv("EIDOLON_OUTPUT_DIR", str(target))
    _patch_home(monkeypatch, tmp_path)

    out = state.resolve_output_dir()

    assert out == target.resolve()


def test_no_env_no_workspaces_falls_back_to_pictures(tmp_path, monkeypatch):
    """No env + no host workspaces → ~/Pictures/eidolon."""
    monkeypatch.delenv("EIDOLON_OUTPUT_DIR", raising=False)
    _patch_home(monkeypatch, tmp_path)
    # tmp_path has no .openclaw or .hermes — clean state.

    out = state.resolve_output_dir()

    assert out == tmp_path / "Pictures" / "eidolon"


def test_only_openclaw_workspace_exists(tmp_path, monkeypatch):
    """Only ~/.openclaw/workspace/ → returns <home>/.openclaw/workspace/eidolon."""
    monkeypatch.delenv("EIDOLON_OUTPUT_DIR", raising=False)
    _patch_home(monkeypatch, tmp_path)
    (tmp_path / ".openclaw" / "workspace").mkdir(parents=True)

    out = state.resolve_output_dir()

    assert out == tmp_path / ".openclaw" / "workspace" / "eidolon"


def test_only_hermes_workspace_exists(tmp_path, monkeypatch):
    """Only ~/.hermes/workspace/ → returns <home>/.hermes/workspace/eidolon."""
    monkeypatch.delenv("EIDOLON_OUTPUT_DIR", raising=False)
    _patch_home(monkeypatch, tmp_path)
    (tmp_path / ".hermes" / "workspace").mkdir(parents=True)

    out = state.resolve_output_dir()

    assert out == tmp_path / ".hermes" / "workspace" / "eidolon"


def test_both_workspaces_exist_openclaw_wins(tmp_path, monkeypatch):
    """Both ~/.openclaw/workspace/ and ~/.hermes/workspace/ → OpenClaw checked first.

    Pins current code behavior (scripts/generate.py lines 239-242: openclaw is
    iterated before hermes). The audit flagged this as docs-vs-code drift; this
    test pins behavior, not intent.
    """
    monkeypatch.delenv("EIDOLON_OUTPUT_DIR", raising=False)
    _patch_home(monkeypatch, tmp_path)
    (tmp_path / ".openclaw" / "workspace").mkdir(parents=True)
    (tmp_path / ".hermes" / "workspace").mkdir(parents=True)

    out = state.resolve_output_dir()

    assert out == tmp_path / ".openclaw" / "workspace" / "eidolon"
