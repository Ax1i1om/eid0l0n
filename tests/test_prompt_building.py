"""Tests for eidolon.py's prompt assembly building blocks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from eidolon import ANCHOR_CLAUSE, safe_label


def test_anchor_clause_uses_anatomical_landmarks():
    """Spec: anchor_clause uses bone structure / eye spacing / hair / etc.,
    not vague 'EXACTLY'."""
    assert "bone structure" in ANCHOR_CLAUSE
    assert "eye spacing" in ANCHOR_CLAUSE
    assert "hair" in ANCHOR_CLAUSE
    assert "EXACTLY" not in ANCHOR_CLAUSE  # diffusion-models-mis-read this


def test_anchor_clause_explicitly_frees_pose_expression_lighting():
    """Spec: explicit free-list prevents over-locking shot variability."""
    assert "pose" in ANCHOR_CLAUSE
    assert "expression" in ANCHOR_CLAUSE
    assert "lighting" in ANCHOR_CLAUSE


def test_anchor_clause_first_person():
    """Character voice: 'That picture is me' not 'Preserve the character'."""
    assert "me" in ANCHOR_CLAUSE.lower() or "my" in ANCHOR_CLAUSE.lower()


def test_safe_label_strips_special_chars():
    assert safe_label("hello world!@#") == "hello_world"


def test_safe_label_truncates_to_30():
    assert len(safe_label("a" * 100)) == 30


def test_safe_label_empty_falls_back_to_shot():
    assert safe_label("") == "shot"


def test_safe_label_only_special_chars_falls_back():
    assert safe_label("!@#$%^") == "shot"


def test_safe_label_preserves_underscore_and_dash():
    assert safe_label("my-test_label") == "my-test_label"
