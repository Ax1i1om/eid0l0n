#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
EID0L0N (skill name: `eidolon`) — generate one image, anchored to the persona + reference.

Code only enforces character consistency. Scene / action / mood / register / lighting /
composition language is in --prompt, written by the agent per SKILL.md guidance.

Usage:
    uv run generate.py --prompt "<scene>" --label "<short>"
    uv run generate.py --state idle | work_focused | street_dusk | ...
    uv run generate.py --prompt P --label L --bootstrap                  # no reference yet
    uv run generate.py --prompt P --label L --bootstrap --reference P    # iterate on a candidate
    uv run generate.py --prompt P --label L --reference PATH             # one-shot ref override
    uv run generate.py --backend gemini                                  # pick a specific backend
    uv run generate.py --list-scenes
    uv run generate.py --list-backends [--json]
    uv run generate.py --doctor

Backend auto-detection (priority order, first available wins):
    1. codex      — Codex/ChatGPT OAuth via ~/.codex/auth.json (no API key, free for Plus/Pro/Team)
    2. gemini     — GEMINI_API_KEY / GOOGLE_API_KEY (Google AI Studio direct)
    3. openai     — OPENAI_API_KEY (OpenAI Images API, gpt-image-2)
    4. fal        — FAL_KEY (fal.ai — flux, gpt-image-2, nano-banana, etc.)
    5. replicate  — REPLICATE_API_TOKEN (Replicate — flux, ideogram, etc.)
    6. openrouter — IMAGE_API_KEY / OPENROUTER_API_KEY (legacy default)

Override with EIDOLON_IMAGE_BACKEND=<name> or --backend <name>.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Make sibling-module imports work whether invoked as ``uv run generate.py``,
# ``python3 scripts/generate.py``, or ``import generate`` from a test harness.
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
from backends import (
    BACKEND_BY_NAME,
    BACKENDS,
    _PIL_OK,
    detect_all,
    select_backend,
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

def build_prompt(scene_text: str, persona_text: str, has_reference: bool, iterate_on_reference: bool) -> str:
    """Only the character-consistency clause is enforced. Scene/composition is the agent's job."""
    if iterate_on_reference:
        anchor_clause = (
            "Iterate on the attached image. Keep the character consistent with the description below "
            "(face structure, hair, eyes, identifying features), but APPLY the requested changes from the prompt. "
            "Treat the attached image as a starting point, not a rigid template."
        )
    elif has_reference:
        anchor_clause = (
            "Preserve the character EXACTLY as in the reference image — face structure, hair, eyes, "
            "skin, build, fixed identifiers, and art style must all match."
        )
    else:
        anchor_clause = (
            "Establish a canonical reference portrait of the character described below. "
            "All future shots will be anchored to this image, so prioritize clean visibility "
            "of face, hair, eyes, and identifying details."
        )
    return f"{anchor_clause}\n\nCharacter description:\n{persona_text}\n\n{scene_text.strip()}"


# ─── top-level dispatch ────────────────────────────────────────────────────

def generate(
    scene_text: str,
    label: str,
    anchor_path: Path,
    ref_path: Path | None,
    iterate_on_reference: bool,
    backend: str,
) -> str | None:
    if not _PIL_OK:
        sys.exit("error: pillow not installed. Run via `uv run` or: pip install pillow openai")
    persona_text, _, slug = parse_anchor(anchor_path)
    full_prompt = build_prompt(scene_text, persona_text, has_reference=ref_path is not None, iterate_on_reference=iterate_on_reference)
    out_dir = resolve_output_dir()

    _display, _detect, gen = BACKEND_BY_NAME[backend]
    out = gen(full_prompt, ref_path, slug, label, out_dir)
    if out is None:
        return None
    print(out)
    return str(out)


# ─── auxiliary commands ────────────────────────────────────────────────────

def cmd_doctor() -> int:
    load_env_file()
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
    print("  backends (priority order, first available is auto-pick):")
    selected = None
    forced = (os.environ.get("EIDOLON_IMAGE_BACKEND") or "").strip().lower()
    detections = detect_all()
    for name, display, _detect, _gen in BACKENDS:
        info = detections[name]
        ok = "✓" if info.get("available") else "✗"
        if info.get("available") and selected is None:
            selected = name
        extra = f"  ({info.get('credit')})" if info.get("available") else f"  — {info.get('missing','')}"
        print(f"    {ok} {name:11s} {display}{extra}")
    if forced:
        print(f"\n  EIDOLON_IMAGE_BACKEND={forced}  (forced override)")
    elif selected:
        print(f"\n  auto-selected:        {selected}")
    else:
        print(f"\n  auto-selected:        (none — configure one)")
    return 0


def cmd_list_scenes() -> int:
    print("eidolon built-in scene shortcuts (use --state <name>):\n")
    for name, desc in sorted(SCENES.items()):
        print(f"  {name:18s}  {desc[:90]}")
    print("\nThese are starting points. For full control, write your own scene prose with --prompt.")
    return 0


def cmd_list_backends(as_json: bool) -> int:
    load_env_file()
    detections = detect_all()
    forced = (os.environ.get("EIDOLON_IMAGE_BACKEND") or "").strip().lower()
    auto = next((name for name, _d, det, _g in BACKENDS if det().get("available")), None)
    if as_json:
        print(json.dumps({
            "selected":  forced or auto or "",
            "forced":    bool(forced),
            "available": [name for name, info in detections.items() if info.get("available")],
            "details":   detections,
        }, indent=2))
    else:
        print("eidolon image-gen backends (priority order):\n")
        for name, display, _det, _gen in BACKENDS:
            info = detections[name]
            ok = "✓" if info.get("available") else "✗"
            extra = f"  ({info.get('credit')})" if info.get("available") else f"  — {info.get('missing','')}"
            print(f"  {ok} {name:11s} {display}{extra}")
        if forced:
            print(f"\nEIDOLON_IMAGE_BACKEND={forced}  (forced override)")
        elif auto:
            print(f"\nauto-selected: {auto}")
    return 0


# ─── main ──────────────────────────────────────────────────────────────────

def main() -> int:
    load_env_file()
    p = argparse.ArgumentParser(prog="eidolon", description="Generate one persona-anchored image.")
    p.add_argument("--prompt", "-p", help="Full scene/action/composition text — written by the agent")
    p.add_argument("--state",  "-s", help="Built-in scene shortcut key (see --list-scenes)")
    p.add_argument("--label",  "-l", default="shot", help="Filename label")
    p.add_argument("--anchor",       help="Override visual_anchor.md path")
    p.add_argument("--reference",    help="Override reference image path (per-call)")
    p.add_argument("--bootstrap", action="store_true", help="No reference image required (or iterate on one with --reference)")
    p.add_argument("--backend",      help=f"Force backend ({', '.join(BACKEND_BY_NAME)}). Overrides EIDOLON_IMAGE_BACKEND.")
    p.add_argument("--list-scenes", action="store_true")
    p.add_argument("--list-backends", action="store_true")
    p.add_argument("--json", action="store_true", help="Use with --list-backends for machine-readable output")
    p.add_argument("--doctor", action="store_true")
    args = p.parse_args()

    if args.doctor:         return cmd_doctor()
    if args.list_scenes:    return cmd_list_scenes()
    if args.list_backends:  return cmd_list_backends(args.json)

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
    _, anchor_ref, _ = parse_anchor(anchor_path)

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

    backend = select_backend(args.backend)
    return 0 if generate(scene_text, label, anchor_path, ref_path, iterate_on_reference, backend) else 1


if __name__ == "__main__":
    sys.exit(main())
