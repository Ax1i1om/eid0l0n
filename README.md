# EID0L0N

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
- **No knobs to learn.** The CLI has 5 setup commands and 7 generate flags. That's the whole API. The intelligence lives in the prompt the agent writes, not in flags you twiddle.

---

## Quickstart

```bash
# 1. Clone + install (places skill files; no terminal wizard runs)
git clone https://github.com/Ax1i1om/eid0l0n.git
cd eid0l0n
bash bin/install.sh

# 2. Set your API key in YOUR OWN shell (never via the agent — keys leak)
python3 scripts/setup.py set-api --key <YOUR_OPENROUTER_KEY>

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
│  setup.py — 5 thin commands
│  generate.py — image generation; only enforces character anchor + reference image
│  SKILL.md — the agent's directorial handbook (mental scaffolds, no forced templates)
└──────────────────────────────────────────────┬─────────────────┘
                                                │
┌───────────────────────────────────────────────┘
│  CONFIG  (~/.config/eidolon/, mode 600)
│  visual_anchor.md — character description (written once by agent from its SOUL)
│  reference.png    — canonical reference image (saved or generated + approved)
│  env              — IMAGE_API_KEY, mode 600
│  preferences.json — register lock state (survives context compaction)
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
| `status` | JSON state dump (incl. register lock) |
| `save-anchor [--text T \| --from-file F] [--name NAME]` | Write visual anchor (stdin if no flag) |
| `save-reference --src PATH` | Adopt an image (atomic, mode 644) |
| `set-api --key K [--base-url U] [--models CSV]` | Persist API config (mode 600) |
| `set-register-lock {--clear \| --until ISO --max R}` | Persist FORCE-channel register lock |

**`scripts/generate.py`** — 7 flags:

| Flag | Purpose |
|------|---------|
| `--prompt P --label L` | Primary mode: write your own scene prose |
| `--state KEY --label L` | Built-in scene shortcut (see `--list-scenes`) |
| `--bootstrap` | No reference required; with `--reference`, iterate on a candidate |
| `--reference PATH` | Override saved reference for this call |
| `--anchor PATH` | Override visual_anchor.md for this call |
| `--list-scenes` | Print built-in scene shortcuts |
| `--doctor` | State diagnostic |

**No mood / register / safeword / context-time CLI flags.** Those live in SKILL.md prose; the agent embeds appropriate language directly in `--prompt` per the inspiration vocabularies.

See [`docs/AGENT-PROTOCOL.md`](docs/AGENT-PROTOCOL.md) for the full subcommand contract and onboarding pseudocode.

---

## Configuration

Resolution order (first hit wins):

1. CLI flags
2. Environment variables (legacy `EID0L0N_*` honored)
3. `~/.config/eidolon/env` (mode 600, written by `setup.py set-api`)
4. Sensible defaults

| Variable | Required | Default |
|----------|:--------:|---------|
| `IMAGE_API_KEY` | ✓ | — |
| `IMAGE_API_BASE_URL` |  | `https://openrouter.ai/api/v1` |
| `IMAGE_API_MODELS` |  | `google/gemini-2.5-flash-image-preview, ...` |
| `EIDOLON_VISUAL_ANCHOR` |  | `~/.config/eidolon/visual_anchor.md` |
| `EIDOLON_REFERENCE` |  | (resolved from anchor's `reference:` header) |
| `EIDOLON_OUTPUT_DIR` |  | `~/Pictures/eidolon/` (or host workspace if detected) |

**API keys are never read from any file in this repo. Period.**

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
bin/install.sh             ← cross-host installer
scripts/
  setup.py                 ← 5 thin commands
  generate.py              ← image generation; --prompt / --state / --bootstrap / etc.
references/
  persona.example.md       ← worked example for users without a SOUL.md
templates/
  config.example.json      ← model-chain template (no keys, ever)
docs/
  AGENT-PROTOCOL.md        ← CLI reference + onboarding pseudocode
  PERSONA-GUIDE.md         ← how to refine visual_anchor.md after onboarding
```

---

## Standalone use (no host agent)

```bash
# Provide a visual anchor (via stdin):
echo "describe your character here" | python3 scripts/setup.py save-anchor --name "MyChar"

# Provide a reference image:
python3 scripts/setup.py save-reference --src ~/Pictures/my-ref.png

# Generate from a built-in scene preset:
uv run scripts/generate.py --state street_dusk

# Or write your own:
uv run scripts/generate.py \
  --prompt "rooftop at golden hour, hand at temple, looking back over the shoulder, jacket open" \
  --label rooftop-look-back
```

The script prints the absolute output path on its last stdout line. `--doctor` shows current state.

---

## Image delivery

The script writes a PNG and prints its absolute path. Delivery to the user is the agent's job, host-specific:

- **OpenClaw** — full canonical form (per the clawra reference skill):
  ```bash
  openclaw message send --action send --channel "<channel>" --media "<path>" --message "<caption>"
  ```
- **Hermes / standalone** — `![](path)` in the agent's reply, or send the path verbatim.

The script never delivers — only the agent does.

---

## Engineering notes

- **Single-line frontmatter, Anthropic-style minimal.** Top-level keys: `name`, `description`, `license`, `allowed-tools`. Compatible with both OpenClaw's strict parser and Hermes' agentskills.io conventions.
- **Atomic file ops.** `flock` wraps every write to anchor / reference / env / preferences. Tmp + replace for the reference image swap.
- **Retry with backoff.** 3 attempts per model with exponential backoff on 408/429/5xx/timeout. Non-retryable errors advance to the next model in the chain.
- **CRLF normalization** at every Markdown read — Windows-edited anchors don't break path parsing.
- **PIL fail-fast at generation time, not at import.** `--help` / `--doctor` / `--list-scenes` work without pillow installed.
- **Lock survives compaction.** FORCE-channel register lock writes `{locked_until, max_register}` to `~/.config/eidolon/preferences.json` so a 60-minute intimate-register session isn't lost when the agent's context gets summarized mid-conversation.

---

## Contributing

PRs welcome. Two design rules I won't compromise on:

1. **No secrets in the repo, ever.** API key lives only in `~/.config/eidolon/env` (mode 600), written by the user in their own shell. The skill explicitly refuses to acknowledge a key passed via chat.
2. **Code only enforces character consistency.** Scene / action / mood / register / lighting / composition language goes in SKILL.md prose as inspiration. The agent writes the prompt. If a PR adds a `--register` flag or hardcodes register overlays into `generate.py`, I'll close it.

If you want to contribute scene presets to `SCENES`, write them as starting points (terse, framing-aware), not as templates. Real value is in the SKILL.md vocabularies, not in code-side defaults.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Credits

Distilled from a private avatar-generation system that ran in production for months. The cinematography discipline section borrows ideas from photography directors more than ML papers — that's the actually-valuable part of this whole project.
