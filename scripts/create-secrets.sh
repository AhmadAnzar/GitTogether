#!/usr/bin/env bash
# Create the Kubernetes Secret the Helm chart reads (POSTGRES_PASSWORD, JWT_SECRET) with random values.
# The values never touch git. Safe to re-run: an existing Secret is kept, because the database volume
# was initialised with that password. Use --rotate only together with a fresh database volume.
#
#   scripts/create-secrets.sh [--rotate] [namespace] [secret-name]
set -euo pipefail

ROTATE=false
if [[ "${1:-}" == "--rotate" ]]; then ROTATE=true; shift; fi
NAMESPACE="${1:-gittogether}"
NAME="${2:-gittogether-secrets}"

random_hex() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

if kubectl get secret "$NAME" -n "$NAMESPACE" >/dev/null 2>&1 && [[ "$ROTATE" == false ]]; then
  echo "Secret $NAMESPACE/$NAME already exists; keeping it (pass --rotate to replace it)."
  exit 0
fi

kubectl create secret generic "$NAME" -n "$NAMESPACE" \
  --from-literal=POSTGRES_PASSWORD="$(random_hex)" \
  --from-literal=JWT_SECRET="$(random_hex)" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secret $NAMESPACE/$NAME is ready (values are random and only stored in the cluster)."
