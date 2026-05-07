# GolfRaiders v2 Operations

## Production Environment Checklist

- Set `LALAGOLF_ENV=production`.
- Set a non-placeholder `SECRET_KEY` from a secret manager or host environment.
- Set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- Restrict `CORS_ORIGINS` to the production web origin.
- Set `WEB_BASE_URL` to the production web origin.
- Set `NEXT_PUBLIC_API_BASE_URL` to the public API base path, e.g. `https://api.example.com/api/v1`.
- Point `DATABASE_URL` and `REDIS_URL` at managed or backed-up services.
- Store `UPLOAD_STORAGE_DIR` outside public web/static paths and include it in backups.
- Keep `LOG_LEVEL=INFO` for normal operation and use `REQUEST_ID_HEADER=X-Request-ID`.
- Keep `OLLAMA_ENABLED=false` unless a reachable Ollama host and timeout are configured.
- If Google sign-in is enabled, set `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and
  `GOOGLE_OAUTH_REDIRECT_URI`. The redirect URI must match the Google console configuration, for
  example `https://api.example.com/api/v1/auth/google/callback`.
- Run `npm run security-check`, API tests, frontend build, and migration dry-run report before release.

## Systemd Deployment

The MVP systemd installer lives at `v2/scripts/install_systemd.sh`.

```bash
cd v2
sudo bash scripts/install_systemd.sh
```

It creates:

- `/opt/lalagolf-v2`
- `/etc/lalagolf-v2/lalagolf-v2.env`
- `/var/lib/lalagolf-v2/uploads`
- `lalagolf-v2-api.service`
- `lalagolf-v2-worker.service`
- `lalagolf-v2-web.service`

The script installs Python dependencies into per-service virtualenvs, runs `npm ci` and
`npm run build`, writes systemd units, and starts the services. It also runs `alembic upgrade head`
unless `SKIP_DB_MIGRATION=true` is set for the installer process.

The default installer environment binds the web service to port `2323` and the API service to port
`2324`. Adjust reverse proxy, firewall, `CORS_ORIGINS`, `WEB_BASE_URL`, and
`NEXT_PUBLIC_API_BASE_URL` together when changing those ports.

Before running it, make sure PostgreSQL and Redis are reachable from the values in
`/etc/lalagolf-v2/lalagolf-v2.env` or edit that file after the first run and restart services:

```bash
sudo systemctl restart lalagolf-v2-api.service lalagolf-v2-worker.service lalagolf-v2-web.service
```

Uninstall:

```bash
cd v2
sudo bash scripts/uninstall_systemd.sh
```

The uninstall script stops and removes the three units and deletes `/opt/lalagolf-v2`,
`/etc/lalagolf-v2`, and `/var/lib/lalagolf-v2`.

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

Local admin access is role-based. The default import owner is `owner@example.com` / `password`, but it
is a normal user unless promoted:

```sql
update users set role = 'admin' where email = 'owner@example.com';
```

After promotion, log out and log back in so the frontend reloads the current user role and exposes
the admin navigation item.
