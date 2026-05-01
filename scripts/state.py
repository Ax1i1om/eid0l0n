"""
EID0L0N — pure state/path/persistence helpers.

The lowest layer of the script package: paths, env-file loading,
anchor/reference resolution, preferences, and a cross-platform file lock.
No backends, no API calls, no CLI. Imported by both `backends` and the
two CLI entry points (`generate`, `setup`).

State + output directory contract — see docs/HOST-COMPATIBILITY.md:

    cwd                | <cwd>/eidolon/   (cwd resolved per host)
    EIDOLON_HOME       | overrides cwd resolution for state (always wins)
    EIDOLON_OUTPUT_DIR | overrides where rendered images land

Output and state share the same dir by default so whichever host invokes
the skill is also where the PNGs land. Running from inside the skill
source repo is refused; agents must point EIDOLON_HOME at a writable
workspace.
"""
from __future__ import annotations

import json
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

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


SKILL_DIR = Path(__file__).resolve().parent.parent
HOME = Path.home()
LEGACY_CONFIG_DIR = HOME / ".config" / "eidolon"  # pre-cwd-design path; flagged for migration


def _resolve_state_dir() -> Path:
    """State lives at ``<cwd>/eidolon/`` where ``<cwd>`` is the current working
    directory the script was invoked from. cwd resolution differs per host:

    OpenClaw (any mode):
        cwd = ~/.openclaw/workspace/ (or ~/.openclaw/workspace-<profile>/) per
        docs.openclaw.ai/concepts/agent-workspace: "The workspace is the only
        working directory used for file tools and for workspace context."

    Hermes CLI:
        cwd = pwd (where the user invoked the command).

    Hermes Gateway (Slack / Discord / Telegram via hermes-gateway):
        cwd = ~ by default. Set MESSAGING_CWD=/path/to/workspace to redirect.

    Hermes Container / remote:
        cwd = container's home dir.

    EIDOLON_HOME=/path overrides cwd resolution entirely (always wins; dev/test
    escape hatch). See docs/HOST-COMPATIBILITY.md for spec citations.

    Running from inside the skill source repo is refused — point the user at
    EIDOLON_HOME=<path> so state cannot pollute the source tree.
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


CONFIG_DIR = _resolve_state_dir()
ANCHOR_PATH = CONFIG_DIR / "visual_anchor.md"
ENV_PATH = CONFIG_DIR / "env"
PREFS_PATH = CONFIG_DIR / "preferences.json"
LOCK_PATH = CONFIG_DIR / ".lock"


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


# ─── text + env ────────────────────────────────────────────────────────────

def _read_text_normalized(path: Path) -> str:
    return path.read_text().replace("\r\n", "\n").replace("\r", "\n")


def load_env_file() -> None:
    """Load ``<cwd>/eidolon/env`` into os.environ if present.

    Optional convenience for users who want to scope arbitrary env vars (e.g.,
    keys their image-gen tool reads) to a workspace. eid0l0n itself does not
    require any env file to be present.
    """
    if not ENV_PATH.exists():
        return
    for line in _read_text_normalized(ENV_PATH).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'").strip('"'))


# ─── anchor + reference + output ───────────────────────────────────────────

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


def find_existing_reference() -> Path | None:
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = CONFIG_DIR / f"reference.{ext}"
        if p.exists():
            return p
    return None


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
    """Output goes alongside state — same workspace as _resolve_state_dir().

    Whichever host invokes the skill (OpenClaw, Hermes CLI, Hermes Gateway,
    container, …) defines cwd; state and output both live at <cwd>/eidolon/.
    EIDOLON_OUTPUT_DIR overrides for advanced/test use (e.g., point PNGs at a
    separate disk while state stays in the workspace).

    Earlier versions probed hardcoded ``~/.openclaw/workspace`` then
    ``~/.hermes/workspace`` and returned the first that existed. That drifted
    from the cwd-based host model in _resolve_state_dir() and routed Hermes
    output into ``.openclaw`` whenever both dirs existed on disk.
    """
    env = os.environ.get("EIDOLON_OUTPUT_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return _resolve_state_dir()


# ─── prefs + lock ──────────────────────────────────────────────────────────

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


def atomic_write_text(path: Path, text: str, mode: int = 0o644) -> None:
    """Atomic text write: tmp → chmod → replace.

    SKILL.md claims "atomic writes" for anchor / preferences / reference;
    this helper is the implementation. A crash mid-write leaves the
    destination untouched (the tmp file is orphaned but harmless).

    Caller is responsible for holding ``_file_lock()`` if cross-process
    serialization is needed — atomicity here is per-write, not per-section.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.chmod(tmp, mode)
    tmp.replace(path)


def load_prefs() -> dict:
    if not PREFS_PATH.exists():
        return {}
    try:
        return json.loads(_read_text_normalized(PREFS_PATH))
    except json.JSONDecodeError:
        return {}


def write_prefs(prefs: dict) -> None:
    with _file_lock():
        atomic_write_text(PREFS_PATH, json.dumps(prefs, indent=2), mode=0o600)
