"""Shared, dependency-free constants and enums used across the engine.

This module intentionally contains only foundational, non-business-specific
values: environment names, logging schema field/category names, default file
locations, and environment-variable names. It must never contain journal-,
publisher-, DOI-, license-, or media-type-specific values — those are
business configuration data (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §5) and
are deliberately out of scope for Milestone 1 (Foundation).

See:
    - 10_LLD_01_STRUCTURE_AND_PACKAGES.md §2 (package layering)
    - 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6.2 (structured log event schema)
"""

from __future__ import annotations

from enum import Enum, unique

APP_NAME: str = "meca-engine"
"""Human-readable application name, used in log output and CLI banners."""


@unique
class Environment(str, Enum):
    """Deployment environment an engine process considers itself running in.

    Read from the ``MECA_ENGINE_ENVIRONMENT`` environment variable at startup
    (12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §5; 14_LLD_05... §12.5).
    """

    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@unique
class LogCategory(str, Enum):
    """The five logging categories sharing one structured-event schema.

    See 12_LLD_03_CONFIG_LOGGING_EXCEPTIONS.md §6.1-6.2. All five categories
    are emitted through the same :class:`~meca_engine.logging_.structured_logger.StructuredLogger`
    and differ only by this field's value plus which sinks/retention apply.
    """

    STRUCTURED = "structured"
    AUDIT = "audit"
    PERFORMANCE = "performance"
    ERROR = "error"
    DEBUG = "debug"


@unique
class LogSeverity(str, Enum):
    """Severity levels for a structured log event (12_LLD_03 §6.2)."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# --- Structured log event field names (12_LLD_03 §6.2) ---
# Centralised here so every log-emitting call site and every log-schema
# validator agree on the exact field name, without repeating string literals.
LOG_FIELD_TIMESTAMP: str = "timestamp"
LOG_FIELD_CORRELATION_ID: str = "correlation_id"
LOG_FIELD_TRACE_ID: str = "trace_id"
LOG_FIELD_STAGE: str = "stage"
LOG_FIELD_CATEGORY: str = "category"
LOG_FIELD_SEVERITY: str = "severity"
LOG_FIELD_RULE_ID: str = "rule_id"
LOG_FIELD_MESSAGE: str = "message"
LOG_FIELD_CONTEXT: str = "context"
LOG_FIELD_DURATION_MS: str = "duration_ms"

# --- Environment variable names (12_LLD_03 §5; 14_LLD_05 §12.3) ---
ENV_VAR_ENVIRONMENT: str = "MECA_ENGINE_ENVIRONMENT"
ENV_VAR_CONFIG_DIR: str = "MECA_ENGINE_CONFIG_DIR"
ENV_VAR_DEBUG_LOGGING: str = "MECA_ENGINE_DEBUG_LOGGING"

# --- Default filesystem locations (10_LLD_01 §1) ---
DEFAULT_CONFIG_DIR: str = "config"
DEFAULT_CONFIG_SCHEMA_DIR: str = "schemas/config-schema"
DEFAULT_RUNTIME_CONFIG_FILENAME: str = "runtime.yaml"
DEFAULT_FEATURE_FLAGS_FILENAME: str = "feature-flags.yaml"

# --- Timestamp format (12_LLD_03 §6.2: "UTC, ISO-8601, millisecond precision") ---
LOG_TIMESTAMP_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%fZ"
