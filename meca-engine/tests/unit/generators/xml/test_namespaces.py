"""Unit tests for meca_engine.generators.xml.namespaces.NamespaceManager."""

from __future__ import annotations

import pytest

from meca_engine.generators.xml.namespaces import NamespaceManager

pytestmark = pytest.mark.unit

_REGISTRY = {
    "xlink": "http://www.w3.org/1999/xlink",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "meca-manifest": "https://manuscriptexchange.org/schema/manifest",
}


def test_uri_for_returns_the_registered_uri() -> None:
    manager = NamespaceManager(_REGISTRY)

    assert manager.uri_for("xlink") == "http://www.w3.org/1999/xlink"


def test_uri_for_returns_none_for_unregistered_prefix() -> None:
    manager = NamespaceManager(_REGISTRY)

    assert manager.uri_for("nonexistent") is None


def test_prefix_for_returns_the_registered_prefix() -> None:
    manager = NamespaceManager(_REGISTRY)

    assert manager.prefix_for("http://www.w3.org/1999/xlink") == "xlink"


def test_prefix_for_returns_none_for_unregistered_uri() -> None:
    manager = NamespaceManager(_REGISTRY)

    assert manager.prefix_for("http://example.com/unknown") is None


def test_prefix_for_returns_first_registered_when_duplicate_uris() -> None:
    manager = NamespaceManager({"a": "http://example.com/x", "b": "http://example.com/x"})

    assert manager.prefix_for("http://example.com/x") == "a"


def test_declarations_builds_prefixed_xmlns_attributes_in_order() -> None:
    manager = NamespaceManager(_REGISTRY)

    declarations = manager.declarations(["xlink", "meca-manifest"])

    assert declarations == {
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "xmlns:meca-manifest": "https://manuscriptexchange.org/schema/manifest",
    }
    assert list(declarations.keys()) == ["xmlns:xlink", "xmlns:meca-manifest"]


def test_declarations_empty_prefix_becomes_default_namespace() -> None:
    manager = NamespaceManager({"": "https://manuscriptexchange.org/schema/manifest"})

    declarations = manager.declarations([""])

    assert declarations == {"xmlns": "https://manuscriptexchange.org/schema/manifest"}


def test_declarations_raises_key_error_for_unregistered_prefix() -> None:
    manager = NamespaceManager(_REGISTRY)

    with pytest.raises(KeyError):
        manager.declarations(["nonexistent"])


def test_declarations_with_no_prefixes_returns_empty_dict() -> None:
    manager = NamespaceManager(_REGISTRY)

    assert manager.declarations([]) == {}
