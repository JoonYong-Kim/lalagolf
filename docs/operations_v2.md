# LalaGolf v2 Operations

## Production Environment Checklist

- Set `LALAGOLF_ENV=production`.
- Set a non-placeholder `SECRET_KEY` from a secret manager or host environment.
- Set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- Restrict `CORS_ORIGINS` to the production web origin.
- Point `DATABASE_URL` and `REDIS_URL` at managed or backed-up services.
- Store `UPLOAD_STORAGE_DIR` outside public web/static paths and include it in backups.
- Keep `LOG_LEVEL=INFO` for normal operation and use `REQUEST_ID_HEADER=X-Request-ID`.
- Keep `OLLAMA_ENABLED=false` unless a reachable Ollama host and timeout are configured.
- Run `npm run security-check`, API tests, frontend build, and migration dry-run report before release.

## Backup

Back up PostgreSQL and uploaded source files together. The database contains metadata and
analytics rows; `UPLOAD_STORAGE_DIR` contains original private uploads referenced by
`source_files.storage_key`.

```bash
pg_dump "$DATABASE_URL" --format=custom --file=backup/lalagolf_v2.dump
tar -C "$UPLOAD_STORAGE_DIR" -czf backup/lalagolf_uploads.tgz .
```

Keep backups encrypted at rest. Retain at least one recent backup that has been restored in a
non-production environment.

## Restore

Restore into an empty database, then restore uploads to the configured storage directory.

```bash
pg_restore --clean --if-exists --dbname "$DATABASE_URL" backup/lalagolf_v2.dump
mkdir -p "$UPLOAD_STORAGE_DIR"
tar -C "$UPLOAD_STORAGE_DIR" -xzf backup/lalagolf_uploads.tgz
```

After restore:

- Run `alembic upgrade head`.
- Run API health checks.
- Spot-check login, dashboard, round detail, upload review, Ask, and shared round pages.
- Run migration/report scripts only against a staging copy unless explicitly doing a migration.

## Logs

API responses include `X-Request-ID`. If the client sends that header, the API reuses it; otherwise
the API generates one. Request completion logs include request id, method, path, status code, and
duration. Upload parse/commit logs include `job_id`.

Worker logs include `job_id` where a job context is available. Ask logs emit a warning when Ollama
wording is enabled but the MVP deterministic answer path is used.

## Admin Upload Errors

Admins can inspect failed upload parses at `/admin/uploads/errors`. The API route is
`GET /api/v1/admin/uploads/errors` and requires `role=admin`. The page is intentionally minimal for
MVP operations and shows filename, failed status, warning codes, and creation time.
