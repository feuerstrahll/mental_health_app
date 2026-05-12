# Deployment

This folder contains scripts for VM-based deployment on Yandex Cloud.

## Scripts

- `yandex/deploy.sh`: build, push, and deploy backend image to a VM.
- `yandex/rollback.sh`: switch backend container to the previous image.

## Fast path

1. Configure environment variables (example below).
2. Run `bash infra/deploy/yandex/deploy.sh`.
3. If release is broken, run `bash infra/deploy/yandex/rollback.sh`.

See `infra/deploy/yandex/README.md` for full setup steps.

