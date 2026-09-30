# Integration Tests

Multi-module flows against faked externals — see
`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §11.2`.

**Empty in Milestone 1 (Foundation).** Milestone 1's modules
(Configuration, Logging, Exceptions, DI container, CLI) are already
exercised together end-to-end by `tests/unit/test_container.py` and
`tests/unit/cli/test_main.py` (both invoke the real bootstrap path against
real fixture configuration), so a separate integration layer adds no
value yet. True cross-module integration tests (e.g. extraction → ICAM →
generators) are populated once those packages exist (Roadmap Phases 2-4).
