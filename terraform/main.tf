# GitTogether infrastructure: a VPC (2 public + 2 private subnets) and an EKS cluster with one managed node group.
#
#   Internet -> load balancer (public subnets) -> worker nodes (private subnets) -> NAT gateway -> Internet
#
# Worker nodes have no public IPs; they reach the internet (image pulls) through a single NAT gateway.
# Cost choices (runs on AWS credits): one NAT gateway instead of one per AZ, no CloudWatch control-plane
# logs or VPC flow logs, and a Kubernetes version in STANDARD support (extended support is $0.60/hr vs
# $0.10/hr). Kubernetes Secrets ARE encrypted with a KMS key (~$1/month, billed hourly).
# Accepted security trade-offs are documented in ../.trivyignore.

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.3"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  public_subnets  = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, 101 + i)] # load balancers, NAT
  private_subnets = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, 1 + i)]   # worker nodes

  enable_nat_gateway   = true
  single_nat_gateway   = true # one NAT for both AZs: fine for a demo, halves the NAT cost
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tell Kubernetes where to place internet-facing vs internal load balancers.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.26.0"

  name               = var.cluster_name
  kubernetes_version = var.kubernetes_version
  upgrade_policy = {
    support_type = "STANDARD" # never silently roll into paid extended support
  }

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets # nodes and control-plane ENIs stay private

  endpoint_public_access                   = true
  enable_cluster_creator_admin_permissions = true

  # Envelope-encrypt Kubernetes Secrets with a customer-managed KMS key. The shortest deletion window
  # (7 days) means the key is gone soon after `terraform destroy`; keys pending deletion are not billed.
  kms_key_deletion_window_in_days = 7

  create_cloudwatch_log_group = false
  enabled_log_types           = []

  addons = {
    vpc-cni = {
      before_compute = true # pod networking must exist before nodes join
    }
    kube-proxy             = {}
    coredns                = {}
    eks-pod-identity-agent = {}
    aws-ebs-csi-driver     = {} # PersistentVolumes for PostgreSQL
    metrics-server         = {} # CPU metrics for the HorizontalPodAutoscaler
  }

  eks_managed_node_groups = {
    main = {
      instance_types = [var.node_instance_type]
      ami_type       = "AL2023_x86_64_STANDARD"
      capacity_type  = "ON_DEMAND" # spot is cheaper but can vanish mid-demo

      min_size     = 2
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      # The EBS CSI driver runs on the nodes and uses their role to create volumes.
      iam_role_additional_policies = {
        ebs_csi = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
      }
    }
  }
}
