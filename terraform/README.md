# Terraform: AWS VPC + EKS for GitTogether

Provisions, in `ap-south-1` (Mumbai):

| Resource | Details |
|---|---|
| VPC | `10.20.0.0/16` across two AZs: 2 public subnets (load balancer, NAT), 2 private subnets (worker nodes), internet gateway, 1 NAT gateway |
| EKS cluster | Kubernetes 1.35, pinned to **standard** support, Secrets encrypted with KMS |
| Managed node group | 2 × `m7i-flex.large` on-demand (min 2, max 2) in private subnets, Amazon Linux 2023 |
| EKS add-ons | vpc-cni, kube-proxy, coredns, pod-identity-agent, aws-ebs-csi-driver, metrics-server |

Modules: `terraform-aws-modules/vpc/aws` 6.7.3 and `terraform-aws-modules/eks/aws` 21.25.3.

## Cost decisions

EKS is never free. While the cluster exists it costs roughly **$0.40/hour** (control plane $0.10, two nodes ~$0.20, NAT gateway ~$0.06, load balancer and public IPs ~$0.05). Nothing is billed between `terraform destroy` and the next `apply`. Choices:

- **Worker nodes in private subnets** behind a NAT gateway, the production pattern: nodes have no public IPs.
- **A single NAT gateway** shared by both AZs instead of one per AZ (halves the NAT cost; acceptable for a non-production cluster).
- **m7i-flex.large, 2 nodes.** The AWS free plan only allows a few instance types (not `t3.medium`) and 5 vCPUs in total. Each `m7i-flex.large` has 2 vCPUs, 8 GiB and 29 pod slots, so 2 nodes (58 pods, 16 GiB) fit the app, Prometheus/Grafana and ArgoCD.
- **Kubernetes Secrets are encrypted** with a customer-managed KMS key (~$1/month, billed hourly; 7-day deletion window after destroy, during which it isn't billed).
- **No CloudWatch control-plane logs or VPC flow logs** (billed per GB). Cluster observability comes from Prometheus and Grafana instead.
- **Kubernetes version in standard support.** Versions in extended support cost $0.60/hr for the control plane instead of $0.10/hr.
- **On-demand nodes, not spot.** Spot is cheaper but can be reclaimed in the middle of a demo.

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars   # optional; the defaults match it
terraform init
terraform fmt -check && terraform validate
terraform plan -out=tfplan
terraform apply tfplan                          # ~15-20 minutes

aws eks update-kubeconfig --region ap-south-1 --name gittogether-eks
kubectl get nodes
```

AWS credentials come from `aws configure`. They are never stored in this folder.

## Destroying (same day, every time)

Kubernetes creates some AWS resources itself (the Ingress load balancer and the PostgreSQL EBS volume). Terraform doesn't know about them, so remove them first or `terraform destroy` will hang on the VPC and leave paid volumes behind:

```bash
helm uninstall gittogether -n gittogether        # app; also deletes the Postgres volume (EBS disk)
kubectl get pvc -n gittogether                   # must print nothing
helm uninstall traefik -n traefik                # deletes the AWS load balancer
kubectl get svc -A | grep LoadBalancer           # must print nothing
terraform destroy
```

Afterwards, check the AWS console (EC2 → Load Balancers, Volumes; VPC → Your VPCs) for anything tagged `Project = gittogether`.
