"""Tests for detect_all, select_backend, and the BACKENDS registry."""
from __future__ import annotations

import pytest

import generate


EXPECTED_BACKEND_NAMES = ["codex", "gemini", "openai", "fal", "replicate", "openrouter"]


def test_backends_registry_has_six_named_entries():
    """BACKENDS is the priority-ordered list of 6 backends."""
    names = [name for name, _display, _detect, _gen in generate.BACKENDS]
    assert names == EXPECTED_BACKEND_NAMES


def test_backend_by_name_has_exactly_six_keys():
    """BACKEND_BY_NAME dict has exactly 6 keys (one per backend)."""
    assert set(generate.BACKEND_BY_NAME.keys()) == set(EXPECTED_BACKEND_NAMES)
    assert len(generate.BACKEND_BY_NAME) == 6


def test_detect_all_with_no_env_keys_returns_all_unavailable(
    clear_backend_env, tmp_path, monkeypatch
):
    """With no env keys and no codex auth, every backend reports unavailable."""
    # Force codex auth path to a non-existent location so codex_detect returns False.
    monkeypatch.setattr(generate, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")

    detections = generate.detect_all()

    assert set(detections.keys()) == set(EXPECTED_BACKEND_NAMES)
    for name, info in detections.items():
        assert info.get("available") is False, f"{name} unexpectedly available: {info}"


def test_detect_all_with_openai_key_marks_openai_available(
    clear_backend_env, tmp_path, monkeypatch
):
    """OPENAI_API_KEY=fake makes openai_detect report available=True."""
    monkeypatch.setattr(generate, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")

    detections = generate.detect_all()

    assert detections["openai"]["available"] is True
    # Other backends should still be unavailable.
    assert detections["gemini"]["available"] is False
    assert detections["fal"]["available"] is False


def test_select_backend_explicit_codex_overrides_detection(
    clear_backend_env, tmp_path, monkeypatch
):
    """select_backend('codex') returns 'codex' even when codex isn't detected."""
    monkeypatch.setattr(generate, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")

    chosen = generate.select_backend("codex")

    assert chosen == "codex"


def test_select_backend_unknown_name_exits(clear_backend_env):
    """select_backend with a name not in BACKEND_BY_NAME calls sys.exit."""
    with pytest.raises(SystemExit) as excinfo:
        generate.select_backend("nonexistent-backend")
    assert "nonexistent-backend" in str(excinfo.value)


def test_select_backend_no_keys_exits(clear_backend_env, tmp_path, monkeypatch):
    """With nothing available and no explicit choice, select_backend exits."""
    monkeypatch.setattr(generate, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")

    with pytest.raises(SystemExit) as excinfo:
        generate.select_backend(None)
    msg = str(excinfo.value)
    assert "no image-gen backend" in msg or "Configure" in msg


def test_eidolon_image_backend_env_forces_choice(
    clear_backend_env, tmp_path, monkeypatch
):
    """EIDOLON_IMAGE_BACKEND=gemini wins even if openai key is present."""
    monkeypatch.setattr(generate, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")
    monkeypatch.setenv("EIDOLON_IMAGE_BACKEND", "gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    chosen = generate.select_backend(None)

    assert chosen == "gemini"


def test_select_backend_auto_picks_first_available(
    clear_backend_env, tmp_path, monkeypatch
):
    """With only OPENAI_API_KEY set, auto-pick returns 'openai' (codex/gemini fail first)."""
    monkeypatch.setattr(generate, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    chosen = generate.select_backend(None)

    assert chosen == "openai"


def test_explicit_arg_beats_env_var(clear_backend_env, tmp_path, monkeypatch):
    """Explicit arg to select_backend wins over EIDOLON_IMAGE_BACKEND env."""
    monkeypatch.setattr(generate, "CODEX_AUTH_PATH", tmp_path / "no-codex-auth.json")
    monkeypatch.setenv("EIDOLON_IMAGE_BACKEND", "gemini")

    chosen = generate.select_backend("fal")

    assert chosen == "fal"
