# Containerization

Planned per `14_LLD_05_TESTING_DEPLOYMENT_STANDARDS.md §12.4`: a
multi-stage `Dockerfile` (build stage running the full test suite, slim
runtime stage), `docker-compose.yml` (engine + LocalStack + Postgres for
local development per §12.1), and `entrypoint.sh`.

**Not implemented in Milestone 1 (Foundation).** Local development in this
milestone runs directly against a Python virtual environment
(see the root `README.md`'s "Local Setup" section) since there is no S3 or
database dependency yet to containerize against. Deferred to
`08_IMPLEMENTATION_ROADMAP.md` Phase 8.
