# Yandex Cloud Deployment - Complete Setup Guide

## What I've Created For You

I've created 4 new deployment guides in `/infra/deploy/yandex/`:

1. **CICD_SETUP.md** - GitHub Actions + Webhook CI/CD options
2. **RESOURCES.md** - VM resource requirements & cost calculator  
3. **TROUBLESHOOTING.md** - Common issues & fixes
4. **.github/workflows/deploy.yml** - Ready-to-use GitHub Actions workflow

---

## TL;DR: Deploy in 10 Minutes

### Prerequisites
- GitHub repository (public or private)
- Yandex VM with Docker installed
- SSH access to VM

### Step 1: Prepare Environment Files

Copy prod env files to your local machine (do NOT commit to git):

```bash
# Create production env files with real values
cp infra/env/backend.env.example infra/env/backend.env.prod
cp infra/env/qwen.env.example infra/env/qwen.env.prod

# Edit with real values:
nano infra/env/backend.env.prod
# Set: DB_DSN, QWEN_BASE_URL, passwords, etc.

nano infra/env/qwen.env.prod
# Set: QWEN_API_KEY if needed
```

**Important**: Add to `.gitignore`:
```bash
echo "infra/env/*.prod" >> .gitignore
```

### Step 2: Set Up GitHub Secrets

1. Go to: GitHub Repo → Settings → Secrets and variables → Actions

2. Add these 5 secrets:
   - `DEPLOY_SSH_KEY` = your SSH private key (from `ssh-keygen`)
   - `DEPLOY_HOST` = VM IP address (e.g., `123.45.67.89`)
   - `DEPLOY_USER` = SSH username (usually `ubuntu`)
   - `DEPLOY_PORT` = SSH port (usually `22`)
   - `YC_REGISTRY_ID` = Yandex Container Registry ID

### Step 3: Commit Workflow

```bash
# Already created at .github/workflows/deploy.yml
# Just commit and push:
git add .github/workflows/deploy.yml
git commit -m "Add auto-deployment to Yandex"
git push origin main
```

### Step 4: Watch Deployment

1. Go to your GitHub repo → Actions tab
2. Click the latest "Deploy Backend to Yandex VM" run
3. Watch logs in real-time
4. Wait for ✓ Health check passed

**Done!** On next push to `main`, deployment happens automatically.

---

## VM Resource Requirements

### Minimum Setup (Testing)
```
vCPU:    4-core
RAM:     16 GB
GPU:     None (CPU-only)
Storage: 50 GB SSD
Cost:    ~$80-120/month
Latency: LLM responses ~5-10 sec (slow)
```

### Recommended Setup (Production)
```
vCPU:    8-core
RAM:     32 GB
GPU:     NVIDIA T4 or RTX 4090 (16-24GB VRAM)
Storage: 100-150 GB SSD
Cost:    $250-400/month
Latency: LLM responses ~1-2 sec (good)
Capacity: 50-100 concurrent users
```

### High Performance (Scale)
```
vCPU:    16-core
RAM:     64 GB
GPU:     NVIDIA A100 (40-80GB VRAM)
Storage: 200 GB SSD
Cost:    $800-1500+/month
Latency: LLM responses < 1 sec
Capacity: 500+ concurrent users
```

**Critical**: Qwen 3.5 27B LLM needs GPU for reasonable latency. CPU-only will be unusable.

---

## What Gets Automated

When you push code to `main`:

```
Local push → GitHub Actions:
├─ Run all tests (pytest)
├─ Build Docker images
├─ Push to Yandex Container Registry
└─ SSH to VM → Pull & run containers
    ├─ Stop old containers
    ├─ Run migrations
    ├─ Start new services
    └─ Health check
        ├─ ✓ Success → Done
        └─ ✗ Fail → Rollback
```

**No manual steps needed after commit!**

---

## Deployment Checklist

- [ ] Create `.env.prod` and `.env.qwen.prod` files locally
- [ ] Add all 5 GitHub secrets
- [ ] Verify `.github/workflows/deploy.yml` is committed
- [ ] Test locally: `docker compose -f infra/docker-compose.yml up --build`
- [ ] Create Yandex Container Registry: `yc container registry create --name mental-health`
- [ ] Install Docker on VM: `sudo apt install docker.io`
- [ ] Test SSH access: `ssh ubuntu@<vm_ip>`
- [ ] Set up VM firewall: Allow TCP 22 (SSH), 8000 (API)
- [ ] First push to `main` triggers deployment

---

## Monitor Deployment

### During deployment
```bash
# Watch in GitHub Actions tab → click running job
# Real-time logs visible in browser
```

### After deployment
```bash
# SSH to VM
ssh ubuntu@<vm_ip>

# Check running containers
docker ps -a

# View backend logs
docker logs -f mental-health-backend

# Test endpoint
curl http://localhost:8000/api/v1/health
```

### Rollback if needed
```bash
# From local machine
export BACKEND_HOST=<vm_ip>
export BACKEND_SSH_USER=ubuntu
export BACKEND_SSH_PORT=22
bash infra/deploy/yandex/rollback.sh
```

---

## Costs & Recommendation

### Your Models Require:
- **BGE-M3**: 2.5GB RAM, benefits from GPU
- **Qwen 3.5 27B**: **GPU mandatory** (27 billion parameters)
- **FastAPI Backend**: 1-2GB RAM, CPU-only fine
- **PostgreSQL**: 10-50GB storage, 1-2GB RAM

### Cost Comparison

| Option | Cost | Performance | Setup Time |
|--------|------|-------------|------------|
| CPU-only | $80/mo | ❌ Unusable (Qwen on CPU) | 5 min |
| T4 GPU | $200/mo | ⚠️ Slow (2-5 sec/response) | 10 min |
| RTX 4090 | $350/mo | ✅ Good (1-2 sec/response) | 15 min |
| A100 40GB | $500/mo | ✅✅ Excellent (< 1 sec) | 15 min |

**Recommendation**: Start with **T4 GPU** for $200/mo to test production setup, then upgrade to RTX 4090 or A100 if latency is critical.

---

## Post-Deployment

### 1. Verify everything works
```bash
# Check health
curl http://<vm_ip>:8000/api/v1/health

# View API docs
open http://<vm_ip>:8000/docs
```

### 2. Set up monitoring
- Add CloudWatch or Grafana monitoring
- Configure log aggregation (ELK Stack, Loki, etc.)
- Set up alerts for service failures

### 3. Configure backups
```bash
# Database backup script already provided
# See TROUBLESHOOTING.md → Database Backup section
```

### 4. Connect Flutter app
```bash
flutter run --dart-define=MH_BACKEND_URL=http://<vm_ip>:8000
```

---

## ⚠️ CRITICAL: Fix 3 Bugs Before First Deploy

**I found 3 networking bugs in your code during audit.**  
**These will break development/testing environments.**

### Bug #1: Qwen URL defaults to localhost
**File**: `backend/app/core/config.py:18`
```python
# WRONG (current):
qwen_base_url: str = "http://127.0.0.1:3264/api"

# CORRECT (fix):
qwen_base_url: str = "http://qwen:3264/api"
```

### Bug #2: BGE port mismatch
**File**: `backend/app/core/config.py:38`
```python
# WRONG (current):
embeddings_bge_base_url: str = "http://bge-gateway:8080"

# CORRECT (fix):
embeddings_bge_base_url: str = "http://bge-gateway:8001"
```

### Bug #3: BGE localhost binding
**File**: `infra/docker-compose.yml:30-33`
```yaml
# WRONG (current):
  bge:
    ports:
      - "127.0.0.1:8001:8001"

# CORRECT (fix):
  bge:
    expose:
      - "8001"
```

**Impact**: Without these fixes, the backend won't connect to Qwen or BGE in Docker environments.

---

## Questions?

See detailed docs:
- **Setup**: `infra/deploy/yandex/CICD_SETUP.md`
- **Resources**: `infra/deploy/yandex/RESOURCES.md`
- **Troubleshooting**: `infra/deploy/yandex/TROUBLESHOOTING.md`
- **Original guide**: `infra/deploy/yandex/README.md`

---

## Next Steps

1. **Fix the 3 bugs** (see above)
2. **Create `.env.prod` and `qwen.env.prod`** with real values
3. **Add 5 GitHub secrets**
4. **Push to main branch**
5. **Watch GitHub Actions** → Done!

Good luck! 🚀
