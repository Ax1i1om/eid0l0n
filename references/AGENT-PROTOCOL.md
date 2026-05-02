# Agent protocol — CLI reference

eidolon exposes **5 setup commands** and 1 generation script. Mood / register / lock / decay logic is **not** in the CLI as a state machine — the agent tracks AUTO-channel transitions in its own context window per SKILL.md prose. The one exception is the FORCE-channel register lock, which is persisted to `preferences.json` so it survives context compaction (see `set-register-lock`). Code only enforces character consistency + workspace isolation.

State lives at `<cwd>/eidolon/`, where `<cwd>` is the host's current working directory. The exact value differs per host and mode:

| Host | Mode | `<cwd>` resolves to |
|------|------|---------------------|
| OpenClaw | any | `~/.openclaw/workspace/` (or `~/.openclaw/workspace-<profile>/`) |
| Hermes | CLI | `pwd` (where the user invoked the command) |
| Hermes | Gateway (Slack / Discord / Telegram) | `~` by default; `MESSAGING_CWD=/path` overrides |
| Hermes | Container / remote | container's home dir |

`EIDOLON_HOME=/some/path` overrides the dir entirely (always wins; dev/test escape hatch). Run `setup.py migrate-from-legacy [--from <subdir>]` to bring forward state from the legacy `~/.config/eidolon/` tree. See [`docs/HOST-COMPATIBILITY.md`](../docs/HOST-COMPATIBILITY.md) for full per-host contract with spec citations.

## Image generation

eid0l0n does not ship a backend selector. Two paths exist:

| Path | What it is | When |
|------|------------|------|
| **Instructions mode (default)** | `generate.py` prints a JSON blob with `full_prompt`, `reference_image`, `output_path`, `mode`, `instructions`. The agent renders the image using its own image-gen tool (MCP image plugin / `curl` + agent's API key / local ComfyUI / etc.) and writes to `output_path`. | Always available. The agent already knows how to call its own image API; eid0l0n just provides the anchored prompt. |
| **`--use-codex`** | Built-in Codex (ChatGPT OAuth) backend. Reads `~/.codex/auth.json` (from `codex login`), calls Codex Responses API → `image_generation` tool, writes the PNG to `output_path`, prints the path on the last stdout line. | ChatGPT Plus / Pro / Team users who want zero-config rendering. |

The only image API eid0l0n ships code for is Codex — because its OAuth + JWT + tool-call protocol cannot be reasonably re-derived by an agent on its own. Every other provider (GPT Image / Nano Banana / Grok / fal / Replicate / MiniMax / 通义万相 / OpenAI-compatible relays / ComfyUI) is the agent's tool's job.

---

## State machine — every turn

```
                    ┌─────────────────┐
                    │ skill invoked   │
                    └────────┬────────┘
                             ▼
                  setup.py status   →  JSON {anchor_exists, reference_exists,
                                             codex_available, register_*, …}
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
   anchor_exists: false           anchor_exists: true
              │                             │
              ▼                             ▼
       save-anchor              reference_exists: false
       (paste SOUL text)                    │
       STOP                                 ▼
                            ask user about reference, STOP
                                            │
                            ┌───────────────┴───────────────┐
                            ▼                               ▼
                      user gives path             user says "generate"
                            │                               │
                            ▼                               ▼
                     save-reference             generate.py --bootstrap
                     STOP                       (instructions JSON OR --use-codex)
                                                show + ask, STOP
                                                            │
                                            ┌───────────────┼─────────────┐
                                            ▼               ▼             ▼
                                       approve      regenerate hint    cancel
                                            │           (loop)            │
                                     save-reference                       └─ STOP
                                            │
                                            ▼
                                  reference_exists: true → PER-SHOT
```

---

## `setup.py status`

Read-only state dump. Returns:

```json
{
  "anchor_exists": false,
  "reference_exists": false,
  "anchor_path": "",
  "reference_path": "",
  "register_locked_until": "",
  "register_max": "",
  "codex_available": true,
  "codex_credit": "free for ChatGPT Plus/Pro/Team",
  "codex_missing": "",
  "state_dir": "/path/to/workspace/eidolon",
  "output_dir": "/path/to/workspace/eidolon",
  "workspace_cwd": "/path/to/workspace",
  "legacy_state_present": false,
  "legacy_config_dir": ""
}
```

Run this **first** every turn. Route from the JSON.

- `anchor_exists` / `reference_exists` drive the onboarding state machine above.
- `codex_available` is `true` iff `~/.codex/auth.json` exists with a valid (non-expired) token. When `true`, the agent can use `generate.py --use-codex` for zero-config rendering. When `false`, the agent must use its own image-gen tool against the instructions JSON from default-mode `generate.py`.
- `register_locked_until` / `register_max` reflect any active FORCE-channel lock — the agent honors this regardless of conversation drift until the lock expires.
- `legacy_state_present` is `true` iff persona files exist under `~/.config/eidolon/` (a pre-cwd-migration layout). When set, call `migrate-from-legacy [--from <subdir>]` to bring them forward into the current workspace's state dir.
- `state_dir` and `output_dir` should be identical by default (both at `<cwd>/eidolon/`); they diverge only if the user has set `EIDOLON_OUTPUT_DIR`.
- `workspace_cwd` reports the actual cwd the script was invoked from — this varies per host/mode (see [`docs/HOST-COMPATIBILITY.md`](../docs/HOST-COMPATIBILITY.md)). On Hermes Gateway it may be `~` unless `MESSAGING_CWD` is configured.

---

## `setup.py save-anchor [--text TEXT | --from-file FILE] [--name NAME]`

Writes `<cwd>/eidolon/visual_anchor.md` from agent-supplied text. State dir = `<cwd>/eidolon/`; set `EIDOLON_HOME` to override. Three input modes:

```bash
# Recommended (avoids heredoc-EOF collision with embedded "EOF" markers in SOUL text):
# Use the Write tool to drop text into a temp file, then:
python3 scripts/setup.py save-anchor --from-file /tmp/anchor.txt --name "<character name>"

# Short text, no embedded EOF marker — heredoc with custom delimiter:
cat <<'EID0L0N_END' | python3 scripts/setup.py save-anchor --name "<character name>"
[the agent paraphrases the visual section from its own SOUL.md context here]
EID0L0N_END

# Direct (small inline text):
python3 scripts/setup.py save-anchor --text "silver-white short hair, pale grey eyes, slim build" --name "Aria"
```

`--name <NAME>` writes a `# Visual Anchor — <name>` heading so generated filenames use the character's slug. Without `--name`, slug defaults to `character`.

Why text-pipe and not "extract from SOUL.md path": SOUL.md is **already in the agent's system prompt** on both OpenClaw and Hermes. Having a Python script grep the file is strictly worse than asking the agent (which has full natural-language understanding of its own SOUL) to extract the visual bits.

The original SOUL.md is **never** modified by this skill.

---

## `setup.py save-reference --src PATH`

Atomically (tmp + replace) copies an image to `<cwd>/eidolon/reference.<ext>` (mode 644). Validates `.png|.jpg|.jpeg|.webp`. Updates the `reference:` header in `visual_anchor.md`. Use both for user-provided paths AND for promoting an approved candidate.

---

## `setup.py set-register-lock {--clear | --until ISO --max R}`

Persists FORCE-channel register lock to `<cwd>/eidolon/preferences.json` (mode 600). Schema:

```json
{
  "locked_until": "<ISO-8601 timestamp, e.g. 2026-05-01T18:30:00Z>",
  "max_register": "intimate"
}
```

When the user says their configured force_word, the agent calls:

```bash
python3 scripts/setup.py set-register-lock \
  --until "$(date -u -v+60M +%Y-%m-%dT%H:%M:%SZ)" \
  --max intimate
```

This survives context compaction. Every turn the agent reads `setup.py status`, sees `register_locked_until` and `register_max`, and shoots in that register regardless of de-escalation signals (work topics, etc.) until the lock expires or is cleared.

To clear:

```bash
python3 scripts/setup.py set-register-lock --clear
```

**The agent must NEVER echo the force_word** in any chat reply, `--prompt`, `--label`, `--name`, filename, or stdout. When detected, immediately map to an opaque internal flag and never re-quote the literal word.

The user's `max_register` policy (`tender` / `intimate` cap) and force/release words live in **the user's SOUL.md** as natural-language instructions, not in any eidolon config file.

---

## `setup.py migrate-from-legacy [--from <subdir>] [--force] [--purge]`

Copies persona state from the legacy `~/.config/eidolon/` tree (flat root or any subdir) into the current workspace's state dir (`<cwd>/eidolon/`). Used once per workspace the first time `status` reports `legacy_state_present: true`.

If the legacy root has `visual_anchor.md` directly, it migrates that. Otherwise it auto-picks if exactly one subdir contains an anchor; if multiple subdirs do, pass `--from <subdir>` to choose.

```bash
python3 scripts/setup.py migrate-from-legacy
# {
#   "from":  "/Users/<user>/.config/eidolon",
#   "to":    "/path/to/workspace/eidolon",
#   "copied":  ["visual_anchor.md", "reference.jpeg", "preferences.json"],
#   "skipped": [],
#   "purged_legacy": false
# }
```

Non-destructive by default: legacy files stay in place, and any pre-existing target file is skipped. `--force` overwrites; `--purge` deletes the legacy originals after a successful copy. The anchor's `reference:` header is rewritten to the new path.

Refuses to run if the target dir equals the legacy root.

---

## `generate.py` — 9 flags

```
--prompt P --label L           # write your own scene prose (primary mode)
--state KEY --label L          # use a built-in scene shortcut (see --list-scenes)
--bootstrap                    # for the initial reference portrait, no input image needed
--reference PATH               # override the saved reference image for this call
--anchor PATH                  # override visual_anchor.md for this call
--use-codex                    # render via the built-in Codex backend (ChatGPT OAuth)
                                 instead of emitting instructions JSON
--list-scenes                  # print scene shortcut list
--doctor                       # state diagnostic (anchor / reference / codex / output dir)
```

### Default mode: instructions JSON

The script:
1. Loads `visual_anchor.md` (character description text).
2. Resolves the reference image (unless `--bootstrap`).
3. Builds the anchor clause + full prompt + output path.
4. Validates that reference paths live under the workspace. Output paths may intentionally leave the workspace only when the user set `EIDOLON_OUTPUT_DIR`.
5. Prints a JSON blob to stdout:

```json
{
  "anchor_clause":   "Preserve the character EXACTLY as in the reference image — …",
  "full_prompt":     "<anchor_clause>\n\nCharacter description:\n…\n\n<scene>",
  "reference_image": "/abs/path/to/eidolon/reference.png",
  "output_path":     "/abs/path/to/eidolon/<slug>-<label>-<YYYYMMDD-HHMMSS>.png",
  "mode":            "bootstrap | with_reference | iterate_on_reference",
  "instructions":    "Generate ONE image using whichever image-gen tool you have configured…"
}
```

The agent then renders the image **using its own tool** — passing `full_prompt` verbatim and attaching `reference_image` — and writes the result to `output_path`. eid0l0n accepts PNG / JPEG / WebP.

**Do NOT paraphrase `full_prompt`.** The character lock is in there.

### `--use-codex` mode

When the user has `codex login`'d (`status.codex_available == true`) and wants zero-config rendering, pass `--use-codex`. The script then:

1. Does steps 1-4 above.
2. Calls the built-in Codex backend (`scripts/codex_backend.py`) with `(full_prompt, reference_image, output_path)`.
3. Codex retries up to 3 times with exponential backoff on transient errors.
4. The PNG is saved atomically to `output_path`.
5. The script prints the absolute output path on its **last stdout line** (no JSON in this mode).

### Common rules

- No context flags, no register flag, no overlay flag, no time-of-day auto-injection. The agent embeds whatever it wants directly in `--prompt`.
- `--state` is a **shortcut** for common scene starters (defined in `generate.py`'s `SCENES` dict). The agent can use it for quick recurring shots, OR write its own prose with `--prompt` for full creative control. Both modes coexist by design.

---

## Onboarding pseudocode (the agent each turn)

```python
state = json.parse(setup.py status)

if not state.anchor_exists:
    visual_text = extract_visual_section_from_my_own_SOUL_context()
    pipe(visual_text → setup.py save-anchor)
    say "Anchor saved. Do you have a reference image of me, or should I generate one?"
    STOP_TURN

if not state.reference_exists:
    user_reply = the_user_just_said
    if user_reply is a path:
        setup.py save-reference --src <path>
        say "Saved. This is me from now on."
        STOP_TURN
    elif user_reply contains "generate":
        # Two render paths:
        if state.codex_available:
            generate.py --bootstrap --use-codex \
                        --prompt "<reference-portrait prose>" --label cand
            # ↑ writes PNG; cand_path is on the last stdout line
        else:
            instr = generate.py --bootstrap \
                                --prompt "<reference-portrait prose>" --label cand
            # ↑ prints JSON; agent renders via own image-gen tool to instr.output_path
        deliver_image(cand_path)
        say "Approve / regenerate <feedback> / cancel?"
        STOP_TURN
    elif user_reply contains "approve":
        setup.py save-reference --src <last_cand_path>
        say "Locked in."
        STOP_TURN
    elif user_reply contains "regenerate":
        # Same branching as 'generate' above, plus --reference <last_cand>
        # for iterate-on-image mode.
        STOP_TURN

# fully onboarded — proceed to per-shot
```

The agent must remember `<last_cand_path>` between turns. On OpenClaw / Hermes, the candidate path appears in the agent's previous reply, so it's recoverable from message history.

---

## Per-shot, after onboarding

The agent composes a complete scene prose (any length, any specificity) and chooses the render path from host capability:

```bash
# Host can attach reference_image and write output_path itself:
uv run scripts/generate.py --prompt "<the agent's scene>" --label "<short>"

# Host cannot do both, and Codex is available:
uv run scripts/generate.py --prompt "<the agent's scene>" --label "<short>" --use-codex
```

Hermes gateway example: if the available image tool is text-only or cannot save to the requested `output_path`, prefer `--use-codex` whenever `setup.py status` reports `codex_available: true`.

For quick recurring scenes:

```bash
uv run scripts/generate.py --state idle --label idle    # uses built-in shortcut
```

The reference image is auto-attached. The character anchor is auto-prepended. Composition / mood / register / lighting / framing — all in the agent's `--prompt` text per SKILL.md guidance.

---

## Image delivery (the script never delivers)

The script writes a PNG, prints the path. Delivery to the user is the agent's job:

- **OpenClaw**: `openclaw message send` requires `--target <dest>` plus at least one of `--message`/`--media`/`--presentation`:
  ```bash
  openclaw message send \
    --channel <session-channel> \
    --target <session-target> \
    --media "<path>" \
    --message "<caption>"
  ```
  The agent fills `--channel` (e.g. `telegram`/`discord`) and `--target` (e.g. `channel:<id>` or `@user`) from session context. There is NO `--action` flag (the verb is the subcommand `send` itself; siblings: `broadcast`, `poll`, `react`).
- **Hermes / standalone**: `![](<path>)` in the agent's reply, or print the path verbatim.

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Operation failed (missing file, API auth, etc.) |
| 2 | CLI usage error |

stderr `error:` lines are user-displayable; `warning:` lines are advisory.
