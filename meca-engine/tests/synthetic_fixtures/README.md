# Synthetic Fixture Tests

Covers every scenario the 3 real samples cannot (0/1/3+/10-round articles,
malformed XML, non-CC-BY license, a second journal, etc.) — see
`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §11.4` and
`04_PRODUCT_BACKLOG.md` Epic 15 Feature 15.2.

**Empty in Milestone 1 (Foundation).** The config-loading synthetic
fixtures that already exist for Milestone 1 live under
`tests/fixtures/config/` instead, since they test the Configuration
Framework directly rather than the full article pipeline.
