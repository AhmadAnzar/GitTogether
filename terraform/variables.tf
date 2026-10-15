variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name, used in tags."
  type        = string
  default     = "dev"
}

variable "cluster_name" {
  description = "Name of the EKS cluster (also used to name the VPC)."
  type        = string
  default     = "gittogether-eks"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version. Keep it in STANDARD support: extended support costs 6x more per hour."
  type        = string
  default     = "1.36"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "node_instance_type" {
  description = "EC2 instance type for the worker nodes."
  type        = string
  default     = "m7i-flex.large"
}

variable "node_desired_size" {
  description = "Number of worker nodes. 2 x m7i-flex.large = 58 pod slots (29 each) and 16 GiB RAM; the free plan allows only a few instance types and 5 vCPUs in total, so 2 nodes is the maximum."
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Upper bound for the node group."
  type        = number
  default     = 2
}
