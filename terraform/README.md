Scaffold Terraform para criação de ambiente (genérico)

Este diretório contém arquivos de exemplo e templates para iniciar infraestrutura em `hcso` e outras nuvens.

Como usar (exemplo):

1. Escolher provedor/nuvem e adaptar `providers.tf`.
2. Preencher variáveis em `terraform.tfvars` ou exportar variáveis de ambiente.
3. Executar `terraform init` e `terraform plan`.

Obs: os arquivos aqui são um ponto de partida — adicione módulos específicos por nuvem em `modules/`.
