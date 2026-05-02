# Changelog

All notable changes to eid0l0n. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Changed
- Clarify host render-path selection: use default instructions JSON only when the host can attach the reference image and write to `output_path`; otherwise prefer `--use-codex` when Codex is available (notably for Hermes gateways with text-only image tools).
- Align path-safety docs with implementation: reference paths are workspace-validated; `EIDOLON_OUTPUT_DIR` remains an explicit user-controlled output escape hatch.

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
