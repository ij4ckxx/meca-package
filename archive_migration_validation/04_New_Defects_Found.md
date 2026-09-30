# Newly Discovered Engine Defects

Two real defects were found and fixed as part of this milestone's exception-by-exception review (`02_Recovery_Matrix.md`). Both are narrowly scoped, low-risk, and confirmed via regression tests plus the full 37-package batch.

## 1. File-matching tolerance tier compared the wrong string

**File:** `src/meca_engine/extraction/file_resolver.py`, `_match_in_directory` (tier 3).

The tier's own module docstring claimed to handle a physical file carrying a disambiguating numeric suffix (e.g. `"Cover Letter (2).pdf"` vs. a declared `"Cover Letter.pdf"`) — but the comparison checked the physical file's extension-less stem against the declared name **including its extension**, which can never match for any input. First surfaced in the prior production-validation round (`bst-2025-3127`, `cs-2025-6619`) as two real, otherwise-unexplained failures. Fixed by comparing against the declared stem instead. Confirmed by both real packages now resolving correctly and 2 new regression tests (`test_suffix_variant_with_extension_now_resolves`, plus the existing tolerance-tier tests all still passing).

## 2. A bare `ValueError` violated the exception hierarchy's own contract

**File:** `src/meca_engine/transform/coordinator.py`, `_reconcile_file_entry_round_labels`.

The codebase's exception hierarchy documentation (`exceptions/base.py`) states "every exception raised anywhere in the engine must be a subclass of `MecaEngineError`... never a bare stdlib exception," but this one internal-invariant check raised a plain `ValueError`. Needed fixing regardless of this milestone's other changes, since the function's contract changed (partial resolution is now expected); fixed to raise `ModelBuildError` instead, correctly classified as `FAILED_ENGINE`.

## Nothing else found

The remaining ~25 exception-raising sites reviewed in `02_Recovery_Matrix.md` were all already correctly implemented for what they guard against — no other latent bugs were found. The full 37-package end-to-end run hit zero `FAILED_ENGINE`/`FAILED_FATAL` outcomes, so no additional defect was surfaced by live data either.
