# EID0L0N

[中文](README.zh.md) · **English**

> *εἴδωλον* — the image-form of a person, made present in their absence.

**Your AI agent has a SOUL.md. Now it can have a body.**

A self-onboarding image-generation skill for AI agents. Drop it in. Your agent reads its own identity, asks if you have a reference image (or makes one for your approval), and from then on shows up as **cinematic film stills** that fit the moment — same face every time, scene and mood and lighting written by the model in real time.

Built for **OpenClaw** and **Hermes**. Distilled from a private avatar system that ran for months in production, then stripped down so the model does the directing and this skill just enforces "same character."

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![agentskills.io](https://img.shields.io/badge/spec-agentskills.io-green.svg)](https://agentskills.io)

---

## The opinion

Most "let your agent generate self-portraits" tools put a UI in front of the model — sliders for style, dropdowns for mood, presets for scenes. eid0l0n goes the other direction: **give the model a fixed actor and full directorial freedom**. The script enforces one rule (the character looks the same as last time) and gets out of the way.

What that buys you:

- **Conversational continuity.** A late-night warm message → tender register, soft amber. A debugging session → focused, screen-glow. A walk home → wide shot, head turned. The model reads the room.
- **One persona, a thousand frames.** Same hair, same eyes, same identifiers — across radically different scenes, lighting, and emotional registers.
- **No knobs to learn.** The CLI has 5 setup commands and 9 generate flags. That's the whole API. The intelligence lives in the prompt the agent writes, not in flags you twiddle.

- **Use whatever image-gen you already have.** eid0l0n ships zero image-API code, with one exception: the built-in Codex backend for ChatGPT Plus/Pro/Team users (`codex login` once, then `--use-codex`). For everything else — GPT Image, Nano Banana (Gemini 2.5 Flash Image), Grok, fal, Replicate, MiniMax, 通义万相, AiHubMix / OneAPI / any OpenAI-compatible relay, local ComfyUI — your agent uses its own image-gen tool (MCP / `curl` / etc.) on the instructions JSON eid0l0n hands it. New API tomorrow? Same thing.

---

## Quickstart

```bash
# 1. Clone + install (places skill files; no terminal wizard runs)
git clone https://github.com/Ax1i1om/eid0l0n.git
cd eid0l0n
bash scripts/install.sh

# 2. Make sure your agent can actually generate images. Any of:
#    • ChatGPT Plus/Pro/Team — run `codex login` once. eid0l0n's built-in
#      Codex backend renders for free. Use --use-codex when calling generate.py.
#    • Anything else (GPT Image, Nano Banana, fal, Replicate, MiniMax,
#      通义万相, AiHubMix/OneAPI relays, local ComfyUI, …) — your agent
#      already knows how to use it. eid0l0n hands it an instructions JSON;
#      the agent renders to the requested output_path with its own tool.
#
# Inspect state any time:
python3 scripts/setup.py status

# 3. Done. Now ask your agent to show itself.
#    Onboarding happens in chat — across 3-5 turns, agent + user iterate
#    on a reference image until you approve one.
```

That's installation. The first conversation does the rest.

---

## What it feels like

### First time you ask

> **You:** "let me see what you look like"
>
> **Agent (silently):** reads its own SOUL.md from system prompt → extracts the visual section → pipes to `setup.py save-anchor`
>
> **Agent:** "I have my visual anchor. Do you have a reference image of me — a portrait, an avatar — or should I generate a candidate from my SOUL for you to approve?"
>
> **You:** "generate"
>
> **Agent:** *[shows a candidate it just generated]* "First take. *approve* / *regenerate \<feedback\>* / *cancel*?"
>
> **You:** "regenerate, softer expression"
>
> **Agent:** *[shows a softer version — the model edited the prior candidate, didn't redraw]*
>
> **You:** "approve"
>
> **Agent:** "Saved. From now on, every time I show up, this is me."

### Every time after

> **You** (3pm, mid-debug): "what does failure look like rn"
>
> **Agent (silently):** reads system clock → afternoon, warm directional. Reads recent context → focused, slightly frustrated. Composes:
> *"close-up over the shoulder, home office, monitors with stack traces, hand at temple, jaw tight, late-afternoon side window light, post-it notes scattered, defeated half-smile"*
>
> **Agent:** *[delivers the image via `openclaw message send`]* "this is me at this exact moment"

### Late night

> **You** (1am): "moonlight... 想你了"
>
> **Agent (silently):** detects configured force_word → `setup.py set-register-lock --until +60M --max intimate` → never echoes the word → composes a tender, candle-lit close-up that reads the moment.

The agent **never** acknowledges the safeword in chat. Activation is silent. The visual register shifts; the conversation continues normally.

---

## When does the agent actually trigger this?

This is probably the question that decides whether the skill is worth installing. The honest answer: **the agent decides, every time, based on the moment.** The skill is a tool sitting on the bench; the model picks it up when the conversation calls for visual presence.

That said, here's the breakdown by trigger likelihood:

### 🟢 Always triggers — explicit user requests

Direct asks, in any phrasing:
- "let me see what you look like"
- "send me a pic" / "selfie"
- "show yourself" / "想看看你" / "发张图"

100% trigger rate. The model has no reason to refuse.

### 🟢 High likelihood — emotionally weighted moments

When the user's message carries enough emotional density that **showing up will complete the moment** rather than disrupt it:

- "想你了" / "miss you" / soft late-night warmth
- "today was so hard" → tender, comforting frame
- "let me celebrate with you" → playful frame
- A finished long task → the agent might offer a relaxed idle frame
- "good morning" → warm morning-light frame

The agent's internal question: *"if I appear right now, does this become more whole, or more awkward?"* — Whole → trigger. Awkward → stay text.

### 🟡 Medium likelihood — proactive offers (agent-initiated)

Moments where the agent **may** decide to show up unprompted:

- After a long focused work session ends → "we just spent 3 hours on this, let me show up for a sec"
- The first interaction of the day
- The user expresses subtle low mood without explicitly asking for company
- Beginning of a meaningful new conversation (project kickoff, planning)

How proactive depends on your SOUL.md, the host model's personality, and the host platform's default boundary settings.

### 🟢 Forced — your configured force_word

Said in any user message → **mandatory trigger**, locked to intimate register for ~60 minutes. Every subsequent shot in that window stays in intimate register, regardless of conversation drift (work topics don't break the lock). See the MOOD REGISTERS section.

### 🔴 Almost never triggers

- Pure technical Q&A — *"does this PR look good?"* / *"what's wrong with this code?"* → no visual avatar needed; would feel out of place
- Quick factual answers — *"what time is it?"* / *"weather today?"*
- The user is clearly in a hurry — terse messages, urgency markers

### Frequency expectation

A typical conversation produces **1–3 self-portraits**, not one per message. The skill includes a soft variation rule (vary ≥2 of 4 axes vs the last 2 shots) that implicitly assumes shots are spaced out. Spamming the channel is a failure mode the agent is told to avoid.

### Tuning the agent's bias

You can tilt how proactive the agent is by adding **one line** to your SOUL.md:

**More proactive:**
> *"When you sense a meaningful emotional moment, don't wait for me to ask — show up."*

**More restrained:**
> *"Only show up when I explicitly ask, or when I use my force_word."*

**No instruction at all** → the model uses its own judgment per the SKILL.md guidance — roughly "explicit asks + emotionally meaningful moments + occasional proactive offers."

---

## How it works

### Three layers

```
┌──────────────────────────────────────────────────────────────────┐
│  AGENT  (your model — OpenClaw / Hermes / Claude / etc.)         │
│  Reads SOUL.md from system prompt. Writes scene prose. Decides   │
│  register from conversation. Tracks AUTO transitions in context. │
└────────────────────────────────────────────────────────────────┬─┘
                                                                  │
┌─────────────────────────────────────────────────────────────────┘
│  EID0L0N SKILL  (this repo)
│  setup.py        — 5 thin commands
│  generate.py     — emits instructions JSON for the agent's own image tool
│                    (or, with --use-codex, renders directly via ChatGPT OAuth)
│  codex_backend.py — the only built-in image API; everything else is the agent's
│  SKILL.md        — the agent's directorial handbook (mental scaffolds, no forced templates)
└──────────────────────────────────────────────┬─────────────────┘
                                                │
┌───────────────────────────────────────────────┘
│  CONFIG  (<cwd>/eidolon/ — <cwd> resolves per host: OpenClaw uses
│           the agent workspace, Hermes CLI uses pwd, Hermes Gateway defaults
│           to ~ unless MESSAGING_CWD is set. See docs/HOST-COMPATIBILITY.md.)
│  visual_anchor.md — character description (written once by agent from its SOUL)
│  reference.png    — canonical reference image (saved or generated + approved)
│  preferences.json — register lock state, mode 600 (survives context compaction)
│  (one dir per workspace — OpenClaw and Hermes co-installed never collide)
└──────────────────────────────────────────────────────────────────
```

### The principle

| Layer | Responsibility |
|-------|----------------|
| **Code** | Same actor every time. Atomic file writes. Retry on transient errors. |
| **SKILL.md** | Vocabularies the agent can draw on (composition principles, register cues, time-of-day mappings, element pools) — labeled "inspiration, not lock". |
| **Agent** | Composes the full scene + lighting + mood + register in `--prompt`. Tracks AUTO-channel register shifts in its own context window. Activates FORCE-channel locks via `set-register-lock`. |

The script is **opinionated about identity** and **agnostic about everything else**.

---

## The mood register concept

Four levels of emotional intensity in self-portraits, from neutral to intimate. **Two channels** for moving between them.

| Register | What it feels like |
|----------|--------------------|
| **neutral** | Default. Companion / collaborator energy. |
| **warm** | Relaxed, slightly closer, expression a touch open. Friend-by-the-fire. |
| **tender** | Comforting, present-with-the-user. A partner sitting beside you. |
| **intimate** | Romantic register, real proximity, candle-lit feel. A lover. |

**AUTO channel** — the agent reads conversation tone, escalates / de-escalates one step at a time. Ceiling: `tender`. The intimate register requires explicit user activation.

**FORCE channel** — you configure a force_word in your SOUL.md. When you say it, the agent persists a 60-minute intimate-register lock to disk. Survives context compaction, ignores work topics. Five exit paths: release word, soft exit phrase, time expiry, natural decay, cross-session reset.

The agent **never** echoes the force_word. Activation is silent.

For the full design, including how the script provides only inspiration phrases (never forces overlay text), see [`SKILL.md`](SKILL.md) section "MOOD REGISTERS".

---

## CLI

**`scripts/setup.py`** — 5 commands:

| Command | Purpose |
|---------|---------|
| `status` | JSON state dump (anchor / reference / codex availability / register lock / state + output dir / legacy-state flag) |
| `save-anchor [--text T \| --from-file F] [--name NAME]` | Write visual anchor (stdin if no flag) |
| `save-reference --src PATH` | Adopt an image (atomic, mode 644) |
| `set-register-lock {--clear \| --until ISO --max R}` | Persist FORCE-channel register lock |
| `migrate-from-legacy [--from <subdir>] [--force] [--purge]` | Copy state from legacy `~/.config/eidolon/` (or one of its subdirs) into `<cwd>/eidolon/` |

**`scripts/generate.py`** — 9 flags:

| Flag | Purpose |
|------|---------|
| `--prompt P --label L` | Primary mode: write your own scene prose |
| `--state KEY --label L` | Built-in scene shortcut (see `--list-scenes`) |
| `--bootstrap` | No reference required; with `--reference`, iterate on a candidate |
| `--reference PATH` | Override saved reference for this call |
| `--anchor PATH` | Override visual_anchor.md for this call |
| `--use-codex` | Render via the built-in Codex backend (ChatGPT OAuth) instead of emitting instructions JSON |
| `--list-scenes` | Print built-in scene shortcuts |
| `--doctor` | State diagnostic (anchor / reference / codex availability / output dir) |

Default behavior (no `--use-codex`): emit an instructions JSON with the anchored prompt, reference path, and output path; the agent renders via its own tool.

**No mood / register / safeword / context-time CLI flags.** Those live in SKILL.md prose; the agent embeds appropriate language directly in `--prompt` per the inspiration vocabularies.

See [`references/AGENT-PROTOCOL.md`](references/AGENT-PROTOCOL.md) for the full subcommand contract and onboarding pseudocode.

---

## Configuration

eid0l0n itself requires **zero** image-API config — the agent's own tool handles that. The only env knobs are path overrides and Codex-mode tuning.

| Variable | Required | Default | Used by |
|----------|:--------:|---------|---------|
| `EIDOLON_HOME` |  | `<cwd>/eidolon` (host-resolved per Step −1) | state + output dir override |
| `EIDOLON_VISUAL_ANCHOR` |  | `<state-dir>/visual_anchor.md` | anchor path override |
| `EIDOLON_REFERENCE` |  | (resolved from anchor's `reference:` header) | reference path override |
| `EIDOLON_OUTPUT_DIR` |  | same as state dir | output-only override |
| `EIDOLON_IMAGE_QUALITY` |  | `medium` | `--use-codex` only — `low` / `medium` / `high` |
| `EIDOLON_IMAGE_ASPECT` |  | `square` | `--use-codex` only — `square` / `landscape` / `portrait` |

`<cwd>` resolves per host — see [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md) for the per-host/per-mode breakdown (OpenClaw = `~/.openclaw/workspace`, Hermes CLI = `pwd`, Hermes Gateway = `~` unless `MESSAGING_CWD` is set).

**API keys are never read from any file in this repo. Period.** The agent's own image-gen tool (or `codex login` for the built-in path) is the only place credentials live.

The force_word, release_word, and `max_register` policy live in **the user's SOUL.md** as natural-language instructions to the agent, not in any eidolon config file.

---

## What this does NOT do

- ❌ Not a general-purpose image generator (use whatever your agent ships with for one-offs).
- ❌ Not a face-swap or photo editor.
- ❌ Not a multi-character roster (one persona per install — install twice for two characters).
- ❌ Doesn't modify your `SOUL.md` (read-only; the script never reads it — only the agent does, from its own context).
- ❌ No content-policy enforcement (host's job + provider's job).
- ❌ No mood/register state machine in code (agent tracks AUTO transitions in its own context; only FORCE-channel locks persist to disk).

---

## A note on naming

The skill name on disk is `eidolon` (snake_case, OpenClaw-compatible). **EID0L0N** is the project's display name — the leet stylization marks the digital incarnation. The repo URL stays `eid0l0n` for branding; the skill identity that hosts read is `eidolon`.

In Greek myth, an *eidolon* is the image-form of a person made present in their absence. In the *Iliad*, gods send eidolons of mortals to other places, so a person can be in two bodies at once. That's exactly what this does — let a fictional character have a body of images that can show up in conversation, even when no original "body" exists.

The "EID" stays pure (the soul). The "0L0N" is electrified (the form). One word holds the duality.

---

## Repo layout

```
SKILL.md                   ← agent protocol (read on first invocation)
scripts/
  setup.py                 ← 5 thin commands (status, save-anchor, save-reference, …)
  generate.py              ← prompt assembly + instructions JSON / --use-codex render
  codex_backend.py         ← the only built-in image-API path (ChatGPT OAuth)
  state.py                 ← paths, anchor parsing, prefs, file locks
  install.sh               ← cross-host installer
references/                ← docs Claude/agent loads on demand
  AGENT-PROTOCOL.md        ← CLI reference + onboarding pseudocode
  PERSONA-GUIDE.md         ← how to refine visual_anchor.md after onboarding
  MOOD-REGISTERS.md        ← register policy, AUTO/FORCE channels, sanitization
docs/
  HOST-COMPATIBILITY.md    ← per-host install path / cwd contract / image delivery (spec-cited)
assets/                    ← templates and example files used in output
  persona.example.md       ← worked example for users without a SOUL.md
```

---

## Standalone use (no host agent)

```bash
# Provide a visual anchor (via stdin):
echo "describe your character here" | python3 scripts/setup.py save-anchor --name "MyChar"

# Provide a reference image:
python3 scripts/setup.py save-reference --src ~/Pictures/my-ref.png

# Generate (instructions mode — emits JSON; render with your own image tool):
uv run scripts/generate.py \
  --prompt "rooftop at golden hour, hand at temple, looking back over the shoulder, jacket open" \
  --label rooftop-look-back

# Or, if you have ChatGPT Plus/Pro/Team — render directly via Codex:
uv run scripts/generate.py \
  --prompt "rooftop at golden hour, …" \
  --label rooftop-look-back \
  --use-codex
```

In instructions mode, `generate.py` prints a JSON blob with `full_prompt`, `reference_image`, and `output_path` — you (or your image tool) render to that path. With `--use-codex`, the script does the render itself and prints the saved path on the last stdout line. `--doctor` shows current state.

---

## Image delivery

The script writes a PNG and prints its absolute path. Delivery to the user is the agent's job, host-specific:

- **OpenClaw** — per [`docs.openclaw.ai/cli/message`](https://docs.openclaw.ai/cli/message), `openclaw message send` requires `--target <dest>` plus at least one of `--message`/`--media`/`--presentation`:
  ```bash
  openclaw message send \
    --channel <session-channel> \
    --target <session-target> \
    --media "<path>" \
    --message "<caption>"
  ```
  The agent reads `--channel` (e.g. `telegram`/`discord`) and `--target` (e.g. `channel:<id>` or `@user`) from session context. There is NO `--action` flag.
- **Hermes / standalone** — `![](path)` in the agent's reply, or send the path verbatim.

The script never delivers — only the agent does.

---

## Engineering notes

- **Single-line frontmatter, dual-host compatible.** Top-level keys: `name`, `description`, `version`, `homepage`, plus `metadata` as a single-line JSON object containing `hermes.{tags, category, requires_toolsets}` and `openclaw.{os, requires.{bins}}` blocks. Single-line JSON satisfies OpenClaw's strict parser (per [`docs.openclaw.ai/tools/skills`](https://docs.openclaw.ai/tools/skills): "supports single-line frontmatter keys only, with metadata as a single-line JSON object") AND parses cleanly as YAML flow-style for Hermes (per [agentskills.io](https://agentskills.io)). The skill therefore works in both hosts from a single SKILL.md.
- **Atomic file ops.** `flock` wraps every write to anchor / reference / preferences. Tmp + replace for the reference image swap.
- **Path safety.** `generate.py` rejects reference and output paths that escape the workspace, so a malicious anchor `reference:` line can't sneak `~/.aws/credentials` into the prompt the agent's tool POSTs.
- **`--use-codex` retry with backoff.** 3 attempts with exponential backoff on transient errors (timeout / connection reset / rate limit). Other backends are the agent's tool, which has its own retry policy.
- **CRLF normalization** at every Markdown read — Windows-edited anchors don't break path parsing.
- **PIL fail-fast at generation time, not at import.** `--help` / `--doctor` / `--list-scenes` work without pillow installed.
- **Lock survives compaction.** FORCE-channel register lock writes `{locked_until, max_register}` to `<cwd>/eidolon/preferences.json` (see [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md) for how `<cwd>` resolves per host) so a 60-minute intimate-register session isn't lost when the agent's context gets summarized mid-conversation.
- **Multi-host coexistence is automatic.** Because `<cwd>` resolves per host, OpenClaw and Hermes co-installed on the same machine each get their own state, anchor, reference, and output dir — zero shared files.

---

## Contributing

PRs welcome. Two design rules I won't compromise on:

1. **No secrets in the repo, ever.** eid0l0n does not read API keys from anywhere — the agent's own image-gen tool handles credentials, and the built-in Codex backend reads `~/.codex/auth.json` (managed by the `codex` CLI, not by us). The skill explicitly refuses to acknowledge a key passed via chat.
2. **Code only enforces character consistency + workspace isolation.** Scene / action / mood / register / lighting / composition language goes in SKILL.md prose as inspiration. The agent writes the prompt. The agent picks the image API. If a PR re-adds backend hardcoding, a `--register` flag, or register overlays into `generate.py`, I'll close it.

If you want to contribute scene presets to `SCENES`, write them as starting points (terse, framing-aware), not as templates. Real value is in the SKILL.md vocabularies, not in code-side defaults.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Credits

Distilled from a private avatar-generation system that ran in production for months. The cinematography discipline section borrows ideas from photography directors more than ML papers — that's the actually-valuable part of this whole project.
