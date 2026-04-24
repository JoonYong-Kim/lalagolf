#!/usr/bin/env bash

set -euo pipefail

APP_NAME="lalagolf"
APP_USER="lalagolf"
APP_GROUP="lalagolf"
INSTALL_DIR="/opt/${APP_NAME}"
SYSTEMD_UNIT="/etc/systemd/system/${APP_NAME}.service"
ETC_DIR="/etc/${APP_NAME}"
USER_REMOVED="no"
GROUP_REMOVED="no"
REMAINING_PIDS=""

find_user_processes() {
    ps -u "${APP_USER}" -o pid= 2>/dev/null | awk '{$1=$1; print}' || true
}

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
        REMAINING_PIDS="$(find_user_processes)"
        if [[ -n "${REMAINING_PIDS}" ]]; then
            echo "Cannot remove user ${APP_USER}: active process(es): ${REMAINING_PIDS}"
        else
            if userdel "${APP_USER}"; then
                USER_REMOVED="yes"
            fi
        fi
    fi

    if getent group "${APP_GROUP}" >/dev/null; then
        if ! getent passwd "${APP_USER}" >/dev/null; then
            if groupdel "${APP_GROUP}"; then
                GROUP_REMOVED="yes"
            fi
        else
            echo "Cannot remove group ${APP_GROUP}: primary group for user ${APP_USER} still exists."
        fi
    fi
}

print_summary() {
    if [[ "${USER_REMOVED}" == "yes" && "${GROUP_REMOVED}" == "yes" ]]; then
        status_line="Uninstall completed."
    else
        status_line="Uninstall completed with warnings."
    fi

    cat <<EOF
${status_line}

- Removed: ${INSTALL_DIR}
- Removed: ${ETC_DIR}
- Removed: ${SYSTEMD_UNIT}
EOF

    if id -u "${APP_USER}" >/dev/null 2>&1; then
        cat <<EOF

- Remaining user: ${APP_USER}
EOF
        if [[ -n "${REMAINING_PIDS}" ]]; then
            cat <<EOF
- Active process(es): ${REMAINING_PIDS}
- Next step: stop those processes, then run \`userdel ${APP_USER}\`
EOF
        fi
    fi

    if getent group "${APP_GROUP}" >/dev/null; then
        cat <<EOF
- Remaining group: ${APP_GROUP}
- Next step: after removing user ${APP_USER}, run \`groupdel ${APP_GROUP}\`
EOF
    fi
}

require_root
stop_and_disable_service
remove_files
remove_service_user
print_summary
