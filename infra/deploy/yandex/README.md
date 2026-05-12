# Yandex Cloud Backend Deployment

This guide deploys the backend from this repo to a Yandex Cloud VM using Docker and Yandex Container Registry.

## 1) One-time Yandex setup

1. Install and initialize Yandex CLI:

```bash
yc init
```

2. Create (or reuse) a container registry and save its ID:

```bash
yc container registry create --name mental-health-registry
```

3. Create a Linux VM for backend (Ubuntu recommended).

4. Configure VM security group inbound rules:
- TCP 22 (SSH)
- TCP 8000 (backend API)

5. Install Docker on VM.

## 2) Prepare this project locally

From repository root:

```bash
chmod +x infra/deploy/yandex/deploy.sh
chmod +x infra/deploy/yandex/rollback.sh
```

Create production env files (do not use example files as-is):

- `infra/env/backend.env.prod`
- `infra/env/qwen.env.prod`

Example `infra/env/backend.env.prod`:

```env
APP_NAME=Mental Health Backend
APP_ENV=prod
APP_DEBUG=false
DB_DSN=postgresql+asyncpg://postgres:password@<db-host>:5432/mental_health
QWEN_ENABLED=true
MEMORY_STORE_BACKEND=postgres
MEMORY_RETRIEVAL_ENABLED=true
EMBEDDINGS_PROVIDER=bge_m3_http
EMBEDDINGS_DIM=1024
```

Example `infra/env/qwen.env.prod`:

```env
QWEN_ENABLED=true
QWEN_BASE_URL=http://<private-qwen-host>:8000
QWEN_API_KEY=EMPTY
QWEN_MODEL=Qwen/Qwen2.5-3B-Instruct
QWEN_TEMPERATURE=0.25
QWEN_MAX_TOKENS=260
QWEN_TIMEOUT_SECONDS=12.0
QWEN_MAX_RESPONSE_CHARS=640
```

## 3) Deploy backend

Export variables and run deploy script:

```bash
export BACKEND_HOST=<vm_public_ip>
export BACKEND_SSH_USER=<vm_user>
export BACKEND_SSH_PORT=22
export YC_REGISTRY_ID=<your_registry_id>

# Optional: if omitted, script uses `yc iam create-token`
# export YC_IAM_TOKEN=<iam_token>

export LOCAL_BACKEND_ENV_FILE=$(pwd)/infra/env/backend.env.prod
export LOCAL_QWEN_ENV_FILE=$(pwd)/infra/env/qwen.env.prod

# Optional tuning
# export IMAGE_NAME=mental-health-backend
# export BACKEND_CONTAINER_NAME=mental-health-backend
# export HEALTHCHECK_URL=http://<vm_public_ip>:8000/api/v1/health

bash infra/deploy/yandex/deploy.sh
```

What deploy script does:

1. Builds backend Docker image.
2. Pushes image to Yandex Container Registry.
3. Uploads env files to VM (`/opt/mental-health/config`).
4. Pulls and runs container on VM (`mental-health-backend`).
5. Saves release pointers in `/opt/mental-health/releases`.
6. Verifies `/api/v1/health`.

Record rollout evidence after each deploy:

```bash
curl -fsS "${HEALTHCHECK_URL:-http://<vm_public_ip>:8000/api/v1/health}"
```

Save the backend image tag, the health JSON, and a non-secret env summary:
`APP_ENV`, `MEMORY_STORE_BACKEND`, `MEMORY_RETRIEVAL_ENABLED`,
`EMBEDDINGS_PROVIDER`, and `EMBEDDINGS_DIM`. If a live database is available,
also run the live Postgres/BGE integration test with `LIVE_POSTGRES_DSN`.

## 4) Rollback

### Retrieval-only emergency bypass

If BGE or pgvector retrieval is unhealthy but the rest of the backend should stay online,
disable vector retrieval without rolling back the image:

```env
MEMORY_RETRIEVAL_ENABLED=false
```

Restart the backend container and verify:

```bash
curl -fsS "${HEALTHCHECK_URL:-http://<vm_public_ip>:8000/api/v1/health}"
```

Expected health shape:

```json
{
  "status": "degraded",
  "retrieval_status": "disabled",
  "embedding_dim_contract": {
    "skipped_reason": "retrieval_disabled"
  }
}
```

In this mode the backend must not call BGE, upsert memory embeddings, or run vector
search. The pipeline uses chronological/context fallback instead.

Do not roll back or delete migrations `20260501_0002` / `20260501_0003` for this bypass.
Existing rows in `user_memory_embeddings` can remain in place and will be reused when
`MEMORY_RETRIEVAL_ENABLED=true` is restored.

### Image rollback

Use image rollback for failures outside the retrieval pipeline, API regressions, or when
the degraded retrieval bypass is not enough.

Rollback to previous deployed image:

```bash
export BACKEND_HOST=<vm_public_ip>
export BACKEND_SSH_USER=<vm_user>
export BACKEND_SSH_PORT=22

bash infra/deploy/yandex/rollback.sh
```

Rollback to a specific image tag:

```bash
export TARGET_IMAGE=cr.yandex/<registry_id>/mental-health-backend:<tag>
bash infra/deploy/yandex/rollback.sh
```

## 5) Connect Flutter app to cloud backend

Use your backend URL at app run/build time:

```bash
flutter run --dart-define=MH_BACKEND_URL=http://<vm_public_ip>:8000
```

For production, place backend behind HTTPS (for example with a domain + reverse proxy) and use `https://...`.
