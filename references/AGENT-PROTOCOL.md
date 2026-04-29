# Agent protocol — CLI reference

eidolon exposes **7 setup commands** and 1 generation script. Mood / register / lock / decay logic is **not** in the CLI as a state machine — the agent tracks AUTO-channel transitions in its own context window per SKILL.md prose. The one exception is the FORCE-channel register lock, which is persisted to `preferences.json` so it survives context compaction (see `set-register-lock`). Code only enforces character consistency.

State lives at `<workspace>/eidolon/`, where `<workspace>` is the host's current working directory. OpenClaw and Hermes both invoke skills with `cwd = active workspace` — we trust that contract instead of inferring host or persona. Switching workspace = switching state, automatically. `EIDOLON_HOME=/some/path` overrides the dir entirely (dev/test escape hatch). Run `setup.py migrate-from-legacy [--from <subdir>]` to bring forward state from the legacy `~/.config/eidolon/` tree.

## Backend auto-detection

The script auto-picks one of 6 image-gen backends in priority order. Run `setup.py detect-backends [--json]` to enumerate; force a specific one with `EIDOLON_IMAGE_BACKEND=<name>` or `--backend <name>`.

| # | Backend | What it needs | Notes |
|---|---------|---------------|-------|
| 1 | `codex` | `~/.codex/auth.json` (from `codex login`) | **Free** for ChatGPT Plus/Pro/Team. Routes through Codex Responses API → `image_generation` tool. |
| 2 | `gemini` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Google AI Studio direct, free tier available. |
| 3 | `openai` | `OPENAI_API_KEY` (+ optional `OPENAI_IMAGE_MODEL`) | OpenAI Images API, gpt-image-2. |
| 4 | `fal` | `FAL_KEY` (+ optional `EIDOLON_FAL_MODEL`) | fal.ai queue API. |
| 5 | `replicate` | `REPLICATE_API_TOKEN` (+ optional `EIDOLON_REPLICATE_MODEL`) | Replicate predictions. |
| 6 | `openrouter` | `IMAGE_API_KEY` (legacy — set via `setup.py set-api`) | OpenRouter chat-completions. |

---

## State machine — every turn

```
                    ┌─────────────────┐
                    │ skill invoked   │
                    └────────┬────────┘
                             ▼
                  setup.py status   →  JSON {anchor_exists, reference_exists, api_key_set}
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
                     STOP                       show + ask, STOP
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
  "api_key_set": false,
  "anchor_path": "",
  "reference_path": "",
  "register_locked_until": "",
  "register_max": "",
  "backend_available": true,
  "backends_available": ["codex"],
  "backend_selected": "codex",
  "backend_forced": false,
  "state_dir": "/path/to/workspace/eidolon",
  "workspace_cwd": "/path/to/workspace",
  "legacy_state_present": false,
  "legacy_config_dir": ""
}
```

Run this **first** every turn. Route from the JSON. Note: `api_key_set` is now informational only (it tracks the legacy `IMAGE_API_KEY`); the agent should branch on `backend_available` instead. If `legacy_state_present` is `true`, persona files exist under the legacy `~/.config/eidolon/` tree — call `migrate-from-legacy [--from <subdir>]` to bring them forward into the current workspace's state dir.

## `setup.py detect-backends [--json]`

Lists which of the 6 image-gen backends are reachable. Use `--json` for machine-readable output (the agent reads `selected` to know what auto-pick chose, and `available` for alternatives).

```bash
python3 scripts/setup.py detect-backends --json
# {
#   "selected": "codex",
#   "forced": false,
#   "available": ["codex", "gemini"],
#   "details": {
#     "codex":      {"available": true, "credit": "free for ChatGPT Plus/Pro/Team", "models": ["gpt-image-2"]},
#     "gemini":     {"available": true, "credit": "free tier available", "models": ["gemini-2.5-flash-image-preview"]},
#     "openai":     {"available": false, "missing": "OPENAI_API_KEY env var"},
#     ...
#   }
# }
```

---

## `setup.py save-anchor [--text TEXT | --from-file FILE] [--name NAME]`

Writes `<workspace>/eidolon/visual_anchor.md` from agent-supplied text. State dir = `<cwd>/eidolon/`; set `EIDOLON_HOME` to override. Three input modes:

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

Atomically (tmp + replace) copies an image to `<workspace>/eidolon/reference.<ext>` (mode 644). Validates `.png|.jpg|.jpeg|.webp`. Updates the `reference:` header in `visual_anchor.md`. Use both for user-provided paths AND for promoting an approved candidate.

---

## `setup.py set-api --key KEY [--base-url URL] [--models CSV]`

Writes `<workspace>/eidolon/env` (mode 600) for the **`openrouter`** backend specifically. Other backends use shell env vars (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `FAL_KEY`, `REPLICATE_API_TOKEN`) or no key at all (`codex` reads `~/.codex/auth.json`).

**Run this in the user's own shell, not via an agent that received the key in chat.** That path leaks the key into chat logs + model context + disk.

If any other backend is reachable (e.g. `codex login` already done, or `GEMINI_API_KEY` exported), this command is unnecessary.

---

## `setup.py set-register-lock {--clear | --until ISO --max R}`

Persists FORCE-channel register lock to `<workspace>/eidolon/preferences.json` (mode 600). Schema:

```json
{
  "locked_until": "2026-04-29T18:30:00Z",
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
#   "copied":  ["visual_anchor.md", "reference.jpeg", "preferences.json", "env"],
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
--backend NAME                 # force backend (codex|gemini|openai|fal|replicate|openrouter)
--list-scenes                  # print scene shortcut list
--list-backends [--json]       # print backend detection results
--doctor                       # state diagnostic (includes backend table)
```

The script:
1. Loads `visual_anchor.md` (character description text)
2. Loads the reference image (unless `--bootstrap`)
3. Sends to API: `[reference image] + [character anchor clause + persona text + your prompt]`
4. Saves PNG, prints absolute path on its **last stdout line**

That's it. No context flags, no register flag, no overlay flag, no time-of-day auto-injection. The agent embeds whatever it wants directly in `--prompt`.

`--state` is a **shortcut** for common scene starters (defined in `generate.py`'s `SCENES` dict). The agent can use it for quick recurring shots, OR write its own prose with `--prompt` for full creative control. Both modes coexist by design.

---

## Onboarding pseudocode (the agent each turn)

```python
state = json.parse(setup.py status)

if not state.backend_available:
    say (
        "I need a way to make images. Pick one (any one is enough):\n"
        "  • codex      run `codex login` once — FREE if you have ChatGPT Plus/Pro/Team\n"
        "  • gemini     export GEMINI_API_KEY=...\n"
        "  • openai     export OPENAI_API_KEY=...\n"
        "  • fal        export FAL_KEY=...\n"
        "  • replicate  export REPLICATE_API_TOKEN=...\n"
        "  • openrouter setup.py set-api --key <KEY>\n"
        "Run that in your own shell — never paste the key here."
    )
    STOP_TURN

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
        cand = generate.py --bootstrap --prompt "<reference-portrait prose>" --label cand
        deliver_image(cand)
        say "Approve / regenerate <feedback> / cancel?"
        STOP_TURN
    elif user_reply contains "approve":
        setup.py save-reference --src <last_cand_path>
        say "Locked in."
        STOP_TURN
    elif user_reply contains "regenerate":
        cand = generate.py --bootstrap --reference <last_cand> \
                           --prompt "<re-write of reference-portrait prose with feedback>" \
                           --label cand
        deliver_image(cand)
        STOP_TURN

# fully onboarded — proceed to per-shot
```

The agent must remember `<last_cand_path>` between turns. On OpenClaw / Hermes, the candidate path appears in the agent's previous reply, so it's recoverable from message history.

---

## Per-shot, after onboarding

The agent composes a complete scene prose (any length, any specificity) and calls:

```bash
uv run scripts/generate.py --prompt "<the agent's scene>" --label "<short>"
```

For quick recurring scenes:

```bash
uv run scripts/generate.py --state idle --label idle    # uses built-in shortcut
```

The reference image is auto-attached. The character anchor is auto-prepended. Composition / mood / register / lighting / framing — all in the agent's `--prompt` text per SKILL.md guidance.

---

## Image delivery (the script never delivers)

The script writes a PNG, prints the path. Delivery to the user is the agent's job:

- **OpenClaw**: `openclaw message send --media "<path>" --text "<caption>"`
- **Hermes / standalone**: `![](<path>)` in the agent's reply, or print the path verbatim.

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Operation failed (missing file, API auth, etc.) |
| 2 | CLI usage error |

stderr `error:` lines are user-displayable; `warning:` lines are advisory.
