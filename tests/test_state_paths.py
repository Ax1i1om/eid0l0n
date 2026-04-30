"""Tests for _resolve_state_dir, EIDOLON_HOME override, source-repo refusal,
and legacy_state_present()."""
from __future__ import annotations

from pathlib import Path

import pytest

import generate


def test_eidolon_home_env_var_is_honored(tmp_path, monkeypatch):
    """_resolve_state_dir honors EIDOLON_HOME unconditionally."""
    target = tmp_path / "custom-state"
    monkeypatch.setenv("EIDOLON_HOME", str(target))

    resolved = generate._resolve_state_dir()

    assert resolved == target.resolve()


def test_resolve_state_dir_returns_cwd_eidolon_when_no_env(tmp_path, monkeypatch):
    """When EIDOLON_HOME is unset and cwd is not the source repo,
    _resolve_state_dir returns <cwd>/eidolon/."""
    monkeypatch.delenv("EIDOLON_HOME", raising=False)
    monkeypatch.chdir(tmp_path)

    resolved = generate._resolve_state_dir()

    # Compare resolved paths to avoid symlink mismatches on macOS (/tmp vs /private/tmp).
    assert resolved.resolve() == (tmp_path / "eidolon").resolve()


def test_resolve_state_dir_refuses_source_repo(tmp_path, monkeypatch):
    """When cwd has .git + SKILL.md + scripts/ together, refuse with sys.exit."""
    monkeypatch.delenv("EIDOLON_HOME", raising=False)
    (tmp_path / ".git").mkdir()
    (tmp_path / "SKILL.md").write_text("# fake skill\n")
    (tmp_path / "scripts").mkdir()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        generate._resolve_state_dir()
    msg = str(excinfo.value)
    assert "source repo" in msg or "EIDOLON_HOME" in msg


def test_resolve_state_dir_allows_repo_when_only_some_markers_present(tmp_path, monkeypatch):
    """Refusal requires ALL three markers; missing any one should NOT refuse."""
    monkeypatch.delenv("EIDOLON_HOME", raising=False)
    # .git + SKILL.md but no scripts/ → not the source repo
    (tmp_path / ".git").mkdir()
    (tmp_path / "SKILL.md").write_text("# unrelated\n")
    monkeypatch.chdir(tmp_path)

    resolved = generate._resolve_state_dir()

    assert resolved.resolve() == (tmp_path / "eidolon").resolve()


def test_legacy_state_present_false_when_dir_missing(tmp_path, monkeypatch):
    """legacy_state_present returns False when ~/.config/eidolon/ doesn't exist."""
    monkeypatch.setattr(generate, "LEGACY_CONFIG_DIR", tmp_path / ".config" / "eidolon")

    assert generate.legacy_state_present() is False


def test_legacy_state_present_true_when_flat_anchor_exists(tmp_path, monkeypatch):
    """legacy_state_present returns True when legacy dir has visual_anchor.md at root."""
    legacy = tmp_path / ".config" / "eidolon"
    legacy.mkdir(parents=True)
    (legacy / "visual_anchor.md").write_text("# fake anchor\n")
    monkeypatch.setattr(generate, "LEGACY_CONFIG_DIR", legacy)

    assert generate.legacy_state_present() is True


def test_legacy_state_present_true_when_subdir_anchor_exists(tmp_path, monkeypatch):
    """legacy_state_present returns True when a subdir has visual_anchor.md."""
    legacy = tmp_path / ".config" / "eidolon"
    sub = legacy / "axiiiom"
    sub.mkdir(parents=True)
    (sub / "visual_anchor.md").write_text("# fake anchor\n")
    monkeypatch.setattr(generate, "LEGACY_CONFIG_DIR", legacy)

    assert generate.legacy_state_present() is True


def test_legacy_state_present_false_when_dir_empty(tmp_path, monkeypatch):
    """legacy_state_present returns False when legacy dir exists but has no anchor."""
    legacy = tmp_path / ".config" / "eidolon"
    legacy.mkdir(parents=True)
    monkeypatch.setattr(generate, "LEGACY_CONFIG_DIR", legacy)

    assert generate.legacy_state_present() is False
