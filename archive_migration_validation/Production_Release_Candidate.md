# Production Release Candidate — v1.0.0-rc1

This repository, at the state left by this milestone, is the candidate
for a `v1.0.0` tag. No architecture was redesigned, no module was
rewritten, no new framework was introduced — this milestone found and
fixed genuine engineering debt and 2 real security defects, cleaned the
repository structure, and documented everything that needed
documenting, while leaving every already-working system untouched.

## What changed

- **Security**: fixed a real path-traversal vulnerability in the
  Dashboard API (`?batch=` accepted an unvalidated value) and a real
  zip-slip vulnerability in archive extraction — both confirmed
  exploitable before the fix, both verified fixed after.
- **Configuration**: `runtime.yaml` previously mixed live and
  silently-dead configuration sections with no way to tell them apart;
  every section is now clearly marked. No secrets found anywhere
  (already correctly handled before this milestone).
- **Performance**: fixed repeated full-file JSON parsing on every single
  Dashboard API call (now cached, mtime-invalidated); documented one
  further, lower-priority bottleneck (repeated directory scans) rather
  than risk a rushed fix.
- **Repository cleanup**: archived ~700MB of pre-existing, confirmed-
  unused-at-runtime milestone/verification output directories; deleted
  4 genuinely orphaned files (an abandoned prototype script, a
  duplicate XSLT file, a stray config backup, a stale build artifact);
  cleared 5 of my own accumulated verification-run batch directories
  from prior milestones this session.
- **Version freeze**: `VERSION.md` (repo root) now the single canonical
  location for every version identifier; engine version bumped
  `0.1.0` → `1.0.0-rc1` to reflect release-candidate status.
- **Documentation**: fixed 8 comments left stale by the repository
  cleanup (references to a path that was briefly moved, then restored).

## One correction made and disclosed

Initial cleanup archived `Output/` believing it unused; the required
full regression run caught that 5 golden tests read it directly. It was
restored immediately, comments were reverted to match, and the full
suite was re-run to confirm. This is recorded in full in
`Verification_Summary.md` — not smoothed over.

## What was reviewed and found already correct

Dashboard navigation/routing/dark-mode/downloads, API naming/response-
format/status-code consistency, HTML-escaping discipline across all 6
report generators, command-injection safety in every subprocess call,
config-write safety (schema-validated, rollback-on-failure), dead-
code/unused-import/TODO-marker sweep (zero findings — `ruff` already
enforces this on every file), and operator-facing error-message
specificity (spot-checked, found already detailed and non-vague).

## What was reviewed and intentionally left unchanged

- Two registered CLI commands (`seed-doi-registry`,
  `rebuild-golden-baseline`) have stale "not yet implemented" docstrings
  from Milestone 1, though their blocking conditions are long since
  resolved — flagged, not changed, since altering a public CLI command's
  behavior is a larger judgment call than a cleanup pass should make
  unilaterally.
- ~100+ JSON Schema properties lack `description` fields — the
  authoritative human-facing docs already live in the corresponding
  YAML files' own comments; fixing the schema layer too is a large,
  low-urgency effort deferred to a dedicated pass.
- No authentication exists on the Dashboard API — a known,
  pre-existing, explicitly out-of-scope gap for this milestone
  ("No Authentication" was an explicit exclusion).

## Full detail

`Repository_Cleanup.md`, `Configuration_Review.md`, `Security_Review.md`,
`API_Review.md`, `Dashboard_Review.md`, `Performance_Review.md`,
`Release_Checklist.md`, `Verification_Summary.md`, `VERSION.md`
(repo root).
