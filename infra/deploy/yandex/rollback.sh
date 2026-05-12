#!/usr/bin/env bash
set -euo pipefail

log() { printf '[rollback] %s\n' "$*"; }
err() { printf '[rollback][error] %s\n' "$*" >&2; }
die() { err "$*"; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Command not found: $1"; }

BACKEND_HOST="${BACKEND_HOST:-}"
BACKEND_SSH_USER="${BACKEND_SSH_USER:-}"
BACKEND_SSH_PORT="${BACKEND_SSH_PORT:-22}"
YCR_REGISTRY_HOST="${YCR_REGISTRY_HOST:-cr.yandex}"
YC_IAM_TOKEN="${YC_IAM_TOKEN:-}"
AUTO_CREATE_TOKEN="${AUTO_CREATE_TOKEN:-true}"

BACKEND_CONTAINER_NAME="${BACKEND_CONTAINER_NAME:-mental-health-backend}"
BACKEND_CONTAINER_PORT="${BACKEND_CONTAINER_PORT:-8000}"
BACKEND_REMOTE_APP_DIR="${BACKEND_REMOTE_APP_DIR:-/opt/mental-health}"
BACKEND_REMOTE_ENV_DIR="${BACKEND_REMOTE_ENV_DIR:-${BACKEND_REMOTE_APP_DIR}/config}"
BACKEND_REMOTE_RELEASES_DIR="${BACKEND_REMOTE_RELEASES_DIR:-${BACKEND_REMOTE_APP_DIR}/releases}"
BACKEND_REMOTE_BACKEND_ENV_FILE="${BACKEND_REMOTE_BACKEND_ENV_FILE:-${BACKEND_REMOTE_ENV_DIR}/backend.env}"
BACKEND_REMOTE_QWEN_ENV_FILE="${BACKEND_REMOTE_QWEN_ENV_FILE:-${BACKEND_REMOTE_ENV_DIR}/qwen.env}"

TARGET_IMAGE="${TARGET_IMAGE:-}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://${BACKEND_HOST}:${BACKEND_CONTAINER_PORT}/api/v1/health}"
HEALTHCHECK_ATTEMPTS="${HEALTHCHECK_ATTEMPTS:-20}"
HEALTHCHECK_INTERVAL_SEC="${HEALTHCHECK_INTERVAL_SEC:-3}"

[[ -n "${BACKEND_HOST}" ]] || die "Set BACKEND_HOST"
[[ -n "${BACKEND_SSH_USER}" ]] || die "Set BACKEND_SSH_USER"

require_cmd docker
require_cmd ssh
require_cmd curl

if [[ -z "${YC_IAM_TOKEN}" ]]; then
  if [[ "${AUTO_CREATE_TOKEN}" != "true" ]]; then
    die "Set YC_IAM_TOKEN or enable AUTO_CREATE_TOKEN=true"
  fi
  require_cmd yc
  log "Creating YC IAM token via yc CLI"
  YC_IAM_TOKEN="$(yc iam create-token)"
fi

REMOTE_TARGET="${BACKEND_SSH_USER}@${BACKEND_HOST}"
SSH_BASE=(ssh -p "${BACKEND_SSH_PORT}")

log "Rolling back on VM: ${BACKEND_HOST}"
ROLLED_BACK_IMAGE="$("${SSH_BASE[@]}" "${REMOTE_TARGET}" bash -s -- \
  "${YCR_REGISTRY_HOST}" \
  "${YC_IAM_TOKEN}" \
  "${BACKEND_CONTAINER_NAME}" \
  "${BACKEND_CONTAINER_PORT}" \
  "${BACKEND_REMOTE_RELEASES_DIR}" \
  "${BACKEND_REMOTE_BACKEND_ENV_FILE}" \
  "${BACKEND_REMOTE_QWEN_ENV_FILE}" \
  "${TARGET_IMAGE}" <<'REMOTE_SCRIPT'
set -euo pipefail

ycr_host="$1"
iam_token="$2"
container_name="$3"
container_port="$4"
remote_releases_dir="$5"
backend_env_file="$6"
qwen_env_file="$7"
target_image_input="$8"

state_current="${remote_releases_dir}/current_image.txt"
state_previous="${remote_releases_dir}/previous_image.txt"

if [[ -n "${target_image_input}" ]]; then
  target_image="${target_image_input}"
else
  target_image="$(cat "${state_previous}" 2>/dev/null || true)"
fi

if [[ -z "${target_image}" ]]; then
  echo "" >&2
  echo "No previous image found. Set TARGET_IMAGE to rollback explicitly." >&2
  exit 1
fi

current_image="$(cat "${state_current}" 2>/dev/null || true)"
if [[ -n "${current_image}" && "${current_image}" != "${target_image}" ]]; then
  printf '%s\n' "${current_image}" >"${state_previous}"
fi
printf '%s\n' "${target_image}" >"${state_current}"

printf '%s' "${iam_token}" | docker login --username oauth --password-stdin "${ycr_host}" >/dev/null
docker pull "${target_image}"

docker rm -f "${container_name}" >/dev/null 2>&1 || true
docker run -d \
  --name "${container_name}" \
  --restart unless-stopped \
  --env-file "${backend_env_file}" \
  --env-file "${qwen_env_file}" \
  -p "${container_port}:8000" \
  "${target_image}" >/dev/null

docker logout "${ycr_host}" >/dev/null 2>&1 || true
printf '%s' "${target_image}"
REMOTE_SCRIPT
)"

log "Health check: ${HEALTHCHECK_URL}"
for ((attempt = 1; attempt <= HEALTHCHECK_ATTEMPTS; attempt++)); do
  if curl -fsS "${HEALTHCHECK_URL}" >/dev/null; then
    log "Rollback succeeded. Image: ${ROLLED_BACK_IMAGE}"
    exit 0
  fi
  log "Health check attempt ${attempt}/${HEALTHCHECK_ATTEMPTS} failed, waiting ${HEALTHCHECK_INTERVAL_SEC}s"
  sleep "${HEALTHCHECK_INTERVAL_SEC}"
done

die "Rollback finished but health check failed: ${HEALTHCHECK_URL}"

