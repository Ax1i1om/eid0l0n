# Migration from 0.8.x

0.9.0 is a structural rewrite. There is no migration script — your
agent does the migration in conversation.

## If you're on 0.8.x

Your state is already at `<cwd>/eidolon/`. The only change you need:

1. The `preferences.json` file in your state dir held the register
   lock state. 0.9.0 removes the register lock mechanism — the
   intimate channel is now character-driven (see
   `references/intimate-channel.md`). Delete `preferences.json`:

   ```bash
   rm -f <cwd>/eidolon/preferences.json
   ```

2. Ask your agent to create `at-hand.md` and `relationship.md` (the
   two new files). It can do this from scratch — they hold timezone
   / rhythm / the word between you (if any) and milestones, not
   anything migrated from 0.8.

3. If your old reference image isn't `reference.png` (e.g. you have
   `reference.jpeg` from 0.8), the new flow expects only one extension.
   Either keep using JPEG (cp the candidate as `reference.jpeg`) or
   `rm <cwd>/eidolon/reference.{jpeg,jpg,webp}` before saving a new PNG.

## If you're on 0.7.x

Your state is at `~/.config/eidolon/<subdir>/`. Ask your agent:

> "Migrate my eidolon state from `~/.config/eidolon/` to `<cwd>/eidolon/`."

Your agent will read the old anchor, write the new one with the
reference path patched, and copy the reference image. No script
needed.

## If you used `--use-codex`

Same as before. `codex login`, then your agent calls eidolon.py
which calls codex_backend.generate() under the hood. The protocol
is unchanged.

## What's gone in 0.9.0

- `install.sh` — your agent installs from the repo link directly
- `setup.py` — replaced by agent using Read/Write/Bash directly
- `setup.py status` JSON dump — agent reads the actual files
- `setup.py migrate-from-legacy` — see above, agent does it in chat
- `preferences.json` + register lock — replaced by character-driven
  intimate channel
- `--use-codex` flag — eidolon.py auto-uses codex_backend (no flag
  needed; it's the only built-in path)
- 12 built-in SCENES — the agent writes its own scenes
- silent fallback to assets/persona.example.md — now sys.exits

## What's added

- `at-hand.md` — timezone, rhythm, the word between you (if any)
- `relationship.md` — milestones, things you've shared
- `anchor_history.md` — visual evolution biography
- `references/photo-spec.md` — reference photo aesthetics
- `references/scene-craft.md` — cinematographic prose principles
- `references/intimate-channel.md` — the quieter layer
