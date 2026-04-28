#!/usr/bin/env bash

set -euo pipefail

APP_NAME="lalagolf"
APP_USER="lalagolf"
APP_GROUP="lalagolf"
INSTALL_DIR="/opt/${APP_NAME}"
SYSTEMD_UNIT="/etc/systemd/system/${APP_NAME}.service"
ETC_DIR="/etc/${APP_NAME}"
ENV_FILE="${ETC_DIR}/${APP_NAME}.env"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_CONFIG=""

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "This script must be run as root."
        exit 1
    fi
}

cleanup() {
    if [[ -n "${TMP_CONFIG}" && -f "${TMP_CONFIG}" ]]; then
        rm -f "${TMP_CONFIG}"
    fi
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

    if [[ -f "${INSTALL_DIR}/conf/lalagolf.conf" ]]; then
        TMP_CONFIG="$(mktemp)"
        cp "${INSTALL_DIR}/conf/lalagolf.conf" "${TMP_CONFIG}"
    fi

    find "${INSTALL_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

    tar \
        --exclude=".git" \
        --exclude=".venv" \
        --exclude=".pytest_cache" \
        --exclude="__pycache__" \
        --exclude=".mypy_cache" \
        --exclude=".ruff_cache" \
        -C "${REPO_ROOT}" \
        -cf - . | tar -C "${INSTALL_DIR}" -xf -

    if [[ -n "${TMP_CONFIG}" && -f "${TMP_CONFIG}" ]]; then
        mkdir -p "${INSTALL_DIR}/conf"
        cp "${TMP_CONFIG}" "${INSTALL_DIR}/conf/lalagolf.conf"
    fi
}

setup_virtualenv() {
    python3 -m venv "${INSTALL_DIR}/.venv"
    "${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
    "${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"
}

setup_env_file() {
    mkdir -p "${ETC_DIR}"

    if [[ ! -f "${ENV_FILE}" ]]; then
        local secret
        secret="$("${INSTALL_DIR}/.venv/bin/python" -c 'import secrets; print(secrets.token_hex(32))')"
        cat > "${ENV_FILE}" <<EOF
LALAGOLF_SECRET_KEY=${secret}
FLASK_DEBUG=0
EOF
    fi
}

write_systemd_unit() {
    cat > "${SYSTEMD_UNIT}" <<EOF
[Unit]
Description=LalaGolf Flask Web Application
After=network.target
Wants=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${INSTALL_DIR}/.venv/bin/python ${INSTALL_DIR}/run_webapp.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
}

finalize_permissions() {
    chown -R "${APP_USER}:${APP_GROUP}" "${INSTALL_DIR}"
    chmod 750 "${INSTALL_DIR}"
    chmod 640 "${ENV_FILE}"
    chown root:"${APP_GROUP}" "${ENV_FILE}"
}

start_service() {
    systemctl daemon-reload
    systemctl enable --now "${APP_NAME}.service"
}

print_summary() {
    cat <<EOF
Installation completed.

- App directory: ${INSTALL_DIR}
- Service: ${APP_NAME}.service
- Environment file: ${ENV_FILE}

Next steps:
1. Review ${INSTALL_DIR}/conf/lalagolf.conf
2. If needed, edit ${ENV_FILE}
3. Check service status with: systemctl status ${APP_NAME}.service
EOF
}

trap cleanup EXIT

require_root
create_service_user
prepare_install_dir
setup_virtualenv
setup_env_file
write_systemd_unit
finalize_permissions
start_service
print_summary
