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
  default     = "t3.medium"
}

variable "node_desired_size" {
  description = "Number of worker nodes. 3 x t3.medium = 51 pod slots (17 each), enough for the app, monitoring and ArgoCD."
  type        = number
  default     = 3
}

variable "node_max_size" {
  description = "Upper bound for the node group."
  type        = number
  default     = 4
}
