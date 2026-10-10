# GitTogether

This repository is also a **DevOps capstone**: it takes the app from a laptop to a monitored Kubernetes
cluster on AWS, with tests, security scanning and infrastructure as code at every step.

![CI/CD](https://github.com/AhmadAnzar/GitTogether/actions/workflows/gittogether-ci.yml/badge.svg)

---

## Architecture

```text
Developer ── git push ──► GitHub
                            │
                            ▼
                   GitHub Actions pipeline
   ┌──────────────┬────────────────┬──────────────────┬────────────────┬─────────────────┐
   │ gitleaks     │ backend        │ frontend         │ terraform      │ trivy config    │
   │ secret scan  │ ruff + pytest  │ eslint + vitest  │ fmt + validate │ (IaC, report)   │
   │              │ (≥90% cover)   │ + vite build     │                │                 │
   └──────────────┴───────┬────────┴────────┬─────────┴────────────────┴─────────────────┘
                          ▼                 ▼
                 docker build ──► Trivy image scan (fails on HIGH/CRITICAL) ──► push to GHCR
                                                                               (tag = commit SHA)

AWS (Terraform)                                   Kubernetes (Helm)
┌───────────────────────────────────────┐        ┌───────────────────────────────────────────┐
│ VPC 10.20.0.0/16, 2 AZs               │        │ Ingress  /     ──► frontend (nginx, React) │
│  public subnets:  load balancer, NAT  │ ─────► │          /api  ──► backend  (FastAPI)      │
│  private subnets: EKS worker nodes    │        │                       │                    │
│ EKS 1.36, 3 × t3.medium, KMS secrets  │        │                   PostgreSQL (PVC)         │
└───────────────────────────────────────┘        │ HPA on backend · Prometheus + Grafana      │
                                                 └───────────────────────────────────────────┘
```

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 18, Vite 5, plain CSS; served by non-root Nginx 1.30 |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic, Uvicorn; argon2 password hashing (pwdlib), JWT sessions (PyJWT) |
| Database | PostgreSQL 16 |
| Quality | pytest + pytest-cov (90% gate), ruff, ESLint, Vitest |
| Security | gitleaks, Trivy (image + config scans), GitHub code scanning, Dependabot |
| Containers | Docker (multi-stage frontend, non-root users), Docker Compose |
| CI/CD | GitHub Actions, GitHub Container Registry (GHCR) |
| Infrastructure | Terraform, AWS VPC, EKS, KMS |
| Kubernetes | Helm, Ingress (Traefik), HPA, metrics-server, Pod Security Admission (restricted), kind for local clusters |
| Observability | Prometheus, Grafana, `/metrics` via prometheus-fastapi-instrumentator |

## Repository layout

```text
.github/workflows/   CI/CD pipeline        backend/      FastAPI app, Alembic migrations, tests
.github/dependabot.yml                     frontend/     React app, Nginx config, tests
terraform/           AWS VPC + EKS          helm/         Helm chart for the app
k8s/                 namespace, kind/EKS add-on values   monitoring/   Prometheus/Grafana values
scripts/             load-test helper       troubleshooting/  deliberately broken manifests (lab)
demo/                screenshots, slides, demo video
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness: the process is up |
| GET | `/ready` | Readiness: database reachable (503 if not) |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/auth/register` | Create an account (email + password) and log in |
| POST | `/api/auth/login` · `/api/auth/logout` | Start / end a session |
| GET | `/api/auth/me` | The logged-in user and their profile id |
| GET | `/api/profiles` | List profiles. Query: `skill`, `q` (name/department), `availability`, `limit` (≤100), `offset` |
| GET | `/api/profiles/stats` | Totals per availability, limited count, top public skills |
| GET | `/api/profiles/{id}` | One profile |
| POST | `/api/profiles` | Create your profile (one per account) 🔒 |
| PUT | `/api/profiles/{id}` | Update your profile (partial) 🔒 owner |
| DELETE | `/api/profiles/{id}` | Delete your profile 🔒 owner |
| PUT · DELETE | `/api/profiles/{id}/resume` | Upload (PDF, ≤ 5 MB) or remove your resume 🔒 owner |
| GET | `/api/profiles/{id}/resume` | Download a resume (subject to the privacy rule) |
| GET | `/api/connections` | Your connections 🔒 |
| GET | `/api/connections/requests` | Your pending requests: `incoming` and `outgoing` 🔒 |
| POST | `/api/connections/requests` | Send a connection request `{ "user_id": … }` 🔒 |
| POST | `/api/connections/requests/{id}/accept` · `/decline` | Answer a request you received 🔒 |
| DELETE | `/api/connections/requests/{id}` | Cancel a request you sent 🔒 |
| DELETE | `/api/connections/{user_id}` | Remove a connection 🔒 |

🔒 = requires login. Sessions use an `httpOnly`, `SameSite=Lax` cookie holding a signed JWT (24 h);
passwords are hashed with argon2 and never stored in plain text.

**Connections:** a request stays pending until the other person accepts (declining or cancelling
deletes it). Accepted connections are mutual.

**Privacy rule:** a `LIMITED` profile's skills, LinkedIn and resume are visible only to its owner and
their connections. The API removes those fields before responding, so the data never reaches anyone
else's browser, and hidden skills are excluded from skill search. Interactive docs:
`http://localhost:8000/docs`.

## Run locally

Requirements: Docker Desktop.

```bash
cp .env.example .env          # optional: change local database credentials
docker compose up --build
```

- App: http://localhost:3000
- API docs: http://localhost:8000/docs

Postgres is not published on a host port; inspect it with `docker compose exec postgres psql -U gittogether`.
Stop with `docker compose down` (add `-v` to delete the database volume).

### Tests and linting

```bash
cd backend && pip install -r requirements-dev.txt && ruff check . && pytest -v
cd frontend && npm ci && npm run lint && npm test
```

## CI/CD pipeline

Defined in [`.github/workflows/gittogether-ci.yml`](.github/workflows/gittogether-ci.yml). Runs on every
push and pull request to `main` (docs-only changes are skipped), and manually via **Run workflow**.

1. **Stage 1, in parallel:** gitleaks secret scan of the full history · backend ruff + pytest (fails
   below 90% coverage) · frontend ESLint + Vitest + build · Terraform fmt + validate · Helm lint + kubeconform
   schema validation of the rendered manifests · Trivy config scan
   of Dockerfiles, Kubernetes and Terraform (report-only, published to the Security tab).
2. **Stage 2, per image:** Docker build → **Trivy image scan that fails on fixable HIGH/CRITICAL CVEs** →
   push to `ghcr.io/ahmadanzar/gittogether/{backend,frontend}` tagged with the full commit SHA.
   Pull requests run everything except the push.

Third-party actions are referenced by version; the Trivy action is pinned to a commit SHA because its
tags were rewritten upstream in 2026.

## Security

- **Trivy image scanning.** Trivy scans each built image's OS packages (Debian / Alpine) and application
  libraries (Python packages, npm) against vulnerability databases, and the pipeline fails if any
  HIGH or CRITICAL issue with an available fix is found. Its first run caught three HIGH CVEs in
  Starlette (e.g. CVE-2025-62727, a denial of service via crafted HTTP `Range` headers) and 41 issues in
  the old `nginx 1.27` / Alpine 3.21 base image; upgrading FastAPI/Starlette and moving to
  `nginx-unprivileged:1.30-alpine` (plus `apk upgrade`) brought both images to zero.
- **Trivy config scanning** checks Terraform, Dockerfiles and Kubernetes manifests. Deliberate trade-offs
  (public EKS endpoint, open node egress, no paid CloudWatch/flow logs) are listed with reasons in
  [`.trivyignore`](.trivyignore).
- **gitleaks** fails the pipeline if a secret appears anywhere in the git history.
- **Containers** run as non-root users (backend uid 10001, frontend uid 101); Nginx sends a strict
  Content-Security-Policy and other security headers and hides its version.
- **No credentials in git:** `.env`, `*.tfvars` and Terraform state are gitignored; AWS credentials come
  from the local AWS CLI profile.

## Infrastructure (Terraform)

See [`terraform/README.md`](terraform/README.md). Summary: a VPC with 2 public and 2 private subnets
across two AZs, one NAT gateway, and an EKS 1.36 cluster (standard support, KMS-encrypted Secrets) with
a managed node group of 3 × `t3.medium` in the private subnets. Cost while running is about $0.35/hour,
so the cluster is created for demos and destroyed the same day.

```bash
cd terraform
terraform init && terraform plan
terraform apply
aws eks update-kubeconfig --region ap-south-1 --name gittogether-eks
```

## Kubernetes / Helm

The app is packaged as a Helm chart in [`helm/gittogether`](helm/gittogether):

| Resource | Details |
|---|---|
| Backend `Deployment` | 2–5 replicas (HPA on CPU, 70% target). An init container runs `alembic upgrade head` first; a Postgres advisory lock makes replicas take turns. Liveness `/health`, readiness `/ready`. |
| Frontend `Deployment` | 2 replicas, non-root nginx; its `/api` proxy target comes from `BACKEND_URL`. |
| PostgreSQL `StatefulSet` | 1 replica with its own PersistentVolumeClaim (deleted on `helm uninstall`, so no disk is left behind). |
| `Service`s | ClusterIP for backend and frontend, headless for Postgres. |
| `Ingress` | `/api` → backend, `/` → frontend (Traefik). `/metrics`, `/health`, `/ready` are not exposed. |
| `HorizontalPodAutoscaler`, `PodDisruptionBudget`s | Scale the API on CPU; keep at least one pod of each component during node drains. |
| `ServiceMonitor` | Prometheus scraping of `/metrics` (enabled with the monitoring stack). |

**Security:** the `gittogether` namespace enforces the Kubernetes **restricted** Pod Security level, so
every pod must run as non-root, with a read-only root filesystem, no privilege escalation, all Linux
capabilities dropped and the RuntimeDefault seccomp profile; anything else is rejected at admission.
Passwords and the JWT key are **not in git or in values files**: `scripts/create-secrets.sh` creates
a Kubernetes Secret with random values, which the chart references.

**Ingress controller:** Traefik. The previously common ingress-nginx project was retired by the
Kubernetes project in March 2026 and no longer receives security fixes; Traefik implements the same
standard `Ingress` resource.

### Run it on a local cluster (kind)

```bash
kind create cluster --config k8s/local/kind-config.yaml        # maps host ports 80/443 to the cluster
helm repo add traefik https://traefik.github.io/charts
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm upgrade --install traefik traefik/traefik --version 41.6.0 -n traefik --create-namespace -f k8s/local/traefik-values.yaml
helm upgrade --install metrics-server metrics-server/metrics-server --version 3.14.0 -n kube-system -f k8s/local/metrics-server-values.yaml

kubectl apply -f k8s/namespace.yaml
scripts/create-secrets.sh
helm upgrade --install gittogether helm/gittogether -n gittogether -f helm/gittogether/values-kind.yaml

kubectl get pods,svc,ingress,hpa -n gittogether
```

Open http://gittogether.localhost. Watch autoscaling with `scripts/load-test.sh` and
`kubectl get hpa -n gittogether -w`.

### Run it on EKS

After `terraform apply` and `aws eks update-kubeconfig ...`:

```bash
helm upgrade --install traefik traefik/traefik --version 41.6.0 -n traefik --create-namespace -f k8s/eks/traefik-values.yaml
kubectl apply -f k8s/namespace.yaml
scripts/create-secrets.sh
helm upgrade --install gittogether helm/gittogether -n gittogether -f helm/gittogether/values-eks.yaml
kubectl get svc -n traefik traefik      # EXTERNAL-IP = the AWS load balancer hostname to open
```

`values-eks.yaml` also creates a default `gp3` StorageClass (new EKS clusters have none).
metrics-server is installed on EKS by Terraform as a managed add-on.

### Deploy a new version

The pipeline tags images with the commit SHA. Set `image.tag` in `helm/gittogether/values.yaml` to that
SHA and run `helm upgrade` (ArgoCD automates this in the GitOps setup). Roll back with
`helm rollback gittogether <revision> -n gittogether`.

### Troubleshooting lab

`troubleshooting/` contains two deliberately broken manifests (an image that doesn't exist, a Service
whose selector matches nothing) with the commands to diagnose and fix them in their comments.

## Observability

*In progress (Phase 8):* kube-prometheus-stack scraping the backend's `/metrics` through a
ServiceMonitor, and a Grafana dashboard for request rate, latency and error rate.

## Known limitations

- No email verification, password reset or login rate limiting yet; anyone can register with any email.
- Resumes are stored in PostgreSQL; at larger scale they would move to object storage (Amazon S3).
- Profiles created before accounts existed have no owner and are read-only.
- PostgreSQL runs inside the cluster with a PersistentVolumeClaim; production would use Amazon RDS.
- One NAT gateway is shared by both availability zones (cheaper, but a single point of failure).
