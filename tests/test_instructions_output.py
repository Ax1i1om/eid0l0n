"""Tests for generate.emit_instructions and the public prompt-building API.

Default mode of generate.py prints an instructions JSON for the host agent
to consume (the agent renders via its own image-gen tool). This pins the
JSON shape and the anchor-clause invariant.
"""
from __future__ import annotations

import json
from pathlib import Path

import generate


PERSONA = "silver hair, pale grey eyes, slim build."
SCENE = "rooftop at golden hour, hand at temple, looking back over the shoulder."


# ─── anchor clause varies by mode ─────────────────────────────────────────

def test_anchor_clause_bootstrap_says_establish_canonical():
    out = generate.build_anchor_clause(has_reference=False, iterate_on_reference=False)
    assert "canonical reference portrait" in out.lower() or "establish" in out.lower()


def test_anchor_clause_with_reference_says_preserve_exactly():
    out = generate.build_anchor_clause(has_reference=True, iterate_on_reference=False)
    assert "exactly" in out.lower()
    assert "reference image" in out.lower()


def test_anchor_clause_iterate_says_apply_changes():
    out = generate.build_anchor_clause(has_reference=True, iterate_on_reference=True)
    assert "iterate" in out.lower()
    assert "apply" in out.lower()


def test_anchor_clauses_differ_per_mode():
    """The three modes must produce three distinct clauses."""
    bootstrap = generate.build_anchor_clause(False, False)
    with_ref = generate.build_anchor_clause(True, False)
    iterate = generate.build_anchor_clause(True, True)

    assert bootstrap != with_ref
    assert with_ref != iterate
    assert bootstrap != iterate


# ─── full prompt assembles in the right order ─────────────────────────────

def test_build_prompt_includes_anchor_persona_and_scene_in_order():
    """build_prompt = anchor_clause + persona + scene, in that order."""
    out = generate.build_prompt(SCENE, PERSONA, has_reference=True, iterate_on_reference=False)

    anchor_idx = out.find("Preserve the character EXACTLY")
    persona_idx = out.find(PERSONA)
    scene_idx = out.find(SCENE)

    assert anchor_idx >= 0, "anchor clause missing"
    assert persona_idx > anchor_idx, "persona must come after anchor"
    assert scene_idx > persona_idx, "scene must come after persona"


# ─── emit_instructions produces well-shaped JSON ──────────────────────────

REQUIRED_INSTRUCTION_KEYS = {
    "anchor_clause",
    "full_prompt",
    "reference_image",
    "output_path",
    "mode",
    "instructions",
}


def test_emit_instructions_prints_complete_json(capsys, tmp_path):
    """emit_instructions outputs all 6 required keys as parseable JSON."""
    ref = tmp_path / "ref.png"
    ref.write_bytes(b"\x89PNG\r\n\x1a\n")
    out_path = tmp_path / "eidolon" / "lyra-shot-20260501-120000.png"

    anchor = generate.build_anchor_clause(True, False)
    full_prompt = generate.build_prompt(SCENE, PERSONA, True, False)

    rc = generate.emit_instructions(full_prompt, anchor, ref, out_path, "with_reference")
    assert rc == 0

    captured = capsys.readouterr().out.strip()
    payload = json.loads(captured)

    assert set(payload.keys()) == REQUIRED_INSTRUCTION_KEYS
    assert payload["anchor_clause"] == anchor
    assert payload["full_prompt"] == full_prompt
    assert payload["reference_image"] == str(ref)
    assert payload["output_path"] == str(out_path)
    assert payload["mode"] == "with_reference"
    assert isinstance(payload["instructions"], str) and len(payload["instructions"]) > 0


def test_emit_instructions_null_reference_when_bootstrap(capsys, tmp_path):
    """In bootstrap mode (no reference), reference_image must be null in JSON."""
    out_path = tmp_path / "eidolon" / "lyra-cand-20260501-120000.png"
    anchor = generate.build_anchor_clause(False, False)
    full_prompt = generate.build_prompt(SCENE, PERSONA, False, False)

    generate.emit_instructions(full_prompt, anchor, None, out_path, "bootstrap")

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["reference_image"] is None
    assert payload["mode"] == "bootstrap"


def test_emit_instructions_mode_enum_values(capsys, tmp_path):
    """`mode` is one of the three documented enum values."""
    out_path = tmp_path / "eidolon" / "shot.png"
    anchor = generate.build_anchor_clause(True, True)
    full_prompt = generate.build_prompt(SCENE, PERSONA, True, True)

    generate.emit_instructions(full_prompt, anchor, Path("/some/ref.png"), out_path, "iterate_on_reference")
    payload = json.loads(capsys.readouterr().out.strip())

    assert payload["mode"] in {"bootstrap", "with_reference", "iterate_on_reference"}


# ─── output filename format ───────────────────────────────────────────────

def test_build_output_path_uses_slug_label_timestamp_pattern(tmp_path):
    """Filename = {slug}-{label}-{YYYYMMDD-HHMMSS}.png under the given dir."""
    out = generate.build_output_path("lyra", "cafe", tmp_path)

    name = out.name
    assert name.startswith("lyra-cafe-")
    assert name.endswith(".png")
    # Timestamp segment is YYYYMMDD-HHMMSS (15 chars: 8 + 1 + 6)
    ts_segment = name[len("lyra-cafe-"):-len(".png")]
    assert len(ts_segment) == 15
    assert ts_segment[8] == "-"
    assert ts_segment[:8].isdigit()
    assert ts_segment[9:].isdigit()


def test_build_output_path_sanitizes_label(tmp_path):
    """Label characters outside [a-zA-Z0-9_-] are stripped."""
    out = generate.build_output_path("lyra", "cafe; rm -rf /", tmp_path)

    name = out.name
    assert "; " not in name
    assert "/" not in name
    # Whitespace-stripped label keeps inner alphanumerics
    assert "carmrf" in name or "cafe" in name
