# Deployment

Development uses Docker Compose for PostgreSQL/pgvector and Redis, with API and dashboard runnable either on the host or in containers. Configuration comes from environment variables based on `.env.example`; secrets are never committed.

The API exposes liveness separately from dependency readiness. Containers run as non-root where practical, use pinned production base images, and persist database/workspace data in explicit volumes. Database schema changes will use migrations before the first production deployment.

Initial deployment is local-first on the owner’s Mac. Remote access, TLS, authentication, backups, restore drills, telemetry export, and multi-host scheduling are later production concerns and must be enabled before exposing the control plane beyond localhost.

Standard commands are `make install`, `make infra-up`, `make api`, `make dashboard`, `make dev`, and `make check`. `CURRENT_STATE.md` records which have been verified in the current milestone.

