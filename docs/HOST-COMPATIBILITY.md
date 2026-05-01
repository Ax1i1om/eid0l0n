# Host compatibility — OpenClaw + Hermes contracts

This file is the canonical reference for how eidolon integrates with each host. Cite this when implementation behavior surprises you.

Last verified: 2026-05-01 against docs.openclaw.ai (full crawl) and hermes-agent.nousresearch.com/docs (full crawl) + agentskills.io/specification.

---

## Install paths

| Host | Path | Discovery |
|------|------|-----------|
| OpenClaw | `~/.openclaw/skills/<name>/` (tier 4) | Auto-loaded; tiers 1-3 (workspace, project agents, personal agents) override |
| Hermes | `~/.hermes/skills/<name>/` | Auto-discovered; "primary directory and source of truth" per `/user-guide/features/skills` |

OpenClaw load precedence (highest first, per `docs.openclaw.ai/concepts/agent-workspace`):
1. `<workspace>/skills/`
2. `<workspace>/.agents/skills/`
3. `~/.agents/skills/`
4. `~/.openclaw/skills/` ← we install here
5. Bundled
6. Extra skill folders (configured)

We chose tier 4 because it's the only user-machine-global tier; eidolon's state is cwd-scoped (not skill-scoped), so install-path ranking doesn't affect behavior.

OpenClaw's documented happy-path installer is `openclaw skills install <slug>` from ClawHub (clawhub.ai). When eidolon ships there, the install path stays the same (tier 4); only the discovery method changes.

Hermes does not need a config-patch step. OpenClaw needs `~/.openclaw/openclaw.json` updated to enable the skill — our installer handles this with `{"skills":{"entries":{"eidolon":{"enabled":true}}}}` (schema per `/tools/skills-config`).

---

## cwd contract — where state lands

**State always lives at `<cwd>/eidolon/`.** What `<cwd>` resolves to differs per host and mode:

| Host | Mode | `<cwd>` resolves to | Source |
|------|------|---------------------|--------|
| OpenClaw | any | `~/.openclaw/workspace/` (or `~/.openclaw/workspace-<profile>/`) | `docs.openclaw.ai/concepts/agent-workspace`: "The workspace is the only working directory used for file tools and for workspace context" |
| Hermes | CLI | `pwd` (where the user invoked the command) | `/user-guide/configuration`: "Current directory where you invoke the command" |
| Hermes | Gateway (Slack / Discord / Telegram) | `~` by default; `MESSAGING_CWD=/path` overrides | `/user-guide/configuration`: "Home directory `~` (override via MESSAGING_CWD)" |
| Hermes | Container / remote | container's home dir | `/user-guide/configuration`: "User's home inside the container/remote machine" |

**Override:** `EIDOLON_HOME=/some/path` always wins (dev/test escape hatch).

**Hermes Gateway users — important:** if you want eidolon state to land in a specific project (rather than `~/eidolon/`), set `MESSAGING_CWD=/path/to/project` (or `EIDOLON_HOME=/path/to/project/eidolon`) before starting `hermes-gateway`.

---

## SOUL.md ownership

| Host | Where it lives | How it's injected |
|------|----------------|-------------------|
| OpenClaw | Agent workspace (e.g. `~/.openclaw/workspace/SOUL.md`) | Runtime-injected per `/concepts/soul`. **Owned by the workspace, NOT by this skill.** |
| Hermes | `$HERMES_HOME/SOUL.md` (default `~/.hermes/SOUL.md`) | Slot #1 of system prompt, no wrapper, per `/user-guide/features/personality`: "SOUL.md is the agent's primary identity. It occupies slot #1 in the system prompt, replacing the hardcoded default identity." |

eidolon never reads or writes SOUL.md. The agent already has it in context — it extracts the visual section from there and pipes to `setup.py save-anchor`.

---

## Frontmatter compatibility

OpenClaw (per `docs.openclaw.ai/tools/skills`): "supports single-line frontmatter keys only, with metadata as a single-line JSON object." Multi-line YAML metadata is silently ignored.

Hermes (per agentskills.io + Hermes extensions): YAML frontmatter, agentskills.io-compliant `name`/`description`/`license`/`compatibility`/`metadata`/`allowed-tools` plus Hermes extensions `version`/`platforms`/`metadata.hermes.*`.

Solution: single-line JSON for `metadata` is also valid YAML flow-style (JSON is a syntactic subset of YAML). One value satisfies both parsers.

Our SKILL.md frontmatter:
- Top-level: `name`, `description`, `version` (Hermes ext), `homepage` (OpenClaw recognized), `metadata` (single-line JSON)
- `metadata.hermes.{tags, category, requires_toolsets}`
- `metadata.openclaw.{os, requires.{bins}}`

`primaryEnv` and `requires.env` are intentionally absent: as of 0.8.0 eidolon does not require any image-API env var (the host agent uses its own image-gen tool, and the built-in Codex backend reads `~/.codex/auth.json`, not env). Verified by `scripts/test_frontmatter.py` (run as part of the audit smoke test).

---

## Image delivery

| Host | Mechanism |
|------|-----------|
| OpenClaw | `openclaw message send --channel <> --target <> --media "<path>" --message "<caption>"` per `/cli/message`. The agent fills `--channel` (e.g. `telegram`/`discord`) and `--target` (e.g. `channel:<id>` or `@user`) from session context. **NO `--action` flag exists.** |
| Hermes | No documented native image-attach API. Convention: `![](path)` markdown in agent reply, or print path verbatim — client renders it. |
| Standalone | The script writes a PNG and prints its absolute path on the last stdout line. The user opens it manually. |

---

## Default output dirs

`generate.py` resolves the output dir in this order:
1. `EIDOLON_OUTPUT_DIR` env var (override-only escape hatch)
2. `<cwd>/eidolon/` — same workspace as state, host-resolved per the cwd contract above

State and output now share the same dir by default, so whichever host invokes the skill is also where the PNGs land. **Multi-host coexistence is automatic.** OpenClaw and Hermes resolve different cwds, so their outputs never share files even when both hosts are installed.

Earlier versions probed hardcoded `~/.openclaw/workspace/` then `~/.hermes/workspace/` and returned the first that existed. That drifted from the cwd-based host model and routed Hermes output into `~/.openclaw/workspace/eidolon/` whenever both dirs existed on disk. The current cwd-based logic fixes that — `state.resolve_output_dir()` now follows the same cwd resolution as `_resolve_state_dir()`.

---

## Sources

- OpenClaw: https://docs.openclaw.ai (`/llms.txt` index)
- Hermes: https://hermes-agent.nousresearch.com/docs
- AgentSkills spec: https://agentskills.io/specification

When this file goes stale, re-crawl those three sources and update the verified-against date.
