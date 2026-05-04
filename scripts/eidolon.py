#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["openai>=1.0.0", "pillow>=10.0.0"]
# ///
"""EID0L0N — render entry point.

Usage (called by agent / sub-agent, NOT by users):
    echo '{"scene": "...", "label": "..."}' | uv run eidolon.py

Modes:
- Built-in Codex (when ~/.codex/auth.json exists with valid token):
  Renders directly via Codex Responses API + image_generation tool.
  Prints absolute PNG path on last stdout line.
- Instructions JSON fallback (no Codex auth):
  Prints {full_prompt, reference_image, output_path, instructions} for
  the agent's own image-gen tool. The agent renders to output_path.

Reads:
    - <state>/eidolon/visual_anchor.md  (character description)
    - <state>/eidolon/reference.png     (canonical face)

The agent writes the scene prose. This script bolts on the anchor clause +
character description, then either calls codex_backend.generate() or
emits instructions for the agent's own tool.
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
    raw = sys.stdin.read(1_000_001)
    if len(raw) > 1_000_000:
        print("error: stdin JSON too large (>1MB)", file=sys.stderr)
        return 2
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"error: invalid stdin JSON: {e.msg} at line {e.lineno}", file=sys.stderr)
        return 2
    if not isinstance(spec, dict):
        print(f"error: stdin JSON must be an object, got {type(spec).__name__}", file=sys.stderr)
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

    # Try built-in Codex backend first; if unavailable, emit instructions
    # JSON for the agent's own image tool to consume.
    if codex_backend.detect().get("available"):
        if not codex_backend.generate(full_prompt, ref_path, output_path):
            return 1
        print(str(output_path))
        return 0

    # Fallback: print instructions JSON. The agent uses its own image-gen
    # tool (MCP image plugin / curl + provider key / local renderer / etc.),
    # writes the resulting PNG to output_path, then surfaces it.
    instructions = {
        "full_prompt": full_prompt,
        "reference_image": str(ref_path),
        "output_path": str(output_path),
        "instructions": (
            "Render ONE image with whichever image-gen tool you have available "
            "(MCP image / curl + provider key / local renderer). The full_prompt "
            "is already anchored — do NOT paraphrase it. Attach reference_image "
            "to the request so the character matches. Save the PNG to output_path."
        ),
    }
    print(json.dumps(instructions, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
