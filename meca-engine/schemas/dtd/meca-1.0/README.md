# Vendored DTD: meca-1.0

Per ADR-025 and Risk Register RISK-023: real DTD files, version-pinned,
required for structural validation of generated XML.

**Populated** — DTD-compliance milestone. `manifest-1.0.dtd`,
`reviews-1.0.dtd`, and `transfer-1.0.dtd` are vendored verbatim from
the official NISO MECA repository:
https://github.com/niso-standards/meca/tree/main/schema (MIT License,
Copyright (c) 2022 National Information Standards Organization (Z39)).

All 3 MECA DTDs declare `<!ENTITY % xmlspecchars.ent PUBLIC ... "JATS-xmlspecchars1.ent">`
— the JATS DTD Suite's own character-entity module. `JATS-xmlspecchars1.ent`,
`JATS-chars1.ent`, and the `iso8879/`/`iso9573-13/` character-entity
directories are copied here from the same JATS Archiving 1.2 DTD Suite
vendored under `../jats-archiving-1.2/` (see that directory's README),
since each DTD resolves its relative `SYSTEM` references against its
own directory, not a shared one. Do not remove these — the 3 MECA DTDs
will fail to load without them.
