"""Reproducibility metadata — Migration Audit milestone.

Answers "what produced this package, and can we reproduce it later" —
version/configuration facts only, never machine-specific secrets
(hostname, username, IP/MAC address, environment variables). Every
value here is either an existing, real constant already in the
codebase (``meca_engine.__version__``, the Recovery Rule catalog's own
count) or a deterministic hash/timestamp computed from the actual
config objects a given package was built with.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from meca_engine import __version__
from meca_engine.model.recovery_rules import ALL_RECOVERY_RULES

if TYPE_CHECKING:
    from meca_engine.config.schema import FeatureFlagsConfig, RuntimeConfig

# Manually kept in sync with `01_BUSINESS_RULE_BOOK.md`'s own "Rule Count
# Summary" footer — the same manual-maintenance convention already used
# by `reporting.aggregation.ALL_BUSINESS_RULE_IDS` (there: BR-001..BR-160;
# the Book itself is at BR-164 as of BR-164's own implementation).
# No machine-readable version field exists in the Book to read this from
# automatically.
BUSINESS_RULE_BOOK_VERSION = "164 rules (BR-001-BR-164)"

# `len(ALL_RECOVERY_RULES)` is real or the only "version" the Recovery
# Rule catalog has (`model/recovery_rules.py` has no version field).
RECOVERY_RULE_VERSION = f"{len(ALL_RECOVERY_RULES)} rules (RR-001-RR-{len(ALL_RECOVERY_RULES):03d})"

# Mirrors the vendored DTD directory names `validation/xml_validator.py`'s
# `_DTD_BY_SUFFIX` maps every generated file to — those directories'
# READMEs are the only place these version strings are documented.
DTD_VERSION = "jats-archiving-1.2, meca-1.0"


@dataclass(frozen=True)
class ReproducibilityInfo:
    """What produced one package, and the facts needed to reproduce it later.

    Attributes:
        engine_version: ``meca_engine.__version__``.
        business_rule_book_version: See ``BUSINESS_RULE_BOOK_VERSION``.
        recovery_rule_version: See ``RECOVERY_RULE_VERSION``.
        dtd_version: The vendored DTD suite names validation runs against.
        config_checksum: SHA-256 of a deterministic JSON snapshot of the
            ``RuntimeConfig``/``FeatureFlagsConfig`` this package was
            built with — never ``AppConfig.environment_settings``
            (``.env``-sourced, may carry secrets/paths).
        generation_timestamp: UTC ISO-8601, captured when this info was built.
        python_version: ``platform.python_version()`` — interpreter
            version only, not machine-identifying.
        operating_system: ``"<system> <release>"`` (e.g. ``"Darwin 25.6.0"``)
            — OS family/version only, never hostname/user/IP/MAC.
    """

    engine_version: str
    business_rule_book_version: str
    recovery_rule_version: str
    dtd_version: str
    config_checksum: str
    generation_timestamp: str
    python_version: str
    operating_system: str

    def to_dict(self) -> dict[str, Any]:
        """Render as a plain, ``json.dumps``-ready dict."""
        return {
            "engine_version": self.engine_version,
            "business_rule_book_version": self.business_rule_book_version,
            "recovery_rule_version": self.recovery_rule_version,
            "dtd_version": self.dtd_version,
            "config_checksum": self.config_checksum,
            "generation_timestamp": self.generation_timestamp,
            "python_version": self.python_version,
            "operating_system": self.operating_system,
        }


def compute_config_checksum(
    runtime_config: RuntimeConfig, feature_flags: FeatureFlagsConfig
) -> str:
    """SHA-256 hex digest of the exact config this package was built with.

    Deliberately scoped to ``RuntimeConfig``/``FeatureFlagsConfig`` only
    (operational/behavioral settings, per their own docstrings) — never
    ``AppConfig.environment_settings``, which is ``.env``-sourced and may
    carry secrets or local file paths.
    """
    payload = json.dumps(
        {
            "runtime_config": dataclasses.asdict(runtime_config),
            "feature_flags": dataclasses.asdict(feature_flags),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_reproducibility_info(
    runtime_config: RuntimeConfig,
    feature_flags: FeatureFlagsConfig,
    *,
    config_checksum: str | None = None,
) -> ReproducibilityInfo:
    """Build this package's reproducibility record.

    Args:
        runtime_config: The batch's runtime settings.
        feature_flags: The batch's feature-flag settings.
        config_checksum: Reuse an already-computed
            :func:`compute_config_checksum` result instead of recomputing
            it here. A caller processing many articles from the same,
            never-mutated config (e.g. :class:`~meca_engine.service.worker.Worker`,
            "every dependency constructed once per batch") should compute
            it once and pass it in — only ``generation_timestamp``
            genuinely needs to vary per call. ``None`` computes it fresh,
            unchanged from before this parameter existed.
    """
    return ReproducibilityInfo(
        engine_version=__version__,
        business_rule_book_version=BUSINESS_RULE_BOOK_VERSION,
        recovery_rule_version=RECOVERY_RULE_VERSION,
        dtd_version=DTD_VERSION,
        config_checksum=config_checksum or compute_config_checksum(runtime_config, feature_flags),
        generation_timestamp=datetime.now(timezone.utc).isoformat(),
        python_version=platform.python_version(),
        operating_system=f"{platform.system()} {platform.release()}",
    )
