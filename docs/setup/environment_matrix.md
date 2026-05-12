# Environment Matrix

| Environment | Backend | Database | Gateway | Notes |
|---|---|---|---|---|
| local | uvicorn | local postgres/docker | optional nginx | fastest loop |
| docker-compose | backend container | postgres container | nginx container | team baseline |
| yandex-cloud | containerized | managed postgres | ingress/nginx | deploy scripts in `infra/deploy/yandex` |
