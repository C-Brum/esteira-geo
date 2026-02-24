# Huawei Cloud (sa-brazil-1 - São Paulo)

Este módulo Terraform provisiona infraestrutura na Huawei Cloud na região de São Paulo.

## Recursos provisionados:

- **VPC** com subnet em `sa-brazil-1`
- **Security Groups** para processing, presentation e RDS
- **OBS Buckets** (equivalente a S3): bronze, silver, gold
- **ECS Instances** (equivalente a EC2):
  - `processing`: VM para processamento de dados com Python
  - `presentation`: VM com camada de apresentação, acessível na internet (EIP)
- **RDS PostgreSQL** com suporte para PostGIS (extensão precisa ser criada manualmente)

## Pré-requisitos:

1. **Credenciais Huawei Cloud**:
   - Exporte `HW_ACCESS_KEY` e `HW_SECRET_KEY` como variáveis de ambiente
   - Ou configure em `~/.huaweicloud/auth.json`

2. **SSH Public Key**:
   - Gere uma chave SSH local: `ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa`
   - Será referenciada via output

## Como usar:

```bash
export HW_ACCESS_KEY=<seu_access_key>
export HW_SECRET_KEY=<seu_secret_key>

cd terraform
terraform init
terraform plan -var-file=envs/huawei-sp.tfvars
terraform apply -var-file=envs/huawei-sp.tfvars
```

## Configuração de região:

A região padrão é `sa-brazil-1` (São Paulo). Se precisar adaptar, edite `envs/huawei-sp.tfvars`.

## Instalación de PostGIS:

Após o RDS estar funcional, conecte-se via psql:

```bash
psql -h <rds_endpoint> -U postgres -d esteira-geo-huawei-sp
CREATE EXTENSION postgis;
```

## Variáveis importantes:

- `region`: Deve ser `sa-brazil-1` para São Paulo
- `ssh_public_key`: Caminho da public key local (ex: `~/.ssh/id_rsa.pub`)
- `instance_flavor`: Tipo de VM (ex: `s3.medium.2`)
- `db_instance_class`: Classe de RDS (ex: `db.xlarge.2`)
