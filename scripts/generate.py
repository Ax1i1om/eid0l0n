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
    uv run generate.py --list-scenes
    uv run generate.py --doctor
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

# PIL is required for generation, but defer the hard error so --help / --doctor /
# --list-scenes still work without it. Imported at the top of generate() with a
# clear error message before any API call.
try:
    from PIL import Image as PILImage
    _PIL_OK = True
except ImportError:
    PILImage = None  # type: ignore
    _PIL_OK = False

SKILL_DIR    = Path(__file__).resolve().parent.parent
CONFIG_DIR   = Path.home() / ".config" / "eidolon"
ANCHOR_PATH  = CONFIG_DIR / "visual_anchor.md"
ENV_PATH     = CONFIG_DIR / "env"
PREFS_PATH   = CONFIG_DIR / "preferences.json"

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODELS = [
    "google/gemini-2.5-flash-image-preview",
    "google/gemini-2.5-flash",
]

# Retry config: 3 attempts per model with exponential backoff on transient errors.
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 0.5  # seconds; doubles each retry
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

# Scene shortcuts. Agent can use --state for quick recurring shots OR --prompt for full control.
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


def _read_text_normalized(path: Path) -> str:
    return path.read_text().replace("\r\n", "\n").replace("\r", "\n")


def load_env_file() -> None:
    if not ENV_PATH.exists():
        return
    for line in _read_text_normalized(ENV_PATH).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'").strip('"'))


def resolve_api() -> tuple[str, str, list[str]]:
    key = os.environ.get("IMAGE_API_KEY", "").strip()
    if not key:
        sys.exit("error: IMAGE_API_KEY not set. Run: setup.py set-api --key <KEY>")
    base = os.environ.get("IMAGE_API_BASE_URL", DEFAULT_BASE_URL).strip()
    models_env = os.environ.get("IMAGE_API_MODELS", "").strip()
    models = [m.strip() for m in models_env.split(",") if m.strip()] if models_env else list(DEFAULT_MODELS)
    return key, base, models


def resolve_anchor_path(cli: str | None) -> Path:
    candidates = [
        cli,
        os.environ.get("EIDOLON_VISUAL_ANCHOR"),
        os.environ.get("EID0L0N_VISUAL_ANCHOR"),  # back-compat
        str(ANCHOR_PATH),
        str(SKILL_DIR / "references" / "persona.example.md"),
    ]
    for c in candidates:
        if c and Path(c).expanduser().exists():
            p = Path(c).expanduser().resolve()
            if "persona.example.md" in str(p):
                print("warning: using shipped example persona; agent should run setup.py save-anchor first.", file=sys.stderr)
            return p
    sys.exit("error: no visual_anchor.md. Agent should pipe SOUL visual section to: setup.py save-anchor")


def parse_anchor(path: Path) -> tuple[str, str | None, str]:
    """Return (anchor_text_without_headers, reference_path_string, character_slug)."""
    text = _read_text_normalized(path)
    ref = None
    m = re.search(r"^reference:\s*(.+)$", text, flags=re.MULTILINE)
    if m:
        ref = m.group(1).strip()
        text = re.sub(r"^reference:\s*.+$\n?", "", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^imported_from:\s*.+$\n?", "", text, count=1, flags=re.MULTILINE)

    name_match = re.search(r"^#\s*(?:Visual\s*Anchor|Persona)\s*[—\-:]\s*(.+)$", text, flags=re.MULTILINE | re.IGNORECASE)
    if not name_match:
        name_match = re.search(r"^#\s*(.+)$", text, flags=re.MULTILINE)
    name = name_match.group(1).strip() if name_match else "character"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_") or "character"
    return text.strip(), ref, slug


def resolve_reference_path(cli: str | None, anchor_ref: str | None) -> Path | None:
    candidates = [
        cli,
        os.environ.get("EIDOLON_REFERENCE"),
        os.environ.get("EID0L0N_REFERENCE"),  # back-compat
        anchor_ref,
    ]
    for c in candidates:
        if c:
            p = Path(c).expanduser().resolve()
            if p.exists():
                return p
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = CONFIG_DIR / f"reference.{ext}"
        if p.exists():
            return p
    return None


def resolve_output_dir() -> Path:
    env = os.environ.get("EIDOLON_OUTPUT_DIR") or os.environ.get("EID0L0N_OUTPUT_DIR")
    if env:
        return Path(env).expanduser().resolve()
    home = Path.home()
    for host_dir in (home / ".openclaw" / "workspace", home / ".hermes" / "workspace"):
        if host_dir.exists():
            return host_dir / "eidolon"
    return home / "Pictures" / "eidolon"


def extract_image_bytes(data: dict) -> bytes | None:
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content", "")
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        return base64.b64decode(url.split(",", 1)[1])
        if isinstance(content, str):
            m = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=\n]+)", content)
            if m:
                return base64.b64decode(m.group(1).replace("\n", ""))
        for img in msg.get("images", []):
            url_obj = img.get("image_url", {})
            url = url_obj.get("url", "") if isinstance(url_obj, dict) else str(url_obj)
            if url.startswith("data:"):
                return base64.b64decode(url.split(",", 1)[1])
    return None


def build_prompt(scene_text: str, persona_text: str, has_reference: bool, iterate_on_reference: bool) -> str:
    """Only the character-consistency clause is enforced. Scene/composition is the agent's job.

    iterate_on_reference=True → --bootstrap + --reference (regen of a candidate). The clause softens
    from 'preserve exactly' to 'iterate on this image' so feedback like 'softer expression' isn't
    fought by identity-lock.
    """
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
    return (
        f"{anchor_clause}\n\n"
        f"Character description:\n{persona_text}\n\n"
        f"{scene_text.strip()}"
    )


def _is_retryable(exc: Exception) -> bool:
    name = type(exc).__name__
    if name in ("APIConnectionError", "APITimeoutError", "TimeoutException", "ReadTimeout", "ConnectTimeout"):
        return True
    status = getattr(exc, "status_code", None)
    if status in RETRYABLE_STATUS:
        return True
    msg = str(exc).lower()
    return any(kw in msg for kw in ("timeout", "connection reset", "temporarily", "rate limit", "503"))


def generate(
    scene_text: str,
    label: str,
    anchor_path: Path,
    ref_path: Path | None,
    iterate_on_reference: bool,
) -> str | None:
    if not _PIL_OK:
        sys.exit("error: pillow not installed. Run via `uv run` or: pip install pillow openai")
    from openai import OpenAI

    persona_text, _, slug = parse_anchor(anchor_path)
    full_prompt = build_prompt(scene_text, persona_text, has_reference=ref_path is not None, iterate_on_reference=iterate_on_reference)

    out_dir = resolve_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    content: list[dict] = []
    if ref_path is not None:
        ext = ref_path.suffix.lstrip(".").lower() or "jpeg"
        if ext == "jpg": ext = "jpeg"
        b64 = base64.b64encode(ref_path.read_bytes()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}})
    content.append({"type": "text", "text": full_prompt})

    key, base, models = resolve_api()
    client = OpenAI(base_url=base, api_key=key)

    for model in models:
        print(f"  · {model}", file=sys.stderr)
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                resp = client.chat.completions.with_raw_response.create(
                    model=model,
                    messages=[{"role": "user", "content": content}],
                    max_tokens=8192,
                )
                data = json.loads(resp.content)
                img_bytes = extract_image_bytes(data)
                if not img_bytes or len(img_bytes) < 1000:
                    print(f"    attempt {attempt}: no image extracted", file=sys.stderr)
                    print(f"    response keys: {list(data.keys())}", file=sys.stderr)
                    break  # not retryable; try next model
                img = PILImage.open(BytesIO(img_bytes))
                if img.mode == "RGBA":
                    bg = PILImage.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                safe = re.sub(r"[^a-zA-Z0-9_-]", "", label.replace(" ", "_"))[:30] or "shot"
                out = out_dir / f"{slug}-{safe}-{ts}.png"
                img.save(str(out), "PNG")
                print(out)  # last stdout line = absolute path (host contract)
                return str(out)
            except Exception as e:
                if _is_retryable(e) and attempt < RETRY_ATTEMPTS:
                    backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                    print(f"    attempt {attempt}: {type(e).__name__}: {e} — retrying in {backoff}s", file=sys.stderr)
                    time.sleep(backoff)
                    continue
                print(f"    attempt {attempt}: {type(e).__name__}: {e}", file=sys.stderr)
                break  # non-retryable or exhausted; advance to next model
    print("error: all models exhausted", file=sys.stderr)
    return None


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
    print(f"  IMAGE_API_KEY:{'  set' if os.environ.get('IMAGE_API_KEY') else '  UNSET'}")
    print(f"  base URL:     {os.environ.get('IMAGE_API_BASE_URL') or DEFAULT_BASE_URL}")
    print(f"  output dir:   {resolve_output_dir()}")
    return 0


def cmd_list_scenes() -> int:
    print("eidolon built-in scene shortcuts (use --state <name>):\n")
    for name, desc in sorted(SCENES.items()):
        print(f"  {name:18s}  {desc[:90]}")
    print("\nThese are starting points. For full control, write your own scene prose with --prompt.")
    return 0


def main() -> int:
    load_env_file()
    p = argparse.ArgumentParser(prog="eidolon", description="Generate one persona-anchored image.")
    p.add_argument("--prompt", "-p", help="Full scene/action/composition text — written by the agent")
    p.add_argument("--state",  "-s", help="Built-in scene shortcut key (see --list-scenes)")
    p.add_argument("--label",  "-l", default="shot", help="Filename label")
    p.add_argument("--anchor",       help="Override visual_anchor.md path")
    p.add_argument("--reference",    help="Override reference image path (per-call)")
    p.add_argument("--bootstrap", action="store_true", help="No reference image required (or iterate on one with --reference)")
    p.add_argument("--list-scenes", action="store_true")
    p.add_argument("--doctor", action="store_true")
    args = p.parse_args()

    if args.doctor:       return cmd_doctor()
    if args.list_scenes:  return cmd_list_scenes()

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

    return 0 if generate(scene_text, label, anchor_path, ref_path, iterate_on_reference) else 1


if __name__ == "__main__":
    sys.exit(main())
