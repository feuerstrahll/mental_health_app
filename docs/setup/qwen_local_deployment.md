# Qwen Local Deployment

This setup keeps inference local: Flutter app -> local backend -> local Qwen server.

## What To Download

1. Python 3.11+
2. Docker Desktop (recommended for running vLLM quickly)
3. NVIDIA driver + CUDA-compatible GPU (recommended for practical speed)
4. Flutter SDK (for running the app)

The model weights (`Qwen/Qwen2.5-3B-Instruct`) are downloaded automatically on first run.

## 1) Start Local Qwen (OpenAI-Compatible)

Run vLLM container:

```powershell
docker run --gpus all --rm -p 8001:8000 `
  -v qwen_cache:/root/.cache/huggingface `
  vllm/vllm-openai:latest `
  --model Qwen/Qwen2.5-3B-Instruct `
  --host 0.0.0.0 `
  --port 8000 `
  --dtype auto
```

If you do not have a GPU, you can still run Qwen locally, but response speed may be slow.

## 2) Configure Backend To Use Qwen

Use these env values (already reflected in `infra/env/qwen.env.example`):

```env

QWEN_ENABLED=true
QWEN_BASE_URL=http://host.docker.internal:8001
QWEN_API_KEY=EMPTY
QWEN_MODEL=Qwen/Qwen2.5-3B-Instruct
QWEN_TEMPERATURE=0.25
QWEN_MAX_TOKENS=260
QWEN_TIMEOUT_SECONDS=12.0
QWEN_MAX_RESPONSE_CHARS=640
```

Run backend:

```powershell
cd backend
pip install -e .[dev]
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 3) Run Flutter App Against Local Backend

From `mental_health_app/`:

```powershell
flutter pub get
flutter run `
  --dart-define=MH_USE_BACKEND_QWEN=true `
  --dart-define=MH_BACKEND_URL=http://10.0.2.2:8000 `
  --dart-define=MH_USER_ID=local_user_1
```

Notes:
- `MH_BACKEND_URL=http://10.0.2.2:8000` is for Android emulator.
- For Windows desktop run, use `http://localhost:8000`.

## 4) Health Checks

1. Backend up: `http://localhost:8000/api/v1/health`
2. Qwen up: `http://localhost:8001/v1/models`
3. App chat now attempts backend/Qwen first, then falls back to local keyword responses if backend is unavailable.
