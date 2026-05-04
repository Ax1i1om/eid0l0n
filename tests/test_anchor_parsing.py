"""Tests for state.parse_anchor — parses visual_anchor.md → (text, ref, slug)."""
from __future__ import annotations

import pytest

import state


def test_parse_anchor_with_reference_header(tmp_path):
    """Anchor with `reference: /path/to/image.png` first line → ref path returned."""
    anchor = tmp_path / "visual_anchor.md"
    anchor.write_text(
        "reference: /tmp/some/reference.png\n"
        "\n"
        "# Visual Anchor — Test Character\n"
        "\n"
        "Body text describing the character.\n"
    )

    text, ref, slug = state.parse_anchor(anchor)

    assert ref == "/tmp/some/reference.png"
    assert "Body text describing the character." in text
    # 'reference:' header must be stripped from the returned text.
    assert "reference:" not in text
    assert slug == "test_character"


def test_parse_anchor_without_reference_header_returns_none(tmp_path):
    """Anchor without reference header → ref is None."""
    anchor = tmp_path / "visual_anchor.md"
    anchor.write_text(
        "# Visual Anchor — Solo\n"
        "\n"
        "Just a body, no reference header.\n"
    )

    text, ref, slug = state.parse_anchor(anchor)

    assert ref is None
    assert "Just a body, no reference header." in text
    assert slug == "solo"


def test_parse_anchor_body_text_preserved(tmp_path):
    """Body text after the header is returned in the text field."""
    anchor = tmp_path / "visual_anchor.md"
    anchor.write_text(
        "# Visual Anchor — Iris\n"
        "\n"
        "Paragraph one.\n"
        "\n"
        "Paragraph two with details.\n"
    )

    text, _ref, _slug = state.parse_anchor(anchor)

    assert "Paragraph one." in text
    assert "Paragraph two with details." in text


def test_parse_anchor_normalizes_crlf_and_cr_line_endings(tmp_path):
    """CRLF and bare CR are normalized to LF before parsing."""
    anchor = tmp_path / "visual_anchor.md"
    raw = (
        "reference: /tmp/x.png\r\n"
        "\r\n"
        "# Visual Anchor — Mixed\r\n"
        "\r\n"
        "Body line one.\r"
        "Body line two.\r\n"
    )
    anchor.write_bytes(raw.encode("utf-8"))

    text, ref, slug = state.parse_anchor(anchor)

    assert ref == "/tmp/x.png"
    # No carriage returns survive normalization.
    assert "\r" not in text
    assert "Body line one." in text
    assert "Body line two." in text
    assert slug == "mixed"


def test_parse_anchor_slug_falls_back_to_generic_h1(tmp_path):
    """Plain '# Name' heading (no 'Visual Anchor — ' prefix) yields a slug from name."""
    anchor = tmp_path / "visual_anchor.md"
    anchor.write_text("# Just A Name\n\nbody\n")

    _text, _ref, slug = state.parse_anchor(anchor)

    assert slug == "just_a_name"


def test_parse_anchor_slug_default_when_no_heading(tmp_path):
    """No heading at all → slug defaults to 'character'."""
    anchor = tmp_path / "visual_anchor.md"
    anchor.write_text("body only, no heading\n")

    _text, _ref, slug = state.parse_anchor(anchor)

    assert slug == "character"


def test_parse_anchor_rejects_multiple_reference_lines(tmp_path):
    """Multiple `reference:` lines → sys.exit (refuses ambiguous anchor)."""
    anchor = tmp_path / "visual_anchor.md"
    anchor.write_text(
        "reference: /tmp/one.png\n"
        "reference: /tmp/two.png\n"
        "\n"
        "# Visual Anchor — Dup\n"
        "\n"
        "body\n"
    )

    with pytest.raises(SystemExit):
        state.parse_anchor(anchor)


def test_parse_anchor_rejects_null_byte_in_reference(tmp_path):
    """Null byte in reference path → sys.exit (path-injection defense)."""
    anchor = tmp_path / "visual_anchor.md"
    anchor.write_text(
        "reference: /tmp/evil\x00.png\n"
        "\n"
        "# Visual Anchor — Null\n"
        "\n"
        "body\n"
    )

    with pytest.raises(SystemExit):
        state.parse_anchor(anchor)


def test_parse_anchor_rejects_over_long_reference(tmp_path):
    """Reference path > 1024 chars → sys.exit (DoS / oversize defense)."""
    anchor = tmp_path / "visual_anchor.md"
    long_path = "/tmp/" + ("a" * 1100) + ".png"
    anchor.write_text(
        f"reference: {long_path}\n"
        "\n"
        "# Visual Anchor — Long\n"
        "\n"
        "body\n"
    )

    with pytest.raises(SystemExit):
        state.parse_anchor(anchor)
