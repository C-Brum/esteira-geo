/*
 Root module that selects cloud-specific modules based on `var.cloud`.
 Uses count to conditionally instantiate modules for a chosen cloud.
*/

variable "project" {}
variable "region" {}

module "aws" {
  source  = "./modules/aws"
  count   = var.cloud == "aws" ? 1 : 0

  project = var.project
  region  = var.region
}

module "hcso" {
  source = "./modules/hcso"
  count  = var.cloud == "hcso" ? 1 : 0

  project = var.project
  region  = var.region
}

module "huawei" {
  source = "./modules/huawei"
  count  = var.cloud == "huawei" ? 1 : 0

  project           = var.project
  region            = var.region
  ssh_public_key    = var.ssh_public_key
}
