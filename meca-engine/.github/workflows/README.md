# CI/CD Workflows

Planned per `14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §12.2`:
`ci.yml` (lint/type-check/unit/integration on every PR), `golden-regression.yml`
(mandatory merge gate against the 3 real samples), `release.yml` (build +
push on tag), plus a nightly/scheduled performance + fault-injection
pipeline.

**Not implemented in Milestone 1 (Foundation).** `make lint`,
`make typecheck`, and `make test` (see `Makefile`) already provide the
local equivalent of what `ci.yml` will automate; wiring them into an actual
CI provider is deferred to the milestone that also stands up the
Docker/AWS deployment path (`08_IMPLEMENTATION_ROADMAP.md` Phase 8).
