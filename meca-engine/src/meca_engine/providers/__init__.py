"""Provider Framework — Archive Migration Platform Phase 1 (ADR-030).

Lets the batch pipeline obtain its input/output locations through
configuration (:class:`~meca_engine.config.schema.InputSettings`/
:class:`~meca_engine.config.schema.OutputSettings`) rather than hard-coded
paths, so a future S3/SFTP-backed deployment only requires implementing
new provider classes — no change to the conversion engine itself.

Relationship to the pre-existing, never-wired-in ``input.readers``/
``input.discovery``/``input.staging`` modules (Milestone 2): those model
a lower-level, per-round file-listing concern for an already-unzipped
folder tree, and were never adopted by any production entry point. This
package's ``LocalInputProvider`` targets the *actual* current production
shape (one ``.zip`` archive per article) directly, since adapting the old
readers to that shape would mean modifying them — out of scope for an
infrastructure-only phase. ``input.readers``/``input.discovery``/
``input.staging`` are therefore superseded by this package and are
candidates for removal in a later cleanup phase; see
``10_Phase1_Implementation_Summary.md`` for the full rationale.
"""

from __future__ import annotations
