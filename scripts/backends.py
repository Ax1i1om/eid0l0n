"""
EID0L0N — image-gen backend registry, detection, selection, and HTTP retry.

Imports from the lower `state` module is not required (no state-file I/O here);
must never import from `generate` or `setup`. All six backends implement the
same interface:

    detect_*() -> dict   # {"available": bool, "credit": str?, "models": list, "missing": str?}
    *_generate(prompt, ref_path, slug, label, out_dir) -> Path | None

The `BACKENDS` list is the priority-ordered registry consumed by `select_backend`
and `detect_all`. Codex is first because it's free for ChatGPT subscribers
(no extra config beyond the user's existing `codex login`).
"""
from __future__ import annotations

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


# ─── constants ─────────────────────────────────────────────────────────────

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


# ─── retry framework ───────────────────────────────────────────────────────

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


# ─── shared image-save helper ──────────────────────────────────────────────

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
