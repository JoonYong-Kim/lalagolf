#!/usr/bin/env bash

set -euo pipefail

APP_NAME="lalagolf"
APP_USER="lalagolf"
APP_GROUP="lalagolf"
INSTALL_DIR="/opt/${APP_NAME}"
SYSTEMD_UNIT="/etc/systemd/system/${APP_NAME}.service"
ETC_DIR="/etc/${APP_NAME}"

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "This script must be run as root."
        exit 1
    fi
}

stop_and_disable_service() {
    if systemctl list-unit-files | grep -q "^${APP_NAME}\.service"; then
        systemctl disable --now "${APP_NAME}.service" || true
    fi

    if [[ -f "${SYSTEMD_UNIT}" ]]; then
        rm -f "${SYSTEMD_UNIT}"
    fi

    systemctl daemon-reload
}

remove_files() {
    rm -rf "${INSTALL_DIR}"
    rm -rf "${ETC_DIR}"
}

remove_service_user() {
    if id -u "${APP_USER}" >/dev/null 2>&1; then
        userdel "${APP_USER}" || true
    fi

    if getent group "${APP_GROUP}" >/dev/null; then
        groupdel "${APP_GROUP}" || true
    fi
}

print_summary() {
    cat <<EOF
Uninstall completed.

- Removed: ${INSTALL_DIR}
- Removed: ${ETC_DIR}
- Removed: ${SYSTEMD_UNIT}
EOF
}

require_root
stop_and_disable_service
remove_files
remove_service_user
print_summary
