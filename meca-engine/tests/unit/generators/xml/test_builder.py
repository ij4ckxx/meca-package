"""Unit tests for meca_engine.generators.xml.builder.XmlDocumentBuilder."""

from __future__ import annotations

import pytest

from meca_engine.exceptions import XmlSerializationError
from meca_engine.generators.xml.builder import CData, DoctypeDeclaration, XmlDocumentBuilder

pytestmark = pytest.mark.unit


@pytest.fixture
def builder() -> XmlDocumentBuilder:
    return XmlDocumentBuilder()


def test_create_root_sets_tag_and_attributes_in_order(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article", attributes={"a": "1", "b": "2"})

    assert root.tag == "article"
    assert list(root.attrib.items()) == [("a", "1"), ("b", "2")]


def test_create_root_without_attributes_has_none(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")

    assert root.attrib == {}


def test_create_element_appends_child_with_text(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article-meta")

    child = builder.create_element(root, "article-title", text="A Study")

    assert list(root) == [child]
    assert child.tag == "article-title"
    assert child.text == "A Study"


def test_create_element_without_text_leaves_text_none(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article-meta")

    child = builder.create_element(root, "empty-tag")

    assert child.text is None


def test_element_order_matches_creation_order(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("contrib-group")
    first = builder.create_element(root, "contrib", text="1")
    second = builder.create_element(root, "contrib", text="2")
    third = builder.create_element(root, "contrib", text="3")

    assert list(root) == [first, second, third]


def test_add_comment_serializes_as_xml_comment(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.add_comment(root, "a note")

    output = builder.serialize(root, pretty=False).decode("utf-8")

    assert "<!-- a note -->" in output


def test_add_processing_instruction_serializes_correctly(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.add_processing_instruction(root, "xml-stylesheet", 'href="x.xsl"')

    output = builder.serialize(root, pretty=False).decode("utf-8")

    assert '<?xml-stylesheet href="x.xsl"?>' in output


def test_cdata_text_is_not_escaped(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.create_element(root, "abstract", text=CData("a <b> & c"))

    output = builder.serialize(root, pretty=False).decode("utf-8")

    assert "<abstract><![CDATA[a <b> & c]]></abstract>" in output


def test_plain_text_is_escaped(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.create_element(root, "abstract", text="a <b> & c")

    output = builder.serialize(root, pretty=False).decode("utf-8")

    assert "a &lt;b&gt; &amp; c" in output
    assert "<![CDATA[" not in output


def test_serialize_includes_xml_declaration_with_encoding(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")

    output = builder.serialize(root, encoding="UTF-8").decode("utf-8")

    assert output.startswith('<?xml version="1.0" encoding="UTF-8"?>')


def test_serialize_can_omit_encoding_from_declaration(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")

    output = builder.serialize(root, encoding=None).decode("utf-8")

    assert output.startswith('<?xml version="1.0"?>')


def test_serialize_can_omit_declaration_entirely(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")

    output = builder.serialize(root, xml_declaration=False).decode("utf-8")

    assert "<?xml" not in output


def test_serialize_standalone_true(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")

    output = builder.serialize(root, standalone=True).decode("utf-8")

    assert 'standalone="yes"' in output


def test_serialize_standalone_false(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")

    output = builder.serialize(root, standalone=False).decode("utf-8")

    assert 'standalone="no"' in output


def test_serialize_with_doctype(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    doctype = DoctypeDeclaration(
        root_tag="article", public_id="-//TEST//DTD//EN", system_id="test.dtd"
    )

    output = builder.serialize(root, doctype=doctype).decode("utf-8")

    assert '<!DOCTYPE article PUBLIC "-//TEST//DTD//EN" "test.dtd">' in output


def test_doctype_system_only() -> None:
    doctype = DoctypeDeclaration(root_tag="manifest", system_id="./schema/manifest-1.0.dtd")

    assert doctype.render() == '<!DOCTYPE manifest SYSTEM "./schema/manifest-1.0.dtd">'


def test_doctype_root_tag_only() -> None:
    doctype = DoctypeDeclaration(root_tag="article")

    assert doctype.render() == "<!DOCTYPE article>"


def test_pretty_mode_indents_nested_elements(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    front = builder.create_element(root, "front")
    builder.create_element(front, "article-meta")

    output = builder.serialize(root, pretty=True).decode("utf-8")

    assert "\n  <front>\n    <article-meta" in output


def test_compact_mode_has_no_whitespace_between_elements(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    front = builder.create_element(root, "front")
    builder.create_element(front, "article-meta")

    output = builder.serialize(root, pretty=False).decode("utf-8")

    assert "<article><front><article-meta" in output


def test_indent_spaces_controls_pretty_width(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.create_element(root, "front")

    output = builder.serialize(root, pretty=True, indent_spaces=4).decode("utf-8")

    assert "\n    <front" in output


def test_serialize_does_not_mutate_the_original_tree(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    front = builder.create_element(root, "front")
    builder.create_element(front, "article-meta")

    builder.serialize(root, pretty=True)

    assert root.text is None
    assert front.text is None


def test_serialize_can_be_called_twice_with_different_modes(builder: XmlDocumentBuilder) -> None:
    root = builder.create_root("article")
    builder.create_element(root, "front")

    pretty_output = builder.serialize(root, pretty=True)
    compact_output = builder.serialize(root, pretty=False)

    assert b"\n" in pretty_output
    assert compact_output.count(b"\n") <= 1


def test_unknown_output_encoding_raises_xml_serialization_error(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("article")

    with pytest.raises(XmlSerializationError):
        builder.serialize(root, encoding="not-a-real-encoding")


def test_unserializable_content_raises_xml_serialization_error(
    builder: XmlDocumentBuilder,
) -> None:
    root = builder.create_root("article")
    root.set("bad", 5)  # type: ignore[arg-type]

    with pytest.raises(XmlSerializationError):
        builder.serialize(root)


def test_import_subtree_deep_copies_without_aliasing(builder: XmlDocumentBuilder) -> None:
    source_root = builder.create_root("source")
    child = builder.create_element(source_root, "child", text="original")

    imported = builder.import_subtree(source_root)
    imported.find("child").text = "changed"  # type: ignore[union-attr]

    assert child.text == "original"
    assert imported is not source_root


def test_import_subtree_can_be_attached_to_another_tree(builder: XmlDocumentBuilder) -> None:
    other_root = builder.create_root("other")
    builder.create_element(other_root, "grandchild", text="value")

    destination = builder.create_root("destination")
    destination.append(builder.import_subtree(other_root))

    assert destination.find("other/grandchild").text == "value"  # type: ignore[union-attr]
