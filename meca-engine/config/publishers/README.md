# Publisher Configuration

One YAML file per onboarded publisher, validated against
`schemas/config-schema/publisher.schema.json` and loaded by
`meca_engine.config.loader.ConfigLoader.load_publisher_config`.

**This directory is intentionally empty in Milestone 1 (Foundation).**

Populating a real publisher file (e.g. `portland-press.yaml`) requires
**ADR-006** (transfer-source contact-name policy) to be confirmed — see
`02_ARCHITECTURE_DECISION_RECORDS.md` and `09_FINAL_READINESS_REPORT.md`.

A schema-conformant **example** fixture (with clearly fictitious values,
for testing the loader only — never real business data) lives at
`tests/fixtures/config/publishers/example-publisher.yaml`.
