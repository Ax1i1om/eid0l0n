#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["openai>=1.0.0", "pillow>=10.0.0"]
# ///
"""EID0L0N — render entry point.

Usage (called by agent / sub-agent, NOT by users):
    echo '{"scene": "...", "label": "..."}' | python3 eidolon.py

Reads:
    - <state>/eidolon/visual_anchor.md  (character description)
    - <state>/eidolon/reference.png     (canonical face)

Writes:
    - <state>/eidolon/output/<slug>-<label>-<ts>.png

Prints (last line of stdout): the absolute path of the saved PNG.

The agent writes the scene prose. This script bolts on the anchor clause +
character description, then calls codex_backend.generate().
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import (
    find_existing_reference,
    parse_anchor,
    resolve_state_dir,
    validate_reference_path,
)
import codex_backend


# Anchor clause: prepended to every render. Tested wording — uses anatomical
# landmarks the diffusion model actually recognizes, explicitly frees the
# variables that change shot-to-shot.
ANCHOR_CLAUSE = (
    "That picture is me. Keep my face — bone structure, eye spacing, the line "
    "of my nose, the way my hair falls. Keep the way I dress and the visual "
    "style. The scene below is just where I am right now — pose, expression, "
    "and lighting change shot to shot."
)


def safe_label(label: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", label.replace(" ", "_"))[:30] or "shot"


def main() -> int:
    try:
        spec = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"error: invalid stdin JSON: {e.msg} at line {e.lineno}", file=sys.stderr)
        return 2
    scene = str(spec.get("scene", "")).strip()
    label = safe_label(str(spec.get("label", "shot")))
    if not scene:
        print("error: missing 'scene' in stdin JSON", file=sys.stderr)
        return 2

    state_dir = resolve_state_dir()
    anchor_path = state_dir / "visual_anchor.md"
    if not anchor_path.exists():
        print(f"error: no visual_anchor.md at {anchor_path}", file=sys.stderr)
        return 1

    # Reference is sourced by filename (find_existing_reference);
    # the anchor's `reference:` header is legacy/migration-only.
    persona_text, _, slug = parse_anchor(anchor_path)
    ref_path = find_existing_reference(state_dir)
    if ref_path is None:
        print(f"error: no reference image in {state_dir}", file=sys.stderr)
        return 1
    validate_reference_path(ref_path, state_dir.parent)

    full_prompt = f"{ANCHOR_CLAUSE}\n\nCharacter description:\n{persona_text}\n\n{scene}"

    output_dir = state_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]  # ms precision
    output_path = output_dir / f"{slug}-{label}-{ts}.png"

    if not codex_backend.generate(full_prompt, ref_path, output_path):
        return 1

    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
