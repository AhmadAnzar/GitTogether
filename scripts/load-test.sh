#!/usr/bin/env bash
# Generate load on the API to watch the HorizontalPodAutoscaler (and later Grafana) react.
# Used in the recorded demo to show the autoscaler working.
#
#   scripts/load-test.sh [url] [seconds] [parallel]
#   URL=http://<load-balancer-hostname> scripts/load-test.sh        # on EKS
#
# In another terminal:  kubectl get hpa -n gittogether -w
set -euo pipefail

URL="${1:-${URL:-http://gittogether.localhost}}"
SECONDS_TO_RUN="${2:-120}"
PARALLEL="${3:-20}"
TARGET="$URL/api/profiles?limit=100"

echo "Hitting $TARGET with $PARALLEL parallel workers for ${SECONDS_TO_RUN}s..."
end=$((SECONDS + SECONDS_TO_RUN))
worker() {
  local n=0
  while (( SECONDS < end )); do
    curl -s -o /dev/null --max-time 5 "$TARGET" || true
    n=$((n + 1))
  done
  echo "$n"
}
total=0
for _ in $(seq "$PARALLEL"); do worker > "/tmp/gt-load-$$-$RANDOM" & done
wait
for f in /tmp/gt-load-$$-*; do total=$((total + $(cat "$f"))); rm -f "$f"; done
echo "Load test completed: $total requests."
