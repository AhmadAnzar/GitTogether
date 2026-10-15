#!/usr/bin/env bash
# Fill a running GitTogether with sample students, profiles and connections (for demos and screenshots).
# Goes through the public API, so it works against docker compose, kind or EKS. Safe to re-run:
# existing accounts are logged into and existing profiles are kept.
#
#   scripts/seed-demo-data.sh http://localhost:3000
#   scripts/seed-demo-data.sh http://<load-balancer-hostname>
#
# All people are made up; the shared password is for demo data only (never use it for a real account).
set -euo pipefail

BASE="${1:?usage: $0 <base-url>}"
BASE="${BASE%/}"
PASSWORD="demo-password-1"
JARS="$(mktemp -d)"
trap 'rm -rf "$JARS"' EXIT

# email|name|department|year|availability|skills|bio
PEOPLE=(
  "aarav@example.com|Aarav Sharma|Computer Science|3|OPEN_TO_TEAM|Python, FastAPI, Docker|Backend dev who likes APIs and CI pipelines. Looking for a hackathon team."
  "diya@example.com|Diya Patel|Computer Science|2|OPEN_TO_TEAM|React, TypeScript, Figma|Frontend and design. I turn rough ideas into clean interfaces."
  "kabir@example.com|Kabir Singh|Electronics|4|BUSY|Embedded C, MQTT, Raspberry Pi|IoT projects, currently busy with my final-year thesis."
  "meera@example.com|Meera Nair|Data Science|3|OPEN_TO_TEAM|Python, Pandas, PyTorch, SQL|Data and ML. Happy to own the model and the notebooks."
  "rohan@example.com|Rohan Gupta|Information Technology|2|OPEN_TO_TEAM|Kubernetes, Terraform, AWS|DevOps enthusiast: infrastructure as code and monitoring."
  "ananya@example.com|Ananya Iyer|Computer Science|1|NOT_LOOKING|Java, Spring, Git|First year, learning the basics. Not looking for a team yet."
  "vikram@example.com|Vikram Rao|Mechanical|4|OPEN_TO_TEAM|CAD, Arduino, 3D printing|Hardware prototyping for robotics and automation projects."
  "sara@example.com|Sara Khan|Computer Science|3|OPEN_TO_TEAM|Go, PostgreSQL, gRPC|Distributed systems and databases. Prefers small teams."
)

api() {  # api <jar> <method> <path> [json-body]  -> prints the response body, fails on HTTP errors except 409
  local jar="$1" method="$2" path="$3" body="${4:-}" out code
  out="$(mktemp)"
  if [[ -n "$body" ]]; then
    code="$(curl -s -o "$out" -w '%{http_code}' -X "$method" -b "$jar" -c "$jar" \
      -H 'Content-Type: application/json' -d "$body" "$BASE$path")"
  else
    code="$(curl -s -o "$out" -w '%{http_code}' -X "$method" -b "$jar" -c "$jar" "$BASE$path")"
  fi
  cat "$out"; rm -f "$out"
  [[ "$code" =~ ^2 || "$code" == 409 ]] || { echo "HTTP $code from $method $path" >&2; return 1; }
}

first_number() { grep -o "\"$1\":[0-9]*" | head -1 | cut -d: -f2; }

skills_json() {  # "a, b, c" -> ["a","b","c"]
  local out="" s
  IFS=',' read -ra parts <<< "$1"
  for s in "${parts[@]}"; do s="${s#"${s%%[![:space:]]*}"}"; out+="\"$s\","; done
  printf '[%s]' "${out%,}"
}

IDS=()
for person in "${PEOPLE[@]}"; do
  IFS='|' read -r email name dept year avail skills bio <<< "$person"
  jar="$JARS/$email"
  creds="{\"email\":\"$email\",\"password\":\"$PASSWORD\"}"
  resp="$(api "$jar" POST /api/auth/register "$creds")"
  if [[ "$resp" == *"already exists"* ]]; then resp="$(api "$jar" POST /api/auth/login "$creds")"; fi
  IDS+=("$(printf '%s' "$resp" | first_number id)")
  slug="$(printf '%s' "$name" | tr 'A-Z ' 'a-z-')"
  profile="{\"name\":\"$name\",\"bio\":\"$bio\",\"skills\":$(skills_json "$skills"),\"department\":\"$dept\",\"year\":$year,\"availability\":\"$avail\",\"visibility\":\"PUBLIC\",\"linkedin_url\":\"https://www.linkedin.com/in/$slug\"}"
  api "$jar" POST /api/profiles "$profile" > /dev/null
  echo "ok  $name <$email>"
done

# connect <from-index> <to-index> <accept: yes|no>
connect() {
  local from="$JARS/$(cut -d'|' -f1 <<< "${PEOPLE[$1]}")" to="$JARS/$(cut -d'|' -f1 <<< "${PEOPLE[$2]}")" rid
  api "$from" POST /api/connections/requests "{\"user_id\":${IDS[$2]}}" > /dev/null
  if [[ "$3" == yes ]]; then
    rid="$(api "$to" GET /api/connections/requests | grep -o '"incoming":\[{"id":[0-9]*' | grep -o '[0-9]*$' | head -1)"
    [[ -n "$rid" ]] && api "$to" POST "/api/connections/requests/$rid/accept" > /dev/null
  fi
}
connect 0 1 yes   # Aarav and Diya are connected
connect 0 3 yes   # Aarav and Meera are connected
connect 4 0 no    # Rohan's request to Aarav is still pending
connect 7 1 no    # Sara's request to Diya is still pending
echo "Seeded ${#PEOPLE[@]} people. Log in as aarav@example.com / $PASSWORD to see connections."
