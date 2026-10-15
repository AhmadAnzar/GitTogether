#!/usr/bin/env bash
# Install ArgoCD on the EKS cluster and point it at this repo.
#
# Why not a plain `kubectl apply`: on EKS 1.35 and 1.36 the API server answers 503 for the protobuf OpenAPI
# schema while the aggregated APIs v1.metrics.eks.amazonaws.com or v1beta1.metrics.k8s.io are registered, and
# ArgoCD cannot start comparing without that schema (Application stuck on "Unknown"). Workaround: unregister both
# APIs, let ArgoCD load the schema and reach Synced, then register metrics-server's API again (needed by the HPA).
# ArgoCD keeps working from its cached schema, but do NOT restart its pods afterwards: run this script again.
#
# Run it after monitoring is installed (the ServiceMonitor needs its CRDs) and with kubectl pointed at the cluster.
set -euo pipefail
cd "$(dirname "$0")/.."

ARGOCD_VERSION="v3.5.5"

echo "Unregistering the metrics APIs (EKS-managed one and metrics-server's)..."
kubectl delete apiservice v1.metrics.eks.amazonaws.com v1beta1.metrics.k8s.io --ignore-not-found

kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd --server-side -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
kubectl wait deploy --all -n argocd --for=condition=available --timeout=300s

kubectl apply -f k8s/namespace.yaml
scripts/create-secrets.sh
kubectl apply -f argocd/application.yaml

echo "Waiting for the Application to compare against the cluster..."
for _ in $(seq 1 30); do
  sync="$(kubectl get application gittogether -n argocd -o jsonpath='{.status.sync.status}' 2>/dev/null || true)"
  [[ "$sync" == "Synced" || "$sync" == "OutOfSync" ]] && break
  sleep 10
done
[[ "$sync" == "Synced" || "$sync" == "OutOfSync" ]] || { echo "ArgoCD did not reach Synced (status: ${sync:-none})" >&2; exit 1; }

echo "ArgoCD is up ($sync). Registering metrics-server's API again..."
kubectl apply -f k8s/eks/metrics-apiservice.yaml
echo "Done. Health may take a minute: kubectl get application gittogether -n argocd"
