variable "cloud" {
  description = "Nuvem alvo (ex: hcso, aws, gcp, azure)"
  type        = string
  default     = "hcso"
}

variable "region" {
  description = "Região/locação padrão"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Nome do projeto"
  type        = string
  default     = "esteira-geo"
}

variable "ssh_public_key" {
  description = "SSH public key para acesso às VMs"
  type        = string
  default     = ""
}

# Variáveis específicas de cada provedor podem ficar em `envs/*.tfvars`.
