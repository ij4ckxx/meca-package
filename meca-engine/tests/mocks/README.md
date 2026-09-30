# Shared Fakes / Mocks

Shared fake implementations of pluggable interfaces, reused across unit,
integration, and fault-injection tests, per
`14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md` §11.2/§11.6.

**As of Milestone 2**: `fake_s3_client.py` provides `FakeS3Client`, an
in-memory stand-in for `S3ClientProtocol` (see
`meca_engine.input.readers.s3_reader`), supporting injected transient
failures for both listing and download operations. Used by
`tests/unit/input/test_s3_reader.py` and available for later milestones'
integration/fault-injection tests too.

A fake Checkpoint Store backend is not needed here —
`meca_engine.checkpoint.backends.in_memory.InMemoryCheckpointStore` is
itself a real, lightweight implementation suitable for tests directly.
