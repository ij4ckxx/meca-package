"""Namespace Manager — Generator Framework (Milestone 6A).

A thin, config-driven, per-instance wrapper around the prefix→URI
registry loaded from ``config/namespaces.yaml``
(:class:`meca_engine.config.schema.NamespaceConfig`). No namespace URI is
hard-coded here or anywhere else in this module — every value comes from
the config the caller supplies.

Deliberately does **not** use :func:`xml.etree.ElementTree.register_namespace`:
that function mutates process-wide, module-level state, which would make
two generators (or two concurrently-generated articles) interfere with
each other's namespace prefixes — exactly the "mutable shared state"
item 12 says to avoid. Every :class:`NamespaceManager` instance is
self-contained; :mod:`meca_engine.generators.xml.builder` never asks
:mod:`xml.etree.ElementTree` to resolve a prefix — every tag/attribute
name it writes is already the final, literal prefixed string (e.g.
``"xlink:href"``), decided by the generator through this class.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


class NamespaceManager:
    """Resolves namespace prefixes to URIs, and builds ``xmlns`` declarations.

    One instance per generation run (or shared read-only across many —
    it never mutates its own registry after construction, so sharing one
    instance across concurrent generations is safe).
    """

    def __init__(self, namespaces: Mapping[str, str]) -> None:
        """Initialize the manager from a loaded namespace registry.

        Args:
            namespaces: Prefix to URI, typically
                :attr:`~meca_engine.config.schema.NamespaceConfig.namespaces`.
        """
        self._by_prefix: dict[str, str] = dict(namespaces)

    def uri_for(self, prefix: str) -> str | None:
        """Return the URI registered for ``prefix``, or ``None`` if unregistered."""
        return self._by_prefix.get(prefix)

    def prefix_for(self, uri: str) -> str | None:
        """Return the first prefix registered for ``uri``, or ``None`` if none is.

        Registration order is a plain ``dict`` iteration order (insertion
        order) — if more than one prefix maps to the same URI, the first
        one registered wins, deterministically.
        """
        for prefix, registered_uri in self._by_prefix.items():
            if registered_uri == uri:
                return prefix
        return None

    def declarations(self, prefixes: Iterable[str]) -> dict[str, str]:
        """Build the ``xmlns`` attribute dict for a root element.

        Args:
            prefixes: Which registered prefixes to declare, in the exact
                order they should appear as attributes. An empty string
                requests the default (unprefixed) namespace declaration
                (``xmlns="..."`` rather than ``xmlns:prefix="..."``).

        Returns:
            An ordered ``{attribute_name: uri}`` mapping, ready to merge
            into a root element's attributes.

        Raises:
            KeyError: If any requested prefix is not registered.
        """
        result: dict[str, str] = {}
        for prefix in prefixes:
            uri = self._by_prefix[prefix]
            attribute_name = "xmlns" if prefix == "" else f"xmlns:{prefix}"
            result[attribute_name] = uri
        return result
