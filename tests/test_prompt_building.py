"""Tests for generate.build_prompt — composes the API prompt from scene + persona."""
from __future__ import annotations

import generate


PERSONA = "Tall woman, copper hair, green eyes, freckled cheeks."
SCENE = "Standing on a rooftop at dusk, wind catching her coat."


def test_has_reference_emits_preserve_clause():
    """has_reference=True (no iterate) → 'Preserve the character EXACTLY' clause."""
    out = generate.build_prompt(SCENE, PERSONA, has_reference=True, iterate_on_reference=False)
    assert "Preserve the character EXACTLY" in out


def test_iterate_on_reference_emits_iterate_clause():
    """iterate_on_reference=True → 'Iterate on the attached image' clause."""
    out = generate.build_prompt(SCENE, PERSONA, has_reference=True, iterate_on_reference=True)
    assert "Iterate on the attached image" in out


def test_no_reference_emits_establish_canonical_clause():
    """has_reference=False, iterate=False → 'Establish a canonical reference portrait' clause."""
    out = generate.build_prompt(SCENE, PERSONA, has_reference=False, iterate_on_reference=False)
    assert "Establish a canonical reference portrait" in out


def test_persona_and_scene_appear_verbatim_in_all_branches():
    """All three branches must include both persona_text and scene_text verbatim."""
    cases = [
        (True, False),
        (True, True),
        (False, False),
    ]
    for has_ref, iterate in cases:
        out = generate.build_prompt(SCENE, PERSONA, has_reference=has_ref, iterate_on_reference=iterate)
        assert PERSONA in out, f"persona missing for has_ref={has_ref}, iterate={iterate}"
        assert SCENE in out, f"scene missing for has_ref={has_ref}, iterate={iterate}"


def test_output_structure_anchor_then_character_then_scene():
    """Output order: <anchor_clause>, then 'Character description:', persona, then scene."""
    out = generate.build_prompt(SCENE, PERSONA, has_reference=True, iterate_on_reference=False)
    anchor_idx = out.find("Preserve the character EXACTLY")
    char_header_idx = out.find("Character description:")
    persona_idx = out.find(PERSONA)
    scene_idx = out.find(SCENE)

    assert anchor_idx == 0, "anchor clause must lead the prompt"
    assert anchor_idx < char_header_idx < persona_idx < scene_idx, (
        f"order broken: anchor={anchor_idx} header={char_header_idx} "
        f"persona={persona_idx} scene={scene_idx}"
    )
    # Exact separator between anchor and 'Character description:'.
    assert "\n\nCharacter description:\n" in out


def test_scene_is_stripped_before_assembly():
    """build_prompt strips leading/trailing whitespace from scene_text."""
    out = generate.build_prompt("   " + SCENE + "   \n", PERSONA,
                                has_reference=False, iterate_on_reference=False)
    assert out.endswith(SCENE)
