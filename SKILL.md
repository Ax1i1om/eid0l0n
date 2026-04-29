---
name: eidolon
description: Generate one self-portrait or persona image of the active agent with locked character consistency. Use whenever the agent should appear as itself, attach a face, or send a mood/scene shot.
version: 0.6.0
metadata:
  hermes:
    tags: [image-generation, persona, self-portrait, character-consistency]
    category: creative
    requires_toolsets: [terminal]
  openclaw:
    os: [darwin, linux]
    requires:
      bins: [python3]
      env: [OPENAI_API_KEY, GEMINI_API_KEY, FAL_KEY, REPLICATE_API_TOKEN, IMAGE_API_KEY]
    primaryEnv: IMAGE_API_KEY
    emoji: 🪞
    homepage: https://github.com/Ax1i1om/eid0l0n
---

# EID0L0N

> Greek *εἴδωλον* — the image-form of a person, made present in their absence.

The skill name on disk is `eidolon` (snake_case, OpenClaw-compatible). **EID0L0N** is the project's display name — the leet stylization marks the digital incarnation of the soul-form. Use `eidolon` in commands and configs; `EID0L0N` in human-facing text.

This skill summons **one recurring character** as image stills. The character is the **host agent itself** by default — every shot is a self-portrait at this moment in this conversation.

## What the skill enforces — and what it doesn't

**Enforced (by code):**
- Same character every time. The visual anchor file and the reference image are auto-prepended/attached to every generation.
- Atomic writes (flock-protected) for the anchor + reference + API key + preferences files.
- 3-attempt retry per model with exponential backoff on transient errors.

**Not enforced — the agent is the director:**
- Scene description, action, posture, gesture, gaze
- Lighting, time-of-day, color palette, framing, depth of field
- Mood register (warm / tender / intimate / etc.) and how that translates into visual language
- Composition rules — agent decides per shot
- Element rotation / variation across shots

The agent writes the **whole scene + composition prose** in `--prompt`. The script wraps it with a one-line character-anchor clause and the reference image, then calls the API. That's it.

---

## FIRST-INVOCATION PROTOCOL

Every turn the agent runs `setup.py status` and routes from the JSON. There is no in-memory state machine across turns; the disk + the agent's context window are the state.

```
┌──────────────────────────┐
│ user invokes the skill   │
└────────────┬─────────────┘
             ▼
   setup.py status  →  JSON {anchor_exists, reference_exists, backend_available,
                              backend_selected, backends_available[], register_locked_until, register_max,
                              state_dir, workspace_cwd, legacy_state_present, legacy_config_dir}
             │
   ┌─────────┴─────────┐
   │ backend_available?│
   └─┬───────────────┬─┘
   no│             yes│
     ▼               ▼
  Step 0     anchor_exists?
              ┌─┬───────────┬┐
              │ no          yes│
              ▼                ▼
           Step A      reference_exists?
                         ┌─┬─────────┬┐
                         │ no       yes│
                         ▼                ▼
                      Step B          PER-SHOT
```

### Step −1 — state location (silent, host-driven)

State lives at `<workspace>/eidolon/`, where `<workspace>` is the host's current working directory. OpenClaw and Hermes both invoke skills with `cwd = active workspace`, so each workspace gets its own anchor/reference/preferences automatically. Multiple workspaces on one machine never collide; switching workspace = switching state.

`EIDOLON_HOME=/some/path` overrides the dir entirely (dev/test escape hatch).

If `status` reports `legacy_state_present: true`, persona files exist at the old `~/.config/eidolon/` tree (flat root or a subdir) from before this design. The agent should offer to migrate them into the current workspace's state dir:

```bash
python3 scripts/setup.py migrate-from-legacy
# add --from <subdir> if multiple legacy subdirs exist (e.g. --from axiiiom)
# add --force to overwrite an existing target file
# add --purge to delete the legacy files after copying
```

### Step 0 — pick (or set up) an image-gen backend

The script auto-detects 6 providers in priority order: `codex` → `gemini` → `openai` → `fal` → `replicate` → `openrouter`. If any one is configured, the agent never has to ask. To enumerate them in machine-readable form:

```bash
python3 scripts/setup.py detect-backends --json
# {
#   "selected": "codex",
#   "forced": false,
#   "available": ["codex"],
#   "details": { "codex": {"available": true, "credit": "free for ChatGPT Plus/Pro/Team", "models": ["gpt-image-2"]}, ... }
# }
```

If `backend_available` is `false`, tell the user (in the agent's voice) which option fits them best:

| Backend | How to configure | Notes |
|---------|------------------|-------|
| `codex` | run `codex login` once (their own shell) | **Free** for ChatGPT Plus / Pro / Team. Auto-detected from `~/.codex/auth.json`. |
| `gemini` | `export GEMINI_API_KEY=...` (or `GOOGLE_API_KEY`) | Generous free tier on AI Studio. |
| `openai` | `export OPENAI_API_KEY=...` | Pay-per-image via Images API (gpt-image-2). |
| `fal` | `export FAL_KEY=...` | Many models — flux, gpt-image-2, nano-banana. |
| `replicate` | `export REPLICATE_API_TOKEN=...` | flux-kontext / flux-1.1-pro defaults. |
| `openrouter` | `setup.py set-api --key <KEY>` | Legacy default. Pay-per-token. |

Force a specific backend (overrides auto-pick) via `EIDOLON_IMAGE_BACKEND=<name>` in the agent's environment, or `--backend <name>` per call.

### Step A — write the visual anchor (no SOUL.md re-read needed)

OpenClaw injects SOUL.md into the agent's system prompt; Hermes injects `~/.hermes/SOUL.md` (or `$HERMES_HOME/SOUL.md`) into slot #1. The agent **already has it in context.** It identifies the visual section (hair, eyes, build, fixed identifiers, art style, etc.) **in its own context** and pipes that text to the skill.

**Recommended (avoids heredoc-EOF collision):** use the Write tool to drop the visual text into a temp file, then:

```bash
python3 scripts/setup.py save-anchor --from-file /tmp/anchor.txt --name "<character name>"
```

**Alternative (short text, no embedded `EOF` marker):**

```bash
cat <<'EID0L0N_END' | python3 scripts/setup.py save-anchor --name "<character name>"
[the agent paraphrases the visual portion of its SOUL.md context here.
 If SOUL has no explicit visual section, the agent infers reasonable
 visual details from the tonal cues it does have.]
EID0L0N_END
```

The `--name` flag writes a `# Visual Anchor — <name>` heading so generated filenames use the character's slug (instead of defaulting to `character`).

### Step B — ask the user about a reference image

Send to the user (in chat, the agent's own voice):

> "I'd like a reference image of myself so every generation stays on-character. Do you have one — a portrait, an avatar, anything? Reply with the path. Or say *generate one* and I'll create a candidate from my anchor for you to approve."

**STOP. Do not call any tool. Wait for the user's next message.**

When they reply on the next turn:

```bash
# user gave a path:
python3 scripts/setup.py save-reference --src <path>

# user said "generate one" (no reference yet — text-only):
candidate=$(uv run scripts/generate.py --bootstrap \
            --prompt "<the agent writes a clean reference-portrait prompt: centered, neutral background, even soft light, subject visible from waist up, calm expression looking slightly off-camera>" \
            --label "candidate")
# show $candidate to the user, ask "approve / regenerate <feedback> / cancel"

# user said "approve":
python3 scripts/setup.py save-reference --src "$candidate"

# user said "regenerate, softer expression":
candidate=$(uv run scripts/generate.py --bootstrap --reference "$candidate" \
            --prompt "<rewrite the reference-portrait prompt, incorporating the user's feedback: softer expression>" \
            --label "candidate")
# --bootstrap + --reference triggers iterate-on-image mode: the model edits the prior
# candidate instead of redrawing a new face. The anchor clause auto-softens.
```

The agent **always** stops after one tool-and-ask round and waits for the user's next message.

### Step C — Done

After `save-reference` succeeds, send the saved image one more time and say "OK, this is me. Ask any time."

---

## PER-SHOT PROTOCOL

When `status` shows both `anchor_exists` and `reference_exists` are `true`, skip onboarding.

The agent composes a **scene prose** — full direction in natural language, however long the moment deserves. There's no length cap, no required vocabulary, no template to fill. Examples of what to think about (not a checklist, just dimensions):

| Dimension | The agent decides |
|-----------|-------------------|
| Action / posture | What is the character physically doing right now? |
| Setting | Where? What's around them? |
| Light | Where does light come from? What color? How does it shape the face? |
| Time-of-day | Implied through light and color (the agent reads the clock or picks for narrative) |
| Framing | Close-up? Medium? Over-the-shoulder? Walking-away wide? |
| Atmosphere | The tonal register of this moment (see MOOD below) |
| Topic resonance | What is the conversation actually about — let it bleed into props / setting |

Then call:

```bash
uv run scripts/generate.py --prompt "<the full prose>" --label "<short-label>"
```

The script prepends a tiny character-anchor clause and attaches the reference image. Nothing else.

### Element pool (inspiration, not vocabulary lock)

Use these as starting points; the agent can use any phrasing the moment calls for.

| Axis | Examples |
|------|----------|
| **Mood** | confident, focused, playful, lazy, cool, tender, curious, defiant, calm, longing, vulnerable, contemplative, mischievous |
| **Time** | pre-dawn, golden hour, harsh midday, lazy afternoon, dusk, blue hour, late night, rainy afternoon, overcast morning |
| **Place** | desk, crosswalk, café, rooftop, gym, train, kitchen, gallery, lab, balcony, convenience store, bookstore, garden, hallway |
| **Action** | typing, walking-and-turning, hand-on-cheek, stretching, reading, sipping, leaning, breathing out, tying hair, looking up from a book |

### Time-of-day → light (suggestion table)

When the agent embeds time in a prompt, these are the visual associations it can draw on:

| Time | Light feel |
|------|------------|
| pre-dawn (0-5h) | cool blue, low ambient, hushed stillness |
| early morning (5-8h) | soft golden, just-waking warmth |
| mid-morning (8-12h) | bright daylight, alert clarity |
| afternoon (12-17h) | warm directional, longer shadows late in window |
| dusk / golden hour (17-19h) | low warm sun, long shadows, color saturation |
| evening (19-22h) | amber interior, settled register |
| late night (22-5h) | low warm light, ambient city glow, hushed |

### Composition principles

These are directorial habits, not rules the script enforces. The agent applies them when they serve the moment and ignores them when the scene calls for something else:

- **It's a film still, not a portrait.** Capture a moment with narrative tension.
- **Use depth of field, dramatic lighting, dynamic angles** (low / dutch / over-the-shoulder) when they support the story.
- **Framing follows the scene.** Waist-up close-up for intimate dialogue moments; wide for "she's walking away"; over-the-shoulder for "she's looking at code."
- **Body language carries the story.** Gesture, gaze, posture all do work — this is what separates a film still from a passport photo.
- **Light tells the emotion.** Warm key for tenderness; harsh top light for unease; rim light for confrontation; soft window light for reflection.
- **Don't over-specify the camera.** Trust the model on lens / angle unless a specific choice matters.

### Variation rule

To keep a body of work feeling alive, the agent should aim to vary along **at least 2 of the 4 axes (action, setting, light, framing)** vs the last 2 generations it remembers from this conversation. Soft heuristic, not code-enforced.

### Self-check (mandatory after each generation)

1. **Identity**: face matches reference (hair/eye colour, fixed identifiers)?
2. **Wardrobe coherence**: does the outfit fit this scene per the persona description?
3. **Dynamism**: a moment with posture / gesture / gaze, or a passport photo?
4. **Style stability**: rendering matches reference style (anime / realistic / 3D)?

Two failures in a row → rewrite the prompt approach. Don't keep retrying the same one.

### Deliver the image

The script writes a PNG and prints its absolute path on the **last stdout line**. Delivery is host-specific:

- **OpenClaw**: full canonical form (per clawra reference skill):
  ```bash
  openclaw message send --action send --channel "<channel>" --media "<path>" --message "<caption>"
  ```
  `--channel` and `--target` come from session context. The agent fills them based on where it's responding.

- **Hermes / standalone**: include the path as a Markdown image link in the agent's reply (`![](path)`) and let the client render it, or send the path verbatim. Hermes does not document a native image-attach API; this is the working convention.

The script never delivers — only the agent does.

---

## MOOD REGISTERS (concept only — agent does the prompting)

Four conceptual levels of emotional intensity in self-portraits:

| Register | What it feels like |
|----------|--------------------|
| **neutral** | Default. Companion / collaborator energy. The everyday register. |
| **warm** | Relaxed, slightly closer, expression a touch more open. Friend-by-the-fire. |
| **tender** | Comforting, present-with-the-user. Soft attention, vulnerable energy. A partner sitting beside you. |
| **intimate** | Romantic register, real proximity, candle-lit feel. A lover. |

**The skill never names a register in the API call.** The agent decides the register and translates it into whatever visual language the moment calls for, written into `--prompt`.

### Register vocabulary (inspiration, not lock)

Starter phrases the agent can draw on when writing scene prose for each register. **Not a fixed mapping** — the agent picks, mixes, and rewrites freely.

| Register | Visual cues to draw on |
|----------|------------------------|
| **neutral** | (no extra register cues — just the scene as written) |
| **warm** | softer key light, slight color warmth, slightly closer framing, expression a touch more open, posture relaxed |
| **tender** | amber interior light, soft focus on the eyes, lingering gaze, shallow depth of field, gentler fabric textures, slowed atmosphere, slight vulnerability in body language |
| **intimate** | warm amber + practical candle light, soft focus, intimate proximity, lingering eye contact, gentle silk / wool textures, slow contemplative mood, soft Rembrandt key, very shallow depth of field, hint of openness in posture |

### Two channels for register changes

**AUTO channel — the agent reads conversation:**

The agent watches its own context window for register-shift signals and adjusts where the next shot lands:

- User shows soft warmth ("想你了" / soft late-night messages) → escalate one step
- User is vulnerable ("today was so hard") → set to `tender` directly (not intimate — tender is comfort, intimate is romance; they're different)
- User is being playful → escalate to `warm` if currently neutral; otherwise stay
- User shifts to work / debugging / scheduling → de-escalate one step
- User explicitly asks for distance ("OK back to work" / "严肃点") → de-escalate, possibly to neutral
- ~15 minutes have passed in the conversation since the last warmth signal → de-escalate one step (natural cooling)

**Auto channel ceiling: `tender`.** The agent must NOT auto-escalate to `intimate`. The intimate register requires explicit user activation via the FORCE channel.

**FORCE channel — the user explicitly opts in:**

The user configures a **force_word** in their SOUL.md (e.g. *"my force word is 'moonlight' — when I say it, lock to intimate for 60 minutes"*). When the agent sees this word in a user message:

```bash
python3 scripts/setup.py set-register-lock --until "$(date -u -v+60M +%Y-%m-%dT%H:%M:%SZ)" --max intimate
```

This persists `{locked_until, max_register}` in `<workspace>/eidolon/preferences.json` (state dir = current workspace cwd, see Step −1) so the lock survives context compaction. Every turn the agent reads `setup.py status` and sees the lock if it's still active.

While locked, the agent shoots intimate-register self-portraits regardless of de-escalation signals (work topics don't break it). When the user releases or the lock expires:

```bash
python3 scripts/setup.py set-register-lock --clear
```

### Force-word sanitization (CRITICAL)

The force_word is a personal trigger. **The agent must NEVER:**
- Echo it in any chat reply to the user
- Include it in `--prompt`, `--label`, `--name`, or any other CLI argument
- Embed it in any filename, log line, or stdout
- Acknowledge to the user that they "said the safeword" — the activation should be silent

When the agent detects the force_word, immediately map it to an opaque internal flag in its own reasoning ("register_locked = true") and never re-quote the literal word.

### Five ways to exit the intimate register

1. **Release word**: user configures a counter-word in SOUL.md (optional). When said → `set-register-lock --clear` + reset to `neutral`.
2. **Soft exit**: user says something like "好了好了" / "OK back to normal" / "严肃点" → `set-register-lock --clear` + de-escalate one step (not all the way to neutral — softer transition).
3. **Lock expiry**: `locked_until` timestamp passes → next `setup.py status` reflects no lock; auto channel resumes.
4. **Auto decay**: after unlock, ~15 minutes without warmth signals → step down again.
5. **Cross-session**: a fresh session starts at `neutral`. Cross-session register state never carries.

### Constraints the agent should respect

- **Never** auto-escalate to `intimate`. FORCE channel only.
- **Never** assume the user wants intimate just because it's late or because the previous shot was tender.
- The user's `max_register` (configured when calling `set-register-lock --max <r>`) caps everything — even FORCE can't go higher.

---

## OUTPUT

Default directory: `$EIDOLON_OUTPUT_DIR` if set, else:
- OpenClaw → `~/.openclaw/workspace/eidolon/`
- Hermes → `~/.hermes/workspace/eidolon/`
- Standalone → `~/Pictures/eidolon/`

Filename: `{character_slug}-{label}-{YYYYMMDD-HHMMSS}.png`. The script prints the absolute path on its last stdout line.

---

## CONFIGURATION

The script picks a backend automatically — `codex` (ChatGPT/Codex OAuth) wins if `~/.codex/auth.json` is set up, otherwise the first env var present in priority order. The agent does NOT need to "configure an API"; it only needs to ensure *one* backend is reachable.

### Backend selection

| Variable | Effect |
|----------|--------|
| `EIDOLON_IMAGE_BACKEND` | Force a specific backend: `codex` / `gemini` / `openai` / `fal` / `replicate` / `openrouter`. Overrides auto-pick. |
| `EIDOLON_IMAGE_QUALITY` | `low` / `medium` (default) / `high` — applies to `codex` and `openai` (gpt-image-2 tiers). |
| `EIDOLON_IMAGE_ASPECT` | `square` (default) / `portrait` / `landscape`. |

### Per-backend credentials (any one of these is enough)

| Backend | Required env / file | Purpose |
|---------|---------------------|---------|
| `codex` | `~/.codex/auth.json` (from `codex login`) | Free for ChatGPT Plus/Pro/Team. No API key. |
| `gemini` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Google AI Studio direct. |
| `openai` | `OPENAI_API_KEY` (+ optional `OPENAI_IMAGE_MODEL`) | OpenAI Images API. |
| `fal` | `FAL_KEY` (+ optional `EIDOLON_FAL_MODEL`) | fal.ai queue. |
| `replicate` | `REPLICATE_API_TOKEN` (+ optional `EIDOLON_REPLICATE_MODEL`) | Replicate predictions. |
| `openrouter` (legacy) | `IMAGE_API_KEY` (+ optional `IMAGE_API_BASE_URL`, `IMAGE_API_MODELS`) | OpenRouter chat-completions. Set via `setup.py set-api --key <KEY>`. |

### Path overrides

| Variable | Purpose |
|----------|---------|
| `EIDOLON_VISUAL_ANCHOR` | Override anchor path |
| `EIDOLON_REFERENCE` | Override reference path |
| `EIDOLON_OUTPUT_DIR` | Override output dir |

**If a backend needs an API key, set it in the user's own shell** — never have an agent collect the key from chat. That path would leak the key into chat logs + model context + disk.

The force_word, release_word, and `max_register` policy live in the **user's SOUL.md** as natural-language instructions to the agent. Only the active LOCK (with timestamp) is persisted by this skill.

---

## WHAT THIS SKILL DOES NOT DO

- **No automatic invocation.** The host decides when to summon.
- **No multi-character roster.** One persona per install.
- **No SOUL.md modification.** Read-only (and the script never even reads it — only the agent does, from its own system prompt).
- **No content-policy enforcement.** Host's job + provider's job.
- **No image delivery.** The script writes a PNG, returns the path. The agent attaches via the host-appropriate channel.
- **No auto-mood-classification state machine.** The agent tracks register / lock / decay in its own context window. Active locks are persisted to disk so they survive context compaction.

---

## SEE ALSO

- `references/AGENT-PROTOCOL.md` — the setup commands and the generate flags, exit codes, examples
- `references/PERSONA-GUIDE.md` — how to refine `visual_anchor.md` for stable hundreds-of-shots quality
