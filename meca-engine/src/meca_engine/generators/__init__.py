"""The Generator Framework, plus the 5 output-XML generators it serves.

The framework — :mod:`meca_engine.generators.base`, `.context`, `.result`,
`.diagnostics`, `.validation_hooks`, and `.xml.*` — was implemented in
Milestone 6A and contains no business-rule or JATS/MECA-mapping logic.

No generator may import another generator subpackage, and none may parse
source XML directly, read a staged file path, or call an S3 client —
every generator consumes only the ICAM, reached exclusively through
:class:`~meca_engine.generators.context.GeneratorContext`.

**The 5 concrete generators are not implemented yet.** See
11_LLD_02_CANONICAL_MODEL_AND_CLASSES.md §4.7 for the full design and
`08_IMPLEMENTATION_ROADMAP.md` for the phase that implements each one.
Each subpackage is still an empty, importable stub — implementing any of
them is explicitly out of Milestone 6A's scope.
"""

from __future__ import annotations
