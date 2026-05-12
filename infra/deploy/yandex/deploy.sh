#!/usr/bin/env bash
set -euo pipefail

log() { printf '[deploy] %s\n' "$*"; }
err() { printf '[deploy][error] %s\n' "$*" >&2; }
die() { err "$*"; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Command not found: $1"; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

BACKEND_HOST="${BACKEND_HOST:-}"
BACKEND_SSH_USER="${BACKEND_SSH_USER:-}"
BACKEND_SSH_PORT="${BACKEND_SSH_PORT:-22}"
YC_REGISTRY_ID="${YC_REGISTRY_ID:-}"
YCR_REGISTRY_HOST="${YCR_REGISTRY_HOST:-cr.yandex}"
YC_IAM_TOKEN="${YC_IAM_TOKEN:-}"
AUTO_CREATE_TOKEN="${AUTO_CREATE_TOKEN:-true}"

IMAGE_NAME="${IMAGE_NAME:-mental-health-backend}"
IMAGE_TAG="${IMAGE_TAG:-}"
if [[ -z "${IMAGE_TAG}" ]]; then
  GIT_SHA="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || true)"
  TS="$(date -u +%Y%m%d%H%M%S)"
  IMAGE_TAG="${GIT_SHA:-manual}-${TS}"
fi
FULL_IMAGE="${YCR_REGISTRY_HOST}/${YC_REGISTRY_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

BACKEND_CONTAINER_NAME="${BACKEND_CONTAINER_NAME:-mental-health-backend}"
BACKEND_CONTAINER_PORT="${BACKEND_CONTAINER_PORT:-8000}"

BACKEND_REMOTE_APP_DIR="${BACKEND_REMOTE_APP_DIR:-/opt/mental-health}"
BACKEND_REMOTE_ENV_DIR="${BACKEND_REMOTE_ENV_DIR:-${BACKEND_REMOTE_APP_DIR}/config}"
BACKEND_REMOTE_RELEASES_DIR="${BACKEND_REMOTE_RELEASES_DIR:-${BACKEND_REMOTE_APP_DIR}/releases}"
BACKEND_REMOTE_BACKEND_ENV_FILE="${BACKEND_REMOTE_BACKEND_ENV_FILE:-${BACKEND_REMOTE_ENV_DIR}/backend.env}"
BACKEND_REMOTE_QWEN_ENV_FILE="${BACKEND_REMOTE_QWEN_ENV_FILE:-${BACKEND_REMOTE_ENV_DIR}/qwen.env}"

LOCAL_BACKEND_ENV_FILE="${LOCAL_BACKEND_ENV_FILE:-${ROOT_DIR}/infra/env/backend.env.example}"
LOCAL_QWEN_ENV_FILE="${LOCAL_QWEN_ENV_FILE:-${ROOT_DIR}/infra/env/qwen.env.example}"

HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://${BACKEND_HOST}:${BACKEND_CONTAINER_PORT}/api/v1/health}"
HEALTHCHECK_ATTEMPTS="${HEALTHCHECK_ATTEMPTS:-20}"
HEALTHCHECK_INTERVAL_SEC="${HEALTHCHECK_INTERVAL_SEC:-3}"

SKIP_BUILD="${SKIP_BUILD:-false}"
SKIP_PUSH="${SKIP_PUSH:-false}"

[[ -n "${BACKEND_HOST}" ]] || die "Set BACKEND_HOST"
[[ -n "${BACKEND_SSH_USER}" ]] || die "Set BACKEND_SSH_USER"
[[ -n "${YC_REGISTRY_ID}" ]] || die "Set YC_REGISTRY_ID"
[[ -f "${LOCAL_BACKEND_ENV_FILE}" ]] || die "Backend env file not found: ${LOCAL_BACKEND_ENV_FILE}"
[[ -f "${LOCAL_QWEN_ENV_FILE}" ]] || die "Qwen env file not found: ${LOCAL_QWEN_ENV_FILE}"

require_cmd docker
require_cmd ssh
require_cmd scp
require_cmd curl
require_cmd git

if [[ -z "${YC_IAM_TOKEN}" ]]; then
  if [[ "${AUTO_CREATE_TOKEN}" != "true" ]]; then
    die "Set YC_IAM_TOKEN or enable AUTO_CREATE_TOKEN=true"
  fi
  require_cmd yc
  log "Creating YC IAM token via yc CLI"
  YC_IAM_TOKEN="$(yc iam create-token)"
fi

log "Docker login: ${YCR_REGISTRY_HOST}"
printf '%s' "${YC_IAM_TOKEN}" | docker login --username oauth --password-stdin "${YCR_REGISTRY_HOST}" >/dev/null
trap 'docker logout "${YCR_REGISTRY_HOST}" >/dev/null 2>&1 || true' EXIT

if [[ "${SKIP_BUILD}" != "true" ]]; then
  log "Building image: ${FULL_IMAGE}"
  docker build \
    -f "${ROOT_DIR}/infra/docker/backend.Dockerfile" \
    -t "${FULL_IMAGE}" \
    "${ROOT_DIR}"
else
  log "Skipping image build (SKIP_BUILD=true)"
fi

if [[ "${SKIP_PUSH}" != "true" ]]; then
  log "Pushing image: ${FULL_IMAGE}"
  docker push "${FULL_IMAGE}"
else
  log "Skipping image push (SKIP_PUSH=true)"
fi

REMOTE_TARGET="${BACKEND_SSH_USER}@${BACKEND_HOST}"
SSH_BASE=(ssh -p "${BACKEND_SSH_PORT}")
SCP_BASE=(scp -P "${BACKEND_SSH_PORT}")

log "Uploading env files to VM"
"${SCP_BASE[@]}" "${LOCAL_BACKEND_ENV_FILE}" "${REMOTE_TARGET}:${BACKEND_REMOTE_BACKEND_ENV_FILE}.new"
"${SCP_BASE[@]}" "${LOCAL_QWEN_ENV_FILE}" "${REMOTE_TARGET}:${BACKEND_REMOTE_QWEN_ENV_FILE}.new"

log "Deploying container on VM: ${BACKEND_HOST}"
"${SSH_BASE[@]}" "${REMOTE_TARGET}" bash -s -- \
  "${YCR_REGISTRY_HOST}" \
  "${YC_IAM_TOKEN}" \
  "${FULL_IMAGE}" \
  "${BACKEND_CONTAINER_NAME}" \
  "${BACKEND_CONTAINER_PORT}" \
  "${BACKEND_REMOTE_ENV_DIR}" \
  "${BACKEND_REMOTE_RELEASES_DIR}" \
  "${BACKEND_REMOTE_BACKEND_ENV_FILE}" \
  "${BACKEND_REMOTE_QWEN_ENV_FILE}" <<'REMOTE_SCRIPT'
set -euo pipefail

ycr_host="$1"
iam_token="$2"
full_image="$3"
container_name="$4"
container_port="$5"
remote_env_dir="$6"
remote_releases_dir="$7"
backend_env_file="$8"
qwen_env_file="$9"

mkdir -p "${remote_env_dir}" "${remote_releases_dir}"

mv -f "${backend_env_file}.new" "${backend_env_file}"
mv -f "${qwen_env_file}.new" "${qwen_env_file}"

printf '%s' "${iam_token}" | docker login --username oauth --password-stdin "${ycr_host}" >/dev/null
docker pull "${full_image}"

state_current="${remote_releases_dir}/current_image.txt"
state_previous="${remote_releases_dir}/previous_image.txt"
if [[ -f "${state_current}" ]]; then
  cp "${state_current}" "${state_previous}"
fi
printf '%s\n' "${full_image}" >"${state_current}"

docker rm -f "${container_name}" >/dev/null 2>&1 || true
docker run -d \
  --name "${container_name}" \
  --restart unless-stopped \
  --env-file "${backend_env_file}" \
  --env-file "${qwen_env_file}" \
  -p "${container_port}:8000" \
  "${full_image}" >/dev/null

docker logout "${ycr_host}" >/dev/null 2>&1 || true
REMOTE_SCRIPT

log "Health check: ${HEALTHCHECK_URL}"
for ((attempt = 1; attempt <= HEALTHCHECK_ATTEMPTS; attempt++)); do
  if curl -fsS "${HEALTHCHECK_URL}" >/dev/null; then
    log "Deployment succeeded. Image: ${FULL_IMAGE}"
    exit 0
  fi
  log "Health check attempt ${attempt}/${HEALTHCHECK_ATTEMPTS} failed, waiting ${HEALTHCHECK_INTERVAL_SEC}s"
  sleep "${HEALTHCHECK_INTERVAL_SEC}"
done

die "Deployment finished but health check failed: ${HEALTHCHECK_URL}"

