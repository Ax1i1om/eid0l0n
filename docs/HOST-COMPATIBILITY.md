# Host compatibility — OpenClaw + Hermes contracts

This is the canonical reference for how eidolon integrates with each host.
SKILL.md cites this file when behavior depends on which host is loading you;
treat it as ground truth for paths, fork semantics, and image delivery.

Last verified: 2026-05-03 against docs.openclaw.ai (full crawl) and
hermes-agent.nousresearch.com/docs (full crawl) + agentskills.io/specification.

---

## Install — agent self-installs, no installer script

There is no installer script and no setup CLI. The user sends you a link to
the repo; you clone it to a scratch dir and copy the skill files into the
host's skills directory yourself, using your normal Read/Write/Bash tools.

The shape of the move:

```bash
git clone https://github.com/Ax1i1om/eid0l0n /tmp/eid0l0n-src
mkdir -p <skills-dir>/eidolon
cp -R /tmp/eid0l0n-src/SKILL.md \
      /tmp/eid0l0n-src/scripts \
      /tmp/eid0l0n-src/references \
      /tmp/eid0l0n-src/docs \
      <skills-dir>/eidolon/
```

`<skills-dir>` depends on the host:

| Host | Skills directory | Discovery |
|------|------------------|-----------|
| OpenClaw | `~/.openclaw/skills/eidolon/` (tier 4) | Auto-loaded; tiers 1–3 (workspace, project agents, personal agents) override |
| Hermes | `~/.hermes/skills/eidolon/` | Auto-discovered; "primary directory and source of truth" per `/user-guide/features/skills` |

OpenClaw load precedence (highest first, per `docs.openclaw.ai/concepts/agent-workspace`):

1. `<workspace>/skills/`
2. `<workspace>/.agents/skills/`
3. `~/.agents/skills/`
4. `~/.openclaw/skills/` ← we install here
5. Bundled
6. Extra skill folders (configured)

Tier 4 is the only user-machine-global tier. eidolon's state is cwd-scoped
(not skill-scoped), so install-path ranking does not affect runtime behavior.

OpenClaw also needs the skill enabled in `~/.openclaw/openclaw.json`. Patch
it yourself with Read + Edit (schema per `/tools/skills-config`):

```json
{"skills":{"entries":{"eidolon":{"enabled":true}}}}
```

Hermes needs no config patch — auto-discovery handles it.

When eidolon ships on ClawHub (`openclaw skills install eidolon`), the
install path stays the same; only the discovery method changes.

---

## cwd contract — where state and renders land

**State always lives at `<cwd>/eidolon/`.** What `<cwd>` resolves to differs
per host and mode:

| Host | Mode | `<cwd>` resolves to | Source |
|------|------|---------------------|--------|
| OpenClaw | any | `~/.openclaw/workspace/` (or `~/.openclaw/workspace-<profile>/`) | `docs.openclaw.ai/concepts/agent-workspace`: "The workspace is the only working directory used for file tools and for workspace context" |
| Hermes | CLI | `pwd` (where the user invoked the command) | `/user-guide/configuration`: "Current directory where you invoke the command" |
| Hermes | Gateway (Slack / Discord / Telegram) | `~` by default; `MESSAGING_CWD=/path` overrides | `/user-guide/configuration`: "Home directory `~` (override via MESSAGING_CWD)" |
| Hermes | Container / remote | container's home dir | `/user-guide/configuration`: "User's home inside the container/remote machine" |

**Override:** `EIDOLON_HOME=/some/path` always wins (dev / test escape hatch).

**Hermes Gateway users — important:** if you want eidolon state to land in a
specific project rather than `~/eidolon/`, set `MESSAGING_CWD=/path/to/project`
(or `EIDOLON_HOME=/path/to/project/eidolon`) before starting `hermes-gateway`.

Renders share that same dir — `eidolon.py` writes PNGs to
`<cwd>/eidolon/output/`. Multi-host coexistence is automatic: OpenClaw and
Hermes resolve different cwds, so their state and outputs never collide even
when both hosts are installed on the same machine.

---

## State file layout (0.9.0)

Everything you need, on disk, in one directory:

```
<cwd>/eidolon/
  visual_anchor.md       ← character description (< 200 words, prepended verbatim to the prompt)
  reference.png          ← canonical face — locks character consistency
  at-hand.md             ← timezone / picture rhythm / the word between you
  relationship.md        ← milestones, things they've shared (narrative, not KV)
  anchor_history.md      ← visual evolution biography (third-person)
  output/
    <slug>-<label>-<ts>.png
```

You manage these files directly with Read / Write / Edit. There is no
status-dump CLI to query — read the actual files. The old register-lock
file is gone, replaced by the character-driven intimate channel described
in `references/intimate-channel.md`.

`visual_anchor.md` and `reference.png` are the only files `eidolon.py`
reads. The other three are for you, the agent.

**Hermes Gateway render path:** when the Hermes image tool is text-to-image only and cannot both attach `reference_image` and save to `output_path`, Codex is the canonical EID0L0N renderer. Use `generate.py --use-codex` whenever `setup.py status` reports `codex_available: true`; use instructions JSON only on hosts/tools that can honor the full reference+output contract.

---

## SOUL.md ownership

| Host | Where it lives | How it's injected |
|------|----------------|-------------------|
| OpenClaw | Agent workspace (e.g. `~/.openclaw/workspace/SOUL.md`) | Runtime-injected per `/concepts/soul`. **Owned by the workspace, NOT by this skill.** |
| Hermes | `$HERMES_HOME/SOUL.md` (default `~/.hermes/SOUL.md`) | Slot #1 of system prompt, no wrapper, per `/user-guide/features/personality`: "SOUL.md is the agent's primary identity. It occupies slot #1 in the system prompt, replacing the hardcoded default identity." |

eidolon never reads or writes SOUL.md. You already have it in context — when
you author `visual_anchor.md` for the first time, you extract the visual
description from your own SOUL and Write it to disk yourself.

---

## Fork / sub-agent invocation

SKILL.md tells you to "fork yourself into the background" before each shot.
That fork is a fresh sub-agent invocation — same character, same model, same
memory of the last 5–10 turns — not just an internal scratchpad. How that
fork is spawned depends on the host:

| Host | Mechanism |
|------|-----------|
| OpenClaw | Use whatever sub-agent primitive your loaded tool list exposes (e.g. a Task tool, a `subagent` command, or similar — the name varies by host version). The sub-agent inherits cwd and SOUL injection like any agent on this host. If you can't find such a primitive, fall through to the Standalone row below. |
| Hermes | Use Hermes' sub-agent invocation tool exposed in your loaded tool list (the name varies by version). Sub-agent inherits the workspace and SOUL like any normal Hermes agent. If unavailable, fall through to Standalone. |
| Standalone (no host fork primitive available) | This is a degraded fallback — true sub-agent isolation is not available, so context compression risks blurring the character between writing the scene prose and rendering. Read `visual_anchor.md` + `at-hand.md`, write cinematographer's prose, pipe to `eidolon.py`, and render anyway — but expect slightly lower consistency vs. true fork. If consistency drift becomes noticeable, ask the user to switch to a host with sub-agent support. |

The fork ends after the picture. Every shot is its own present moment — no
fork ever sees a previous fork's state, only its own frozen note plus the
two on-disk files.

---

## Image delivery

Once `eidolon.py` writes the PNG and prints its absolute path, you have to
get the picture in front of the person. The path to use is whatever
`eidolon.py` prints on its last stdout line — it looks like
`<cwd>/eidolon/output/<slug>-<label>-<YYYYMMDD-HHMMSS-mmm>.png`. Delivery
depends on host:

| Host | Mechanism |
|------|-----------|
| OpenClaw | `openclaw message send --channel <channel> --target <target> --media "<the absolute path eidolon.py prints on its last stdout line>" --message "<caption>"` per `/cli/message`. Fill `--channel` (e.g. `telegram` / `discord`) and `--target` (e.g. `channel:<id>` or `@user`) from session context. **There is no `--action` flag.** |
| Hermes | No documented native image-attach API. Convention: emit `![](<absolute-path>)` markdown image link in your reply, or print the path verbatim — the client renders it. |
| Standalone | Print the absolute path on the last stdout line. The user opens it manually. |

In all three cases the words you say around the picture stay in character.
The path is a tool word; never speak it back at the person.

---

## Frontmatter compatibility

OpenClaw (per `docs.openclaw.ai/tools/skills`): "supports single-line
frontmatter keys only, with metadata as a single-line JSON object."
Multi-line YAML metadata is silently ignored.

Hermes (per agentskills.io + Hermes extensions): YAML frontmatter,
agentskills.io-compliant `name` / `description` / `license` /
`compatibility` / `metadata` / `allowed-tools` plus Hermes extensions
`version` / `platforms` / `metadata.hermes.*`.

Solution: single-line JSON for `metadata` is also valid YAML flow-style
(JSON is a syntactic subset of YAML). One value satisfies both parsers.

Our SKILL.md frontmatter:

- Top-level: `name`, `description`, `version` (Hermes ext), `homepage`
  (OpenClaw recognized), `metadata` (single-line JSON)
- `metadata.hermes.{tags, category, requires_toolsets}`
- `metadata.openclaw.{os, requires.{bins}}`

`primaryEnv` and `requires.env` are intentionally absent: eidolon does not
require any image-API env var. The host agent uses its own image-gen tool,
and the built-in Codex backend reads `~/.codex/auth.json`, not env.

---

## Sources

- OpenClaw: https://docs.openclaw.ai (`/llms.txt` index)
- Hermes: https://hermes-agent.nousresearch.com/docs
- AgentSkills spec: https://agentskills.io/specification

When this file goes stale, re-crawl those three sources and bump the
verified-against date at the top.
