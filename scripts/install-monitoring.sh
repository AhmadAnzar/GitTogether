#!/usr/bin/env bash
# Installs kube-prometheus-stack (Prometheus + Grafana) and loads the GitTogether dashboard.
# The app's ServiceMonitor (enabled in values-kind.yaml / values-eks.yaml) then makes Prometheus scrape the
# backend's /metrics. The ServiceMonitor needs this stack's CRDs, so run this before deploying the app.
# Usage: scripts/install-monitoring.sh
set -euo pipefail
cd "$(dirname "$0")/.."

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo update prometheus-community >/dev/null

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus-values.yaml --wait --timeout 10m

# Grafana's sidecar imports every ConfigMap labelled grafana_dashboard=1.
kubectl create configmap gittogether-dashboard -n monitoring \
  --from-file=monitoring/dashboards/gittogether-api.json --dry-run=client -o yaml \
  | kubectl label --local -f - grafana_dashboard=1 -o yaml \
  | kubectl apply -f -

echo
echo "Grafana password:  kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 -d"
echo "Grafana:           kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80   (user: admin)"
echo "Prometheus:        kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090"
