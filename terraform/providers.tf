/*
Providers configured for common clouds. Set `var.cloud` to select module.
Make sure credentials for the target provider are available in environment or shared config.
*/

# AWS provider (example)
provider "aws" {
  region = var.region
}

# Huawei Cloud provider
provider "huaweicloud" {
  region = var.region
}

# GCP provider example (commented)
# provider "google" {
#   project = var.project
#   region  = var.region
# }

# Azure provider example (commented)
# provider "azurerm" {
#   features = {}
# }

# Placeholder for HCSO provider — adapt when provider is available
# provider "hcso" {
#   endpoint = var.hcso_endpoint
#   token    = var.hcso_token
# }

# Dica: mantenha provedores em arquivos separados e use workspaces/envs para ambientes.
