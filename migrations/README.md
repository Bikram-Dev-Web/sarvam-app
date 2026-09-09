# Database migrations

Alembic is the authoritative, versioned schema history for the SQLite database.

Apply every migration from the repository root:

```bash
python -m alembic upgrade head
```

The application retains a create-if-missing safeguard for local convenience, but
reviewers and deployments should apply migrations before seeding or starting the
server.
