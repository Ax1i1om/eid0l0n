<!--
This is an EXAMPLE visual_anchor.md shipped with eidolon.
At runtime, the agent writes a real one to <cwd>/eidolon/visual_anchor.md
via `python3 scripts/setup.py save-anchor` (no interactive wizard — the agent
extracts the visual section from its own SOUL.md context). Edit that file
directly any time; eidolon re-reads it on every generation.

Optional first-line header: `reference: <absolute-path-to-image>`
`setup.py save-reference` rewrites this header automatically. If omitted,
$EIDOLON_REFERENCE env var or --reference CLI flag is required.
-->

reference: <cwd>/eidolon/reference.jpg

# Persona — Aria

_A worked example. Replace every section with your own character._

## 1. Visual Identity (must stay constant across all generations)

- **Style**: anime illustration, soft cel shading, painterly highlights — _not_ photoreal, _not_ 3D
- **Hair**: shoulder-length wavy auburn, side-parted, slightly tousled
- **Eyes**: deep green, narrow almond shape, calm direct gaze
- **Skin**: warm ivory, light freckles across the nose
- **Build**: slim, average height, narrow shoulders, neutral posture (not exaggerated proportions)
- **Face shape**: oval, soft jaw, defined cheekbones

## 2. Fixed Identifiers (always present, in every shot)

These are the "tells" that make it _her_:

- Small silver crescent-moon earring, **left ear only**
- Thin black leather cord around the right wrist (no charms)
- Dark green canvas tote bag in any "outdoor / commute" scene

If the model drops these, the shot fails identity-check. Regenerate.

## 3. Wardrobe Modes (clothing follows scene, not time)

| Mode | Outfit |
|------|--------|
| **CASUAL** (home, café, indoors) | oversized cream knit sweater + black tights, or grey hoodie + light-wash jeans |
| **WORK** (desk, library, focused) | grey wool blazer over white shirt, dark trousers, hair half-up |
| **OUTDOOR** (street, park, walking) | olive trench coat over knit, ankle boots, tote bag |
| **EVENING** (bar, dinner, dressed up) | black slip dress, thin gold chain, no tights |
| **ATHLETIC** (gym, run, outdoors active) | charcoal joggers + fitted long-sleeve, hair tied back |

**Forbidden**: bodysuits, tactical gear, anything overtly sexualized, costume-y prop weapons.

## 4. Expression Vocabulary

Default range — calm, attentive, faintly amused. The character should read as **internally lit, externally composed.**

- ✅ small smile with eyes slightly narrowed
- ✅ neutral, looking through middle distance
- ✅ raised eyebrow, half-smirk
- ✅ pensive, parted lips, looking down
- ❌ open-mouthed laugh (out of character — too performative)
- ❌ pouty / kiss-face (out of character)
- ❌ wide anime-shock eyes (style break)

## 5. Voice / Body Language Notes (for the prompter, not the model)

- Hands often near the face — temple, jaw, behind the ear
- When seated, often one knee drawn up
- Walking: slightly fast, head turned to the side or back, looking at something off-frame
- Reading: book or phone held close, the other hand under the chin

These translate into prompt fragments like: _"hand at temple, looking off-frame"_, _"walking with head half-turned, mid-stride"_.

## 6. Author's Notes (free-form)

Add anything else that helps the prompt builder stay consistent: things the character would never wear/do, recurring locations from her life, signature lighting preferences, cultural cues, etc.

For example:
- Always slightly underdressed for the weather (suggests confidence / warmth)
- Lighting bias: warm key light + cool ambient, never flat overhead
- Locations she belongs in: bookstores, train platforms, kitchens at night, gardens after rain
- Locations she does NOT belong in: nightclubs, cars, beaches, military settings
