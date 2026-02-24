Documentação: Terraform

- Coloque módulos reutilizáveis em `terraform/modules/`.
- Use `terraform/envs/` para arquivos de variáveis por ambiente (ex: `dev.tfvars`, `prod.tfvars`).
- Recomenda-se usar `backend` remoto para estado (S3, GCS, Azure Blob ou equivalente do `hcso`).
