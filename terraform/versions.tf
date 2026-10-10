terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.59"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Every resource gets these tags, so leftovers are easy to find in the AWS console.
  default_tags {
    tags = {
      Project     = "gittogether"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
