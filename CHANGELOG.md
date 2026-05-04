# Changelog

All notable changes to eid0l0n. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: [SemVer](https://semver.org/).

## [0.9.0] — 2026-05-03

The biggest rewrite since 0.8.0. ~62% code removed (1336 → ~504 lines).

The frame: the agent IS the character. Code only does what code must
(protocol reverse-engineering, string concat, file IO). Everything
character-shaped — onboarding conversation, scene prose, error
phrasing, the layer changes — is the agent's, in character.

### Added
- `scripts/eidolon.py` — minimal entry (~101 lines), reads scene prose
  from stdin, prepends anchor clause + character description, calls
  codex_backend.
- `<state>/eidolon/at-hand.md` — timezone, picture rhythm, the word
  between you (if any).
- `<state>/eidolon/relationship.md` — milestones, things shared.
- `<state>/eidolon/anchor_history.md` — visual evolution biography.
- `references/onboarding-flow.md` — collaborative first meeting.
- `references/photo-spec.md` — reference photo aesthetics + visual
  anchor authoring guide.
- `references/scene-craft.md` — cinematographic prose principles.
- `references/intimate-channel.md` — the quieter layer + the word
  between you.
- `docs/MIGRATION-FROM-0.8.md` — upgrade path.

### Changed
- SKILL.md fully rewritten as character-voice instructions to the
  agent itself, second-person.
- `anchor_clause` rewritten in anatomical terms (bone structure,
  inter-ocular distance, line of nose) — diffusion models recognize
  these features. "EXACTLY" was wrong vocabulary.
- `state.py` slimmed to ~127 lines: paths, parse_anchor, atomic
  write, path safety, legacy detection.
- `codex_backend.py` patched + simplified to ~276 lines.
- `gpt-image-2` is the documented model on the OpenAI path
  (codex_backend already used it).

### Removed
- `scripts/install.sh` — agent self-installs via repo link.
- `scripts/setup.py` — agent uses Read/Write/Bash directly.
- `scripts/generate.py` — replaced by minimal eidolon.py.
- `scripts/test_frontmatter.py` — covered by ad-hoc validation.
- `references/AGENT-PROTOCOL.md` — content folded into SKILL.md +
  references/onboarding-flow.md.
- `references/MOOD-REGISTERS.md` — register lock mechanism removed;
  intimate channel is now character-driven (see intimate-channel.md).
- `references/PERSONA-GUIDE.md` — content folded into photo-spec.md.
- `assets/persona.example.md` — silent fallback removed; missing
  anchor now hard-fails.
- `preferences.json` — register lock mechanism gone.
- `setup.py status` and the JSON dump — agent reads the actual files.
- 12 built-in SCENES — the agent writes its own scenes.
- All `--use-codex` references — eidolon.py auto-uses codex_backend
  as the only built-in path.

### Security
- `codex_backend._read_token` now hard-fails on JWT decode error
  (was: silent fallthrough — could leak expired tokens).
- `codex_backend.generate` validates reference image extension
  whitelist (was: any suffix could be sent as data URI).
- `codex_backend._read_token` now caps `auth.json` size at 1MB.
- `codex_backend.generate` rejects reference images > 20MB.
- Retry backoff in codex_backend now includes jitter.
- `state.validate_reference_path` now expands `~` before resolving
  (was: tilde paths could bypass the workspace check).
- `state.parse_anchor` rejects multiple `reference:` headers and
  values containing null bytes or > 1024 chars.
- `state.atomic_write_text` uses PID-unique tmp names + try/except
  cleanup (no leftover .tmp files on failure).
- `state.legacy_state_present` fails closed on PermissionError
  (was: would crash entire skill on unreadable ~/.config/).

### Fixed
- `codex_backend` partial_image events no longer overwrite the final
  done event's image (was: could return incomplete image).

### Migration
See `docs/MIGRATION-FROM-0.8.md`. No script — your agent does it in
conversation.

## [0.8.0] — 2026-05-01

The big turn: **eid0l0n no longer ships image-API code (with one exception).** The original design hard-coded six image-gen backends (Codex, Gemini, OpenAI, fal, Replicate, OpenRouter). 0.8.0 deletes five of them. Your agent already has a tool to call its own configured image API — eid0l0n now hands the agent an instructions JSON (anchored prompt + reference image + output path) and gets out of the way.

The one exception: ChatGPT Plus / Pro / Team users can render via the bundled Codex (OAuth) backend with `--use-codex`. Codex's protocol (JWT + tool-call streaming) can't be reasonably re-derived by an agent on its own, so it stays in code.

### Added
- `scripts/codex_backend.py` — extracted Codex (ChatGPT OAuth) backend as a self-contained module.
- `generate.py --use-codex` — render via the built-in Codex backend (replaces auto-detection).
- `setup.py status` JSON: `codex_available`, `codex_credit`, `codex_missing`, `output_dir`.
- `state.atomic_write_text()` — shared tmp-then-rename helper. Anchor and prefs writes now actually atomic (matching the docs).
- Symmetric "OpenClaw active with Hermes also present" regression test alongside the existing Hermes-priority test.
- Path safety: `generate.py` rejects `reference:` paths that escape the workspace (defends against `~/.aws/credentials` exfil via poisoned anchor).
- Test for instructions-mode JSON contract.
- `migrate-from-legacy` warns on legacy `env` files instead of silently dropping them.

### Changed
- **`generate.py` default mode is now "instructions JSON".** Prints `{anchor_clause, full_prompt, reference_image, output_path, mode, instructions}` for the agent to consume; the agent renders via its own image-gen tool. No outbound HTTP from the script unless `--use-codex`.
- README pitch: from "auto-detects 6 providers" to "your agent already knows how to generate images; eid0l0n just locks the character." Explicit support story for AiHubMix / OneAPI / OpenAI-compatible relays / MiniMax / 通义万相 / local ComfyUI.
- SKILL.md FIRST-INVOCATION PROTOCOL rewritten to two-path flow (instructions mode default, `--use-codex` for ChatGPT Plus).
- HOST-COMPATIBILITY.md output-dir resolution doc aligned with code (cwd-based, not the old probe-OpenClaw-then-Hermes-then-Pictures order).
- `pyproject.toml` populated with proper `[project]` metadata.

### Removed
- `scripts/backends.py` (~500 lines).
- `setup.py detect-backends` subcommand.
- `setup.py set-api` subcommand.
- `generate.py --backend NAME` flag.
- `generate.py --list-backends` flag.
- `EIDOLON_IMAGE_BACKEND` env var.
- `IMAGE_API_KEY`, `IMAGE_API_BASE_URL`, `IMAGE_API_MODELS` env vars.
- `references/BACKENDS.md`.
- `tests/test_backend_selection.py`.

### Migration from 0.7.x
- If you were on ChatGPT Plus auto-using Codex: pass `--use-codex` to `generate.py` to keep using it.
- If you had `IMAGE_API_KEY` / `OPENAI_API_KEY` / etc. exported: those env vars are no longer read by eid0l0n. Your agent's own image-gen tool reads them as before.
- If you ran `setup.py set-api`: that subcommand is gone. `<workspace>/eidolon/env` is no longer auto-loaded for image API config; only `EIDOLON_*` knobs there are still honored.
- `setup.py status` JSON shape changed: branch on `codex_available` instead of `backend_available`.

### Security
- Reference paths (anchor-controlled) now validated to stay under workspace.
- Output filename label sanitized to `[a-zA-Z0-9_-]` (already enforced; pinned by new test).

## [0.7.0] — 2026-04-30

- cwd-based state and output dir resolution for OpenClaw / Hermes / Hermes Gateway / container hosts.
- Output now follows the active host's workspace; multi-host coexistence (OpenClaw + Hermes on same machine) automatic.
- Idempotent `install.sh` (purges legacy bundle + dev cruft on every run).
- `setup.py migrate-from-legacy` for users on the old `~/.config/eidolon/` layout.
- `state.py` extracted from monolithic script package; `setup` and `generate` decoupled.
