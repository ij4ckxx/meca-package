# Journal Configuration

One YAML file per onboarded journal, validated against
`schemas/config-schema/journal.schema.json` and loaded by
`meca_engine.config.loader.ConfigLoader.load_journal_config`.

**This directory is intentionally empty in Milestone 1 (Foundation).**

Populating a real journal file (e.g. `clinical-science.yaml`) requires the
following Architecture Decision Records to be confirmed first — see
`02_ARCHITECTURE_DECISION_RECORDS.md` and `09_FINAL_READINESS_REPORT.md`:

- **ADR-007** — the correct `acronym` value.
- **ADR-001** — the `article_type_mapping_ref` table this journal uses.
- **ADR-002** — the `license_templates_ref` table this journal uses.
- **ADR-015** — the `doi_registry_scope` for this journal.

`ConfigLoader` will refuse to load any journal file whose value for a
required field starts with the literal placeholder prefix
`<CONFIRM-VIA-...>`, raising `ConfigurationError` — see
`meca_engine.config.loader._reject_placeholder_values`. This is a
deliberate safeguard against ever accidentally shipping an unconfirmed
business value.

A schema-conformant **example** fixture (with clearly fictitious values,
for testing the loader only — never real business data) lives at
`tests/fixtures/config/journals/example-journal.yaml`.
