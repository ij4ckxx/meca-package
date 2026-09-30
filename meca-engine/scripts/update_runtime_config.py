#!/usr/bin/env python
"""Update config/runtime.yaml with a partial set of changes, validating via ConfigLoader.

Reads a JSON object of partial updates from stdin (top-level section keys
matching runtime.yaml's own structure, e.g. ``{"concurrency": {"worker_count": 4}}``),
deep-merges them into the current file, and writes back only if the merged
result still validates — reusing :meth:`ConfigLoader.load_runtime_config`
(and therefore the existing JSON Schema) exactly as every other consumer
does, with zero new validation logic. On failure, the original file is
restored unchanged and this script exits non-zero with the error on stderr.

Known limitation: rewrites the whole file via ``yaml.safe_dump``, so
hand-written comments in ``runtime.yaml`` are not preserved across an
edit made through this script (round-trip-preserving YAML would need a
new dependency; not worth it for this).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

MECA_ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MECA_ENGINE_ROOT / "src"))

from meca_engine.config.loader import ConfigLoader  # noqa: E402
from meca_engine.exceptions import ConfigurationError  # noqa: E402


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def main() -> int:
    """Merge stdin's JSON updates into runtime.yaml, validating before committing."""
    updates = json.load(sys.stdin)
    config_path = MECA_ENGINE_ROOT / "config" / "runtime.yaml"
    original_text = config_path.read_text()
    current = yaml.safe_load(original_text)
    merged = _deep_merge(current, updates)

    config_path.write_text(yaml.safe_dump(merged, sort_keys=False))

    loader = ConfigLoader(
        config_dir=MECA_ENGINE_ROOT / "config",
        schema_dir=MECA_ENGINE_ROOT / "schemas" / "config-schema",
    )
    try:
        loader.load_runtime_config()
    except ConfigurationError as exc:
        config_path.write_text(original_text)
        print(f"Validation failed, reverted: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(merged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
