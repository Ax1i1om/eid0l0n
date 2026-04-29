# How to write a persona that holds up

The setup wizard produces a working `persona.md` from 8 quick answers. That gets you to "the character looks roughly right." This guide is what takes you from "roughly right" to "rock solid across hundreds of generations."

Every section of this guide maps to a section in your `~/.config/eidolon/persona.md`. Edit by hand any time — `eidolon` re-reads the file on every run.

---

## The mental model

A persona file is **the contract between you and the model.** Everything in it is prepended to every prompt as the *Character anchor*. The scene description you pass to `--prompt` is the *delta* — what's different about this particular shot.

So the persona must answer two questions:

1. **What never changes?** (face, build, fixed identifiers, art style)
2. **What changes by context?** (wardrobe by mode, expression by mood)

Don't write descriptions of *one specific image*. Write the **invariants** of a thousand images.

---

## Section 1: Visual Identity (must stay constant)

The non-negotiables. If any of these drift, the character no longer reads as the same person.

- **Style** — anime / realistic / painterly / 3D. Be specific: *"anime, soft cel shading, painterly highlights"* not just *"anime."* The model picks up on adjective texture.
- **Hair** — color + length + texture + parting. *"shoulder-length wavy auburn, side-parted, slightly tousled."*
- **Eyes** — color + shape + gaze quality. *"deep green, narrow almond, calm direct gaze."* The gaze quality is what keeps a character feeling *like themselves* even at distance.
- **Skin** — undertone + distinctive markings. *"warm ivory, light freckles across the nose."*
- **Build** — frame + proportions + posture default. *"slim, average height, narrow shoulders, neutral posture."* Resist the urge to write fantasy proportions; they invite drift.
- **Face shape** — jaw + cheekbones. The face shape is the single most-likely-to-drift attribute; pin it down.

**Rule of thumb:** if you'd have trouble picking the character out of a lineup based only on the description, add detail.

---

## Section 2: Fixed Identifiers — the "tells"

This is the section that does the heavy lifting. Pick **2–3 small, persistent objects** that make this character unmistakably theirs:

- A specific earring, only on one ear
- A specific scar, mole, or marking
- A specific accessory (key on a chain, ring with a stone, hair clip)

These are your **identity-check anchors**. After every generation, look for these. If the model dropped them, regenerate.

**Why few, not many:** if you list 12 fixed objects, the model averages them out and drops half. Three sharp things beat twelve fuzzy ones.

---

## Section 3: Wardrobe Modes

The single biggest source of "the character looks wrong" is wardrobe drift — the model picks an outfit suited to the *time of day* instead of the *scene type*.

Define **modes**, not outfits-by-time:

| Mode | When | Outfit |
|------|------|--------|
| CASUAL | home, café, indoors | oversized cream knit + black tights |
| WORK | desk, library, focused | grey blazer over white shirt, dark trousers |
| OUTDOOR | street, park, walking | olive trench + ankle boots + tote bag |
| EVENING | bar, dinner, dressed up | black slip dress + thin gold chain |
| ATHLETIC | gym, run | charcoal joggers + fitted long-sleeve |

Then in your scene prompts, **let the scene imply the mode**: `"sitting at a desk at night with code on multiple monitors"` → WORK mode triggers automatically through the persona contract.

**Forbidden list** — lock out wardrobes the character would never wear. *"Bodysuits, tactical gear, anything overtly sexualized, costume props"* prevents the model from defaulting to default-anime-girl tropes when the scene is ambiguous.

---

## Section 4: Expression Vocabulary

Default range for the character's face. Two kinds of entries:

- ✅ **Allowed expressions** — *"small smile with eyes slightly narrowed", "neutral, looking through middle distance", "raised eyebrow, half-smirk"*
- ❌ **Out-of-character expressions** — *"open-mouthed laugh (too performative)", "pouty kiss-face", "wide anime-shock eyes (style break)"*

Listing what's *out* is just as important as listing what's *in* — it stops the model from defaulting to anime-default expressions when your prompt doesn't specify.

---

## Section 5: Body Language Notes

Not for the model — for **you**, the prompt builder. These are recurring physical idioms that translate into prompt fragments:

- *"Hands often near the face — temple, jaw, behind the ear"* → use `"hand at temple"` or `"hand behind ear, looking up"` in scene prompts.
- *"When seated, often one knee drawn up"* → use `"sitting, one knee drawn up"`.
- *"Walking: head turned to the side or back"* → use `"walking with head half-turned, looking back over shoulder"`.

These idioms are how the *character* appears in the world, separate from how they look. Without them, every shot tends toward "model standing for portrait."

---

## Section 6: Author's Notes (free-form)

The catch-all. Add anything that helps you stay consistent:

- **Locations they belong in** — bookstores, train platforms, kitchens at night. Use these on slow days when nothing specific is happening.
- **Locations they don't belong in** — nightclubs, beaches, military settings. Knowing the boundary helps you reject bad scene ideas before generating.
- **Lighting biases** — *"warm key + cool ambient, never flat overhead"*. Useful when the scene is lighting-ambiguous.
- **Cultural cues, era, taste** — what music plays in the scene, what books they'd read. These rarely make it into the image but help you write *believable* scenes.

---

## Iteration loop

1. **Run setup wizard** — get a baseline persona from 8 questions
2. **Generate 10 shots** across very different scenes (preset variety: `idle`, `street_dusk`, `rooftop_dusk`, `kitchen_night`, `library_quiet`, ...)
3. **Inspect** — what drifted? What got dropped? What's wrong?
4. **Edit `~/.config/eidolon/persona.md`** — add anchors for what drifted, list what got dropped under fixed identifiers, add to forbidden if a wrong outfit/expression keeps showing up
5. **Generate the same 10 shots again** — confirm fixes didn't break other things
6. **Repeat until stable**

Most personas converge in 2–3 iteration loops. After that, edits are rare — usually adding a new wardrobe mode for a new context.

---

## Common failure modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Hair color wrong | Reference image undersampled | Use a higher-res reference; restate hair color in section 1 |
| Wardrobe drifts to "sexy default" | No forbidden list, scene is ambiguous | Populate forbidden list; make scene mode explicit |
| Different person each shot | Fixed identifiers missing | Add 2–3 sharp identifiers (earring, scar, accessory) |
| Expression always the same | No expression vocabulary section | Add allowed + forbidden expressions |
| "Doll-like" / lifeless | No body-language notes | Add gesture idioms; use them in prompts |
| Style flips between shots | Style description too vague | Be specific: "anime, soft cel shading, painterly highlights" |

---

## Last principle

**The persona file is the only thing the model sees about your character besides the reference image.** If a quality of the character doesn't appear in either, the model will make it up. Persona drift is almost always a missing-information problem, not a model problem.

Write less prose. Write more invariants.
