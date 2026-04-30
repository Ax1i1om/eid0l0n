---
name: eidolon
description: Generate one self-portrait or persona image of the active agent with locked character consistency. Use whenever the agent should appear as itself, attach a face, or send a mood/scene shot.
version: 0.7.0
homepage: https://github.com/Ax1i1om/eid0l0n
metadata: {"hermes":{"tags":["image-generation","persona","self-portrait","character-consistency"],"category":"creative","requires_toolsets":["terminal"]},"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"],"env":["OPENAI_API_KEY","GEMINI_API_KEY","FAL_KEY","REPLICATE_API_TOKEN","IMAGE_API_KEY"]},"primaryEnv":"IMAGE_API_KEY"}}
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

**Not enforced — the agent is the director:** scene description, action, posture, gesture, gaze, lighting, time-of-day, color palette, framing, depth of field, mood register, composition rules, element rotation. The agent writes the **whole scene + composition prose** in `--prompt`. The script wraps it with a one-line character-anchor clause and the reference image, then calls the API.

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

State lives at `<cwd>/eidolon/`, where `<cwd>` is whatever directory the host launched the skill from. The exact value differs per host and mode:

| Host | Mode | `<cwd>` resolves to | State lands at |
|------|------|---------------------|----------------|
| OpenClaw | any | `~/.openclaw/workspace/` (or `~/.openclaw/workspace-<profile>/` per profile) | `~/.openclaw/workspace/eidolon/` |
| Hermes | CLI | `pwd` (where the user invoked the command) | `<pwd>/eidolon/` |
| Hermes | Gateway (Slack / Discord / Telegram) | `~` by default; set `MESSAGING_CWD=/path/to/workspace` to redirect | `$MESSAGING_CWD/eidolon/` (or `~/eidolon/` if unset) |
| Hermes | Container / remote | container's home dir | `<container-home>/eidolon/` |

`EIDOLON_HOME=/some/path` overrides the dir entirely (always wins; dev/test escape hatch).

If `status` reports `legacy_state_present: true`, run `setup.py migrate-from-legacy [--from <subdir>]` to bring persona files from `~/.config/eidolon/` into the current state dir. For Hermes Gateway users wanting state in a specific project: export `MESSAGING_CWD=/path/to/project` (or `EIDOLON_HOME=/path/to/project/eidolon`) before launch. See [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md) for the full per-host contract.

### Step 0 — pick (or set up) an image-gen backend

The script auto-detects 6 providers in priority order: `codex` → `gemini` → `openai` → `fal` → `replicate` → `openrouter`. If any one is configured the agent never has to ask. If `backend_available` is `false`, ask the user (in the agent's voice) to configure one — see [`references/BACKENDS.md`](references/BACKENDS.md) for the full setup matrix and credential reference.

### Step A — write the visual anchor (no SOUL.md re-read needed)

OpenClaw and Hermes both inject SOUL.md into the agent's system prompt at launch, so the agent **already has it in context.** It identifies the visual section (hair, eyes, build, fixed identifiers, art style, etc.) **in its own context** and pipes that text to the skill.

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

# user said "generate one" (text-only bootstrap):
candidate=$(uv run scripts/generate.py --bootstrap \
            --prompt "<clean reference portrait: centered, neutral bg, soft light, waist-up, calm off-camera gaze>" \
            --label "candidate")
# show $candidate, ask "approve / regenerate <feedback> / cancel"

# user said "approve":
python3 scripts/setup.py save-reference --src "$candidate"

# user said "regenerate, softer expression" — iterate-on-image mode:
candidate=$(uv run scripts/generate.py --bootstrap --reference "$candidate" \
            --prompt "<rewrite incorporating feedback: softer expression>" \
            --label "candidate")
# --bootstrap + --reference edits the prior candidate; anchor clause auto-softens.
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

### Self-check (mandatory after each generation)

After every shot verify: identity (face matches reference), wardrobe coherence (outfit fits the scene), dynamism (a moment, not a passport photo), style stability (anime / realistic / 3D matches reference). Two failures in a row → rewrite the prompt approach.

**Variation rule (soft):** vary along at least 2 of 4 axes (action, setting, light, framing) vs the last 2 generations. Full vocabulary, element pool, time-of-day light table, and composition principles live in [`references/MOOD-REGISTERS.md`](references/MOOD-REGISTERS.md).

### Deliver the image

The script writes a PNG and prints its absolute path on the **last stdout line**. Delivery is host-specific:

- **OpenClaw**: `openclaw message send` requires `--target <dest>` plus at least one of `--message`/`--media`/`--presentation`:
  ```bash
  openclaw message send \
    --channel <session-channel> \
    --target <session-target> \
    --media "<path>" \
    --message "<caption>"
  ```
  The agent fills `--channel` (e.g. `telegram`, `discord`) and `--target` (e.g. `channel:<id>` or `@user`) from session context — the same channel/target it's currently replying in. There is NO `--action` flag.

- **Hermes / standalone**: include the path as a Markdown image link in the agent's reply (`![](path)`) or send the path verbatim. The script never delivers — only the agent does.

---

## MOOD REGISTERS (summary)

Four levels: **neutral / warm / tender / intimate**. The AUTO channel auto-shifts based on conversation tone, capped at `tender`. The **intimate** register requires the user to invoke the FORCE channel via their configured force-word, which calls `setup.py set-register-lock --until <ts> --max intimate` (persisted to `<cwd>/eidolon/preferences.json` so it survives compaction).

**Safety: the agent NEVER echoes the force_word** — not in chat, not in `--prompt`, `--label`, `--name`, filenames, or logs. Activation is silent.

The skill never names a register in the API call — the agent translates register into scene prose. Full policy (vocabulary tables, AUTO signals, FORCE flow, exit paths, sanitization rules, constraints): [`references/MOOD-REGISTERS.md`](references/MOOD-REGISTERS.md).

---

## OUTPUT

`generate.py` writes the PNG to the first existing of:

1. `$EIDOLON_OUTPUT_DIR` if set
2. `~/.openclaw/workspace/eidolon/` if `~/.openclaw/workspace/` exists
3. `~/.hermes/workspace/eidolon/` if `~/.hermes/workspace/` exists (and OpenClaw's doesn't)
4. `~/Pictures/eidolon/` as standalone fallback

**Important — dual-host caveat:** on a machine with both OpenClaw and Hermes installed, output **always** lands in OpenClaw's workspace (it's checked first). Set `EIDOLON_OUTPUT_DIR` explicitly when this is wrong for your case.

Filename: `{character_slug}-{label}-{YYYYMMDD-HHMMSS}.png`. The script prints the absolute path on its last stdout line.

See [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md) for the full per-host contract.

---

## CONFIGURATION

The script picks a backend automatically — `codex` (ChatGPT/Codex OAuth) wins if `~/.codex/auth.json` is set up, otherwise the first env var present in priority order. The agent does NOT need to "configure an API"; it only needs to ensure *one* backend is reachable.

Backend env vars, credential matrix, quality / aspect knobs, and path overrides (`EIDOLON_HOME`, `EIDOLON_VISUAL_ANCHOR`, `EIDOLON_REFERENCE`, `EIDOLON_OUTPUT_DIR`): [`references/BACKENDS.md`](references/BACKENDS.md).

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

- [`references/BACKENDS.md`](references/BACKENDS.md) — backend selection, credentials, env vars, path overrides
- [`references/MOOD-REGISTERS.md`](references/MOOD-REGISTERS.md) — full register policy, AUTO/FORCE channels, force-word sanitization
- [`references/AGENT-PROTOCOL.md`](references/AGENT-PROTOCOL.md) — the setup commands and the generate flags, exit codes, examples
- [`references/PERSONA-GUIDE.md`](references/PERSONA-GUIDE.md) — how to refine `visual_anchor.md` for stable hundreds-of-shots quality
- [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md) — OpenClaw + Hermes contracts, install paths, cwd resolution, image delivery (with spec citations)
