# Yandex VM Resource Calculator

## Quick Decision Matrix

### Use Case 1: Development/Testing
- **GPU**: Optional (testing)
- **vCPU**: 4
- **RAM**: 16 GB
- **Storage**: 50 GB SSD
- **Monthly Cost**: ~$100-150
- **Performance**: Slow LLM (Qwen on CPU), fast embeddings not critical

### Use Case 2: Small Production (< 500 daily users)
- **GPU**: NVIDIA T4 (16GB)
- **vCPU**: 4-core
- **RAM**: 16 GB
- **Storage**: 100 GB SSD
- **Monthly Cost**: $150-250
- **Performance**: LLM latency ~2-5 sec/response (quantized Qwen 27B)
- **Requires**: 4-bit quantization for Qwen

### Use Case 3: Medium Production (500-5K daily users)
- **GPU**: RTX 4090 or A100 40GB
- **vCPU**: 8-core
- **RAM**: 32 GB
- **Storage**: 150 GB SSD
- **Monthly Cost**: $400-600
- **Performance**: LLM latency ~1-2 sec/response
- **Capacity**: ~50-100 concurrent users

### Use Case 4: High Performance (5K+ daily users)
- **GPU**: A100 80GB (or 2x A100 40GB)
- **vCPU**: 16-core
- **RAM**: 64 GB
- **Storage**: 200 GB SSD + database server
- **Monthly Cost**: $1000-1500+
- **Performance**: LLM latency ~500-800ms, multi-tenancy support
- **Capacity**: 200+ concurrent users

---

## What Each Component Needs

### PostgreSQL Database
- **RAM**: 1-2 GB (can be separate VM or managed service)
- **Storage**: 10-50 GB (depends on user data retention)
- **CPU**: 2-4 vCPU
- **Recommendation**: Use Yandex Managed Postgres (cheaper, auto-backup)

### BGE Embeddings Service
- **RAM**: 2.5 GB (BAAI/bge-m3 model)
- **GPU**: Optional (benefits from GPU, but CPU is acceptable)
- **vCPU**: 2-4 (CPU-bound if no GPU)
- **Storage**: 4 GB (model weights)

### Qwen LLM (3.5 27B)
- **Full Precision (FP32)**: Requires 108 GB VRAM
- **Half Precision (FP16)**: Requires 54 GB VRAM
- **4-bit Quantization**: Requires 13-16 GB VRAM (A100, RTX 4090, L40)
- **8-bit Quantization**: Requires 27 GB VRAM
- **GPU**: REQUIRED for production (CPU too slow)
- **Recommended**: A100 40GB or RTX 4090 for 4-bit

### FastAPI Backend
- **RAM**: 1-2 GB
- **vCPU**: 1-2 (rarely bottleneck)
- **Storage**: 100 MB
- **GPU**: Not needed (CPU-bound async I/O)

### Nginx Reverse Proxy
- **RAM**: 256 MB
- **vCPU**: 1 (rarely bottleneck)
- **GPU**: Not needed

---

## Storage Calculation

```
Docker images:
  ├─ Backend:    2 GB
  ├─ BGE-M3:     4 GB
  ├─ Qwen 27B:   40 GB (with model weights)
  ├─ Nginx:      50 MB
  └─ Postgres:   200 MB
  
Model weights (extracted):
  ├─ Qwen 27B:   50 GB (FP16 or quantized)
  └─ BGE-M3:     1 GB

Database (user data):
  └─ Postgres:   10-100 GB (depends on retention + user count)

System & cache:
  ├─ OS (Ubuntu): 5 GB
  ├─ Docker:     2 GB
  ├─ Logs:       5 GB
  └─ Temp:       5 GB

TOTAL: 120-180 GB SSD
```

---

## Recommended Configuration for Your Stack

Based on production mental health app with BGE+Qwen:

### Tier 1: MVP/Beta (< 100 daily users)
```
Instance: Yandex Standard-4 with T4 GPU
vCPU:      4 cores
RAM:       16 GB
GPU:       NVIDIA T4 (16GB VRAM)
Storage:   100 GB SSD
Network:   1 Gbps
Cost:      ~$200/month
Setup:     Qwen 4-bit quantized, BGE on CPU
Latency:   LLM response ~2-5 seconds
```

### Tier 2: Growth (100-1K daily users)
```
Instance: Yandex GPU v100-1 or RTX4000
vCPU:      8 cores
RAM:       32 GB
GPU:       RTX 4090 (24GB VRAM) or A100 (40GB)
Storage:   150 GB SSD
Network:   1 Gbps
Cost:      $400-600/month
Setup:     Qwen FP16 (if A100) or quantized, BGE FP32
Latency:   LLM response ~1-2 seconds
Capacity:  50-100 concurrent users
```

### Tier 3: Scale (1K+ daily users)
```
Separate services:
├─ App VM:       Yandex Standard-4 (no GPU)
├─ LLM VM:       Yandex GPU with A100 80GB
├─ Embeddings:   Yandex GPU with A100 40GB
└─ Database:     Yandex Managed Postgres (managed service)

Total Cost: $1000-1500/month
Latency:    < 1 second
Capacity:   500+ concurrent users
```

---

## GPU Comparison for Your Models

| GPU | VRAM | Qwen 27B | BGE-M3 | Cost/mo | Notes |
|-----|------|----------|--------|---------|-------|
| T4 | 16GB | 4-bit ⚠️ | ✓ | $50-100 | Slow, entry-level |
| RTX 4090 | 24GB | 4-bit ✓ | ✓ | $300-400 | Good price/perf |
| A100 40GB | 40GB | FP16 ✓ | ✓ | $400-600 | Balanced |
| A100 80GB | 80GB | FP16 ✓ | ✓✓ | $600-1000 | Enterprise |
| H100 | 80GB | FP32 ✓ | ✓✓ | $1000+ | Overkill |

**Recommendation**: Start with RTX 4090 or A100 40GB + quantized Qwen for cost-effectiveness.

---

## Cost Breakdown (Monthly on Yandex Cloud)

### Option A: Single VM (Everything)
```
vCPU (8 core, preemptible):   $30
RAM (32 GB):                  $50
GPU (T4):                     $100
Storage (150 GB SSD):         $50
Outbound traffic:             $5-20
Total:                        ~$230-300/month
```

### Option B: Separate VMs (Better scaling)
```
App VM (Standard):            $80
LLM VM (GPU A100):            $400
BGE VM (GPU T4):              $100
Database (Managed Postgres):  $50
Storage:                      $30
Outbound traffic:             $20-50
Total:                        ~$680-750/month
```

### Option C: Minimal (Development)
```
vCPU (4 core, preemptible):   $15
RAM (16 GB):                  $30
GPU (None, CPU only):         $0
Storage (100 GB):             $35
Total:                        ~$80/month
```

---

## Scaling Tips

1. **Start small**: Use preemptible instances for dev ($0.30-0.50/hour vs $0.50-1.00/hour)
2. **Use Yandex services**: Managed DB, Container Registry (cheaper than self-hosted)
3. **Quantize early**: 4-bit Qwen 27B is ~70% speed of FP16 but 4x cheaper GPU
4. **Cache embeddings**: BGE results can be cached to reduce inference load
5. **Separate concerns**: Run LLM/BGE separately from app for independent scaling

---

## Next Steps

1. **Choose tier** (Tier 1 recommended for start)
2. **Set up CI/CD** using CICD_SETUP.md
3. **Test locally** with Docker Compose
4. **Deploy to Yandex**:
   ```bash
   export BACKEND_HOST=<vm_ip>
   export YC_REGISTRY_ID=<your_id>
   bash infra/deploy/yandex/deploy.sh
   ```
5. **Monitor** logs and performance
6. **Scale** when needed
