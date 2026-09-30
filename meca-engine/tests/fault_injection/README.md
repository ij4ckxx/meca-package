# Fault-Injection Tests

In-process fault-injecting fake dependencies (S3, DOI Registry, Checkpoint
Store) exercising Retry/Recovery/Packaging-error scenarios — see
`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §11.6` and Test Specification
§20-24. Process-kill fault injection (for atomicity/restart proof) is a
separate, slower nightly-only variant per the same section.

**Empty in Milestone 1 (Foundation).** Populated once
`meca_engine.retry`, `meca_engine.recovery`, `meca_engine.checkpoint`, and
`meca_engine.registry` are implemented (Roadmap Phase 6).
