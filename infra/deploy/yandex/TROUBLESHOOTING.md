# Yandex VM CI/CD Troubleshooting & Quick Start

## Quick Start: GitHub Actions (Easiest)

### 1-2-3 Setup (5 minutes)

**Step 1: Generate SSH key**
```bash
# On your local machine
ssh-keygen -t rsa -b 4096 -f ~/.ssh/yandex_deploy -N ""

# Show private key (copy this)
cat ~/.ssh/yandex_deploy
```

**Step 2: Add key to VM**
```bash
# On Yandex VM
mkdir -p ~/.ssh
echo "<paste your public key from ~/.ssh/yandex_deploy.pub>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**Step 3: GitHub Secrets**
- Go to your GitHub repo → Settings → Secrets and variables → Actions
- Add 5 secrets:
  - `DEPLOY_SSH_KEY` = (private key from Step 1)
  - `DEPLOY_HOST` = your VM IP
  - `DEPLOY_USER` = `ubuntu` (or your SSH user)
  - `DEPLOY_PORT` = `22`
  - `YC_REGISTRY_ID` = your Yandex Container Registry ID

**Step 4: Copy workflow file**
```bash
mkdir -p .github/workflows
cp infra/deploy/yandex/github-deploy.yml .github/workflows/deploy.yml
git add .github/workflows/deploy.yml
git commit -m "Add CD workflow"
git push
```

**Done!** Next push to `main` triggers auto-deployment.

---

## Common Issues & Fixes

### Issue: "Permission denied (publickey)"

**Cause**: SSH key not properly added to VM

**Fix**:
```bash
# On VM
ls -la ~/.ssh/authorized_keys
# Should show rw for owner

cat ~/.ssh/authorized_keys
# Should contain your public key

# Reset if needed
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### Issue: "Deployment failed: docker: command not found"

**Cause**: Docker not installed on VM

**Fix**:
```bash
# On VM (as root)
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu  # Allow ubuntu user to use docker
```

### Issue: "Yandex CLI not found"

**Cause**: CLI not installed or not in PATH

**Fix** (in GitHub Actions):
```yaml
- name: Install Yandex CLI
  run: |
    curl https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
    export PATH=$PATH:$HOME/yandex-cloud/bin
```

### Issue: "Container Registry authentication failed"

**Cause**: IAM token expired or invalid

**Fix**:
```bash
# Option 1: Regenerate token
yc iam create-token

# Option 2: Use Yandex CLI in GitHub Actions (auto)
export YC_IAM_TOKEN=$(yc iam create-token)
```

### Issue: "Tests failed, but deployment still ran"

**Cause**: `continue-on-error: true` in workflow

**Fix**: Set to `false` in `.github/workflows/deploy.yml`:
```yaml
- name: Run tests
  run: pytest backend/app/tests -q
  continue-on-error: false  # CHANGE THIS
```

### Issue: "Health check failed after deploy"

**Cause**: Container not running or slow startup

**Fix**:
```bash
# On VM
docker ps -a
# Check if container is running

docker logs mental-health-backend
# View error logs

# If stuck, restart
docker restart mental-health-backend
sleep 5
curl http://localhost:8000/api/v1/health
```

### Issue: "BGE service unreachable"

**Related to known issue in project!**

**See**: [Project Audit Results](../../AUDIT_RESULTS.md)

The dev environment has 3 networking bugs:
1. Qwen URL defaults to localhost (won't work in Docker)
2. BGE port mismatch (8080 default vs 8001 actual)
3. BGE localhost binding in docker-compose

**Fix** (apply these before deploying):
```bash
# Fix 1: BGE default port
# In backend/app/core/config.py line 38
# Change: "http://bge-gateway:8080"
# To:     "http://bge-gateway:8001"

# Fix 2: Qwen default URL
# In backend/app/core/config.py line 18
# Change: "http://127.0.0.1:3264/api"
# To:     "http://qwen:3264/api"

# Fix 3: docker-compose.yml BGE binding
# In infra/docker-compose.yml line 30-33
# Change: ports: ["127.0.0.1:8001:8001"]
# To:     expose: ["8001"]
```

### Issue: "Postgres migration failed"

**Cause**: Migration not applied on previous deploy

**Fix**:
```bash
# On VM
docker exec -it mental-health-backend alembic upgrade head

# Or manually run migration
docker exec -it mental-health-backend python -c \
  "from app.repositories.postgres.session import engine; import asyncio; asyncio.run(engine.dispose())"
```

### Issue: "GitHub Actions timeout (6+ hours)"

**Cause**: Large Docker image build or network issues

**Fix**:
```yaml
- name: Deploy (with timeout)
  timeout-minutes: 30  # Add this
  run: bash infra/deploy/yandex/deploy.sh
```

### Issue: "Qwen 27B model too slow (>10 seconds/response)"

**Cause**: Running on CPU or wrong quantization

**Check**:
```bash
# On VM
docker logs qwen | grep -i "gpu\|cuda\|quantization"

# Should see GPU enabled if present
# If CPU only, responses will be slow

# Solution: 
# Use smaller model or get GPU VM
```

### Issue: "Disk full (100% usage)"

**Cause**: Docker images and containers accumulating

**Fix**:
```bash
# On VM
docker system prune -a --volumes  # WARNING: removes all unused images

# Check usage
df -h

# If database bloated:
docker exec postgres pg_dump -U postgres mental_health > backup.sql
docker exec postgres vacuumdb -U postgres mental_health
```

---

## Monitoring Deployment

### Real-time logs

```bash
# On VM via SSH
ssh ubuntu@<vm_ip>

# View backend logs
docker logs -f mental-health-backend

# View all services
docker compose logs -f
```

### Health check from CI/CD

```yaml
- name: Verify deployment
  run: |
    for i in {1..10}; do
      if curl -f http://${{ secrets.DEPLOY_HOST }}:8000/api/v1/health; then
        echo "✓ Health check passed"
        exit 0
      fi
      echo "Attempt $i/10, waiting..."
      sleep 5
    done
    echo "✗ Health check failed"
    exit 1
```

---

## Rollback Procedures

### Immediate rollback (keep same DB)

```bash
# On VM
ssh ubuntu@<vm_ip>

# Disable BGE if retrieval failing
docker exec mental-health-backend \
  sed -i 's/MEMORY_RETRIEVAL_ENABLED=true/MEMORY_RETRIEVAL_ENABLED=false/' .env

docker restart mental-health-backend

# Verify
curl http://localhost:8000/api/v1/health
# Should return status: "degraded"
```

### Full rollback to previous image

```bash
# Run from your local machine with SSH access
export BACKEND_HOST=<vm_ip>
export BACKEND_SSH_USER=ubuntu
export BACKEND_SSH_PORT=22

bash infra/deploy/yandex/rollback.sh
```

---

## Database Backup & Recovery

### Automated backup

```bash
# On VM, create backup script
cat > /opt/mental-health/backup.sh << 'EOF'
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE=/backups/mental_health_$TIMESTAMP.sql.gz

docker exec postgres pg_dump -U postgres mental_health | gzip > $BACKUP_FILE
echo "Backup saved: $BACKUP_FILE"

# Keep only last 30 days
find /backups -name "mental_health_*.sql.gz" -mtime +30 -delete
EOF

chmod +x /opt/mental-health/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l; echo "0 2 * * * /opt/mental-health/backup.sh") | crontab -
```

### Restore from backup

```bash
# On VM
BACKUP_FILE=/backups/mental_health_YYYYMMDD_HHMMSS.sql.gz

gunzip -c $BACKUP_FILE | docker exec -i postgres psql -U postgres -d mental_health
```

---

## Performance Tuning

### Reduce Qwen inference time

```yaml
# In infra/env/backend.env.prod
QWEN_TEMPERATURE=0.3  # Lower = faster (less variability)
QWEN_MAX_COMPLETION_TOKENS=300  # Reduce if too large
QWEN_TIMEOUT_SECONDS=15  # Adjust based on GPU speed
```

### Cache BGE embeddings

```python
# In backend/app/services/context/memory_index_service.py
# Add Redis caching layer for repeated queries
```

### Scale horizontally (multiple backends)

```yaml
# Use Yandex Load Balancer in front of multiple backend VMs
# Each with same DB connection
services:
  - backend-1 (port 8000)
  - backend-2 (port 8001)
  - backend-3 (port 8002)
  - load-balancer (routes to all three)
```

---

## Cost Optimization

### Use preemptible instances (save 60%)
```bash
# On Yandex Cloud, enable "preemptible" flag
# Cheaper but can be interrupted
# Good for: dev, testing, non-critical services
```

### Managed services vs self-hosted
```
Self-hosted Postgres:     $50-100/month + admin overhead
Yandex Managed Postgres:  $80-120/month + auto-backup + monitoring
→ Managed usually cheaper for small/medium projects
```

### Shared GPU resources
```
Dedicated A100 80GB:    $600-800/month
Shared GPU service:     $10-50/month per inference
→ Consider Yandex Functions or serverless APIs
```

---

## Final Checklist Before Production Deploy

- [ ] All 3 networking bugs fixed (see Issue section)
- [ ] Tests pass locally (`pytest backend/app/tests`)
- [ ] `.env.prod` created with real passwords (NOT in git)
- [ ] Yandex Container Registry created
- [ ] SSH keys in GitHub Secrets
- [ ] GitHub Actions workflow file committed
- [ ] VM has Docker installed
- [ ] VM firewall allows TCP 22 (SSH) and 8000 (API)
- [ ] Health endpoint responds: `curl http://<vm_ip>:8000/api/v1/health`
- [ ] Database backups configured
- [ ] Monitoring/logs setup (e.g., send to CloudWatch or Grafana)

---

## Still Stuck?

1. Check logs: `docker logs mental-health-backend`
2. Test manually: `curl http://localhost:8000/api/v1/health`
3. SSH to VM: `ssh ubuntu@<vm_ip>`
4. Check GitHub Actions output: Repo → Actions → latest run
