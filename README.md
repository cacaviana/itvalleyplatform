# petraplatform

SDK multi-tenant plug-and-play da Petra. O dev constrói o sistema normal, sem login,
sem tenant. No final, adiciona `Depends(require_tenant)` nas rotas. Nada mais.

> 📖 Documentação visual completa com diagramas: [`docs/index.html`](docs/index.html)
> (abre direto no navegador — single-page, Mermaid)

## Instalação

```bash
pip install petraplatform
# se for usar RLS no Azure SQL:
pip install 'petraplatform[sql]'
```

`petraplatform` já incorpora `itvalleysecurity` (JWT) — você instala um pacote só.

## Configuração — só `.env`

```env
# obrigatório (do itvalleysecurity)
JWT_SECRET_KEY=uma_chave_com_pelo_menos_32_caracteres_xxx

# banco do APP (cada sistema escolhe o seu) — onde aplica RLS
APP_SQL_CONNECTION=Driver={ODBC Driver 18 for SQL Server};Server=...;Database=<seu_db>;...

# banco platform (dbpetra) — só usado por init-platform CLI e admin/login
PLATFORM_SQL_CONNECTION=Driver={ODBC Driver 18 for SQL Server};Server=...;Database=dbpetra;...

# slug do produto onde checamos permissões
PLATFORM_PRODUCT_SLUG=<slug_do_seu_produto>
```

Você nunca chama `load_dotenv()` no seu app. O pacote carrega sozinho no import.

## Uso — uma linha por rota (padrão IT Valley: Router/Service/Repository)

**Router fino — só Depends. Nunca SQL na rota.**

```python
# routers/leads.py
from fastapi import Depends, FastAPI
from petraplatform import TenantContext, require_permission, require_tenant
from services.leads_service import LeadsService, get_leads_service

app = FastAPI()

@app.get("/api/leads")
async def list_leads(
    tenant: TenantContext = Depends(require_tenant),
    _ = Depends(require_permission("leads")),
    service: LeadsService = Depends(get_leads_service),
):
    return await service.list_all()
```

**Service orquestra. Repository é único lugar com SQL.**

```python
# services/leads_service.py
class LeadsService:
    def __init__(self, repo): self._repo = repo
    async def list_all(self):
        return await self._repo.find_all()

# data/leads_repository.py
class LeadsRepository:
    async def find_all(self):
        # query intacta — RLS no banco filtra por tenant via SESSION_CONTEXT
        return await self._db.fetch_all("SELECT * FROM <seu_schema>.leads")
```

O dev nunca escreve `WHERE tenant_id = X`. RLS aplica sozinha.

## Master users

JWT com claim `is_master: true` acessa qualquer tenant.

- Sem `X-Tenant-Id` → SESSION_CONTEXT marca `is_master=1`, RLS deixa passar.
- Com `X-Tenant-Id: <slug-do-tenant>` → master vê só esse tenant.

Não-master ignora o header sempre — confinado ao próprio `tenant_id` do JWT.

## Setup do banco (1x por ambiente)

### 1. Criar `dbpetra` no Azure
```bash
az sql db create --server <seu-servidor> --resource-group <seu-rg> \
                 --name dbpetra --service-objective S0
```

### 2. Aplicar DDL do schema `platform.*`
```bash
petraplatform init-platform -o platform_init.sql
sqlcmd -S <seu-servidor>.database.windows.net -d dbpetra \
       -U <user> -P $SQL_PWD -i platform_init.sql
```

Cria 8 tabelas (`tenants`, `users`, `tenant_users`, `products`, `tenant_products`,
`permissions`, `role_permissions`, `audit_logs`), seeda os produtos IT Valley e o tenant master.
**Idempotente** — pode rodar várias vezes.

## Setup de RLS por sistema (1x por sistema)

```bash
petraplatform generate-rls --schema <seu_schema> \
    --tables <tabela_a>,<tabela_b>,<tabela_c> -o rls_<seu_sistema>.sql

sqlcmd -S <seu-servidor>.database.windows.net -d <seu_db> \
       -U <user> -P $SQL_PWD -i rls_<seu_sistema>.sql
```

A função `rls.fn_tenant_filter` já vem com o bypass para master:

```sql
WHERE @tenant_id = CAST(SESSION_CONTEXT(N'tenant_id') AS NVARCHAR(100))
   OR CAST(SESSION_CONTEXT(N'is_master') AS BIT) = 1;
```

## Workflow recomendado

1. **Dev:** rotas cruas, zero `Depends`. Foca em negócio (Service/Repository).
2. **Pré-staging:** passa nas rotas, adiciona `Depends(require_tenant)`.
3. **DBA:** `petraplatform generate-rls`, revisa o SQL, roda 1x.
4. **Pronto.** Sistema é multi-tenant.

## Tests

```bash
pip install -e '.[dev]'
pytest -q
```
