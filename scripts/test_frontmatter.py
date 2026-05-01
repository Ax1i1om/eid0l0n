#!/usr/bin/env python3
"""Smoke test: SKILL.md frontmatter parses correctly for both Hermes (YAML)
and OpenClaw (single-line JSON metadata).

Stdlib-only — no external deps. Validates the *exact* shape we ship: top-level
scalars + a single `metadata:` line whose value is single-line JSON. PyYAML is
used opportunistically when present for a stricter YAML-grammar check.

Run from anywhere:
    python3 scripts/test_frontmatter.py

Exit codes:
    0  all checks passed
    1  frontmatter delimiters / shape invalid
    2  required top-level key missing
    3  metadata not single-line JSON (OpenClaw parser would reject)
    4  required nested metadata keys missing
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml  # PyYAML — optional; stricter YAML check when available
    _HAS_YAML = True
except ImportError:
    yaml = None  # type: ignore
    _HAS_YAML = False

SKILL_PATH = Path(__file__).resolve().parent.parent / "SKILL.md"

REQUIRED_TOP_LEVEL = ["name", "description", "version", "homepage", "metadata"]
REQUIRED_HERMES = ["tags", "category", "requires_toolsets"]
# `primaryEnv` and `requires.env` are optional in the OpenClaw spec — eid0l0n
# 0.8+ no longer requires any image-API env var (the host agent uses its own
# tool, and the built-in Codex backend reads ~/.codex/auth.json, not env).
REQUIRED_OPENCLAW = ["os", "requires"]
REQUIRED_OPENCLAW_REQUIRES = ["bins"]


def main() -> int:
    text = SKILL_PATH.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        print("error: SKILL.md missing YAML frontmatter delimiters", file=sys.stderr)
        return 1

    fm_text = parts[1]

    # Stdlib path: parse the simple `key: value` lines + isolate the metadata
    # JSON manually. This is sufficient because our frontmatter is intentionally
    # one-scalar-per-line + one single-line JSON metadata value.
    fm: dict[str, str] = {}
    metadata_line: str | None = None
    for line in fm_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^metadata\s*:", line):
            metadata_line = line
            fm["metadata"] = line.split(":", 1)[1].strip()
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()

    if _HAS_YAML:
        try:
            yaml_fm = yaml.safe_load(fm_text)
            if not isinstance(yaml_fm, dict):
                print("error: PyYAML loaded frontmatter as non-dict", file=sys.stderr)
                return 1
        except yaml.YAMLError as e:
            print(f"error: PyYAML rejected frontmatter (Hermes would fail): {e}", file=sys.stderr)
            return 1

    missing = [k for k in REQUIRED_TOP_LEVEL if k not in fm]
    if missing:
        print(f"error: missing required top-level keys: {missing}", file=sys.stderr)
        return 2

    if metadata_line is None:
        print("error: no `metadata:` line found", file=sys.stderr)
        return 3

    json_part = metadata_line.split(":", 1)[1].strip()
    try:
        parsed_json = json.loads(json_part)
    except json.JSONDecodeError as e:
        print(
            f"error: metadata value is not valid single-line JSON "
            f"(required for OpenClaw parser per docs.openclaw.ai/tools/skills): {e}",
            file=sys.stderr,
        )
        return 3

    if "hermes" not in parsed_json:
        print("error: metadata missing `hermes` block", file=sys.stderr)
        return 4
    if "openclaw" not in parsed_json:
        print("error: metadata missing `openclaw` block", file=sys.stderr)
        return 4

    h_missing = [k for k in REQUIRED_HERMES if k not in parsed_json["hermes"]]
    if h_missing:
        print(f"error: metadata.hermes missing keys: {h_missing}", file=sys.stderr)
        return 4

    oc_missing = [k for k in REQUIRED_OPENCLAW if k not in parsed_json["openclaw"]]
    if oc_missing:
        print(f"error: metadata.openclaw missing keys: {oc_missing}", file=sys.stderr)
        return 4

    oc_req_missing = [k for k in REQUIRED_OPENCLAW_REQUIRES if k not in parsed_json["openclaw"]["requires"]]
    if oc_req_missing:
        print(f"error: metadata.openclaw.requires missing: {oc_req_missing}", file=sys.stderr)
        return 4

    yaml_note = "PyYAML+stdlib" if _HAS_YAML else "stdlib"
    print(f"✓ SKILL.md frontmatter passes both Hermes (YAML) and OpenClaw (single-line JSON metadata) checks [{yaml_note}]")
    print(f"  name:        {fm['name']}")
    print(f"  version:     {fm['version']}")
    print(f"  homepage:    {fm['homepage']}")
    print(f"  metadata.hermes.tags:    {parsed_json['hermes']['tags']}")
    print(f"  metadata.openclaw.os:    {parsed_json['openclaw']['os']}")
    print(f"  metadata.openclaw.bins:  {parsed_json['openclaw']['requires'].get('bins', [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
