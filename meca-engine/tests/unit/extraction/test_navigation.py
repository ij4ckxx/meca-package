"""Unit tests for meca_engine.extraction.navigation."""

from __future__ import annotations

import pytest

from meca_engine.extraction.navigation import (
    XML_NAMESPACE_URI,
    as_bool,
    as_float,
    as_int,
    build_id_index,
    find_all,
    find_by_path,
    find_first,
    get_attribute,
    get_text,
    iter_descendants,
)
from meca_engine.extraction.parsed_model import ParsedAttribute, ParsedElement

pytestmark = pytest.mark.unit


def _el(
    tag: str, *, ns: str | None = None, attrs=(), children=(), text=None, tail=None
) -> ParsedElement:
    return ParsedElement(
        tag=tag,
        namespace_uri=ns,
        attributes=tuple(attrs),
        children=tuple(children),
        text=text,
        tail=tail,
    )


def test_iter_descendants_depth_first_includes_self_by_default() -> None:
    tree = _el("a", children=[_el("b", children=[_el("c")]), _el("d")])

    tags = [e.tag for e in iter_descendants(tree)]

    assert tags == ["a", "b", "c", "d"]


def test_iter_descendants_can_exclude_self() -> None:
    tree = _el("a", children=[_el("b")])

    tags = [e.tag for e in iter_descendants(tree, include_self=False)]

    assert tags == ["b"]


def test_find_first_recursive_finds_nested_match() -> None:
    tree = _el("a", children=[_el("b", children=[_el("target")])])

    found = find_first(tree, "target")

    assert found is not None
    assert found.tag == "target"


def test_find_first_non_recursive_only_checks_direct_children() -> None:
    tree = _el("a", children=[_el("b", children=[_el("target")])])

    found = find_first(tree, "target", recursive=False)

    assert found is None


def test_find_first_returns_none_when_not_found() -> None:
    tree = _el("a")

    assert find_first(tree, "missing") is None


def test_find_first_respects_namespace() -> None:
    tree = _el("a", children=[_el("b", ns="urn:x"), _el("b", ns=None)])

    found = find_first(tree, "b", namespace_uri="urn:x")

    assert found is not None
    assert found.namespace_uri == "urn:x"


def test_find_all_returns_every_match_in_document_order() -> None:
    tree = _el("a", children=[_el("item"), _el("other"), _el("item")])

    found = find_all(tree, "item")

    assert len(found) == 2


def test_find_by_path_navigates_direct_children() -> None:
    tree = _el("a", children=[_el("b", children=[_el("c", text="deep")])])

    found = find_by_path(tree, "b/c")

    assert found is not None
    assert found.text == "deep"


def test_find_by_path_skips_empty_segments_from_leading_or_double_slashes() -> None:
    tree = _el("a", children=[_el("b", children=[_el("c", text="deep")])])

    assert find_by_path(tree, "/b/c") is not None
    found = find_by_path(tree, "b//c")
    assert found is not None
    assert found.text == "deep"


def test_find_by_path_returns_none_for_broken_path() -> None:
    tree = _el("a", children=[_el("b")])

    assert find_by_path(tree, "b/nonexistent") is None


def test_get_attribute_returns_value_when_present() -> None:
    element = _el("a", attrs=[ParsedAttribute(name="id", namespace_uri=None, value="x1")])

    assert get_attribute(element, "id") == "x1"


def test_get_attribute_returns_none_when_absent() -> None:
    element = _el("a")

    assert get_attribute(element, "id") is None


def test_get_attribute_distinguishes_by_namespace() -> None:
    element = _el(
        "a",
        attrs=[
            ParsedAttribute(name="href", namespace_uri="urn:xlink", value="xlink-value"),
            ParsedAttribute(name="href", namespace_uri=None, value="plain-value"),
        ],
    )

    assert get_attribute(element, "href", namespace_uri="urn:xlink") == "xlink-value"
    assert get_attribute(element, "href") == "plain-value"


def test_get_text_non_recursive_returns_immediate_text_only() -> None:
    element = _el("a", text="hello", children=[_el("b", text="nested")])

    assert get_text(element) == "hello"


def test_get_text_non_recursive_returns_empty_string_when_none() -> None:
    element = _el("a")

    assert get_text(element) == ""


def test_get_text_recursive_concatenates_text_and_tails() -> None:
    element = _el(
        "p",
        text="a ",
        children=[_el("b", text="bold", tail=" tail text")],
    )

    assert get_text(element, recursive=True) == "a bold tail text"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("42", 42), ("  7  ", 7), ("-3", -3), (None, None), ("not-a-number", None), ("", None)],
)
def test_as_int(value: str | None, expected: int | None) -> None:
    assert as_int(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("3.14", 3.14), (None, None), ("nope", None)],
)
def test_as_float(value: str | None, expected: float | None) -> None:
    assert as_float(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("no", False),
        (None, None),
        ("maybe", None),
    ],
)
def test_as_bool(value: str | None, expected: bool | None) -> None:
    assert as_bool(value) is expected


def test_build_id_index_finds_plain_id_attributes() -> None:
    tree = _el(
        "root",
        children=[
            _el("aff", attrs=[ParsedAttribute(name="id", namespace_uri=None, value="aff1")]),
            _el("aff", attrs=[ParsedAttribute(name="id", namespace_uri=None, value="aff2")]),
        ],
    )

    index = build_id_index(tree)

    assert set(index) == {"aff1", "aff2"}
    assert index["aff1"].tag == "aff"


def test_build_id_index_recognizes_xml_id() -> None:
    tree = _el(
        "root",
        children=[
            _el(
                "x", attrs=[ParsedAttribute(name="id", namespace_uri=XML_NAMESPACE_URI, value="x1")]
            )
        ],
    )

    index = build_id_index(tree)

    assert "x1" in index


def test_build_id_index_respects_custom_attribute_names() -> None:
    tree = _el(
        "root",
        children=[
            _el("x", attrs=[ParsedAttribute(name="xml_id", namespace_uri=None, value="custom1")])
        ],
    )

    index = build_id_index(tree, id_attribute_names=("xml_id",))

    assert "custom1" in index


def test_build_id_index_keeps_first_element_for_duplicate_id() -> None:
    first = _el("first", attrs=[ParsedAttribute(name="id", namespace_uri=None, value="dup")])
    second = _el("second", attrs=[ParsedAttribute(name="id", namespace_uri=None, value="dup")])
    tree = _el("root", children=[first, second])

    index = build_id_index(tree)

    assert index["dup"].tag == "first"
