# Phase 1 Configuration Guide

## New `runtime.yaml` settings

```yaml
output:
  provider: LOCAL                 # LOCAL | SFTP
  local_path: ./archive_migration_validation/generated_packages

input:
  provider: LOCAL                 # LOCAL | S3
  local_path: ./Input

dashboard:
  reports_path: ./archive_migration_validation

logging:
  level: INFO                     # DEBUG | INFO | WARNING | ERROR | CRITICAL
```

All relative paths resolve against the repo root (`meca-package/`), not the
process's working directory — see `_resolve_path()` in
`scripts/archive_migration_batch.py`.

## Provider selection

`input.provider` / `output.provider` select a concrete provider via
`create_input_provider()` / `create_output_provider()`
(`src/meca_engine/providers/{input,output}.py`):

| provider value | class | status |
|---|---|---|
| `LOCAL` (input) | `LocalInputProvider` | implemented — lists/extracts local `.zip` files |
| `S3` (input) | `S3InputProvider` | placeholder — raises `ProviderNotConfiguredError` on use |
| `LOCAL` (output) | `LocalOutputProvider` | implemented — writes to a local directory |
| `SFTP` (output) | `SftpOutputProvider` | placeholder — raises `ProviderNotConfiguredError` on use |

An unrecognized provider value also raises `ProviderNotConfiguredError`
(schema validation already restricts the accepted enum values; this is
defense-in-depth in the factory).

## Why the output default is `archive_migration_validation/generated_packages`

`./Output` at the repo root holds 3 hand-curated reference MECA packages used
as the project's ground truth. `LocalOutputProvider` and `OutputSettings` are
built so they can never default there — enforced by a regression test
(`test_output_settings_defaults_never_point_to_output_folder`). Point
`output.local_path` elsewhere explicitly if you need a different location;
never point it at `./Output`.

## Adding S3 / SFTP later

1. Set `input.provider: S3` or `output.provider: SFTP` in `runtime.yaml` (the
   schema already accepts these values).
2. Implement the provider body in `S3InputProvider.list_articles()` /
   `.stage_article()` or `SftpOutputProvider.article_output_root()` — these
   currently just raise `ProviderNotConfiguredError`.
3. Add whatever connection settings the implementation needs (bucket,
   credentials, host, etc.) to `InputSettings` / `OutputSettings` and the
   corresponding JSON Schema, following the same pattern used for `local_path`.

No changes to `scripts/archive_migration_batch.py`, `PackageBuilder`, or any
generator are required — they only ever see the `InputProvider`/`OutputProvider`
interface.
