"""XsltRawXmlGenerator — Milestone 9.

An alternative `raw_xml` generator that produces raw.xml by applying
`rawtocleanup.xslt` directly to the original source XML
(`generators.raw_xml.xslt_transform`), instead of `RawXmlGenerator`'s
ICAM-field-by-field reconstruction. See that module's docstring, and
`generators/base.py`'s module docstring, for why this is the one
documented exception to "the ICAM is the only route to article data."

**Not yet wired into `PackageBuilder`** — this class exists side-by-side
with `RawXmlGenerator`, independently testable, so its output can be
verified against real reference packages before any cutover decision is
made. `ArticleXmlGenerator` is expected to compose against this
generator's output unchanged (it already treats raw.xml as an opaque,
re-parsed XML tree for everything it copies verbatim — see that
module's own docstring), but that composition has not yet been
exercised end-to-end as part of this milestone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from meca_engine.exceptions import GeneratorInvariantError
from meca_engine.generators.base import BaseGenerator
from meca_engine.generators.raw_xml.document import RawXmlDocument
from meca_engine.generators.raw_xml.xslt_transform import transform

if TYPE_CHECKING:
    from meca_engine.generators.context import GeneratorContext

_GENERATOR_NAME = "raw_xml"

# Must match `rawtocleanup.xslt`'s `match="article"` template, which
# hardcodes these 4 `xmlns:*` declarations on the root element (BR-037) —
# not independently configurable, unlike `RawXmlConfig.namespace_prefixes`.
_NAMESPACE_PREFIXES: tuple[str, ...] = ("mml", "xlink", "xsi", "ali")


class XsltRawXmlGenerator(BaseGenerator[RawXmlDocument]):
    """Generates raw.xml by applying `rawtocleanup.xslt` to the source XML."""

    @property
    def generator_name(self) -> str:
        """This generator's stable name, ``"raw_xml"`` — matches `RawXmlGenerator`."""
        return _GENERATOR_NAME

    @property
    def namespace_prefixes(self) -> tuple[str, ...]:
        """BR-037's namespace prefixes, hardcoded in `rawtocleanup.xslt`'s root template.

        Same purpose as `RawXmlGenerator.namespace_prefixes` — lets
        `ArticleXmlGenerator` re-parse this generator's raw.xml output
        without hard-coding a second, possibly-drifting copy of this
        prefix set.
        """
        return _NAMESPACE_PREFIXES

    def _generate(self, context: GeneratorContext) -> RawXmlDocument:
        article_id = context.model.identity.article_id
        if context.source_xml_bytes is None:
            raise GeneratorInvariantError(
                "XsltRawXmlGenerator requires GeneratorContext.source_xml_bytes",
                article_id=article_id,
                stage=f"generators.{_GENERATOR_NAME}",
            )

        xml_bytes = transform(context.source_xml_bytes, article_id=article_id)

        return RawXmlDocument(
            article_id=article_id,
            filename=f"{article_id}_raw.xml",  # BR-048
            xml_bytes=xml_bytes,
        )
