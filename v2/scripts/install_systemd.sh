#!/usr/bin/env bash

set -euo pipefail

APP_NAME="lalagolf-v2"
APP_USER="lalagolf-v2"
APP_GROUP="lalagolf-v2"
INSTALL_DIR="/opt/${APP_NAME}"
ETC_DIR="/etc/${APP_NAME}"
ENV_FILE="${ETC_DIR}/${APP_NAME}.env"
DATA_DIR="/var/lib/${APP_NAME}"
UPLOAD_DIR="${DATA_DIR}/uploads"

API_UNIT="/etc/systemd/system/${APP_NAME}-api.service"
WEB_UNIT="/etc/systemd/system/${APP_NAME}-web.service"
WORKER_UNIT="/etc/systemd/system/${APP_NAME}-worker.service"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V2_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NPM_BIN=""

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "This script must be run as root."
        exit 1
    fi
}

require_commands() {
    local missing=()
    for command in python3 npm systemctl tar; do
        if ! command -v "${command}" >/dev/null 2>&1; then
            missing+=("${command}")
        fi
    done
    if [[ "${#missing[@]}" -gt 0 ]]; then
        echo "Missing required command(s): ${missing[*]}"
        exit 1
    fi
    NPM_BIN="$(command -v npm)"
}

create_service_user() {
    if ! getent group "${APP_GROUP}" >/dev/null; then
        groupadd --system "${APP_GROUP}"
    fi

    if ! id -u "${APP_USER}" >/dev/null 2>&1; then
        useradd --system \
            --gid "${APP_GROUP}" \
            --home-dir "${INSTALL_DIR}" \
            --create-home \
            --shell /usr/sbin/nologin \
            "${APP_USER}"
    fi
}

prepare_install_dir() {
    mkdir -p "${INSTALL_DIR}"
    find "${INSTALL_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

    tar \
        --exclude=".next" \
        --exclude=".venv" \
        --exclude="node_modules" \
        --exclude=".pytest_cache" \
        --exclude=".ruff_cache" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        -C "${V2_ROOT}" \
        -cf - . | tar -C "${INSTALL_DIR}" -xf -
}

setup_env_file() {
    mkdir -p "${ETC_DIR}" "${UPLOAD_DIR}"

    if [[ ! -f "${ENV_FILE}" ]]; then
        local secret
        local public_host
        local public_web_origin
        local public_api_base_url
        local cors_origins
        local google_oauth_redirect_uri
        secret="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
        public_host="${PUBLIC_HOST:-${LALAGOLF_PUBLIC_HOST:-$(hostname -f 2>/dev/null || hostname)}}"
        public_web_origin="${PUBLIC_WEB_ORIGIN:-${WEB_BASE_URL:-http://${public_host}:2323}}"
        public_api_base_url="${PUBLIC_API_BASE_URL:-${NEXT_PUBLIC_API_BASE_URL:-http://${public_host}:2324/api/v1}}"
        cors_origins="${CORS_ORIGINS:-${public_web_origin}}"
        google_oauth_redirect_uri="${GOOGLE_OAUTH_REDIRECT_URI:-${public_api_base_url}/auth/google/callback}"
        cat > "${ENV_FILE}" <<EOF
LALAGOLF_ENV=production
NEXT_PUBLIC_API_BASE_URL=${public_api_base_url}
DATABASE_URL=postgresql+psycopg://lalagolf:lalagolf@localhost:5432/lalagolf_v2
REDIS_URL=redis://localhost:6379/0
ANALYSIS_ENQUEUE_ENABLED=true
SECRET_KEY=${secret}
SESSION_COOKIE_NAME=lalagolf_session
SESSION_COOKIE_SECURE=true
SESSION_LIFETIME_DAYS=30
REQUEST_ID_HEADER=X-Request-ID
LOG_LEVEL=INFO
UPLOAD_STORAGE_DIR=${UPLOAD_DIR}
UPLOAD_MAX_BYTES=1000000
CORS_ORIGINS=${cors_origins}
WEB_BASE_URL=${public_web_origin}
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=${google_oauth_redirect_uri}
ANALYSIS_QUEUE_NAME=analysis
RQ_QUEUES=analysis
WORKER_USE_RQ=true
WORKER_POLL_INTERVAL_SECONDS=5
OLLAMA_ENABLED=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
OLLAMA_TIMEOUT_SECONDS=5
EOF
    else
        echo "Keeping existing ${ENV_FILE}. Review NEXT_PUBLIC_API_BASE_URL, CORS_ORIGINS, WEB_BASE_URL, and GOOGLE_OAUTH_REDIRECT_URI for the public host."
    fi
}

load_env_for_install() {
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
}

setup_api() {
    python3 -m venv "${INSTALL_DIR}/api/.venv"
    "${INSTALL_DIR}/api/.venv/bin/pip" install --upgrade pip
    "${INSTALL_DIR}/api/.venv/bin/pip" install -e "${INSTALL_DIR}/packages/analytics_core"
    "${INSTALL_DIR}/api/.venv/bin/pip" install -e "${INSTALL_DIR}/api"
}

setup_worker() {
    python3 -m venv "${INSTALL_DIR}/worker/.venv"
    "${INSTALL_DIR}/worker/.venv/bin/pip" install --upgrade pip
    "${INSTALL_DIR}/worker/.venv/bin/pip" install -e "${INSTALL_DIR}/packages/analytics_core"
    "${INSTALL_DIR}/worker/.venv/bin/pip" install -e "${INSTALL_DIR}/api"
    "${INSTALL_DIR}/worker/.venv/bin/pip" install -e "${INSTALL_DIR}/worker"
}

setup_web() {
    npm --prefix "${INSTALL_DIR}/web" ci
    npm --prefix "${INSTALL_DIR}/web" run build
}

run_migrations() {
    if [[ "${SKIP_DB_MIGRATION:-false}" == "true" ]]; then
        echo "Skipping Alembic migration because SKIP_DB_MIGRATION=true"
        return
    fi
    (
        cd "${INSTALL_DIR}/api"
        "${INSTALL_DIR}/api/.venv/bin/alembic" upgrade head
    )
}

write_systemd_units() {
    cat > "${API_UNIT}" <<EOF
[Unit]
Description=LalaGolf v2 API
After=network.target
Wants=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${INSTALL_DIR}/api
EnvironmentFile=${ENV_FILE}
ExecStart=${INSTALL_DIR}/api/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 2324
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    cat > "${WORKER_UNIT}" <<EOF
[Unit]
Description=LalaGolf v2 Worker
After=network.target ${APP_NAME}-api.service
Wants=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${INSTALL_DIR}/worker/.venv/bin/python -m lalagolf_worker.main
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    cat > "${WEB_UNIT}" <<EOF
[Unit]
Description=LalaGolf v2 Web
After=network.target ${APP_NAME}-api.service
Wants=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${INSTALL_DIR}/web
EnvironmentFile=${ENV_FILE}
ExecStart=${NPM_BIN} run start -- --hostname 0.0.0.0 --port 2323
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
}

finalize_permissions() {
    chown -R "${APP_USER}:${APP_GROUP}" "${INSTALL_DIR}" "${DATA_DIR}"
    chmod 750 "${INSTALL_DIR}" "${DATA_DIR}"
    chmod 750 "${UPLOAD_DIR}"
    chmod 640 "${ENV_FILE}"
    chown root:"${APP_GROUP}" "${ENV_FILE}"
}

start_services() {
    systemctl daemon-reload
    systemctl enable --now \
        "${APP_NAME}-api.service" \
        "${APP_NAME}-worker.service" \
        "${APP_NAME}-web.service"
}

print_summary() {
    cat <<EOF
LalaGolf v2 systemd installation completed.

- Install directory: ${INSTALL_DIR}
- Environment file: ${ENV_FILE}
- Upload storage: ${UPLOAD_DIR}
- Services:
  - ${APP_NAME}-api.service
  - ${APP_NAME}-worker.service
  - ${APP_NAME}-web.service

Next steps:
1. Review ${ENV_FILE}
2. Ensure PostgreSQL and Redis match DATABASE_URL and REDIS_URL
3. Check status with:
   systemctl status ${APP_NAME}-api.service
   systemctl status ${APP_NAME}-worker.service
   systemctl status ${APP_NAME}-web.service
EOF
}

require_root
require_commands
create_service_user
prepare_install_dir
setup_env_file
load_env_for_install
setup_api
setup_worker
setup_web
run_migrations
write_systemd_units
finalize_permissions
start_services
print_summary
