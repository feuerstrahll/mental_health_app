# Yandex VM CI/CD Auto-Deployment Setup

This guide enables automatic deployment when you push code to your Git repository.

## Option 1: GitHub Actions → Yandex VM (Recommended for GitHub)

### Prerequisites
- GitHub repository (public or private)
- Yandex VM with Docker installed
- SSH key pair for VM access

### Setup

#### Step 1: Create SSH keypair on VM

```bash
# On Yandex VM
ssh-keygen -t rsa -b 4096 -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/deploy_key
```

Copy the private key output (everything from `-----BEGIN` to `-----END`).

#### Step 2: Add secrets to GitHub

Go to: **Settings → Secrets and variables → Actions**

Create secrets:
- `DEPLOY_SSH_KEY` = (paste the private key from Step 1)
- `DEPLOY_HOST` = your VM public IP
- `DEPLOY_USER` = SSH user (e.g., `ubuntu`)
- `DEPLOY_PORT` = 22 (or your SSH port)
- `YC_REGISTRY_ID` = your Yandex Container Registry ID
- `YC_IAM_TOKEN` = (optional, script can auto-generate)

#### Step 3: Create workflow file

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Backend to Yandex

on:
  push:
    branches:
      - main
      - production
    paths:
      - 'backend/**'
      - 'bge_service/**'
      - 'infra/**'
      - '.github/workflows/deploy.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Run tests
        run: |
          pip install -e backend.[dev]
          pytest backend/app/tests -q --tb=short
        continue-on-error: false
      
      - name: Install Yandex CLI
        run: |
          curl https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
          export PATH=$PATH:$HOME/yandex-cloud/bin
      
      - name: Deploy to VM
        env:
          SSH_KEY: ${{ secrets.DEPLOY_SSH_KEY }}
          DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
          DEPLOY_USER: ${{ secrets.DEPLOY_USER }}
          DEPLOY_PORT: ${{ secrets.DEPLOY_PORT }}
          YC_REGISTRY_ID: ${{ secrets.YC_REGISTRY_ID }}
          YC_IAM_TOKEN: ${{ secrets.YC_IAM_TOKEN }}
          LOCAL_BACKEND_ENV_FILE: ${{ github.workspace }}/infra/env/backend.env.prod
          LOCAL_QWEN_ENV_FILE: ${{ github.workspace }}/infra/env/qwen.env.prod
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -p $DEPLOY_PORT $DEPLOY_HOST >> ~/.ssh/known_hosts 2>/dev/null
          
          export BACKEND_HOST=$DEPLOY_HOST
          export BACKEND_SSH_USER=$DEPLOY_USER
          export BACKEND_SSH_PORT=$DEPLOY_PORT
          export PATH=$PATH:$HOME/yandex-cloud/bin
          
          bash infra/deploy/yandex/deploy.sh
      
      - name: Health check
        run: |
          sleep 10
          curl -f "http://${{ secrets.DEPLOY_HOST }}:8000/api/v1/health" || exit 1
      
      - name: Notify on failure
        if: failure()
        run: echo "Deployment failed. Check logs above."
```

#### Step 4: Commit and test

```bash
git add .github/workflows/deploy.yml
git commit -m "Add auto-deployment workflow"
git push origin main
```

Watch deployment in **Actions** tab.

---

## Option 2: Self-Hosted Webhook on VM (No External CI/CD)

If you want deployment directly on the VM via Git push webhook.

### Setup

#### Step 1: Create deployment user on VM

```bash
sudo useradd -m -s /bin/bash deployer
sudo usermod -aG docker deployer
sudo mkdir -p /opt/mental-health
sudo chown -R deployer:deployer /opt/mental-health
```

#### Step 2: Create webhook listener script

Save as `/opt/mental-health/webhook-listener.sh`:

```bash
#!/bin/bash
set -e

REPO_PATH="/opt/mental-health/repo"
LOG_FILE="/opt/mental-health/webhook.log"

# Ensure repo exists
if [ ! -d "$REPO_PATH" ]; then
  git clone <your_git_repo_url> "$REPO_PATH"
fi

cd "$REPO_PATH"

# Pull latest code
echo "[$(date)] Pulling latest code..." >> "$LOG_FILE"
git fetch origin
git reset --hard origin/main

# Run tests
echo "[$(date)] Running tests..." >> "$LOG_FILE"
cd backend
pip install -e .[dev] >> "$LOG_FILE" 2>&1
pytest app/tests -q >> "$LOG_FILE" 2>&1

# Deploy
echo "[$(date)] Deploying..." >> "$LOG_FILE"
cd /opt/mental-health/repo

export BACKEND_HOST=localhost
export BACKEND_SSH_USER=deployer
export BACKEND_SSH_PORT=22
export YC_REGISTRY_ID=<your_registry_id>
export LOCAL_BACKEND_ENV_FILE=/opt/mental-health/config/backend.env.prod
export LOCAL_QWEN_ENV_FILE=/opt/mental-health/config/qwen.env.prod

bash infra/deploy/yandex/deploy.sh >> "$LOG_FILE" 2>&1

echo "[$(date)] Deployment complete" >> "$LOG_FILE"
```

#### Step 3: Set up webhook receiver (Node.js)

Save as `/opt/mental-health/webhook.js`:

```javascript
const http = require('http');
const crypto = require('crypto');
const { exec } = require('child_process');

const PORT = 3333;
const SECRET = process.env.WEBHOOK_SECRET || 'change-me';

http.createServer((req, res) => {
  if (req.method !== 'POST') {
    res.writeHead(405);
    res.end('Method not allowed');
    return;
  }

  let body = '';
  req.on('data', chunk => body += chunk);
  req.on('end', () => {
    const signature = req.headers['x-hub-signature-256'];
    const hash = 'sha256=' + crypto
      .createHmac('sha256', SECRET)
      .update(body)
      .digest('hex');

    if (signature !== hash) {
      res.writeHead(401);
      res.end('Unauthorized');
      return;
    }

    const event = JSON.parse(body);
    if (event.ref === 'refs/heads/main' || event.ref === 'refs/heads/production') {
      console.log('Deployment triggered by push to', event.ref);
      exec('bash /opt/mental-health/webhook-listener.sh', (err, stdout, stderr) => {
        if (err) console.error('Deploy error:', stderr);
        else console.log('Deploy output:', stdout);
      });
      res.writeHead(200);
      res.end('OK');
    }
  });
}).listen(PORT, () => console.log(`Webhook listening on :${PORT}`));
```

#### Step 4: Run webhook service

```bash
# Install Node.js
sudo apt update && sudo apt install -y nodejs npm

# Start webhook listener
export WEBHOOK_SECRET=your-secret-key
node /opt/mental-health/webhook.js &

# To make it persistent, use systemd or supervisor
# Or use PM2:
sudo npm install -g pm2
pm2 start /opt/mental-health/webhook.js --name deploy-webhook
pm2 save
pm2 startup
```

#### Step 5: Configure GitHub webhook

In your GitHub repo:
1. **Settings → Webhooks → Add webhook**
2. **Payload URL**: `http://<vm_public_ip>:3333` (requires public access or ngrok)
3. **Secret**: Use your `WEBHOOK_SECRET`
4. **Events**: `Push events`
5. **Active**: ✓

---

## VM Resource Requirements

### Models & Resource Usage

Your stack uses:
- **Backend (FastAPI)**: Minimal
- **BGE-M3 (Embeddings)**: ~2.5GB RAM, benefits from GPU
- **Qwen 3.5 27B (LLM)**: **27 billion parameters** — GPU intensive
- **PostgreSQL (Database)**: Variable by data size

### Minimal Setup (Without GPU)

```
vCPU:    8-core
RAM:     32 GB
Storage: 100 GB SSD
GPU:     None (embeddings/LLM will be slow)
Cost:    ~$200-300/month on Yandex
```

**Note**: Qwen 3.5 27B runs extremely slowly on CPU-only. Not recommended for production.

### Recommended Setup (With GPU)

```
vCPU:    8-core
RAM:     32 GB (minimum for Qwen 27B)
Storage: 100 GB SSD
GPU:     NVIDIA A100 (40GB VRAM) OR RTX 4090 (24GB)
Cost:    $400-800/month on Yandex
```

**Better GPU option for Qwen 27B**:
- A100 40GB: Runs Qwen 27B efficiently (full precision)
- A100 80GB: Best for concurrent requests
- RTX 4090: Cheaper alternative, requires 4-bit quantization

### Budget Setup (For Testing)

```
vCPU:    4-core
RAM:     16 GB
Storage: 50 GB SSD
GPU:     NVIDIA T4 (16GB VRAM)
Cost:    ~$150-250/month
```

**Limitation**: Qwen 27B requires 4-bit quantization on T4 (slower inference).

### Storage Breakdown

```
OS & Docker:         10 GB
Backend image:       2 GB
BGE image:           4 GB
Qwen image:         30-50 GB (model weights)
PostgreSQL data:    10-20 GB (depends on user data)
Logs & temp:         5 GB
Reserve:            10 GB

Total minimum:      100 GB SSD
Recommended:        150 GB SSD
```

---

## Full Deployment Sequence (With CI/CD)

### Local (your machine)
```bash
# Edit code locally
git add .
git commit -m "feature: add new support response"
git push origin main
```

### GitHub Actions (or webhook)
1. ✅ Run tests (fail fast if needed)
2. ✅ Build Docker images
3. ✅ Push to Yandex Container Registry
4. ✅ SSH to VM
5. ✅ Pull & run new containers
6. ✅ Health check
7. ✅ Slack/Email notification

### VM (Yandex Cloud)
```
Updated containers running, old ones stopped
Health check passes
Database migrations run automatically (if configured)
```

---

## Monitoring Deployment

### View logs on VM

```bash
# SSH to VM
ssh ubuntu@<vm_ip>

# View backend logs
docker logs -f mental-health-backend

# View BGE logs
docker logs -f bge-gateway

# View Qwen logs
docker logs -f qwen

# Check services
docker ps -a
```

### Rollback if needed

```bash
# On VM
bash infra/deploy/yandex/rollback.sh

# Or manually
docker stop mental-health-backend
docker run -d --name mental-health-backend \
  -e APP_ENV=prod \
  ... (previous image tag)
```

---

## Security Checklist

- [ ] SSH keys stored as GitHub secrets (not in code)
- [ ] Webhook secret set (random, strong password)
- [ ] VM firewall allows only TCP 22 (SSH) + 8000 (API)
- [ ] Database password not in code (env file only)
- [ ] `.env.prod` file **not committed** to git
- [ ] API keys stored in Yandex Secrets Manager or env vars
- [ ] Consider HTTPS reverse proxy (nginx/Caddy) in front of backend

---

## Quick Start Commands

### Option 1: GitHub Actions
```bash
# Create workflow
mkdir -p .github/workflows
# Paste deploy.yml from above
git add .github/workflows/deploy.yml
git commit -m "Add CI/CD workflow"
git push
# Done! Next push to main triggers deployment
```

### Option 2: Webhook
```bash
# On VM
ssh ubuntu@<vm_ip>
sudo su - deployer
mkdir -p /opt/mental-health/config

# Copy env files to VM
scp infra/env/backend.env.prod deployer@<vm_ip>:/opt/mental-health/config/
scp infra/env/qwen.env.prod deployer@<vm_ip>:/opt/mental-health/config/

# Start webhook listener
node /opt/mental-health/webhook.js
```
