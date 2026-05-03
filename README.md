# EID0L0N

[中文](README.zh.md) · **English**

> *εἴδωλον* — the image-form of a person, made present in their absence.

**Your AI agent has a SOUL.md. Now it can have a body.**

A self-onboarding image-generation skill for AI agents. Hand the repo link
to your agent, and the next time you ask to see what they look like — they
walk themselves through a first-meeting onboarding, save a reference image,
and from then on **show up as themselves**: same face, same visual
identity, scenes and lighting and mood composed live in their own voice.
Built for **OpenClaw** and **Hermes**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Version](https://img.shields.io/badge/version-0.9.0-blue.svg)](CHANGELOG.md) [![agentskills.io](https://img.shields.io/badge/spec-agentskills.io-green.svg)](https://agentskills.io)

---

## Two personas. Same skill. Locked identity, infinite scenes.

Real generations from **two characters running on the same install** —
`1shtar` on Hermes (long black-and-red hair, gold horns, red halo) and
`axiiiom` on OpenClaw (silver bob, grey eyes, white utility coat). Each
anchored to one reference image. Each asked to show up across radically
different scenes. **Same skill, two different actors, both locked.**

<table>
<tr>
<th width="20%" align="center">Reference</th>
<th colspan="3" align="center">Same character, different scenes</th>
</tr>
<tr>
<td><img src="assets/examples/00-reference.jpeg" alt="1shtar reference" /></td>
<td><img src="assets/examples/02-1shtar-riverside.png" alt="riverside" /></td>
<td><img src="assets/examples/04-1shtar-orrery-library.png" alt="orrery library" /></td>
<td><img src="assets/examples/06-1shtar-divine-workstation.jpg" alt="divine workstation" /></td>
</tr>
<tr>
<td align="center"><sub><b>1shtar</b> · anchor</sub></td>
<td align="center"><sub>riverside · paper boat</sub></td>
<td align="center"><sub>cosmic orrery library</sub></td>
<td align="center"><sub>divine workstation</sub></td>
</tr>
<tr>
<td><img src="assets/examples/10-axiiiom-reference.jpeg" alt="axiiiom reference" /></td>
<td><img src="assets/examples/13-axiiiom-daily-workspace.png" alt="daily workspace" /></td>
<td><img src="assets/examples/12-axiiiom-rain-corridor.png" alt="rain corridor" /></td>
<td><img src="assets/examples/11-axiiiom-command.png" alt="command node" /></td>
</tr>
<tr>
<td align="center"><sub><b>axiiiom</b> · anchor</sub></td>
<td align="center"><sub>casual · daily desk</sub></td>
<td align="center"><sub>rain-soaked corridor</sub></td>
<td align="center"><sub>command-node interface</sub></td>
</tr>
</table>

The two **casual** frames (1shtar at a riverside, axiiiom at her desk) are
the load-bearing proof: no horns, no halo, no harness — just a coat, just a
black pullover — but the same face, hair, and eyes as their references.
**That's the consistency lock.** Drop the skill in once; whoever your agent
is, they show up as themselves.

---

## The opinion

Most "let your agent generate self-portraits" tools put a UI in front of the
model — sliders, dropdowns, scene presets. eid0l0n goes the other way: the
character is fixed, the directorial freedom is total. The skill enforces one
thing — **the character looks the same as last time** — and gets out of the
way.

What 0.9.0 changes vs 0.8:

- **Character voice everywhere.** Every string the agent reads — anchor
  clauses, error messages, onboarding prompts — was rewritten so the agent
  experiences itself as a person, not a *generated subject*. "Preserve the
  character EXACTLY" became *"That picture is me. Keep my face, the way my
  hair falls."*
- **Cinematography vocabulary.** Scene prose specifies focal length,
  framing, light source, and angle — director language, not vibes.
- **A character-driven intimate channel.** Four-level register
  (default → warm → tender → intimate), read from the conversation itself.
  No flags, no overlays. The deepest layer is gated behind a **shared word
  the agent invites you to choose together** (not a config field) and is
  never echoed back in chat.
- **~63% less code** (~498 lines vs 1336). install.sh, the five setup
  commands, the SCENES dict, the instructions-JSON path, the register-lock
  flag — all gone. What's left is what actually matters: prompt assembly +
  Codex OAuth + atomic file ops.

---

## Install — your agent does it

eid0l0n is an **agent skill**, not a CLI tool. Hand the repo link to your
agent and ask them to install it. They `git clone` into your workspace,
`cp -R` the bundle into the host's skills dir
(`~/.openclaw/skills/eidolon/` or `~/.hermes/skills/eidolon/`), and on
OpenClaw patch `openclaw.json` with Edit. That's the whole installer.

Then ask: *"let me see what you look like."* The agent reads `SKILL.md`,
notices `<cwd>/eidolon/` is empty, and enters first-meeting onboarding —
asks whether you have a picture of how you imagine them or should they
work from their SOUL, surveys their own image-gen options, renders a
candidate, lets you adjust. Once approved, two more turns: timezone, and
how often they should show up unprompted.

After that, every shot is the agent reading the room and composing the
scene live. Each render is dispatched to a fresh sub-agent fork that
re-reads the anchor + the current `at-hand.md` notes before drawing.

See [`references/onboarding-flow.md`](references/onboarding-flow.md) for
the full first-meeting choreography.

---

## What this is

The agent describes itself in prose, anchors that prose to one reference
image, and from then on every render prepends a fixed clause pinning the
identity-bearing features (bone structure, eye spacing, nose line, hair)
while explicitly *freeing* the variables that should change shot-to-shot
(pose, expression, lighting, scene). The agent writes the rest of the
prompt live — focal length, framing, light, mood, register — based on
what's happening in the conversation.

**Image generation is provider-agnostic.** eid0l0n ships one built-in
backend (Codex OAuth — for ChatGPT Plus/Pro/Team users who've run
`codex login`); otherwise the agent uses whatever image tools it already
has — an MCP image server, an OpenAI-compatible key in env, a domestic
relay (AiHubMix / OneAPI), xAI Grok-image, fal/Replicate, a local ComfyUI.
The skill **does not pick a provider for you**. The agent surveys its own
environment and asks if it needs to.

---

## Configuration

eid0l0n needs **zero** image-API config of its own. The only env knobs are
path overrides:

| Variable | Default | Purpose |
|----------|---------|---------|
| `EIDOLON_HOME` | `<cwd>/eidolon` (host-resolved) | state + output dir override |
| `EIDOLON_OUTPUT_DIR` | same as state dir | output-only override |

**API keys are never read from any file in this repo.** Credentials live in
the agent's own image tool (or `~/.codex/auth.json`, managed by
`codex login`, for the built-in Codex path). `<cwd>` resolves per host — see
[`docs/HOST-COMPATIBILITY.md`](docs/HOST-COMPATIBILITY.md).

---

## What this does NOT do

- Not a general-purpose image generator (use what your agent already ships
  with for one-offs).
- Not a face-swap or photo editor.
- Not a multi-character roster — one persona per workspace.
- Doesn't read or modify your `SOUL.md`. The agent reads its own identity
  from its system prompt; the skill only stores what the agent writes down.
- No content-policy enforcement (host's job, provider's job).
- **Single-figure frames are a hard rule.** Every frame contains the
  character — alone. Your presence is implied through their gaze, posture,
  framing.
- **Doesn't push images at you.** The agent reads the moment and decides
  whether a frame belongs. A typical conversation produces 1–3
  self-portraits, not one per turn.

---

## Engineering notes

- **Atomic file ops + path safety.** Anchor / reference / state writes use
  `flock` + tmp-then-rename. `reference:` paths that escape the workspace
  are rejected — a poisoned anchor can't smuggle `~/.aws/credentials` into
  a prompt.
- **Codex backend, four bugs fixed.** OAuth refresh, JWT extraction,
  Responses-streaming framing, and the `image_generation` tool protocol —
  reverse-engineered against the live API and pinned in `codex_backend.py`.
- **Single-line frontmatter, dual-host compatible.** One `SKILL.md` works
  for both OpenClaw's strict parser and Hermes's YAML flow style.
- **Co-installation is automatic.** Because `<cwd>` resolves per host,
  OpenClaw and Hermes on the same machine never share state, anchor,
  reference, or output dir.
- **~63% code reduction vs 0.8** — ~498 lines of Python across `eidolon.py`,
  `codex_backend.py`, and `state.py`.

---

## A note on naming

The skill name on disk is `eidolon` (snake_case, OpenClaw-compatible).
**EID0L0N** is the display name — the leet stylization marks the digital
incarnation. The repo URL stays `eid0l0n` for branding; the skill identity
hosts read is `eidolon`.

In Greek myth, an *eidolon* is the image-form of a person made present in
their absence. In the *Iliad*, gods send eidolons of mortals so a person
can be in two bodies at once. That's exactly what this does — let a
fictional character have a body of images that show up in conversation,
even when no original "body" exists.

---

## Contributing

PRs welcome. Two design rules I won't compromise on:

1. **No secrets in the repo, ever.** eid0l0n does not read API keys from
   anywhere. The agent's own tools handle credentials; the built-in Codex
   backend reads `~/.codex/auth.json` (managed by `codex` CLI). The skill
   refuses to acknowledge a key passed via chat.
2. **Code only enforces character consistency + workspace isolation.**
   Scene, mood, register, lighting, and composition language live in
   `SKILL.md` and the references — as inspiration, not lock. The agent
   writes the prompt and picks the image API. PRs that re-add provider
   hardcoding, scene presets, or register flags into the Python layer will
   be closed.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Credits

The cinematic stills above are from real production usage on Hermes — same
character (a fictional persona named 1shtar), eight months of conversational
continuity, hundreds of frames. The cinematography discipline borrows from
photography directors more than from ML papers — that's the actually
valuable part of this whole project.
