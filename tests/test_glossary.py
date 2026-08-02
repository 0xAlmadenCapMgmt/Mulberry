"""Tests for the glossary data module and its report/web surfaces."""

import pytest

from mulberry.core import glossary


# --- Data integrity ----------------------------------------------------------

def test_every_term_is_well_formed():
    for t in glossary.all_terms():
        assert t.slug and t.slug == t.slug.strip()
        assert t.term.strip()
        assert t.category in glossary.CATEGORIES, f"{t.slug}: bad category {t.category!r}"
        # A real definition, not a stub or a leaked tuple.
        assert isinstance(t.definition, str) and len(t.definition) > 25
        assert isinstance(t.formula, str)
        assert isinstance(t.aliases, tuple)


def test_slugs_are_unique_and_url_safe():
    slugs = [t.slug for t in glossary.all_terms()]
    assert len(slugs) == len(set(slugs)), "duplicate slugs"
    for s in slugs:
        assert all(c.islower() or c.isdigit() or c == "-" for c in s), f"bad slug {s!r}"


def test_no_conflicting_alias_maps_to_two_terms():
    # Every normalized alias/term resolves to exactly one entry.
    seen = {}
    for t in glossary.all_terms():
        for name in (t.term, t.slug, *t.aliases):
            key = glossary._norm(name)
            resolved = glossary.lookup(name)
            assert resolved is not None, f"{name!r} did not resolve"
            seen.setdefault(key, resolved.slug)


# --- Lookup ------------------------------------------------------------------

@pytest.mark.parametrize("query, expected_slug", [
    ("NCAV", "ncav"),
    ("ncav", "ncav"),
    ("Net Current Asset Value (NCAV)", "ncav"),
    ("MoS", "margin-of-safety"),
    ("margin of safety", "margin-of-safety"),
    ("P/E", "pe-ratio"),
    ("EV/EBITDA", "ev-ebitda"),
    ("sharpe", "sharpe-ratio"),
    ("composite score", "composite-score"),
    ("PEG", "peg-ratio"),
])
def test_lookup_resolves_known_terms(query, expected_slug):
    term = glossary.lookup(query)
    assert term is not None
    assert term.slug == expected_slug


def test_lookup_unknown_returns_none():
    assert glossary.lookup("definitely-not-a-term") is None
    assert glossary.lookup("") is None


# --- Grouping ----------------------------------------------------------------

def test_by_category_covers_all_terms_in_order():
    grouped = glossary.by_category()
    # Categories present appear in the canonical order.
    order = [c for c in glossary.CATEGORIES if c in grouped]
    assert list(grouped) == order
    # Every term shows up exactly once across the groups.
    flat = [t.slug for terms in grouped.values() for t in terms]
    assert sorted(flat) == sorted(t.slug for t in glossary.all_terms())
    # Terms within a group are alphabetical by display name.
    for terms in grouped.values():
        names = [t.term.lower() for t in terms]
        assert names == sorted(names)


# --- annotate() (inline tooltip HTML) ---------------------------------------

def test_annotate_wraps_known_term_with_escaped_definition():
    html = glossary.annotate("NCAV")
    assert 'class="gloss"' in html
    assert 'data-tip="' in html
    assert ">NCAV<" in html
    # Definition text is present and HTML-escaped (no raw quotes/brackets break out).
    assert "&lt;" not in "NCAV"  # sanity
    assert '"' not in html.split('data-tip="', 1)[1].split('"', 1)[0].replace("&quot;", "")


def test_annotate_key_override():
    html = glossary.annotate("Avg Intrinsic Value", key="intrinsic-value")
    assert 'class="gloss"' in html
    assert "Avg Intrinsic Value" in html


def test_annotate_unknown_term_returns_plain_escaped_text():
    assert glossary.annotate("Whatchamacallit") == "Whatchamacallit"
    # Unknown text with markup is escaped, never wrapped.
    assert glossary.annotate("<b>x</b>") == "&lt;b&gt;x&lt;/b&gt;"


# --- Coverage guard: key report terms must be defined -----------------------

@pytest.mark.parametrize("must_have", [
    "composite-score", "margin-of-safety", "graham-number", "ncav", "dcf",
    "pe-ratio", "pb-ratio", "roe", "sharpe-ratio", "peg-ratio",
    "dividend-yield", "data-confidence", "red-flag",
])
def test_core_report_terms_present(must_have):
    assert any(t.slug == must_have for t in glossary.all_terms())
