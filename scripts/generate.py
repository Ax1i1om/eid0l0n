#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
EID0L0N (skill name: `eidolon`) — produce one image, anchored to the persona.

Two modes:

  Instructions mode (DEFAULT):
      Prints a JSON blob with anchor_clause, full_prompt, reference_image,
      output_path, and instructions. The HOST AGENT renders the image using
      its own image-gen tool (MCP / curl / local ComfyUI / etc.) and writes
      it to output_path. eid0l0n does not call any external image API.

  --use-codex:
      Render via the built-in Codex (ChatGPT OAuth) backend and save the PNG.
      The only backend shipped as code, for ChatGPT Plus/Pro/Team users who
      want zero-config white-label image generation.

Usage:
    uv run generate.py --prompt "<scene>" --label "<short>"
    uv run generate.py --state idle | work_focused | street_dusk | ...
    uv run generate.py --prompt P --bootstrap                   # no reference yet
    uv run generate.py --prompt P --bootstrap --reference P     # iterate on a candidate
    uv run generate.py --prompt P --reference PATH              # one-shot ref override
    uv run generate.py --prompt P --use-codex                   # render via Codex
    uv run generate.py --list-scenes
    uv run generate.py --doctor

The script ENFORCES character consistency. Scene / action / mood / register /
lighting / composition is in --prompt, written by the agent per SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import (
    ANCHOR_PATH,
    CONFIG_DIR,
    PREFS_PATH,
    SKILL_DIR,
    _read_text_normalized,
    load_env_file,
    parse_anchor,
    resolve_anchor_path,
    resolve_output_dir,
    resolve_reference_path,
)


# ─── built-in scene shortcuts ──────────────────────────────────────────────

SCENES = {
    "idle":            "medium shot, living room, warm afternoon light, sitting on sofa, knees tucked, relaxed, reading",
    "work_focused":    "close-up over the shoulder, home office at night, monitors with code, cool blue glow, focused gaze, hands at keyboard",
    "work_morning":    "medium shot, minimal desk by window, morning light, hand wrapped around a mug, glancing up from a notebook",
    "street_dusk":     "wide medium shot, city crosswalk at dusk, traffic lights on wet pavement, head turned mid-stride looking back",
    "street_neon":     "medium shot, narrow alley at night, neon signage above, leaning against brick, hands in pockets, smoke in air",
    "cafe_window":     "close-up, café table by a rain-streaked window, hand at chin, cup steaming, soft overcast light",
    "rooftop_dusk":    "wide shot, rooftop at golden hour, wind in hair, city skyline behind, contemplative, jacket open",
    "rain_window":     "medium shot from inside, rain-streaked window at night, city glow outside, looking through the glass, soft Rembrandt lighting",
    "kitchen_night":   "medium shot, modern kitchen, late night, making tea, soft overhead pendant light, oversized shirt",
    "library_quiet":   "medium shot, library aisle, late afternoon shafts through high windows, pulling a book from a shelf, half-turned",
    "morning_window":  "close-up, bedroom, soft morning light, just woken up, oversized shirt, blinking at the window",
    "walking_back":    "wide shot from behind, tree-lined street, walking away with head turned over the shoulder, late afternoon light",
}


# ─── prompt assembly ───────────────────────────────────────────────────────

def build_anchor_clause(has_reference: bool, iterate_on_reference: bool) -> str:
    """The character-consistency clause — the project's only invariant.

    Built here (script-side) so every backend, including agent-written ones,
    receives an already-anchored prompt and can't accidentally drift the
    character by paraphrasing or skipping the lock.
    """
    if iterate_on_reference:
        return (
            "Iterate on the attached image. Keep the character consistent with the description below "
            "(face structure, hair, eyes, identifying features), but APPLY the requested changes from the prompt. "
            "Treat the attached image as a starting point, not a rigid template."
        )
    if has_reference:
        return (
            "Preserve the character EXACTLY as in the reference image — face structure, hair, eyes, "
            "skin, build, fixed identifiers, and art style must all match."
        )
    return (
        "Establish a canonical reference portrait of the character described below. "
        "All future shots will be anchored to this image, so prioritize clean visibility "
        "of face, hair, eyes, and identifying details."
    )


def build_prompt(scene_text: str, persona_text: str, has_reference: bool, iterate_on_reference: bool) -> str:
    """Compose the final prompt: anchor clause + persona description + scene."""
    anchor_clause = build_anchor_clause(has_reference, iterate_on_reference)
    return f"{anchor_clause}\n\nCharacter description:\n{persona_text}\n\n{scene_text.strip()}"


def build_output_path(slug: str, label: str, out_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", label.replace(" ", "_"))[:30] or "shot"
    return out_dir / f"{slug}-{safe}-{ts}.png"


def _mode(has_reference: bool, iterate_on_reference: bool) -> str:
    if iterate_on_reference:
        return "iterate_on_reference"
    if has_reference:
        return "with_reference"
    return "bootstrap"


# ─── path safety ───────────────────────────────────────────────────────────

def _under(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _validate_paths(ref_path: Path | None) -> None:
    """Reject reference paths that escape the workspace.

    ref_path is anchor-controlled — a poisoned ``visual_anchor.md`` could
    set ``reference: ~/.aws/credentials`` and the agent's image-gen tool
    would base64-encode and POST it. We reject any reference that resolves
    outside the workspace (cwd) before the prompt leaves the script.

    out_dir is NOT validated here: ``EIDOLON_OUTPUT_DIR`` is a documented
    user-set escape hatch ("point PNGs at a separate disk while state stays
    in the workspace") and the user is trusted with their own filesystem.
    """
    if ref_path is None:
        return
    workspace = CONFIG_DIR.parent
    if not _under(ref_path, workspace):
        sys.exit(f"error: reference image escapes workspace: {ref_path!r}")


# ─── instructions mode ─────────────────────────────────────────────────────

def emit_instructions(
    full_prompt: str,
    anchor_clause: str,
    ref_path: Path | None,
    output_path: Path,
    mode: str,
) -> int:
    payload = {
        "anchor_clause":   anchor_clause,
        "full_prompt":     full_prompt,
        "reference_image": str(ref_path) if ref_path else None,
        "output_path":     str(output_path),
        "mode":            mode,
        "instructions": (
            "Generate ONE image using whichever image-gen tool you have configured "
            "(MCP image tool / curl + your API key / local ComfyUI / etc.). "
            "The full_prompt is already anchored — do NOT paraphrase it. "
            "If reference_image is set, attach it to the request so the character matches. "
            "Save the resulting PNG (or any image format — eid0l0n will normalize) to output_path. "
            "Then confirm the file exists at output_path."
        ),
    }
    print(json.dumps(payload, indent=2))
    return 0


# ─── codex mode ────────────────────────────────────────────────────────────

def render_via_codex(full_prompt: str, ref_path: Path | None, output_path: Path) -> int:
    import codex_backend
    ok = codex_backend.generate(full_prompt, ref_path, output_path)
    if not ok:
        return 1
    print(str(output_path))
    return 0


# ─── auxiliary commands ────────────────────────────────────────────────────

def cmd_doctor() -> int:
    load_env_file()
    import codex_backend
    print("eidolon doctor")
    print(f"  skill dir:    {SKILL_DIR}")
    print(f"  config dir:   {CONFIG_DIR}{'  (exists)' if CONFIG_DIR.exists() else '  (missing)'}")
    print(f"  visual_anchor:{ANCHOR_PATH}{'  ✓' if ANCHOR_PATH.exists() else '  ✗ (run setup.py save-anchor)'}")
    ref = None
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = CONFIG_DIR / f"reference.{ext}"
        if p.exists():
            ref = p; break
    print(f"  reference:    {ref or '✗ (run setup.py save-reference, or generate with --bootstrap)'}")
    if PREFS_PATH.exists():
        try:
            prefs = json.loads(_read_text_normalized(PREFS_PATH))
            if prefs.get("locked_until"):
                print(f"  register lock:until {prefs['locked_until']} max {prefs.get('max_register','?')}")
            else:
                print(f"  register lock:(none)")
        except json.JSONDecodeError:
            print(f"  register lock:(preferences.json corrupt)")
    else:
        print(f"  register lock:(none)")
    print(f"  output dir:   {resolve_output_dir()}")
    print()
    info = codex_backend.detect()
    if info.get("available"):
        print(f"  codex (built-in):  ✓  {info.get('credit','')}")
    else:
        print(f"  codex (built-in):  ✗  {info.get('missing','')}")
    print()
    print("  Other backends: handled by the host agent. eid0l0n does not")
    print("  detect or call them. The agent uses its own image-gen tool")
    print("  (MCP / curl / local ComfyUI) on the instructions JSON.")
    return 0


def cmd_list_scenes() -> int:
    print("eidolon built-in scene shortcuts (use --state <name>):\n")
    for name, desc in sorted(SCENES.items()):
        print(f"  {name:18s}  {desc[:90]}")
    print("\nThese are starting points. For full control, write your own scene prose with --prompt.")
    return 0


# ─── main ──────────────────────────────────────────────────────────────────

def main() -> int:
    load_env_file()
    p = argparse.ArgumentParser(prog="eidolon", description="Produce one persona-anchored image.")
    p.add_argument("--prompt", "-p", help="Full scene/action/composition text — written by the agent")
    p.add_argument("--state",  "-s", help="Built-in scene shortcut key (see --list-scenes)")
    p.add_argument("--label",  "-l", default="shot", help="Filename label")
    p.add_argument("--anchor",       help="Override visual_anchor.md path")
    p.add_argument("--reference",    help="Override reference image path (per-call)")
    p.add_argument("--bootstrap", action="store_true", help="No reference image required (or iterate on one with --reference)")
    p.add_argument("--use-codex", action="store_true",
                   help="Render via the built-in Codex (ChatGPT OAuth) backend instead of emitting instructions for the agent.")
    p.add_argument("--list-scenes", action="store_true")
    p.add_argument("--doctor", action="store_true")
    args = p.parse_args()

    if args.doctor:        return cmd_doctor()
    if args.list_scenes:   return cmd_list_scenes()

    if args.prompt:
        scene_text, label = args.prompt, args.label
    elif args.state:
        scene_text = SCENES.get(args.state)
        if not scene_text:
            print(f"unknown scene: {args.state}. Try --list-scenes.", file=sys.stderr)
            return 1
        label = args.state
    else:
        p.print_help()
        return 1

    anchor_path = resolve_anchor_path(args.anchor)
    persona_text, anchor_ref, slug = parse_anchor(anchor_path)

    iterate_on_reference = False
    if args.bootstrap:
        if args.reference:
            ref_path = Path(args.reference).expanduser().resolve()
            if not ref_path.exists():
                sys.exit(f"error: --reference not found: {ref_path}")
            iterate_on_reference = True
        else:
            ref_path = None
    else:
        ref_path = resolve_reference_path(args.reference, anchor_ref)
        if ref_path is None:
            sys.exit("error: no reference image. Either pass --bootstrap (initial portrait) or run: setup.py save-reference --src <path>")

    _validate_paths(ref_path)
    out_dir = resolve_output_dir()
    output_path = build_output_path(slug, label, out_dir)

    has_reference = ref_path is not None
    anchor_clause = build_anchor_clause(has_reference, iterate_on_reference)
    full_prompt = build_prompt(scene_text, persona_text, has_reference, iterate_on_reference)
    mode = _mode(has_reference, iterate_on_reference)

    if args.use_codex:
        return render_via_codex(full_prompt, ref_path, output_path)
    return emit_instructions(full_prompt, anchor_clause, ref_path, output_path, mode)


if __name__ == "__main__":
    sys.exit(main())
