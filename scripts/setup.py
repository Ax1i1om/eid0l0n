#!/usr/bin/env python3
"""
EID0L0N (skill name: `eidolon`) — setup toolkit.

6 thin commands. Everything else lives in agent context + SKILL.md prose.

    setup.py status                                    JSON state dump (incl. register lock + backends)
    setup.py detect-backends [--json]                  Available image-gen backends (auto-pick info)
    setup.py save-anchor [--text T | --from-file F] [--name NAME]
                                                       Write visual_anchor.md
    setup.py save-reference --src PATH                 Adopt image (atomic, flock-protected)
    setup.py set-api --key K [--base-url U] [--models CSV]
                                                       Write env (mode 600) — only needed for openrouter backend
    setup.py set-register-lock {--clear | --until ISO --max R}
                                                       Persist register lock for the FORCE channel
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from contextlib import contextmanager

# fcntl is POSIX-only. On Windows we degrade to no-op locking — the skill is
# designed for one agent at a time per workspace, so concurrent writers from a
# single host are extremely rare. If you need real Windows locking, install
# portalocker and patch _file_lock.
try:
    import fcntl  # type: ignore
    _HAS_FCNTL = True
except ImportError:
    fcntl = None  # type: ignore
    _HAS_FCNTL = False
from pathlib import Path

# Share the backend registry and the cwd-derived state dir with generate.py.
# State dir = <cwd>/eidolon (or $EIDOLON_HOME) — see generate._resolve_state_dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from generate import (  # type: ignore
        BACKENDS,
        CONFIG_DIR,
        LEGACY_CONFIG_DIR,
        detect_all,
        legacy_state_present,
        load_env_file as _load_gen_env,
    )
except Exception:
    BACKENDS = []
    CONFIG_DIR = Path.cwd() / "eidolon"
    LEGACY_CONFIG_DIR = Path.home() / ".config" / "eidolon"
    def detect_all() -> dict:  # type: ignore
        return {}
    def legacy_state_present() -> bool:  # type: ignore
        return False
    def _load_gen_env() -> None:  # type: ignore
        pass

ANCHOR_PATH = CONFIG_DIR / "visual_anchor.md"
ENV_PATH    = CONFIG_DIR / "env"
PREFS_PATH  = CONFIG_DIR / "preferences.json"
LOCK_PATH   = CONFIG_DIR / ".lock"

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
REF_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


@contextmanager
def _file_lock():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    fp = open(LOCK_PATH, "w")
    try:
        if _HAS_FCNTL:
            fcntl.flock(fp, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if _HAS_FCNTL:
                fcntl.flock(fp, fcntl.LOCK_UN)
        finally:
            fp.close()


def _read_text_normalized(path: Path) -> str:
    return path.read_text().replace("\r\n", "\n").replace("\r", "\n")


def find_existing_reference() -> Path | None:
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = CONFIG_DIR / f"reference.{ext}"
        if p.exists():
            return p
    return None


def env_has_key() -> bool:
    if not ENV_PATH.exists():
        return False
    for line in _read_text_normalized(ENV_PATH).splitlines():
        if line.strip().startswith("IMAGE_API_KEY="):
            return bool(line.split("=", 1)[1].strip())
    return False


def load_prefs() -> dict:
    if not PREFS_PATH.exists():
        return {}
    try:
        return json.loads(_read_text_normalized(PREFS_PATH))
    except json.JSONDecodeError:
        return {}


def write_prefs(prefs: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with _file_lock():
        PREFS_PATH.write_text(json.dumps(prefs, indent=2))
        os.chmod(PREFS_PATH, 0o600)


# ─── status ────────────────────────────────────────────────────────────────

def cmd_status(args) -> int:
    _load_gen_env()
    prefs = load_prefs()
    detections = detect_all()
    available = [name for name, info in detections.items() if info.get("available")]
    forced = (os.environ.get("EIDOLON_IMAGE_BACKEND") or "").strip().lower()
    auto = next((name for name, _d, det, _g in BACKENDS if det().get("available")), "")
    try:
        cwd = str(Path.cwd())
    except (FileNotFoundError, OSError):
        cwd = ""
    payload = {
        "anchor_exists":         ANCHOR_PATH.exists(),
        "reference_exists":      find_existing_reference() is not None,
        "api_key_set":           bool(os.environ.get("IMAGE_API_KEY") or env_has_key()),
        "anchor_path":           str(ANCHOR_PATH) if ANCHOR_PATH.exists() else "",
        "reference_path":        str(find_existing_reference() or ""),
        "register_locked_until": prefs.get("locked_until", ""),
        "register_max":          prefs.get("max_register", ""),
        "backend_available":     bool(available),
        "backends_available":    available,
        "backend_selected":      forced or auto,
        "backend_forced":        bool(forced),
        "state_dir":             str(CONFIG_DIR),
        "workspace_cwd":         cwd,
        "legacy_state_present":  legacy_state_present(),
        "legacy_config_dir":     str(LEGACY_CONFIG_DIR) if legacy_state_present() else "",
    }
    print(json.dumps(payload, indent=2))
    return 0


# ─── detect-backends ───────────────────────────────────────────────────────

def cmd_detect_backends(args) -> int:
    _load_gen_env()
    detections = detect_all()
    forced = (os.environ.get("EIDOLON_IMAGE_BACKEND") or "").strip().lower()
    auto = next((name for name, _d, det, _g in BACKENDS if det().get("available")), "")
    if args.json:
        print(json.dumps({
            "selected":  forced or auto,
            "forced":    bool(forced),
            "available": [name for name, info in detections.items() if info.get("available")],
            "details":   detections,
        }, indent=2))
        return 0
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
    else:
        print("\nauto-selected: (none — configure one)")
    return 0


# ─── save-anchor ───────────────────────────────────────────────────────────

def cmd_save_anchor(args) -> int:
    if args.text:
        text = args.text
    elif args.from_file:
        text = _read_text_normalized(Path(args.from_file).expanduser().resolve())
    else:
        text = sys.stdin.read()
    text = text.strip()
    if not text:
        sys.exit("error: no text. Use --text, --from-file <path>, or pipe via stdin.")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    name = (args.name or "").strip()
    heading = f"# Visual Anchor — {name}" if name else "# Visual Anchor"
    ref = find_existing_reference()
    header = f"reference: {ref}\n\n" if ref else ""
    body = (
        f"{header}{heading}\n\n"
        f"_Authored by the agent (extracted from SOUL.md context). Edit freely; not auto-overwritten._\n\n"
        f"{text}\n"
    )
    with _file_lock():
        ANCHOR_PATH.write_text(body)
    print(f"✓ wrote {ANCHOR_PATH}")
    print(ANCHOR_PATH)
    return 0


# ─── save-reference ────────────────────────────────────────────────────────

def cmd_save_reference(args) -> int:
    src = Path(args.src).expanduser().resolve()
    if not src.exists():
        sys.exit(f"error: not found: {src}")
    if src.suffix.lower() not in REF_EXTS:
        sys.exit(f"error: must be one of {', '.join(sorted(REF_EXTS))}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    dst = CONFIG_DIR / f"reference.{ext}"
    with _file_lock():
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        shutil.copyfile(src, tmp)
        os.chmod(tmp, 0o644)
        tmp.replace(dst)
        for other_ext in ("jpg", "jpeg", "png", "webp"):
            other = CONFIG_DIR / f"reference.{other_ext}"
            if other != dst and other.exists():
                try: other.unlink()
                except OSError: pass
        _patch_anchor_reference(dst)
    print(f"✓ saved {dst}")
    print(dst)
    return 0


def _patch_anchor_reference(ref_path: Path) -> None:
    if not ANCHOR_PATH.exists():
        return
    text = _read_text_normalized(ANCHOR_PATH)
    if re.search(r"^reference:\s*.+$", text, flags=re.MULTILINE):
        text = re.sub(r"^reference:\s*.+$", f"reference: {ref_path}", text, count=1, flags=re.MULTILINE)
    else:
        text = f"reference: {ref_path}\n\n" + text
    ANCHOR_PATH.write_text(text)


# ─── set-api ───────────────────────────────────────────────────────────────

def cmd_set_api(args) -> int:
    if not args.key:
        sys.exit("error: --key required")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# eidolon env — mode 600. Do not commit. Do not let an agent collect the key from chat.",
        f"IMAGE_API_KEY={args.key}",
        f"IMAGE_API_BASE_URL={args.base_url or DEFAULT_BASE_URL}",
    ]
    if args.models:
        lines.append(f"IMAGE_API_MODELS={args.models}")
    with _file_lock():
        ENV_PATH.write_text("\n".join(lines) + "\n")
        os.chmod(ENV_PATH, 0o600)
    print(f"✓ wrote {ENV_PATH} (mode 600)")
    print("Reminder: run this command IN YOUR OWN SHELL. Never have an agent collect the key from chat and run this for you.")
    return 0


# ─── set-register-lock ─────────────────────────────────────────────────────

def cmd_set_register_lock(args) -> int:
    prefs = load_prefs()
    if args.clear:
        prefs.pop("locked_until", None)
        prefs.pop("max_register", None)
        write_prefs(prefs)
        print("✓ register lock cleared")
        return 0
    if not args.until or not args.max:
        sys.exit("error: provide both --until <ISO-8601> and --max <register>, or use --clear")
    prefs["locked_until"] = args.until
    prefs["max_register"] = args.max
    write_prefs(prefs)
    print(f"✓ register lock set: until={args.until} max={args.max}")
    return 0


# ─── migrate-from-legacy ───────────────────────────────────────────────────

def cmd_migrate_from_legacy(args) -> int:
    """Copy persona state from the legacy ~/.config/eidolon/ tree (flat root or
    any subdir) into the current state dir (<cwd>/eidolon/). If the legacy
    layout has multiple subdirs, ``--from <name>`` selects which one (defaults
    to the flat root if it has visual_anchor.md, else fails)."""
    legacy = LEGACY_CONFIG_DIR
    target = CONFIG_DIR
    if target.resolve() == legacy.resolve():
        sys.exit("error: target equals legacy root — nothing to migrate.")
    if not legacy.exists():
        sys.exit(f"error: no legacy state at {legacy}")

    # Pick source: --from <subdir> or root if it has anchor.
    if args.from_:
        source = legacy / args.from_
        if not source.exists() or not source.is_dir():
            sys.exit(f"error: legacy subdir not found: {source}")
    elif (legacy / "visual_anchor.md").exists():
        source = legacy
    else:
        # Auto-pick if exactly one subdir has an anchor.
        candidates = [c for c in legacy.iterdir() if c.is_dir() and (c / "visual_anchor.md").exists()]
        if len(candidates) == 1:
            source = candidates[0]
        elif not candidates:
            sys.exit(f"error: no migratable state under {legacy}")
        else:
            names = ", ".join(c.name for c in candidates)
            sys.exit(f"error: multiple legacy subdirs with anchors ({names}); use --from <name>")

    moved: list = []
    skipped: list = []
    target.mkdir(parents=True, exist_ok=True)
    file_names = ["visual_anchor.md", "preferences.json", "env"] + [f"reference.{e}" for e in ("jpg","jpeg","png","webp")]
    lock_fp = open(target / ".lock", "w")
    try:
        if _HAS_FCNTL:
            fcntl.flock(lock_fp, fcntl.LOCK_EX)
        for name in file_names:
            src = source / name
            if not src.exists() or src.is_dir():
                continue
            dst = target / name
            if dst.exists() and not args.force:
                skipped.append(f"{name} (target exists; pass --force to overwrite)")
                continue
            tmp = dst.with_suffix(dst.suffix + ".tmp")
            shutil.copyfile(src, tmp)
            try:
                mode = src.stat().st_mode & 0o777
            except OSError:
                mode = 0o600 if name in ("env", "preferences.json") else 0o644
            os.chmod(tmp, mode)
            tmp.replace(dst)
            moved.append(name)
            if args.purge:
                try: src.unlink()
                except OSError: pass
        # Repoint the anchor's `reference:` header to the new path.
        for ext in ("jpg","jpeg","png","webp"):
            ref = target / f"reference.{ext}"
            if ref.exists():
                anchor = target / "visual_anchor.md"
                if anchor.exists():
                    text = _read_text_normalized(anchor)
                    if re.search(r"^reference:\s*.+$", text, flags=re.MULTILINE):
                        text = re.sub(r"^reference:\s*.+$", f"reference: {ref}", text, count=1, flags=re.MULTILINE)
                    else:
                        text = f"reference: {ref}\n\n" + text
                    anchor.write_text(text)
                break
    finally:
        if _HAS_FCNTL:
            fcntl.flock(lock_fp, fcntl.LOCK_UN)
        lock_fp.close()

    print(json.dumps({
        "from":   str(source),
        "to":     str(target),
        "copied":  moved,
        "skipped": skipped,
        "purged_legacy": bool(args.purge),
    }, indent=2))
    return 0


# ─── main ──────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(prog="eidolon-setup")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("status")

    a = sub.add_parser("detect-backends")
    a.add_argument("--json", action="store_true", help="machine-readable output for the agent")

    a = sub.add_parser("save-anchor")
    a.add_argument("--text")
    a.add_argument("--from-file", dest="from_file")
    a.add_argument("--name")

    a = sub.add_parser("save-reference")
    a.add_argument("--src", required=True)

    a = sub.add_parser("set-api")
    a.add_argument("--key", required=True)
    a.add_argument("--base-url")
    a.add_argument("--models")

    a = sub.add_parser("set-register-lock")
    a.add_argument("--until", help="ISO-8601 timestamp when lock expires")
    a.add_argument("--max", help="Max register: warm | tender | intimate")
    a.add_argument("--clear", action="store_true")

    a = sub.add_parser("migrate-from-legacy",
                       help="copy ~/.config/eidolon/* into <cwd>/eidolon/")
    a.add_argument("--from", dest="from_", default=None,
                   help="legacy subdir to migrate (e.g. --from axiiiom). Auto-picks if only one exists, or root if it has visual_anchor.md.")
    a.add_argument("--force", action="store_true",
                   help="overwrite target files if they already exist")
    a.add_argument("--purge", action="store_true",
                   help="delete legacy files after a successful copy")

    args = p.parse_args()
    dispatch = {
        "status":               cmd_status,
        "detect-backends":      cmd_detect_backends,
        "save-anchor":          cmd_save_anchor,
        "save-reference":       cmd_save_reference,
        "set-api":              cmd_set_api,
        "set-register-lock":    cmd_set_register_lock,
        "migrate-from-legacy":  cmd_migrate_from_legacy,
    }
    if args.cmd in dispatch:
        return dispatch[args.cmd](args)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
