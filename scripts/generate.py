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
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image as PILImage
    _PIL_OK = True
except ImportError:
    PILImage = None  # type: ignore
    _PIL_OK = False

SKILL_DIR    = Path(__file__).resolve().parent.parent
HOME         = Path.home()
LEGACY_CONFIG_DIR = HOME / ".config" / "eidolon"  # pre-cwd-design path; flagged for migration


def _resolve_state_dir() -> Path:
    """State lives at ``<workspace>/eidolon/`` where ``<workspace>`` is the
    current working directory.

    OpenClaw and Hermes both document that ``cwd == active workspace`` when a
    skill is invoked (OpenClaw: "the only working directory used for file
    tools and for workspace context"; Hermes: writes "relative to the active
    workspace/backend working directory"). We trust that contract.

    ``$EIDOLON_HOME`` overrides for dev/test use. Running from inside the
    skill source repo is refused — point the user at ``$EIDOLON_HOME`` so
    state cannot pollute the source tree.
    """
    override = os.environ.get("EIDOLON_HOME")
    if override:
        return Path(override).expanduser().resolve()
    try:
        cwd = Path(os.getcwd())
    except (FileNotFoundError, OSError):
        sys.exit("error: cwd is gone. Set EIDOLON_HOME=<path> to a writable dir.")
    # Refuse to write inside the skill's own source repo.
    if (cwd / ".git").exists() and (cwd / "SKILL.md").exists() and (cwd / "scripts").is_dir():
        sys.exit(
            "error: cwd looks like the eidolon source repo. Refusing to write state here.\n"
            "Run from your host workspace, or set EIDOLON_HOME=<path>."
        )
    return cwd / "eidolon"


CONFIG_DIR   = _resolve_state_dir()
ANCHOR_PATH  = CONFIG_DIR / "visual_anchor.md"
ENV_PATH     = CONFIG_DIR / "env"
PREFS_PATH   = CONFIG_DIR / "preferences.json"


def legacy_state_present() -> bool:
    """True iff persona files sit in the legacy ``~/.config/eidolon/`` tree
    (flat root or any subdir). Independent of the current state dir."""
    if not LEGACY_CONFIG_DIR.exists():
        return False
    if (LEGACY_CONFIG_DIR / "visual_anchor.md").exists():
        return True
    for child in LEGACY_CONFIG_DIR.iterdir():
        if child.is_dir() and (child / "visual_anchor.md").exists():
            return True
    return False

# Codex CLI auth (shared with the user's existing `codex login`)
CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
CODEX_HOST_MODEL = "gpt-5.4"  # the chat model that hosts the image_generation tool call
CODEX_IMAGE_MODEL = "gpt-image-2"
CODEX_INSTRUCTIONS = (
    "You are an assistant that must fulfill image generation requests by "
    "using the image_generation tool when provided."
)

# OpenRouter (legacy) defaults
DEFAULT_OR_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OR_MODELS = [
    "google/gemini-2.5-flash-image-preview",
    "google/gemini-2.5-flash",
]

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 0.5
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

DEFAULT_ASPECT = "square"
SIZES = {
    "landscape": "1536x1024",
    "square":    "1024x1024",
    "portrait":  "1024x1536",
}

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


# ─── shared helpers ────────────────────────────────────────────────────────

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


def resolve_anchor_path(cli: str | None) -> Path:
    candidates = [
        cli,
        os.environ.get("EIDOLON_VISUAL_ANCHOR"),
        str(ANCHOR_PATH),
        str(SKILL_DIR / "assets" / "persona.example.md"),
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
    env = os.environ.get("EIDOLON_OUTPUT_DIR")
    if env:
        return Path(env).expanduser().resolve()
    home = Path.home()
    for host_dir in (home / ".openclaw" / "workspace", home / ".hermes" / "workspace"):
        if host_dir.exists():
            return host_dir / "eidolon"
    return home / "Pictures" / "eidolon"


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


def _save_png(img_bytes: bytes, slug: str, label: str, out_dir: Path) -> Path:
    if not _PIL_OK:
        sys.exit("error: pillow not installed. Run via `uv run` or: pip install pillow openai")
    img = PILImage.open(BytesIO(img_bytes))
    if img.mode == "RGBA":
        bg = PILImage.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", label.replace(" ", "_"))[:30] or "shot"
    out = out_dir / f"{slug}-{safe}-{ts}.png"
    img.save(str(out), "PNG")
    return out


def _is_retryable(exc: Exception) -> bool:
    name = type(exc).__name__
    if name in ("APIConnectionError", "APITimeoutError", "TimeoutException", "ReadTimeout", "ConnectTimeout"):
        return True
    status = getattr(exc, "status_code", None)
    if status in RETRYABLE_STATUS:
        return True
    if isinstance(exc, urllib.error.HTTPError) and exc.code in RETRYABLE_STATUS:
        return True
    msg = str(exc).lower()
    return any(kw in msg for kw in ("timeout", "connection reset", "temporarily", "rate limit", "503"))


def _retry(fn, label: str):
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return fn()
        except Exception as e:
            if _is_retryable(e) and attempt < RETRY_ATTEMPTS:
                backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                print(f"    {label} attempt {attempt}: {type(e).__name__}: {e} — retrying in {backoff}s", file=sys.stderr)
                time.sleep(backoff)
                continue
            print(f"    {label} attempt {attempt}: {type(e).__name__}: {e}", file=sys.stderr)
            return None
    return None


# ─── codex (ChatGPT/Codex OAuth — no API key) ──────────────────────────────

def _codex_read_token() -> str | None:
    """Return a non-expired Codex access_token from ~/.codex/auth.json, or None."""
    if not CODEX_AUTH_PATH.exists():
        return None
    try:
        data = json.loads(CODEX_AUTH_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    tokens = data.get("tokens") or {}
    token = tokens.get("access_token")
    if not isinstance(token, str) or not token.strip():
        return None
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            exp = claims.get("exp", 0)
            if exp and time.time() > exp:
                return None
    except Exception:
        pass
    return token.strip()


def _codex_cloudflare_headers(token: str) -> dict:
    """Codex/CF requires originator + UA matching codex_cli_rs and ChatGPT-Account-ID from JWT."""
    headers = {
        "User-Agent": "codex_cli_rs/0.0.0 (eid0l0n)",
        "originator": "codex_cli_rs",
    }
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            acct = claims.get("https://api.openai.com/auth", {}).get("chatgpt_account_id")
            if isinstance(acct, str) and acct:
                headers["ChatGPT-Account-ID"] = acct
    except Exception:
        pass
    return headers


def _codex_quality() -> str:
    q = (os.environ.get("EIDOLON_IMAGE_QUALITY") or "medium").strip().lower()
    return q if q in ("low", "medium", "high") else "medium"


def codex_detect() -> dict:
    token = _codex_read_token()
    if token:
        return {"available": True, "credit": "free for ChatGPT Plus/Pro/Team", "models": [CODEX_IMAGE_MODEL]}
    if CODEX_AUTH_PATH.exists():
        return {"available": False, "missing": "Codex auth present but token expired — run `codex login`"}
    return {"available": False, "missing": "no ~/.codex/auth.json — run `codex login`"}


def codex_generate(prompt: str, ref_path: Path | None, slug: str, label: str, out_dir: Path) -> Path | None:
    from openai import OpenAI

    token = _codex_read_token()
    if not token:
        print("error: codex backend selected but no valid Codex token found.", file=sys.stderr)
        return None

    client = OpenAI(api_key=token, base_url=CODEX_BASE_URL, default_headers=_codex_cloudflare_headers(token))
    aspect = (os.environ.get("EIDOLON_IMAGE_ASPECT") or DEFAULT_ASPECT).strip().lower()
    size = SIZES.get(aspect, SIZES[DEFAULT_ASPECT])
    quality = _codex_quality()

    content: list[dict] = []
    if ref_path is not None:
        ext = ref_path.suffix.lstrip(".").lower() or "jpeg"
        if ext == "jpg":
            ext = "jpeg"
        b64 = base64.b64encode(ref_path.read_bytes()).decode()
        content.append({"type": "input_image", "image_url": f"data:image/{ext};base64,{b64}"})
    content.append({"type": "input_text", "text": prompt})

    print(f"  · codex / {CODEX_IMAGE_MODEL} ({quality}, {size})", file=sys.stderr)

    def _call() -> bytes | None:
        image_b64: str | None = None
        with client.responses.stream(
            model=CODEX_HOST_MODEL,
            store=False,
            instructions=CODEX_INSTRUCTIONS,
            input=[{"type": "message", "role": "user", "content": content}],
            tools=[{
                "type": "image_generation",
                "model": CODEX_IMAGE_MODEL,
                "size": size,
                "quality": quality,
                "output_format": "png",
                "background": "opaque",
                "partial_images": 1,
            }],
            tool_choice={
                "type": "allowed_tools",
                "mode": "required",
                "tools": [{"type": "image_generation"}],
            },
        ) as stream:
            for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_item.done":
                    item = getattr(event, "item", None)
                    if getattr(item, "type", None) == "image_generation_call":
                        result = getattr(item, "result", None)
                        if isinstance(result, str) and result:
                            image_b64 = result
                elif event_type == "response.image_generation_call.partial_image":
                    partial = getattr(event, "partial_image_b64", None)
                    if isinstance(partial, str) and partial:
                        image_b64 = partial
            final = stream.get_final_response()
        for item in getattr(final, "output", None) or []:
            if getattr(item, "type", None) == "image_generation_call":
                result = getattr(item, "result", None)
                if isinstance(result, str) and result:
                    image_b64 = result
        return base64.b64decode(image_b64) if image_b64 else None

    img_bytes = _retry(_call, "codex")
    if not img_bytes or len(img_bytes) < 1000:
        print("error: codex returned no image", file=sys.stderr)
        return None
    return _save_png(img_bytes, slug, label, out_dir)


# ─── openai (Images API, direct API key) ───────────────────────────────────

def openai_detect() -> dict:
    if (os.environ.get("OPENAI_API_KEY") or "").strip():
        return {"available": True, "credit": "billed per image", "models": [os.environ.get("OPENAI_IMAGE_MODEL") or "gpt-image-2"]}
    return {"available": False, "missing": "OPENAI_API_KEY env var"}


def openai_generate(prompt: str, ref_path: Path | None, slug: str, label: str, out_dir: Path) -> Path | None:
    from openai import OpenAI

    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        print("error: OPENAI_API_KEY not set", file=sys.stderr)
        return None
    model = (os.environ.get("OPENAI_IMAGE_MODEL") or "gpt-image-2").strip() or "gpt-image-2"
    client = OpenAI(api_key=key)
    print(f"  · openai-images / {model}", file=sys.stderr)

    def _call() -> bytes | None:
        if ref_path is not None:
            with open(ref_path, "rb") as fh:
                result = client.images.edit(model=model, image=[fh], prompt=prompt)
        else:
            result = client.images.generate(model=model, prompt=prompt)
        data = getattr(result, "data", None) or []
        for item in data:
            b64 = item.get("b64_json") if isinstance(item, dict) else getattr(item, "b64_json", None)
            if b64:
                return base64.b64decode(b64)
        return None

    img_bytes = _retry(_call, "openai")
    if not img_bytes or len(img_bytes) < 1000:
        print("error: openai returned no image", file=sys.stderr)
        return None
    return _save_png(img_bytes, slug, label, out_dir)


# ─── gemini (Google AI Studio) ─────────────────────────────────────────────

def _gemini_key() -> str:
    return (os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GOOGLE_AI_STUDIO_KEY")
            or "").strip()


def gemini_detect() -> dict:
    if _gemini_key():
        return {"available": True, "credit": "free tier available", "models": ["gemini-2.5-flash-image-preview"]}
    return {"available": False, "missing": "GEMINI_API_KEY (or GOOGLE_API_KEY)"}


def gemini_generate(prompt: str, ref_path: Path | None, slug: str, label: str, out_dir: Path) -> Path | None:
    key = _gemini_key()
    if not key:
        print("error: GEMINI_API_KEY not set", file=sys.stderr)
        return None
    model = (os.environ.get("EIDOLON_GEMINI_MODEL") or "gemini-2.5-flash-image-preview").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    parts: list[dict] = []
    if ref_path is not None:
        ext = ref_path.suffix.lstrip(".").lower() or "jpeg"
        if ext == "jpg":
            ext = "jpeg"
        b64 = base64.b64encode(ref_path.read_bytes()).decode()
        parts.append({"inlineData": {"mimeType": f"image/{ext}", "data": b64}})
    parts.append({"text": prompt})
    body = json.dumps({
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }).encode()

    print(f"  · gemini / {model}", file=sys.stderr)

    def _call() -> bytes | None:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
        return None

    img_bytes = _retry(_call, "gemini")
    if not img_bytes or len(img_bytes) < 1000:
        print("error: gemini returned no image", file=sys.stderr)
        return None
    return _save_png(img_bytes, slug, label, out_dir)


# ─── fal.ai ────────────────────────────────────────────────────────────────

def _fal_key() -> str:
    return (os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY") or "").strip()


def fal_detect() -> dict:
    if _fal_key():
        return {"available": True, "credit": "billed per image", "models": ["fal-ai/nano-banana", "fal-ai/flux/dev"]}
    return {"available": False, "missing": "FAL_KEY env var"}


def _fal_default_model(has_reference: bool) -> str:
    explicit = (os.environ.get("EIDOLON_FAL_MODEL") or "").strip()
    if explicit:
        return explicit
    return "fal-ai/nano-banana/edit" if has_reference else "fal-ai/nano-banana"


def fal_generate(prompt: str, ref_path: Path | None, slug: str, label: str, out_dir: Path) -> Path | None:
    key = _fal_key()
    if not key:
        print("error: FAL_KEY not set", file=sys.stderr)
        return None
    model = _fal_default_model(ref_path is not None)
    submit_url = f"https://queue.fal.run/{model}"
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}

    payload: dict = {"prompt": prompt, "num_images": 1}
    if ref_path is not None:
        ext = ref_path.suffix.lstrip(".").lower() or "jpeg"
        if ext == "jpg":
            ext = "jpeg"
        b64 = base64.b64encode(ref_path.read_bytes()).decode()
        payload["image_urls"] = [f"data:image/{ext};base64,{b64}"]

    print(f"  · fal / {model}", file=sys.stderr)

    def _submit_and_poll() -> bytes | None:
        req = urllib.request.Request(submit_url, data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            queue = json.loads(resp.read())
        status_url = queue.get("status_url")
        response_url = queue.get("response_url")
        if not status_url or not response_url:
            return None
        for _ in range(60):
            time.sleep(5)
            sreq = urllib.request.Request(status_url, headers={"Authorization": f"Key {key}"})
            with urllib.request.urlopen(sreq, timeout=30) as sresp:
                sdata = json.loads(sresp.read())
            status = sdata.get("status")
            if status == "COMPLETED":
                break
            if status in ("FAILED", "CANCELED"):
                raise RuntimeError(f"fal status: {status}")
        rreq = urllib.request.Request(response_url, headers={"Authorization": f"Key {key}"})
        with urllib.request.urlopen(rreq, timeout=60) as rresp:
            result = json.loads(rresp.read())
        images = result.get("images") or []
        if not images:
            return None
        url = images[0].get("url")
        if not url:
            return None
        with urllib.request.urlopen(url, timeout=60) as ir:
            return ir.read()

    img_bytes = _retry(_submit_and_poll, "fal")
    if not img_bytes or len(img_bytes) < 1000:
        print("error: fal returned no image", file=sys.stderr)
        return None
    return _save_png(img_bytes, slug, label, out_dir)


# ─── Replicate ─────────────────────────────────────────────────────────────

def _replicate_token() -> str:
    return (os.environ.get("REPLICATE_API_TOKEN") or "").strip()


def replicate_detect() -> dict:
    if _replicate_token():
        return {"available": True, "credit": "billed per image", "models": ["black-forest-labs/flux-kontext-pro", "black-forest-labs/flux-1.1-pro"]}
    return {"available": False, "missing": "REPLICATE_API_TOKEN env var"}


def _replicate_default_model(has_reference: bool) -> str:
    explicit = (os.environ.get("EIDOLON_REPLICATE_MODEL") or "").strip()
    if explicit:
        return explicit
    return "black-forest-labs/flux-kontext-pro" if has_reference else "black-forest-labs/flux-1.1-pro"


def replicate_generate(prompt: str, ref_path: Path | None, slug: str, label: str, out_dir: Path) -> Path | None:
    token = _replicate_token()
    if not token:
        print("error: REPLICATE_API_TOKEN not set", file=sys.stderr)
        return None
    model = _replicate_default_model(ref_path is not None)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Prefer": "wait=60"}

    inp: dict = {"prompt": prompt, "output_format": "png"}
    if ref_path is not None:
        ext = ref_path.suffix.lstrip(".").lower() or "jpeg"
        if ext == "jpg":
            ext = "jpeg"
        b64 = base64.b64encode(ref_path.read_bytes()).decode()
        inp["input_image"] = f"data:image/{ext};base64,{b64}"

    payload = json.dumps({"input": inp}).encode()
    submit_url = f"https://api.replicate.com/v1/models/{model}/predictions"
    print(f"  · replicate / {model}", file=sys.stderr)

    def _submit_and_poll() -> bytes | None:
        req = urllib.request.Request(submit_url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            pred = json.loads(resp.read())
        for _ in range(60):
            status = pred.get("status")
            if status == "succeeded":
                break
            if status in ("failed", "canceled"):
                raise RuntimeError(f"replicate status: {status}: {pred.get('error', '')}")
            time.sleep(3)
            poll_url = pred.get("urls", {}).get("get")
            if not poll_url:
                return None
            preq = urllib.request.Request(poll_url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(preq, timeout=30) as presp:
                pred = json.loads(presp.read())
        output = pred.get("output")
        url = output[0] if isinstance(output, list) else output
        if not isinstance(url, str):
            return None
        with urllib.request.urlopen(url, timeout=60) as ir:
            return ir.read()

    img_bytes = _retry(_submit_and_poll, "replicate")
    if not img_bytes or len(img_bytes) < 1000:
        print("error: replicate returned no image", file=sys.stderr)
        return None
    return _save_png(img_bytes, slug, label, out_dir)


# ─── OpenRouter (legacy default) ───────────────────────────────────────────

def _openrouter_key() -> str:
    return (os.environ.get("IMAGE_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or "").strip()


def openrouter_detect() -> dict:
    key = _openrouter_key()
    if key:
        models_env = (os.environ.get("IMAGE_API_MODELS") or "").strip()
        models = [m.strip() for m in models_env.split(",") if m.strip()] if models_env else list(DEFAULT_OR_MODELS)
        return {"available": True, "credit": "billed per token", "models": models}
    return {"available": False, "missing": "IMAGE_API_KEY (or OPENROUTER_API_KEY)"}


def _extract_or_image(data: dict) -> bytes | None:
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


def openrouter_generate(prompt: str, ref_path: Path | None, slug: str, label: str, out_dir: Path) -> Path | None:
    from openai import OpenAI

    key = _openrouter_key()
    if not key:
        print("error: IMAGE_API_KEY (or OPENROUTER_API_KEY) not set", file=sys.stderr)
        return None
    base = (os.environ.get("IMAGE_API_BASE_URL") or DEFAULT_OR_BASE_URL).strip()
    models_env = (os.environ.get("IMAGE_API_MODELS") or "").strip()
    models = [m.strip() for m in models_env.split(",") if m.strip()] if models_env else list(DEFAULT_OR_MODELS)

    content: list[dict] = []
    if ref_path is not None:
        ext = ref_path.suffix.lstrip(".").lower() or "jpeg"
        if ext == "jpg":
            ext = "jpeg"
        b64 = base64.b64encode(ref_path.read_bytes()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}})
    content.append({"type": "text", "text": prompt})

    client = OpenAI(base_url=base, api_key=key)

    for model in models:
        print(f"  · openrouter / {model}", file=sys.stderr)

        def _call(_m=model) -> bytes | None:
            resp = client.chat.completions.with_raw_response.create(
                model=_m,
                messages=[{"role": "user", "content": content}],
                max_tokens=8192,
            )
            data = json.loads(resp.content)
            return _extract_or_image(data)

        img_bytes = _retry(_call, f"openrouter[{model}]")
        if img_bytes and len(img_bytes) >= 1000:
            return _save_png(img_bytes, slug, label, out_dir)
    print("error: all openrouter models exhausted", file=sys.stderr)
    return None


# ─── backend registry & selection ──────────────────────────────────────────

# Priority order for auto-pick. Codex first because it's free for ChatGPT subscribers
# (no extra config needed beyond the user's existing `codex login`).
BACKENDS = [
    ("codex",      "Codex / ChatGPT OAuth (no API key)",     codex_detect,      codex_generate),
    ("gemini",     "Google AI Studio (Gemini)",              gemini_detect,     gemini_generate),
    ("openai",     "OpenAI Images API (gpt-image-2)",        openai_detect,     openai_generate),
    ("fal",        "fal.ai",                                 fal_detect,        fal_generate),
    ("replicate",  "Replicate",                              replicate_detect,  replicate_generate),
    ("openrouter", "OpenRouter (legacy default)",            openrouter_detect, openrouter_generate),
]
BACKEND_BY_NAME = {name: (display, detect, gen) for name, display, detect, gen in BACKENDS}


def detect_all() -> dict:
    return {name: detect() for name, _display, detect, _gen in BACKENDS}


def select_backend(explicit: str | None) -> str:
    """Pick a backend: explicit > EIDOLON_IMAGE_BACKEND env > first auto-detected."""
    candidate = (explicit or os.environ.get("EIDOLON_IMAGE_BACKEND") or "").strip().lower()
    if candidate:
        if candidate not in BACKEND_BY_NAME:
            sys.exit(f"error: unknown backend '{candidate}'. Available: {', '.join(BACKEND_BY_NAME)}")
        return candidate
    for name, _display, detect, _gen in BACKENDS:
        if detect().get("available"):
            return name
    sys.exit(
        "error: no image-gen backend available. Configure one of:\n"
        "  - codex:      run `codex login` (free for ChatGPT Plus/Pro/Team)\n"
        "  - gemini:     export GEMINI_API_KEY=...\n"
        "  - openai:     export OPENAI_API_KEY=...\n"
        "  - fal:        export FAL_KEY=...\n"
        "  - replicate:  export REPLICATE_API_TOKEN=...\n"
        "  - openrouter: setup.py set-api --key <KEY>"
    )


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
