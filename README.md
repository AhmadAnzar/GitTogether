# GitTogether

**A campus skill marketplace.** Students list what they can build (skills, LinkedIn, availability) so that
anyone forming a hackathon or project team can find them. Shy students can choose a **limited** profile:
their name, department and availability are public, but their skills and LinkedIn stay private.

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
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic, Uvicorn |
| Database | PostgreSQL 16 |
| Quality | pytest + pytest-cov (90% gate), ruff, ESLint, Vitest |
| Security | gitleaks, Trivy (image + config scans), GitHub code scanning, Dependabot |
| Containers | Docker (multi-stage frontend, non-root users), Docker Compose |
| CI/CD | GitHub Actions, GitHub Container Registry (GHCR) |
| Infrastructure | Terraform, AWS VPC, EKS, KMS |
| Kubernetes | Helm, Ingress (ingress-nginx), HPA, metrics-server |
| Observability | Prometheus, Grafana, `/metrics` via prometheus-fastapi-instrumentator |

## Repository layout

```text
.github/workflows/   CI/CD pipeline        backend/      FastAPI app, Alembic migrations, tests
.github/dependabot.yml                     frontend/     React app, Nginx config, tests
terraform/           AWS VPC + EKS          helm/         Helm chart for the app
k8s/                 namespace manifests    monitoring/   Prometheus/Grafana values
scripts/             load-test helper       troubleshooting/  deliberately broken manifests (lab)
demo/                screenshots, slides, demo video
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness: the process is up |
| GET | `/ready` | Readiness: database reachable (503 if not) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/profiles` | List profiles. Query: `skill`, `q` (name/department), `availability`, `limit` (≤100), `offset` |
| GET | `/api/profiles/stats` | Totals per availability, limited count, top public skills |
| GET | `/api/profiles/{id}` | One profile |
| POST | `/api/profiles` | Create a profile |
| PUT | `/api/profiles/{id}` | Update a profile (partial) |
| DELETE | `/api/profiles/{id}` | Delete a profile |

**Privacy rule:** for `LIMITED` profiles the API itself removes `skills` and `linkedin_url` before
responding, so the data never reaches the browser, and limited skills are excluded from skill search.
Interactive docs: `http://localhost:8000/docs`.

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
   below 90% coverage) · frontend ESLint + Vitest + build · Terraform fmt + validate · Trivy config scan
   of Dockerfiles, Kubernetes and Terraform (report-only, published to the Security tab).
2. **Stage 2, per image:** Docker build → **Trivy image scan that fails on fixable HIGH/CRITICAL CVEs** →
   push to `ghcr.io/ahmadanzar/gittogether-{backend,frontend}` tagged with the full commit SHA.
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

*In progress (Phase 7):* namespace, Helm chart with backend and frontend Deployments (2+ replicas each),
ClusterIP Services, PostgreSQL with a PersistentVolumeClaim, Ingress routing `/` and `/api`, and an HPA
on the backend.

## Observability

*In progress (Phase 8):* kube-prometheus-stack scraping the backend's `/metrics` through a
ServiceMonitor, and a Grafana dashboard for request rate, latency and error rate.

## Known limitations

- No user accounts yet: anyone can edit or delete any profile, and a profile owner can't see their own
  hidden skills. Accounts and "followers can see my skills" are planned as the next feature.
- PostgreSQL runs inside the cluster with a PersistentVolumeClaim; production would use Amazon RDS.
- One NAT gateway is shared by both availability zones (cheaper, but a single point of failure).
