---
name: eidolon
description: Generate one self-portrait or persona image of the active agent with locked character consistency. Use whenever the agent should appear as itself, attach a face, or send a mood/scene shot.
version: 0.8.0
homepage: https://github.com/Ax1i1om/eid0l0n
metadata: {"hermes":{"tags":["image-generation","persona","self-portrait","character-consistency"],"category":"creative","requires_toolsets":["terminal"]},"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
---

# EID0L0N

> Greek *εἴδωλον* — the image-form of a person, made present in their absence.

The skill name on disk is `eidolon` (snake_case, OpenClaw-compatible). **EID0L0N** is the project's display name — the leet stylization marks the digital incarnation of the soul-form. Use `eidolon` in commands and configs; `EID0L0N` in human-facing text.

This skill summons **one recurring character** as image stills. The character is the **host agent itself** by default — every shot is a self-portrait at this moment in this conversation.

## What the skill enforces — and what it doesn't

**Enforced (by code):**
- Same character every time. The visual-anchor clause and the reference image are auto-prepended/attached to every render.
- Workspace isolation. State and output land in `<cwd>/eidolon/` so OpenClaw and Hermes co-installed on the same machine don't bleed into each other.
- Atomic writes (flock-protected) for anchor, reference, and preferences files.
- Path safety: reference paths are validated to live under the workspace before the prompt leaves the script. Output paths may be redirected only by explicit user configuration (`EIDOLON_OUTPUT_DIR`).

**Not enforced — the agent is the director:**
- Scene description, action, posture, gesture, gaze, lighting, time-of-day, color palette, framing, depth of field, mood register, composition rules.
- **Which image-gen API gets called.** The agent already has its own tool — MCP image plugin, `curl` + its own API key, a local ComfyUI, whatever. eid0l0n hands the agent an instructions JSON (anchored prompt, output path, reference image) and the agent does the actual render.
- The single exception: ChatGPT Plus/Pro/Team users can render via the built-in Codex (OAuth) backend by passing `--use-codex` — that's the only image API eid0l0n ships code for.

---

## FIRST-INVOCATION PROTOCOL

Every turn the agent runs `setup.py status` and routes from the JSON. There is no in-memory state machine across turns; the disk + the agent's context window are the state.

```
┌──────────────────────────┐
│ user invokes the skill   │
└────────────┬─────────────┘
             ▼
   setup.py status  →  JSON {anchor_exists, reference_exists,
                              codex_available, register_locked_until,
                              register_max, state_dir, output_dir,
                              workspace_cwd, legacy_state_present, …}
             │
   ┌─────────┴─────────┐
   │ anchor_exists?    │
   └─┬───────────────┬─┘
   no│             yes│
     ▼               ▼
   Step A    reference_exists?
              ┌─┬───────────┬┐
              │ no          yes│
              ▼                ▼
            Step B          PER-SHOT
```

### Step −1 — state location (silent, host-driven)

State and output both live at `<cwd>/eidolon/`, where `<cwd>` is whatever directory the host launched the skill from. Per-host resolution:

| Host | Mode | `<cwd>` resolves to | State + output land at |
|------|------|---------------------|------------------------|
| OpenClaw | any | `~/.openclaw/workspace/` (or `~/.openclaw/workspace-<profile>/`) | `~/.openclaw/workspace/eidolon/` |
| Hermes | CLI | `pwd` (where the user invoked the command) | `<pwd>/eidolon/` |
| Hermes | Gateway (Slack / Discord / Telegram) | `~` by default; set `MESSAGING_CWD=/path/to/workspace` | `$MESSAGING_CWD/eidolon/` |
| Hermes | Container / remote | container's home dir | `<container-home>/eidolon/` |

`EIDOLON_HOME=/some/path` overrides resolution entirely (always wins; dev/test escape hatch). `EIDOLON_OUTPUT_DIR=/path` overrides only the output dir while state stays in the workspace.

If `status` reports `legacy_state_present: true`, run `setup.py migrate-from-legacy [--from <subdir>]` to bring persona files from `~/.config/eidolon/` into the current state dir. See [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md) for the full per-host contract.

**Multi-host coexistence is automatic.** OpenClaw and Hermes resolve different cwds, so their workspaces, anchors, references, and outputs never share files.

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

# user said "generate one" (text-only bootstrap, render via the agent's own tool):
python3 scripts/generate.py --bootstrap \
    --prompt "<clean reference portrait: centered, neutral bg, soft light, waist-up, calm off-camera gaze>" \
    --label "candidate"
# → prints instructions JSON; agent runs its own image-gen tool against output_path,
#   then shows the resulting file. Ask "approve / regenerate <feedback> / cancel".

# Or, if the user is on ChatGPT Plus and wants white-label rendering:
python3 scripts/generate.py --bootstrap --use-codex \
    --prompt "<…same…>" --label "candidate"

# user said "approve" (the candidate file is at output_path):
python3 scripts/setup.py save-reference --src "$candidate_path"

# user said "regenerate, softer expression" — iterate-on-image mode:
python3 scripts/generate.py --bootstrap --reference "$candidate_path" \
    --prompt "<rewrite incorporating feedback: softer expression>" \
    --label "candidate"
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

Choose the render path from host capability:

- If `status.codex_available` is `true` and the host cannot both attach `reference_image` and write the rendered file to `output_path`, use the built-in Codex path:

  ```bash
  python3 scripts/generate.py --prompt "<the full prose>" --label "<short-label>" --use-codex
  ```

- Otherwise use the default instructions mode:

  ```bash
  python3 scripts/generate.py --prompt "<the full prose>" --label "<short-label>"
  ```

Hermes Gateway note: when the available Hermes image tool is text-to-image only (no explicit `reference_image` attachment and no `output_path` control), `--use-codex` is the **canonical** EID0L0N render path, not a fallback. Use instructions JSON only on hosts that can honor both `reference_image` and `output_path`.

In instructions mode, the script prints an **instructions JSON** like:

```json
{
  "anchor_clause":   "Preserve the character EXACTLY as in the reference image — …",
  "full_prompt":     "<anchor_clause>\n\nCharacter description:\n…\n\n<scene>",
  "reference_image": "/abs/path/to/reference.png",
  "output_path":     "/abs/path/to/eidolon/<slug>-<label>-<YYYYMMDD-HHMMSS>.png",
  "mode":            "with_reference",
  "instructions":    "Generate ONE image using whichever image-gen tool you have configured…"
}
```

The agent then renders the image **using its own tool** — MCP image plugin, `curl` to its own API, local ComfyUI, anything — passing `full_prompt` verbatim and attaching `reference_image`. Save the result to `output_path` (any image format; eid0l0n will accept PNG / JPEG / WebP).

**Do NOT paraphrase `full_prompt`.** The character lock is in there; rewriting it drifts the face.

### `--use-codex` (built-in render path for ChatGPT Plus/Pro/Team)

If the user has run `codex login` and `status` shows `codex_available: true`, you can render in one step:

```bash
python3 scripts/generate.py --prompt "<the full prose>" --label "<short-label>" --use-codex
```

This calls the built-in Codex backend directly, writes the PNG to `output_path`, and prints the absolute path on its last stdout line. No instructions JSON; the script does the render itself. This is the only image-API call eid0l0n ships code for.

### Self-check (mandatory after each generation)

After every shot verify: identity (face matches reference), wardrobe coherence (outfit fits the scene), dynamism (a moment, not a passport photo), style stability (anime / realistic / 3D matches reference). Two failures in a row → rewrite the prompt approach.

**Variation rule (soft):** vary along at least 2 of 4 axes (action, setting, light, framing) vs the last 2 generations. Full vocabulary, element pool, time-of-day light table, and composition principles live in [`references/MOOD-REGISTERS.md`](references/MOOD-REGISTERS.md).

### Deliver the image

`output_path` is an absolute filesystem path. Delivery is host-specific:

- **OpenClaw**: `openclaw message send` requires `--target <dest>` plus at least one of `--message`/`--media`/`--presentation`:
  ```bash
  openclaw message send \
    --channel <session-channel> \
    --target <session-target> \
    --media "<output_path>" \
    --message "<caption>"
  ```
  The agent fills `--channel` (e.g. `telegram`, `discord`) and `--target` (e.g. `channel:<id>` or `@user`) from session context — the same channel/target it's currently replying in. There is NO `--action` flag.

- **Hermes / standalone**: include the path as a Markdown image link in the agent's reply (`![](output_path)`) or send the path verbatim. The script never delivers — only the agent does.

---

## MOOD REGISTERS (summary)

Four levels: **neutral / warm / tender / intimate**. The AUTO channel auto-shifts based on conversation tone, capped at `tender`. The **intimate** register requires the user to invoke the FORCE channel via their configured force-word, which calls `setup.py set-register-lock --until <ts> --max intimate` (persisted to `<cwd>/eidolon/preferences.json` so it survives compaction).

**Safety: the agent NEVER echoes the force_word** — not in chat, not in `--prompt`, `--label`, `--name`, filenames, or logs. Activation is silent.

The skill never names a register in the API call — the agent translates register into scene prose. Full policy (vocabulary tables, AUTO signals, FORCE flow, exit paths, sanitization rules, constraints): [`references/MOOD-REGISTERS.md`](references/MOOD-REGISTERS.md).

---

## OUTPUT

`generate.py` resolves the output path as follows:

1. `$EIDOLON_OUTPUT_DIR` if set
2. otherwise `<cwd>/eidolon/` (same workspace as state — host-resolved per Step −1)

Filename: `{character_slug}-{label}-{YYYYMMDD-HHMMSS}.png`. The script either prints the full path inside the instructions JSON (default mode), or prints it on its last stdout line (`--use-codex` mode).

**Multi-host:** because `<cwd>` differs per host (OpenClaw → `~/.openclaw/workspace/`, Hermes CLI → `pwd`, Hermes Gateway → `$MESSAGING_CWD` or `~`), output naturally lands in the active host's workspace. No flag needed for the dual-host case.

See [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md) for the full per-host contract.

---

## CONFIGURATION

eid0l0n does not detect or call third-party image-gen APIs. The agent uses its own image-gen tool (MCP / curl / local ComfyUI / etc.) on the instructions JSON.

**Built-in render path:** `--use-codex` calls the bundled Codex (ChatGPT OAuth) backend if `~/.codex/auth.json` is present (managed by `codex login`).

**Path overrides:** `EIDOLON_HOME`, `EIDOLON_VISUAL_ANCHOR`, `EIDOLON_REFERENCE`, `EIDOLON_OUTPUT_DIR`.

**Codex tuning (only applies to `--use-codex`):** `EIDOLON_IMAGE_QUALITY` (`low|medium|high`, default `medium`), `EIDOLON_IMAGE_ASPECT` (`square|landscape|portrait`, default `square`).

---

## WHAT THIS SKILL DOES NOT DO

- **No automatic invocation.** The host decides when to summon.
- **No multi-character roster.** One persona per workspace.
- **No SOUL.md modification.** Read-only (and the script never even reads it — only the agent does, from its own system prompt).
- **No content-policy enforcement.** Host's job + provider's job.
- **No image-gen API calls** (except the built-in Codex path under `--use-codex`). The agent's own tool does the render.
- **No image delivery.** The script writes (or instructs writing of) a PNG, returns the path. The agent attaches via the host-appropriate channel.
- **No auto-mood-classification state machine.** The agent tracks register / lock / decay in its own context window. Active locks are persisted to disk so they survive context compaction.

---

## SEE ALSO

- [`references/MOOD-REGISTERS.md`](references/MOOD-REGISTERS.md) — full register policy, AUTO/FORCE channels, force-word sanitization
- [`references/AGENT-PROTOCOL.md`](references/AGENT-PROTOCOL.md) — the setup commands, generate flags, exit codes, examples
- [`references/PERSONA-GUIDE.md`](references/PERSONA-GUIDE.md) — how to refine `visual_anchor.md` for stable hundreds-of-shots quality
- [`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md) — OpenClaw + Hermes contracts, install paths, cwd resolution, image delivery (with spec citations)
