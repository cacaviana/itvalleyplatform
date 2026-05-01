# itvalleyplatform

SDK multi-tenant plug-and-play da IT Valley. O dev constrói o sistema normal, sem login,
sem tenant. No final, adiciona `Depends(require_tenant)` nas rotas. Nada mais.

> 📖 Documentação visual completa com diagramas: [`docs/index.html`](docs/index.html)
> (abre direto no navegador — single-page, Mermaid)

## Instalação

```bash
pip install itvalleyplatform
# se for usar RLS no Azure SQL:
pip install 'itvalleyplatform[sql]'
```

`itvalleyplatform` já incorpora `itvalleysecurity` (JWT) — você instala um pacote só.

## Configuração — só `.env`

```env
# obrigatório (do itvalleysecurity)
JWT_SECRET_KEY=uma_chave_com_pelo_menos_32_caracteres_xxx

# banco do APP (Genesis usa dblumina, etc) — onde aplica RLS
APP_SQL_CONNECTION=Driver={ODBC Driver 18 for SQL Server};Server=srvmasterclass.database.windows.net;Database=dblumina;...

# banco platform (dbplatform) — só usado por init-platform CLI e admin/login
PLATFORM_SQL_CONNECTION=Driver={ODBC Driver 18 for SQL Server};Server=srvmasterclass.database.windows.net;Database=dbplatform;...

# slug do produto onde checamos permissões
PLATFORM_PRODUCT_SLUG=genesis
```

Você nunca chama `load_dotenv()` no seu app. O pacote carrega sozinho no import.

## Uso — uma linha por rota

```python
from fastapi import Depends, FastAPI
from itvalleyplatform import TenantContext, require_permission, require_tenant

app = FastAPI()

@app.get("/api/leads")
async def list_leads(
    tenant: TenantContext = Depends(require_tenant),
    _ = Depends(require_permission("leads")),
):
    # query intacta — RLS no banco filtra por tenant via SESSION_CONTEXT
    return await db.query("SELECT * FROM genesis.leads")
```

## Master users

JWT com claim `is_master: true` acessa qualquer tenant.

- Sem `X-Tenant-Id` → SESSION_CONTEXT marca `is_master=1`, RLS deixa passar.
- Com `X-Tenant-Id: clinica-abc` → master vê só esse tenant.

Não-master ignora o header sempre — confinado ao próprio `tenant_id` do JWT.

## Setup do banco (1x por ambiente)

### 1. Criar `dbplatform` no Azure
```bash
az sql db create --server srvmasterclass --resource-group rg-webapp \
                 --name dbplatform --service-objective S0
```

### 2. Aplicar DDL do schema `platform.*`
```bash
itvalleyplatform init-platform -o platform_init.sql
sqlcmd -S srvmasterclass.database.windows.net -d dbplatform \
       -U adminitvalley -P $SQL_PWD -i platform_init.sql
```

Cria 8 tabelas (`tenants`, `users`, `tenant_users`, `products`, `tenant_products`,
`permissions`, `role_permissions`, `audit_logs`), seeda 8 produtos e o tenant master.
**Idempotente** — pode rodar várias vezes.

## Setup de RLS por sistema (1x por sistema)

```bash
itvalleyplatform generate-rls --schema genesis \
    --tables leads,deals,campaigns -o rls_genesis.sql

sqlcmd -S srvmasterclass.database.windows.net -d dblumina \
       -U adminitvalley -P $SQL_PWD -i rls_genesis.sql
```

A função `rls.fn_tenant_filter` já vem com o bypass para master:

```sql
WHERE @tenant_id = CAST(SESSION_CONTEXT(N'tenant_id') AS NVARCHAR(100))
   OR CAST(SESSION_CONTEXT(N'is_master') AS BIT) = 1;
```

## Workflow recomendado

1. **Dev:** rotas cruas, zero `Depends`. Foca em negócio.
2. **Pré-staging:** passa nas rotas, adiciona `Depends(require_tenant)`.
3. **DBA:** `itvalleyplatform generate-rls`, revisa o SQL, roda 1x.
4. **Pronto.** Sistema é multi-tenant.

## Tests

```bash
pip install -e '.[dev]'
pytest -q
```
