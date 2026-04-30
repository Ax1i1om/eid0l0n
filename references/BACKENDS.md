# Backends — credentials, env vars, and selection

eid0l0n auto-detects 6 image-gen backends. Any one configured is enough. Priority order (first available wins): `codex` → `gemini` → `openai` → `fal` → `replicate` → `openrouter`.

To enumerate at runtime:

```bash
python3 scripts/setup.py detect-backends --json
```

Force a specific one via `EIDOLON_IMAGE_BACKEND=<name>` or `--backend <name>` per call.

## Per-backend setup

| Backend | How to configure | Notes |
|---------|------------------|-------|
| `codex` | run `codex login` once (their own shell) | **Free** for ChatGPT Plus / Pro / Team. Auto-detected from `~/.codex/auth.json`. |
| `gemini` | `export GEMINI_API_KEY=...` (or `GOOGLE_API_KEY`) | Generous free tier on AI Studio. |
| `openai` | `export OPENAI_API_KEY=...` | Pay-per-image via Images API (gpt-image-2). |
| `fal` | `export FAL_KEY=...` | Many models — flux, gpt-image-2, nano-banana. |
| `replicate` | `export REPLICATE_API_TOKEN=...` | flux-kontext / flux-1.1-pro defaults. |
| `openrouter` | `setup.py set-api --key <KEY>` | Legacy default. Pay-per-token. |

## Per-backend credentials reference

| Backend | Required env / file | Purpose |
|---------|---------------------|---------|
| `codex` | `~/.codex/auth.json` (from `codex login`) | Free for ChatGPT Plus/Pro/Team. No API key. |
| `gemini` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Google AI Studio direct. |
| `openai` | `OPENAI_API_KEY` (+ optional `OPENAI_IMAGE_MODEL`) | OpenAI Images API. |
| `fal` | `FAL_KEY` (+ optional `EIDOLON_FAL_MODEL`) | fal.ai queue. |
| `replicate` | `REPLICATE_API_TOKEN` (+ optional `EIDOLON_REPLICATE_MODEL`) | Replicate predictions. |
| `openrouter` (legacy) | `IMAGE_API_KEY` (+ optional `IMAGE_API_BASE_URL`, `IMAGE_API_MODELS`) | OpenRouter chat-completions. Set via `setup.py set-api --key <KEY>`. |

## Quality / aspect knobs (Codex + OpenAI only)

| Variable | Effect |
|----------|--------|
| `EIDOLON_IMAGE_QUALITY` | `low` / `medium` (default) / `high` — applies to `codex` and `openai` (gpt-image-2 tiers) |
| `EIDOLON_IMAGE_ASPECT` | `square` (default) / `portrait` / `landscape` |

## Path overrides

| Variable | Purpose |
|----------|---------|
| `EIDOLON_HOME` | Full state-dir override (always wins; dev/test escape hatch). Default: `<cwd>/eidolon/` (per-host cwd, see `docs/HOST-COMPATIBILITY.md`). |
| `EIDOLON_VISUAL_ANCHOR` | Override anchor path |
| `EIDOLON_REFERENCE` | Override reference path |
| `EIDOLON_OUTPUT_DIR` | Override output dir (see SKILL.md OUTPUT section for the auto-detect fallback) |

## API-key safety rule

**If a backend needs an API key, set it in the user's own shell** — never have the agent collect the key from chat. That path leaks the key into chat logs + model context + disk.

The `openrouter` legacy backend is the exception that has a `setup.py set-api` command — but you should still run it in your own shell, not let the agent run it on your behalf with a key it just received in chat.
