"""
EID0L0N — built-in Codex (ChatGPT OAuth) image-gen backend.

The ONLY backend shipped as code. Everything else is delegated to the host
agent: it already has tools to call its own configured image API (MCP /
Bash+curl / local ComfyUI / etc.) and writes the result to ``output_path``.

Codex is the exception because its protocol cannot be reasonably re-derived
by an agent on its own:

    - OAuth tokens stored in ~/.codex/auth.json (managed by `codex login`)
    - JWT decoding to extract chatgpt_account_id for ChatGPT-Account-ID header
    - originator + UA must match codex_cli_rs literal strings
    - Streaming responses API with image_generation tool inside
      tool_choice: allowed_tools

Self-contained: stdlib only except for openai SDK (pinned in pyproject) and
PIL (used for the final PNG normalize step).

Public surface:

    detect() -> dict          # {available: bool, credit?: str, missing?: str}
    generate(prompt, reference_path, output_path) -> bool
"""
from __future__ import annotations

import base64
import json
import os
import random
import re
import sys
import time
from pathlib import Path

# Bearer/sk-* token shapes that may appear in OpenAI SDK exception strings
# when the SDK echoes failed-request headers. Redact before any stderr print.
_TOKEN_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),  # JWT
)


def _redact(s: str) -> str:
    for pat in _TOKEN_PATTERNS:
        s = pat.sub("[REDACTED]", s)
    return s

CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
CODEX_HOST_MODEL = "gpt-5.4"
CODEX_IMAGE_MODEL = "gpt-image-2"
CODEX_INSTRUCTIONS = (
    "You are an assistant that must fulfill image generation requests by "
    "using the image_generation tool when provided."
)

DEFAULT_ASPECT = "square"
SIZES = {
    "landscape": "1536x1024",
    "square":    "1024x1024",
    "portrait":  "1024x1536",
}

_REF_EXT_WHITELIST = {"png", "jpeg", "jpg", "webp"}

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 0.5


def _decode_jwt_payload(token: str) -> dict | None:
    """Decode JWT payload (no signature verification — we only read claims)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        return None


def _read_token() -> str | None:
    if not CODEX_AUTH_PATH.exists():
        return None
    # Defensive: refuse oversized auth.json (corrupt/malicious)
    try:
        if CODEX_AUTH_PATH.stat().st_size > 1_000_000:
            return None
    except OSError:
        return None
    try:
        data = json.loads(CODEX_AUTH_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    token = (data.get("tokens") or {}).get("access_token")
    if not isinstance(token, str) or not token.strip():
        return None
    # JWT exp check; failure to decode → reject (don't let bad tokens through)
    claims = _decode_jwt_payload(token)
    if claims is None:
        return None
    exp = claims.get("exp", 0)
    if not exp or time.time() > exp:
        return None
    return token.strip()


def _account_id(token: str) -> str | None:
    claims = _decode_jwt_payload(token)
    if claims is None:
        return None
    acct = claims.get("https://api.openai.com/auth", {}).get("chatgpt_account_id")
    return acct if isinstance(acct, str) and acct else None


def _quality() -> str:
    q = (os.environ.get("EIDOLON_IMAGE_QUALITY") or "medium").strip().lower()
    return q if q in ("low", "medium", "high") else "medium"


def detect() -> dict:
    token = _read_token()
    if token:
        return {"available": True, "credit": "free for ChatGPT Plus/Pro/Team"}
    if CODEX_AUTH_PATH.exists():
        return {"available": False, "missing": "Codex auth present but token expired — run `codex login`"}
    return {"available": False, "missing": "no ~/.codex/auth.json — run `codex login`"}


def _is_retryable(exc: Exception) -> bool:
    name = type(exc).__name__
    if name in ("APIConnectionError", "APITimeoutError", "TimeoutException", "ReadTimeout", "ConnectTimeout"):
        return True
    msg = str(exc).lower()
    return any(kw in msg for kw in ("timeout", "connection reset", "temporarily", "rate limit", "503"))


def generate(prompt: str, reference_path: Path | None, output_path: Path) -> bool:
    """Render one image via Codex and write it to ``output_path``.

    Returns True on success. Prints structured error to stderr on failure and
    returns False so the caller can decide whether to fall back."""
    try:
        from openai import OpenAI
    except ImportError:
        print("error: openai SDK not installed. Run via `uv run` or: pip install openai pillow", file=sys.stderr)
        return False

    token = _read_token()
    if not token:
        print("error: no valid Codex token. Run `codex login` and try again.", file=sys.stderr)
        return False

    headers = {
        "User-Agent": "codex_cli_rs/0.0.0 (eid0l0n)",
        "originator": "codex_cli_rs",
    }
    acct = _account_id(token)
    if acct:
        headers["ChatGPT-Account-ID"] = acct

    client = OpenAI(api_key=token, base_url=CODEX_BASE_URL, default_headers=headers)
    aspect = (os.environ.get("EIDOLON_IMAGE_ASPECT") or DEFAULT_ASPECT).strip().lower()
    size = SIZES.get(aspect, SIZES[DEFAULT_ASPECT])
    quality = _quality()

    content: list[dict] = []
    if reference_path is not None:
        ext = reference_path.suffix.lstrip(".").lower()
        if ext == "jpg":
            ext = "jpeg"
        if ext not in _REF_EXT_WHITELIST:
            print(f"error: reference image must be png/jpeg/webp, got: {ext}",
                  file=sys.stderr)
            return False
        try:
            if reference_path.stat().st_size > 20_000_000:
                print(f"error: reference image too large (>20MB): {reference_path}",
                      file=sys.stderr)
                return False
        except OSError as e:
            print(f"error: cannot stat reference image: {e}", file=sys.stderr)
            return False
        b64 = base64.b64encode(reference_path.read_bytes()).decode()
        content.append({"type": "input_image",
                        "image_url": f"data:image/{ext};base64,{b64}"})
    content.append({"type": "input_text", "text": prompt})

    print(f"  · codex / {CODEX_IMAGE_MODEL} ({quality}, {size})", file=sys.stderr)

    def _call() -> bytes | None:
        image_b64: str | None = None
        partial_b64: str | None = None  # only used if no done event arrives
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
                        partial_b64 = partial
            final = stream.get_final_response()
        for item in getattr(final, "output", None) or []:
            if getattr(item, "type", None) == "image_generation_call":
                result = getattr(item, "result", None)
                if isinstance(result, str) and result:
                    image_b64 = result
        final_b64 = image_b64 or partial_b64
        return base64.b64decode(final_b64) if final_b64 else None

    img_bytes: bytes | None = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            img_bytes = _call()
            break
        except Exception as e:
            err = _redact(f"{type(e).__name__}: {e}")
            if _is_retryable(e) and attempt < RETRY_ATTEMPTS:
                backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                backoff += random.uniform(0, backoff * 0.3)  # jitter
                print(f"  codex attempt {attempt}: {err} — retrying in {backoff:.2f}s", file=sys.stderr)
                time.sleep(backoff)
                continue
            print(f"  codex attempt {attempt}: {err}", file=sys.stderr)
            return False

    if not img_bytes or len(img_bytes) < 1000:
        print("error: codex returned no image", file=sys.stderr)
        return False

    try:
        from PIL import Image as PILImage
        from io import BytesIO
        img = PILImage.open(BytesIO(img_bytes))
        if img.mode == "RGBA":
            bg = PILImage.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
        try:
            img.save(str(tmp), "PNG")
            tmp.replace(output_path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    except ImportError:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(img_bytes)
    return True
