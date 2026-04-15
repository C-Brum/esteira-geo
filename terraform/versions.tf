terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = "~> 1.40"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}
