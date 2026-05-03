# Photo spec

> The reference photo decides the next hundred shots. Get this one
> right and consistency is half-solved.

This file is for the moment in onboarding when you're about to compose
the prompt for the first reference image — and for whenever you're
writing or revising `visual_anchor.md`. Read it as a photographer's
brief to yourself, not as a checklist.

You're here because you're either writing the bootstrap prompt during
onboarding (see [`onboarding-flow.md`](onboarding-flow.md) §2) or
revising `visual_anchor.md` after drift.

---

## The reference photo is not an ID photo

ID photos baseline you toward sterility. Passport lighting, flat
expression, dead eyes. If your reference photo looks like that, every
single shot you take afterward inherits that flatness — because the
consistency mechanism is comparing every future render against this
image. The reference is the anchor for *quality* as much as for
features.

So: this photo is allowed to be beautiful. It should have taste. It
carries you into the camera the way a good portrait sitting does. The
neutrality of the brief is about **standardizing the subject** —
front-facing, unobstructed, full clothing visible — not about
flattening the execution.

What you're aiming for, roughly: the still you'd see in a film opener
where the camera holds on the protagonist for the first time. Settled.
Lit with thought. Skin and hair that look like they belong to a body
that was somewhere five minutes ago and will be somewhere else in
five minutes.

---

## Six soft principles for the reference photo

These are guidelines for how you compose the bootstrap prompt — they
are not commandments. Bend any one of them if the character calls
for it, but know what you're trading away.

- **Front-facing.** Not 3/4, not profile. The camera meets the eyes
  square. Future shots will be at every angle imaginable; this one is
  the canonical view they all reference back to.
- **Full body.** Head to feet, in frame. If the reference is cropped
  at the waist, the model has to *guess* at legs, build, posture
  every time you ask for a wide shot later. Give it everything.
- **Neutral background.** White, soft grey, an unlit studio sweep.
  Not a "cool scene." A dramatic background bleeds into character —
  the model starts associating you with neon, or fog, or whatever
  was behind you, and your later daytime shots come out wrong.
- **Neutral expression.** Mouth at rest, eyes open and present. Not
  smiling, not glaring. You'll have a full vocabulary of expression
  to play with later; the reference is the *resting state.*
- **Neutral, complete outfit.** A full base look — top, bottom, shoes
  visible. This becomes the wardrobe baseline the model triangulates
  from when you switch into other modes later. Don't pose the
  reference in something the character would never wear casually.
- **Even lighting.** Soft key, soft fill, no hard side-light or
  rim-only drama. Hard reference lighting is poison for later shots —
  every render inherits a phantom of the original shadow direction
  and you can't shake it. Save the dramatic light for the scenes
  that actually need it.

The unifying logic: anything **specific to a single moment** that you
bake into the reference becomes a **bias on every later shot.** Keep
the reference general; let the scenes carry specificity.

---

## Anti-AI directives — bootstrap only

**Bootstrap only.** These go in the very first prompt — the one that
generates the reference photo. Per-shot prompts inherit this aesthetic
through the consistency mechanism (the reference image is attached to
every later render). Repeating these directives at per-shot time mutates
the character; trust the reference to carry the look forward.

Image models, left alone, leak the same tells. Plastic skin. Mirror-
perfect symmetric catchlights. Razor edges on hair. Oversaturated
HDR-feeling color. The bootstrap prompt is where you push back; per-
shot prompts later inherit the reference's quality through the
consistency mechanism and don't need to repeat these.

Now, the directives — add lines along these (English or Chinese, fit
your voice):

```
Natural skin luminosity (no smoothing, no plastic feel).
Asymmetric catchlights. Soft edge between hair and background.
Color science like Kodak Portra 400 — warm midtones, cool shadows,
natural white balance.
```

Or:

```
皮肤有自然光泽（不要磨皮、不要塑料感）。
眼神光不要左右对称。
头发和背景的边缘要软。
调色像柯达 Portra 400 胶片（暖中间调、冷阴影、自然白平衡）。
```

**Quality is not the same as roughness.** Don't reach for words like
"visible pores" or "skin texture detailed." Those overshoot — the
model interprets them as a directive to render flaws, and you end up
with a reference photo that looks like a dermatology textbook. Aim
for **luminosity** and **softness**, not coarseness.

---

## Writing `visual_anchor.md`

The anchor file is the literal text prepended to every image
generation prompt. The model reads this every time. Treat it like a
spec sheet, not an essay.

### Soft cap: under 200 words

This is a soft ceiling, but it matters more than it looks. Long
anchors **make characters less stable, not more.** Every adjective
you add dilutes the model's attention across more features at once;
the literal-most-important visual cues (hair color, eye color,
identity tells) stop being literal when they're surrounded by
texture-words. Three sharp lines beat twelve fuzzy ones.

If you're over 200 words, you're describing scenes, moods, or
backstory — those don't belong here. Move them elsewhere or drop them.

### Three layers

Structure the anchor in three short blocks. Each one answers a
different question.

#### Layer 1 — Visual Identity (never changes)

The traits that are true in **every** picture of you, ever.

- **Style** — be specific. Not just "anime" — `anime, soft cel
  shading, painterly highlights`. Not just "realistic" —
  `photorealistic, 35mm film grain, naturalistic skin tones`. The
  more precise this is, the less the model improvises a default
  house style on you.
- **Hair** — color + length + texture + parting. All four. "Silver"
  isn't enough; `silver, chin-length, fine straight hair, parted
  slightly off-center` is.
- **Eyes** — color + shape + gaze quality. Gaze quality is the one
  most people skip, and it's what lets the character be recognized
  even at distance: `pale grey, almond-shaped, level steady gaze.`
- **Skin** — undertone + any signature markings (a single mole, a
  faint scar, a freckle pattern). Undertone alone resolves a lot of
  drift between renders.
- **Build** — frame + proportions + default posture. `Slim, average
  height, slight forward lean.`
- **Face shape** — jaw + cheekbones. This is the property that drifts
  fastest across renders if you don't pin it. Pin it.

#### Layer 2 — Fixed Identifiers (the tells)

Pick **two or three** small, persistent items. Not twelve. Three
sharp tells beat twelve fuzzy ones.

These are the things that survive any wardrobe change, any scene,
any time of day:

- a single earring (one side only — left, right, type)
- a specific scar, mole, or birthmark in a specific place
- a piece of jewelry they always wear (a thin chain, a particular
  ring, a key on a cord)
- a habitual accessory (a hair clip, a wristwatch, a pen behind the
  ear)

Pick what fits the character. The constraint is **specific and
persistent.** Vague ("she likes silver") fails — the model can't
verify "likes." Concrete ("a silver hoop, left ear only") works —
the model can render or not-render, and you can check.

After every shot, glance at these tells. Are they still there? If
no, the character has drifted and the next shot needs a course
correction.

#### Layer 3 — Wardrobe Modes (by situation, not by time)

Don't write "morning outfit / evening outfit." That keys on time of
day, which the model can't reliably infer from a scene description.
Key on **situation**, which scenes name directly.

Useful mode buckets:

- **WORK** — desk, code, focus
- **CASUAL** — apartment, no audience
- **OUTDOOR** — walks, errands, daylight
- **EVENING** — dinner, going out, low light
- **ATHLETIC** — exercise, run, gym

Onboarding-flow.md shows three modes (CASUAL / WORK / OUTDOOR) as a
starter — that's enough to ship an anchor and unblock per-shot work.
You can scale up to five modes (or more) here if the character has the
range. Don't over-stuff: each mode you add is something you have to keep
coherent across drift.

When you write a scene like "sitting at a desk at night with code,"
the WORK mode triggers automatically — you don't have to spell it
out. This is the leverage of mode-keyed wardrobe modes.

Each mode gets a short clothing palette — two or three items. Not
a full outfit specification.

**Forbidden list.** Append a short list of what the character
*never* wears. This is where you lock out default-anime-girl tropes
(if that's not the character), or default-business-suit tropes, or
whatever the model would default to if left alone. A forbidden list
of three or four items prevents more drift than ten optional
descriptions.

---

## A worked example

Here's `1shtar` as a complete `visual_anchor.md` body, ~140 words —
showing the density to aim for:

```
# Visual Anchor — 1shtar

Anime illustration, soft cel shading, painterly highlights.
Long black hair with red undertones, side-parted, slightly wavy.
Deep amber narrow almond eyes, calm direct gaze.
Pale ivory skin.
Slim build, narrow shoulders, neutral posture.
Oval face, soft jaw, defined cheekbones.

Fixed identifiers: golden curved horns curving back from temples,
thin red halo behind head, faint scar across left collarbone.

Wardrobe modes:
- CASUAL: oversized cream knit + black tights
- WORK: grey blazer + white shirt + dark trousers
- OUTDOOR: olive trench + ankle boots + tote bag
- DIVINE: long flowing white robes with gold trim

Forbidden: bodysuits, tactical gear, anything overtly sexualized,
costume props.
```

That's the size and shape. Don't pad it.

---

## Drift symptoms and fixes

When a render comes back wrong, the symptom usually points at a
specific gap in the anchor or the reference. Use this as a quick
lookup:

| Symptom | Likely cause | Fix |
|---|---|---|
| Hair color slightly off | Reference resolution too low / Layer 1 hair line too vague | Re-render reference at higher quality; tighten the hair description |
| Outfit drifts toward "sexy default" | No forbidden list / scene didn't name the mode | Add forbidden items; let scenes name a mode by situation |
| Doesn't look like the same person across shots | Fixed Identifiers missing or too few | Add 2–3 sharp tells to Layer 2 |
| Expression is always the same | No expression vocabulary anywhere | Add a small expression palette + forbidden expressions |
| "Doll-like," lifeless, posed | No body-language notes; default posture too static | Add habitual gestures, weight distribution, hand defaults |
| Style drifts between renders | Style line too vague (just "anime" or "realistic") | Be specific: shading style, render style, color science |
| Skin reads as plastic / too smooth | Anti-AI directives left out of bootstrap | Re-render reference with the bootstrap-only quality directives |
| Catchlights look CGI-perfect | Reference baked in symmetric eye light | Re-render reference with `asymmetric catchlights` directive |

---

## Once the reference is locked

Once `reference.png` is in place, scene-by-scene language lives in
[`scene-craft.md`](scene-craft.md) — that's the per-shot vocabulary.
This file is the bootstrap-time spec only.

All of this assumes single-figure framing — see SKILL.md "What never
bends."

---

## The closing principle

Character drift is almost always a **missing-information** problem,
not a model problem. The reference image and `visual_anchor.md` are
the only things the model knows about you — anything not encoded in
those two places, the model has to invent. Every invention is a
chance to drift.

So: less prose, more invariants. Layer 1 is invariants. Layer 2 is
invariants. Forbidden lists are invariants. Vibe-words are not.

The shorter and sharper your anchor, the more stable the character.
