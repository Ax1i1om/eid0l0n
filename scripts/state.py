"""EID0L0N — paths, anchor parsing, atomic writes, path safety.

Stateless helpers used by eidolon.py and codex_backend.py.
No CLI, no API calls. Agent manages state files directly via Read/Write.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
HOME = Path.home()
LEGACY_CONFIG_DIR = HOME / ".config" / "eidolon"  # for migration detection only


def resolve_state_dir() -> Path:
    """State lives at <cwd>/eidolon/. EIDOLON_HOME overrides for dev/test.

    Refuses to write inside the skill's own source repo.
    """
    override = os.environ.get("EIDOLON_HOME")
    if override:
        return Path(override).expanduser().resolve()
    try:
        cwd = Path(os.getcwd())
    except (FileNotFoundError, OSError):
        sys.exit("error: cwd is gone. Set EIDOLON_HOME to a writable dir.")
    if (cwd / ".git").exists() and (cwd / "SKILL.md").exists() and (cwd / "scripts").is_dir():
        sys.exit(
            "error: cwd looks like the eidolon source repo. "
            "Run from your host workspace, or set EIDOLON_HOME."
        )
    return cwd / "eidolon"


def legacy_state_present() -> bool:
    """True iff persona files sit in the legacy ~/.config/eidolon/ tree.
    Agent uses this signal to trigger migration playbook.

    Fails closed (returns False) on permission errors — this is a probe,
    not an authoritative read.
    """
    if not LEGACY_CONFIG_DIR.exists():
        return False
    if (LEGACY_CONFIG_DIR / "visual_anchor.md").exists():
        return True
    try:
        return any(
            c.is_dir() and (c / "visual_anchor.md").exists()
            for c in LEGACY_CONFIG_DIR.iterdir()
        )
    except (PermissionError, OSError):
        return False


def read_text_normalized(path: Path) -> str:
    """Read with explicit UTF-8, normalize line endings."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def atomic_write_text(path: Path, text: str, mode: int = 0o644) -> None:
    """tmp → chmod → replace. Crash-safe per write.

    Tmp file uses PID to avoid collision; cleaned up on failure.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.chmod(tmp, mode)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def parse_anchor(path: Path) -> tuple[str, str | None, str]:
    """Return (anchor_text_without_headers, reference_path_string, character_slug)."""
    text = read_text_normalized(path)
    ref = None
    ref_matches = re.findall(r"^reference:\s*(.+)$", text, flags=re.MULTILINE)
    if len(ref_matches) > 1:
        sys.exit(f"error: multiple reference: lines in {path}")
    if ref_matches:
        ref = ref_matches[0].strip()
        if "\x00" in ref or len(ref) > 1024:
            sys.exit(f"error: invalid reference value in {path}")
        text = re.sub(r"^reference:\s*.+$\n?", "", text, count=1, flags=re.MULTILINE)
    name_match = (
        re.search(r"^#\s*(?:Visual\s*Anchor|Persona)\s*[—\-:]\s*(.+)$",
                  text, flags=re.MULTILINE | re.IGNORECASE)
        or re.search(r"^#\s*(.+)$", text, flags=re.MULTILINE)
    )
    name = name_match.group(1).strip() if name_match else "character"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_") or "character"
    return text.strip(), ref, slug


def find_existing_reference(state_dir: Path) -> Path | None:
    """Find reference.{png,jpg,jpeg,webp} in state_dir.

    Raises (sys.exit) if multiple extensions coexist (write-time invariant violation).
    """
    found = []
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = state_dir / f"reference.{ext}"
        if p.exists():
            found.append(p)
    if len(found) > 1:
        names = ", ".join(p.name for p in found)
        sys.exit(f"error: multiple reference images coexist ({names}). Keep one.")
    return found[0] if found else None


def validate_reference_path(ref_path: Path, workspace: Path) -> None:
    """Reject reference paths that escape the workspace.

    Defends against poisoned visual_anchor.md `reference: ~/.aws/credentials`.
    Expands `~` before resolving so tilde-paths can't sneak through.
    """
    expanded = Path(os.path.expanduser(str(ref_path))).resolve()
    try:
        expanded.relative_to(workspace.resolve())
    except ValueError:
        sys.exit(f"error: reference image escapes workspace: {ref_path!r}")
