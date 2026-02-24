# Diagramas - Esteira Geo

Visualizações em Mermaid da arquitetura e fluxos do projeto.

## 📊 Diagramas Disponíveis

### 1. `terraform_architecture.mmd`
**Descrição**: Arquitetura multi-cloud com Terraform e Ansible

**Inclui:**
- AWS Cloud com S3, EC2, RDS
- Huawei Cloud (São Paulo) com OBS, ECS, RDS
- Medallion architecture (Bronze/Silver/Gold)
- Fluxo de deployment com Terraform
- Automação com Ansible

**Use para:**
- Entender deployment em produção
- Planejar infraestrutura multi-cloud
- Documentar arquitetura
- Onboarding de novos desenvolvedores

---

### 2. `docker_architecture.mmd`
**Descrição**: Stack Docker completa para desenvolvimento local

**Inclui:**
- Host machine (Scripts, Docker Compose)
- PostgreSQL 13 + PostGIS
- MinIO (S3 simulado)
- Pipeline ETL Container (Bronze → Silver → Gold → PostGIS)
- Flask Web Container
- Volumes de persistência

**Use para:**
- Development local
- Testes rápidos
- Aprendizado
- CI/CD local

---

### 3. `medallion_flow.mmd`
**Descrição**: Fluxo de dados através das camadas Medallion

**Inclui:**
- Input data (flooding areas + citizens)
- Bronze layer (raw data)
- Silver layer (normalized)
- Gold layer (processed, spatial join)
- PostGIS (spatial database)
- Flask Dashboard (visualization)

**Use para:**
- Entender transformações de dados
- Documentar pipeline
- Desenhar novas features
- Onboarding de data engineers

---

## 🔍 Visualizar Online

### Opção 1: Mermaid Live Editor
1. Abra https://mermaid.live
2. Copie o conteúdo de um arquivo `.mmd`
3. Cole no editor
4. Visualize o diagrama

### Opção 2: Git (GitHub/GitLab)
- Se fazer push para repositório, GitHub renderiza automaticamente

### Opção 3: VS Code
- Instale extensão "Mermaid Support": `bierner.markdown-mermaid`
- Abra arquivo `.mmd` no editor
- Visualize preview ao lado

---

## 💾 Exportar para PNG/SVG

### Pré-requisitos
```bash
# Instalar CLI
npm install -g @mermaid-js/mermaid-cli

# Verificar instalação
mmdc --version
```

### Converter para PNG
```bash
# Converter todos
mmdc -i terraform_architecture.mmd -o terraform_architecture.png
mmdc -i docker_architecture.mmd -o docker_architecture.png
mmdc -i medallion_flow.mmd -o medallion_flow.png

# Ou em um batch
for file in *.mmd; do mmdc -i "$file" -o "${file%.mmd}.png"; done
```

### Converter para SVG
```bash
mmdc -i terraform_architecture.mmd -o terraform_architecture.svg
```

### Converter para PDF
```bash
mmdc -i terraform_architecture.mmd -o terraform_architecture.pdf
```

---

## ✏️ Editar Diagramas

### Online (Mermaid Live Editor)
1. Abra https://mermaid.live
2. Cole conteúdo do `.mmd`
3. Edite no editor
4. Copie resultado de volta
5. Atualize arquivo `.mmd`

### Localmente (No VSCode)
1. Abra arquivo `.mmd` no VSCode
2. Instale extensão Mermaid
3. Edite lado a lado com preview
4. Save

### Syntax de Mermaid
Referência: https://mermaid.js.org/intro/

**Principais elementos:**
```mermaid
graph TB              # Direction: TB, LR, BT, RL
    A["Box"]          # Node with text
    B{Diamond}        # Diamond shape
    C[/Parallelogram]  # Parallelogram
    D[[Subroutine]]    # Subroutine
    
    A -->|Label| B     # Directed edge with label
    B --> C            # Simple edge
    C --> D
    
    style A fill:#FF0,stroke:#000  # Color node
```

---

## 📋 Checklist para Manutenção

Antes de fazer commit:

- [ ] Diagrama renderiza sem erros
- [ ] Cores estão legíveis
- [ ] Labels são claros e concisos
- [ ] Fluxo segue lógica sensata
- [ ] Documentação (este README) está atualizada
- [ ] Arquivo `.mmd` tem sintaxe correta

---

## 🔗 Referências

- **Mermaid Docs**: https://mermaid.js.org/
- **Editor Online**: https://mermaid.live/
- **VS Code Extension**: bierner.markdown-mermaid
- **CLI**: https://github.com/mermaid-js/mermaid-cli

---

## 📝 Notas

1. **Versão Control**: Mantenha `.mmd` no git, não PNG (menor size)
2. **Export PNGs**: Só faça quando precisar para docs/apresentações
3. **Cores**: Use palette do projeto (AWS orange, Huawei red, etc)
4. **Responsive**: Mermaid é responsivo, SVG/PNG não

---

## 🖼️ Preview Atual

Se instalou mermaid-cli, você pode gerar previews:

```bash
# Generate all diagrams
make diagrams

# Or manually
mmdc -i *.mmd --output-dir .
```

---

## Última Atualização

- 📅 Criado: Feb 24, 2026
- 🔄 Última revisão: Feb 24, 2026
- 📊 Diagramas: 3 (Terraform, Docker, Medallion)
- ✅ Status: Completo e validado
