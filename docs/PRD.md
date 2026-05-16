# PRD — petraplatform

**Versão:** 0.1.0
**Status:** MVP em produção interna
**Autor:** Petra AI (Carlos Viana) + Claude
**Última atualização:** 2026-05-16

> Documento independente. Quem ler isso (humano ou IA) deve entender o pacote inteiro
> sem precisar de contexto adicional de conversa ou outros documentos. Ele explica
> o **que é**, **por que existe**, **como funciona** e **como usar** o `petraplatform`.

---

## Índice

1. [Visão e propósito](#1-visão-e-propósito)
2. [Problema que resolve](#2-problema-que-resolve)
3. [Princípios fundamentais (regras IT Valley)](#3-princípios-fundamentais-regras-it-valley)
4. [Arquitetura macro](#4-arquitetura-macro)
5. [Schema `platform.*` (8 tabelas)](#5-schema-platform-8-tabelas)
6. [SDK Python — API pública](#6-sdk-python--api-pública)
7. [Fluxo de uma requisição](#7-fluxo-de-uma-requisição)
8. [Configuração — `.env`](#8-configuração--env)
9. [JWT — claims e ciclo de vida](#9-jwt--claims-e-ciclo-de-vida)
10. [Row-Level Security (RLS) no Azure SQL](#10-row-level-security-rls-no-azure-sql)
11. [Master bypass](#11-master-bypass)
12. [CLI — comandos de setup](#12-cli--comandos-de-setup)
13. [Dependências do pacote](#13-dependências-do-pacote)
14. [Padrão Router / Service / Repository](#14-padrão-router--service--repository)
15. [User vs Contact — distinção crítica](#15-user-vs-contact--distinção-crítica)
16. [Casos de uso (cenários reais)](#16-casos-de-uso-cenários-reais)
17. [Restrições e o que NÃO faz](#17-restrições-e-o-que-não-faz)
18. [Roadmap (v0.2+)](#18-roadmap-v02)
19. [Glossário](#19-glossário)
20. [Apêndice A — Estrutura de arquivos do pacote](#apêndice-a--estrutura-de-arquivos-do-pacote)
21. [Apêndice B — Comparação com soluções alternativas](#apêndice-b--comparação-com-soluções-alternativas)

---

## 1. Visão e propósito

`petraplatform` é um **SDK Python plug-and-play** que dá multi-tenancy a qualquer API FastAPI da
suíte Petra (Genesis, Quanto, Vitrine, Polaris, Calenda) — e a qualquer sistema futuro Petra ou
IT Valley educacional (TaskDemand).

### Princípio fundamental

> O dev constrói o sistema **normal**, sem login, sem tenant.
> No final do desenvolvimento, adiciona `Depends(require_tenant)` nas rotas.
> Nada mais.

O dev **não escreve**:
- código de autenticação JWT (vem do `itvalleysecurity`, dependência embutida)
- filtro `WHERE tenant_id = X` em SQL (Row-Level Security do Azure SQL faz isso)
- decorator próprio, middleware Starlette, hash de senha
- `load_dotenv()` no app (o pacote carrega sozinho)

### O que é

Uma biblioteca Python distribuída via `pip install petraplatform` que:
- Valida JWT (delegando ao `itvalleysecurity`)
- Constrói um objeto `TenantContext` em memória a partir das claims do token
- Seta `SESSION_CONTEXT` no Azure SQL para a RLS aplicar isolamento por tenant
- Expõe 3 dependencies FastAPI: `require_tenant`, `require_permission(slug)`, `require_product(slug)`
- Oferece CLI (`petraplatform init-platform`, `petraplatform generate-rls`) para setup do banco

### O que **não** é

- Não é um sistema com frontend
- Não é uma API standalone
- Não é um framework (não impõe estrutura ao código do dev além das dependencies)

---

## 2. Problema que resolve

A Petra tem **5 produtos SaaS B2B** (Genesis, Quanto, Vitrine, Polaris, Calenda) que serão
contratados por **N empresas clientes** (clínicas, escritórios, e-commerce, etc.). Cada
empresa tem:
- Seus próprios dados (leads, cotações, conteúdo, agenda)
- Seus próprios usuários (dono + funcionários)
- Sua própria assinatura (quais produtos contratou)

Sem multi-tenancy correto, os 5 produtos teriam que cada um implementar:
- Autenticação JWT (5x o mesmo código)
- Filtro de tenant em toda query (risco enorme de vazamento entre clientes)
- Catálogo de produtos/permissões (5 implementações divergentes)
- Master access para suporte (5x manualmente)

**`petraplatform` centraliza tudo isso em 1 SDK.** Resultado:

| Aspecto | Sem `petraplatform` | Com `petraplatform` |
|---|---|---|
| Linhas pra autenticar uma rota | ~20 (extrair JWT, decode, validar, parsear) | **1** (`Depends(require_tenant)`) |
| Filtro de tenant na query | `WHERE tenant_id = ?` em **toda** query | **zero** — RLS no banco resolve |
| Risco de vazamento entre tenants | Alto (qualquer query esquecida vaza) | **Próximo de zero** (RLS bloqueia mesmo se dev errar) |
| Mudança de regra (ex: nova role) | Propagar nos 5 produtos | Atualizar 1 tabela `role_permissions` |
| Master/suporte interno | Implementar override em cada produto | JWT com `is_master: true` já bypassa |

---

## 3. Princípios fundamentais (regras IT Valley)

Estes princípios **não são negociáveis** — qualquer mudança no SDK deve respeitar.

### 3.1 Env-only

Toda configuração via variável de ambiente. `Settings` é `@dataclass(frozen=True)` interna,
populada via `os.getenv(...)`. **O pacote chama `load_dotenv()` sozinho no `import`.**

```python
# petraplatform/config.py — primeiro arquivo lido no import
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(usecwd=True), override=False)

@dataclass(frozen=True)
class Settings:
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    APP_SQL_CONNECTION: str = os.getenv("APP_SQL_CONNECTION", "")
    ...
```

O dev **nunca**:
- Chama `load_dotenv()` no app dele
- Instancia `Settings()`
- Passa configuração via argumento de função

### 3.2 Segurança vive no SDK, nunca na camada API

Toda lógica de autenticação, validação, permissão, RLS está **dentro do pacote**.
A camada API do dev (routers FastAPI) só declara `Depends(...)`.

Anti-padrão proibido:
```python
# ERRADO — router não pode conhecer JWT
@app.get("/leads")
async def list_leads(request: Request):
    token = request.headers.get("Authorization").replace("Bearer ", "")
    claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    if not claims.get("permissions", {}).get("leads"):
        raise HTTPException(403)
    return await db.execute(f"SELECT * FROM leads WHERE tenant_id = '{claims['tenant_id']}'")
```

Correto:
```python
# router fino
@app.get("/api/leads")
async def list_leads(
    tenant: TenantContext = Depends(require_tenant),
    _ = Depends(require_permission("leads")),
    service: LeadsService = Depends(get_leads_service),
):
    return await service.list_all()  # SQL intacto, RLS filtra no banco
```

### 3.3 Dev pluga `Depends` só no final

Durante desenvolvimento, rotas são **cruas**, sem auth, sem `Depends`. Foco em negócio
puro. Quando o sistema vai pra teste/staging, o dev **passa nas rotas** adicionando:
- `Depends(require_tenant)` em qualquer rota que precisa de identificação
- `Depends(require_permission("X"))` em rotas que exigem permissão específica

### 3.4 Não reimplementar JWT

`petraplatform` importa `itvalleysecurity` como dependência. Nunca duplica código de JWT.
Toda emissão/validação de token passa por `issue_pair()` e `verify_access()` do
`itvalleysecurity`.

---

## 4. Arquitetura macro

### 4.1 Componentes externos ao SDK

```
┌──────────────────────────────────────────────────────────────┐
│              Cliente (browser/app)                            │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTPS + JWT
                       ▼
┌──────────────────────────────────────────────────────────────┐
│        FastAPI app (Genesis / Quanto / etc.)                  │
│        ┌─────────────────────────────────────────────────┐    │
│        │  petraplatform SDK (pip install)                │    │
│        │   ├── require_tenant                            │    │
│        │   ├── require_permission                        │    │
│        │   ├── require_product                           │    │
│        │   └── TenantContext                             │    │
│        └─────────────┬───────────────────────────────────┘    │
└──────────────────────┼───────────────────────────────────────┘
                       │
        ┌──────────────┼───────────────┐
        │              │               │
        ▼              ▼               ▼
   ┌─────────┐  ┌──────────┐   ┌──────────────┐
   │ JWT     │  │ Azure SQL│   │ Azure SQL    │
   │ verify  │  │ APP DB   │   │ PLATFORM DB  │
   │ (memory)│  │ (RLS)    │   │ (dbpetra)    │
   └─────────┘  └──────────┘   └──────────────┘
                  ▲                  ▲
                  │                  │
        SESSION_CONTEXT          (só no /login
        toda request             e admin CRUD)
```

### 4.2 Dois bancos SQL — papéis distintos

| Banco | Schema | Conteúdo | Quem toca |
|---|---|---|---|
| **APP DB** (cada sistema escolhe — Genesis usa `dblumina`, etc.) | `<sistema>.*` | Dados de domínio (leads, cotações, mensagens) | Backend a **cada request**, com SESSION_CONTEXT setado pelo SDK |
| **PLATFORM DB** (`dbpetra`) | `platform.*` | Identidade compartilhada (tenants, users, products, perms) | Apenas no `/login` e em endpoints admin |

**Crítico**: o SDK em `require_tenant` **não consulta** o PLATFORM DB no request path
(v0.1). Todas as claims necessárias já estão no JWT — o middleware lê, monta o
`TenantContext` em memória, e seta SESSION_CONTEXT no APP DB. Zero round-trip extra.

---

## 5. Schema `platform.*` (8 tabelas)

Estas 8 tabelas vivem em `dbpetra.platform.*` e são compartilhadas por todos os
produtos da Petra.

### 5.1 Diagrama ER

```
TENANTS ──< TENANT_USERS >── USERS
   │                              │
   ├──< TENANT_PRODUCTS >── PRODUCTS ──< PERMISSIONS
   │                                          │
   └──< AUDIT_LOGS >── USERS                  │
                                       ROLE_PERMISSIONS
```

### 5.2 Definição de cada tabela

#### `platform.tenants` — a empresa cliente

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | NVARCHAR(50) PK | slug curto (ex: `clinica-abc`) |
| `name` | NVARCHAR(200) | nome legível (ex: "Clínica ABC Saúde") |
| `slug` | NVARCHAR(100) UNIQUE | usado em URLs, paths de storage |
| `plan` | NVARCHAR(50) | livre (ex: `captar`, `fidelizar`, `internal`) |
| `status` | NVARCHAR(20) | `active` / `suspended` / `trial` |
| `is_master` | BIT | `1` = master da Petra (bypassa RLS) |
| `config` | NVARCHAR(MAX) NULL | JSON livre |
| `deleted_at` | DATETIME2 NULL | soft delete |
| `created_at`, `updated_at` | DATETIME2 | timestamps automáticos |

**Não entra aqui**: funcionário (vai pra `users`), lead capturado (vai pra `shared.contacts`).

#### `platform.users` — a pessoa física que LOGA

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | NVARCHAR(50) PK | uuid |
| `email` | NVARCHAR(255) **UNIQUE GLOBAL** | 1 email → 1 pessoa, atravessa tenants |
| `name` | NVARCHAR(200) | |
| `password_hash` | NVARCHAR(500) NOT NULL | argon2id ou bcrypt |
| `is_active` | BIT DEFAULT 1 | |
| `deleted_at`, `created_at`, `updated_at` | DATETIME2 | |

**Não entra aqui**: lead/contato (não loga, vai pra `shared.contacts`).

#### `platform.tenant_users` — vínculo pessoa ↔ empresa

| Coluna | Tipo | Notas |
|---|---|---|
| `tenant_id` | NVARCHAR(50) FK → tenants(id) | PK composta |
| `user_id` | NVARCHAR(50) FK → users(id) | PK composta |
| `role` | NVARCHAR(50) DEFAULT 'user' | resolve em `role_permissions` |
| `status` | NVARCHAR(20) | |
| `created_at` | DATETIME2 | |

1 pessoa pode estar em N tenants (consultora que atende várias clínicas).

#### `platform.products` — catálogo de produtos Petra

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | INT IDENTITY PK | |
| `slug` | NVARCHAR(50) UNIQUE | `genesis`, `quanto`, `vitrine`, `polaris`, `calenda` |
| `name`, `description` | NVARCHAR | |
| `is_active` | BIT | |

Tabela quase estática. Pacotes comerciais (Atrair/Captar/Relacionar/Fidelizar) **não**
entram aqui — são camada de marketing.

#### `platform.tenant_products` — assinaturas

| Coluna | Tipo | Notas |
|---|---|---|
| `tenant_id`, `product_id` | FK | PK composta |
| `status` | NVARCHAR(20) | `active` / `expired` / `trial` |
| `expires_at` | DATETIME2 NULL | |

Verdade plana do que cada tenant pagou pra usar.

#### `platform.permissions` — catálogo de ações

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | INT IDENTITY PK | |
| `product_id` | INT FK → products(id) | |
| `slug` | NVARCHAR(100) | ex: `leads.view`, `leads.edit`, `quotes.send` |
| `name` | NVARCHAR(200) | rótulo legível |

UNIQUE em (product_id, slug).

#### `platform.role_permissions` — mapa role → permissões

| Coluna | Tipo | Notas |
|---|---|---|
| `role` | NVARCHAR(50) | "admin", "user", "viewer" |
| `product_id` | INT FK | |
| `permission_id` | INT FK | |

PK composta dos 3.

#### `platform.audit_logs` — eventos de plataforma

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | NVARCHAR(50) PK | |
| `tenant_id` | NVARCHAR(50) FK NULL | NULL para ações master/globais |
| `user_id` | NVARCHAR(50) FK NULL | quem fez |
| `action` | NVARCHAR(100) | `user.invited`, `tenant.created`, `role.changed` |
| `entity_type`, `entity_id` | NVARCHAR | alvo do evento |
| `payload_json` | NVARCHAR(MAX) | dados adicionais |
| `created_at` | DATETIME2 | |

**Crítico**: registra eventos de **identidade/governança**, não de negócio. Eventos
de negócio (criou lead, fechou deal) ficam em `<sistema>.audit_logs`.

### 5.3 Seeds aplicados pelo `init-platform`

- **1 tenant master**: `id='petra', name='Petra (Master)', is_master=1, plan='internal'`
- **5 produtos**: genesis, quanto, vitrine, polaris, calenda
- A definição de roles e permissões é deixada pra cada produto (cada sistema rodará seu próprio script)

---

## 6. SDK Python — API pública

### 6.1 Exports

```python
from petraplatform import (
    TenantContext,
    require_tenant,
    require_permission,
    require_product,
    InvalidToken,
    PermissionDenied,
    ProductNotSubscribed,
    TenantNotFound,
    TokenMissing,
)
```

### 6.2 `TenantContext` — objeto entregue à rota

```python
@dataclass
class TenantContext:
    id: str                              # 'clinica-abc'
    user_id: str                         # 'u-001'
    user_email: str | None
    is_master: bool                      # True se o JWT tem is_master=True
    products: list[str]                  # ['genesis', 'calenda']
    permissions: dict[str, list[str]]    # {'genesis': ['leads.view','leads.edit']}
    raw_claims: dict                     # todas as claims do JWT
    current_product: str | None          # = PLATFORM_PRODUCT_SLUG do .env

    def has_product(self, product_slug: str) -> bool: ...
    def check_product(self, product_slug: str) -> None: ...      # raise se não
    def has_permission(self, permission: str) -> bool: ...
    def check_permission(self, permission: str) -> None: ...     # raise se não
```

Master sempre passa em `has_product`/`has_permission`/`check_*`.

### 6.3 Dependencies FastAPI

#### `require_tenant`

```python
async def require_tenant(request: Request, claims: dict = Depends(decode_jwt)) -> TenantContext
```

- Valida JWT (via `itvalleysecurity`)
- Monta `TenantContext` a partir das claims
- Lê header `X-Tenant-Id` se master (escolhe tenant alvo); ignora se não master
- Seta `SESSION_CONTEXT` no APP DB (`tenant_id` + `is_master`)
- Retorna o `TenantContext`

#### `require_permission(slug, product_slug=None)`

Factory: gera um `Depends` que valida se o user tem a permissão no produto atual
(definido por `PLATFORM_PRODUCT_SLUG` do `.env`) ou no produto explicitamente passado.

```python
@app.get("/api/leads")
async def list_leads(
    tenant: TenantContext = Depends(require_tenant),
    _ = Depends(require_permission("leads.view")),
):
    ...
```

Se não tiver permissão → HTTP 403 com `detail="Permission 'leads.view' required"`.
Master sempre passa.

#### `require_product(slug)`

Garante que o tenant tem o produto na assinatura. 403 se não tem (`Tenant has no
subscription to product 'X'`).

---

## 7. Fluxo de uma requisição

```
1. Cliente envia: GET /api/leads + Header "Authorization: Bearer <jwt>"

2. FastAPI vê Depends(require_tenant) → executa decode_jwt:
     - Extrai token do header (Bearer) ou cookie (config EV_TOKEN_SOURCE)
     - Chama itvalleysecurity.verify_access(token)
     - Se inválido: HTTP 401 (TokenMissing ou InvalidToken)

3. require_tenant lê as claims:
     - sub, email, tenant_id, is_master, products, permissions
     - Se master e header X-Tenant-Id presente: usa esse tenant
     - Se não master: força tenant_id do JWT (ignora header)

4. SDK chama set_session_context(tenant_id, is_master) no APP DB:
     EXEC sp_set_session_context @key=N'tenant_id', @value=?, @read_only=1
     EXEC sp_set_session_context @key=N'is_master', @value=?, @read_only=1

5. Rota recebe TenantContext, chama Service:
     await service.list_all()

6. Service chama Repository:
     await repo.find_all()

7. Repository executa SQL:
     SELECT * FROM <schema>.leads

8. Azure SQL aplica Security Policy automaticamente:
     - filtra linhas onde tenant_id = SESSION_CONTEXT('tenant_id')
     - exceção: is_master=1 (bypass)

9. Resposta retorna pela cadeia. Cliente recebe só dados isolados do seu tenant.
```

---

## 8. Configuração — `.env`

Todo o pacote configurado por variáveis de ambiente. O `.env` é carregado pelo SDK
no momento do import.

```env
# === itvalleysecurity (JWT) ===
JWT_SECRET_KEY=<32+ chars, MESMO valor nos 5 produtos da Petra>
JWT_ISSUER=Petra                          # opcional, default = ITValley
EV_TOKEN_SOURCE=bearer                    # bearer | cookie | auto
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# === petraplatform ===
APP_SQL_CONNECTION=Driver={ODBC Driver 18 for SQL Server};Server=<servidor>.database.windows.net;Database=<db do sistema>;...
PLATFORM_SQL_CONNECTION=Driver={ODBC Driver 18 for SQL Server};Server=<servidor>.database.windows.net;Database=dbpetra;...
PLATFORM_PRODUCT_SLUG=genesis             # qual produto é esse sistema
PLATFORM_TENANT_HEADER=X-Tenant-Id        # default
PLATFORM_LOG_LEVEL=WARNING
```

| Variável | Função | Obrigatória |
|---|---|---|
| `JWT_SECRET_KEY` | Segredo HMAC pro JWT — **mesmo** nos 5 produtos | ✅ (32+ chars, senão pacote explode no import) |
| `APP_SQL_CONNECTION` | Banco do sistema (onde aplica RLS) | 🟡 sem ela, RLS não aplica |
| `PLATFORM_SQL_CONNECTION` | Banco `dbpetra` (só /login + admin) | 🟡 sem ela, /login não funciona |
| `PLATFORM_PRODUCT_SLUG` | Slug do produto desse sistema | ✅ sem ela, `require_permission` vira 403 silencioso |
| `JWT_ISSUER` | Claim `iss` | ❌ default `ITValley` |
| `EV_TOKEN_SOURCE` | `bearer` / `cookie` / `auto` | ❌ default `bearer` |

---

## 9. JWT — claims e ciclo de vida

### 9.1 Emissão

Quem emite o JWT é o **endpoint `/login` de cada sistema** (em v0.1). Em v0.2,
provavelmente um `auth.petra.ai` central emite pros 5 produtos compartilhando
`JWT_SECRET_KEY`.

```python
# routers/auth.py (em cada produto)
from itvalleysecurity import issue_pair

@app.post("/login")
async def login(body: LoginPayload, service: AuthService = Depends(get_auth_service)):
    user, claims = await service.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(401, "credenciais invalidas")
    return issue_pair(
        sub=user.id,
        email=user.email,
        tenant_id=claims["tenant_id"],          # de platform.tenant_users
        is_master=claims["is_master"],          # de platform.tenants.is_master
        products=claims["products"],            # de platform.tenant_products
        permissions=claims["permissions"],      # de platform.role_permissions
    )
```

### 9.2 Claims dentro do JWT

| Claim | Origem (tabela) | Usada por |
|---|---|---|
| `sub` | `platform.users.id` | identificar o user logado |
| `email` | `platform.users.email` | display |
| `tenant_id` | `platform.tenant_users.tenant_id` | `require_tenant` + RLS |
| `is_master` | `platform.tenants.is_master` | bypass RLS, suporte |
| `products` | `platform.tenant_products` (slugs) | `require_product` |
| `permissions` | `platform.role_permissions` (`{product: [perms]}`) | `require_permission` |
| `iss` | env `JWT_ISSUER` | validação |
| `exp`, `iat`, `nbf` | tempo | TTL |

### 9.3 TTL e renovação

- Access token: 15 min (default)
- Refresh token: 7 dias (default)
- Cliente troca por novo access via endpoint `/refresh` (a implementar em cada produto ou centralmente em v0.2)

---

## 10. Row-Level Security (RLS) no Azure SQL

A RLS é o mecanismo que impede vazamento de dados entre tenants. **O dev não escreve
`WHERE tenant_id = X`** em nenhuma query. O banco aplica o filtro automaticamente.

### 10.1 Como funciona

1. Toda tabela de domínio ganha uma coluna `tenant_id NVARCHAR(100) NOT NULL`
2. Cria-se uma função TVF `rls.fn_tenant_filter(@tenant_id)` que retorna linha se
   o valor é igual ao `SESSION_CONTEXT('tenant_id')` **OU** o `SESSION_CONTEXT('is_master')` = 1
3. Cria-se uma `SECURITY POLICY` por tabela ligando FILTER + BLOCK PREDICATE à TVF

```sql
CREATE OR ALTER FUNCTION rls.fn_tenant_filter(@tenant_id NVARCHAR(100))
RETURNS TABLE WITH SCHEMABINDING AS
RETURN SELECT 1 AS result
WHERE @tenant_id = CAST(SESSION_CONTEXT(N'tenant_id') AS NVARCHAR(100))
   OR CAST(SESSION_CONTEXT(N'is_master') AS BIT) = 1;
```

A cada request, o SDK seta os dois valores via `EXEC sp_set_session_context`. A
partir desse momento, qualquer `SELECT * FROM genesis.leads` retorna só linhas onde
`tenant_id` bate (ou todas, se master).

### 10.2 Geração do SQL

O CLI `petraplatform generate-rls --schema X --tables Y,Z` gera o SQL completo
e idempotente para um sistema. O DBA roda 1 vez por sistema no APP DB.

Exemplo para Genesis:

```bash
petraplatform generate-rls --schema genesis \
    --tables leads,deals,campaigns,contacts \
    -o rls_genesis.sql

sqlcmd -S srvmasterclass.database.windows.net -d dblumina \
       -U adminitvalley -P $SQL_PWD -i rls_genesis.sql
```

---

## 11. Master bypass

Usuários internos da Petra (suporte, debug, ops) recebem JWT com `is_master: true`.
A função RLS tem `OR is_master=1`, então master atravessa.

| JWT do Carlos | Header `X-Tenant-Id` | O que enxerga |
|---|---|---|
| `is_master=true` | (ausente) | Linhas de **todos** os tenants |
| `is_master=true` | `clinica-abc` | Só `clinica-abc` (modo "ver como cliente") |
| `is_master=false`, `tenant_id=clinica-abc` | (ignorado) | Só `clinica-abc` |
| `is_master=false`, `tenant_id=clinica-abc` | `outra-clinica` (forjado) | Só `clinica-abc` (header ignorado) |

Não-master **nunca** consegue trocar de tenant via header — segurança forte.

---

## 12. CLI — comandos de setup

```bash
$ petraplatform --help
Usage: petraplatform [OPTIONS] COMMAND [ARGS]...

Commands:
  init-platform   Gera DDL do schema platform.* (banco dbpetra)
  generate-rls    Gera SQL de RLS multi-tenant para um schema/tabelas
```

### 12.1 `init-platform`

Gera o DDL idempotente do schema `platform.*` (8 tabelas) + seeds (5 produtos + tenant
master `petra`).

```bash
petraplatform init-platform -o platform_init.sql
sqlcmd -S srvmasterclass.database.windows.net -d dbpetra -U <user> -P $PWD -i platform_init.sql
```

Roda 1 vez por ambiente (DEV/ACCP/PROD).

### 12.2 `generate-rls`

Gera o SQL de RLS para qualquer schema/tabelas. Rodado 1 vez por sistema.

```bash
petraplatform generate-rls --schema genesis --tables leads,deals -o rls_genesis.sql
```

Inclui: schema `rls`, função `fn_tenant_filter` com bypass de master, ALTER TABLE
adicionando `tenant_id`, INDEX em `tenant_id`, e `SECURITY POLICY` com FILTER + BLOCK
predicates pra INSERT/UPDATE/DELETE.

---

## 13. Dependências do pacote

```toml
[project]
name = "petraplatform"
version = "0.1.0"
dependencies = [
    "itvalleysecurity>=0.1.0",   # JWT (já publicado por Carlos no PyPI)
    "fastapi>=0.111",
    "python-dotenv>=1.0.1",
    "click>=8.0.0",              # CLI
    "jinja2>=3.1.0",             # templates SQL
]

[project.optional-dependencies]
sql = ["pyodbc>=5.0.0"]           # pip install petraplatform[sql]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "httpx>=0.27"]
```

`pyodbc` é opcional porque em dev local pode-se rodar sem APP_SQL_CONNECTION (o
SDK loga warning e segue). Em produção é obrigatório.

---

## 14. Padrão Router / Service / Repository

Toda API IT Valley/Petra segue 3 camadas. Esta é **regra de arquitetura**, não estilo.

```
Router  (FastAPI)              ← fino, só Depends
  └── chama via Depends
Service (negócio)              ← orquestra repositories, sem SQL
  └── chama
Repository / Data              ← único lugar com SQL
  └── executa
Banco
```

| Camada | PODE | NUNCA pode |
|---|---|---|
| Router | Receber request, chamar Service via Depends, retornar JSON | SQL, conhecer DTO de banco, sessão SQLAlchemy, regra de negócio |
| Service | Orquestrar repositories, aplicar regras de negócio, transformar dados | SQL inline, conhecer FastAPI (request/response) |
| Repository | SQL, ORM, stored procedures | Lógica de negócio, conhecer HTTP |

Anti-padrão (proibido):

```python
@app.get("/api/leads")  # ERRADO
async def list_leads(tenant = Depends(require_tenant)):
    return await db.fetch_all("SELECT * FROM leads")  # SQL no router
```

Correto:

```python
# routers/leads.py
@app.get("/api/leads")
async def list_leads(
    tenant = Depends(require_tenant),
    service: LeadsService = Depends(get_leads_service),
):
    return await service.list_all()

# services/leads_service.py
class LeadsService:
    def __init__(self, repo): self._repo = repo
    async def list_all(self): return await self._repo.find_all()

# data/leads_repository.py
class LeadsRepository:
    async def find_all(self):
        return await self._db.fetch_all("SELECT * FROM leads")
```

---

## 15. User vs Contact — distinção crítica

Erro mais comum em SaaS multi-produto: **misturar quem LOGA com quem é DADO**.

| Tipo | Tabela | Loga? | Email único? |
|---|---|---|---|
| **User da plataforma** | `platform.users` | ✅ Sim | ✅ UNIQUE global |
| **Contact** (lead, prospect, paciente) | `shared.contacts` ou `<sistema>.contatos` | ❌ Não | ❌ Pode repetir entre tenants |

### Analogia (Google Workspace)

- `carlos@gmail.com` loga no Google → **User do Google** (Workspace, Drive, YouTube)
- Carlos manda email pra `joao@empresa.com` → João é **Contact** na agenda do Carlos. **Não virou cliente do Google.**

Na Petra:
- Carlos contrata Genesis + Quanto → entra em `platform.users` + `platform.tenant_users`
- Maria (lead) chega no WhatsApp do Genesis da Clínica ABC → entra em `genesis.contatos` (ou `shared.contacts` quando essa tabela for criada em v0.2). **Nunca em `platform.users`.**

Sinais de violação (rever imediatamente):
- `INSERT INTO platform.users` em rota de captura de lead
- Coluna tipo `lead_source`, `whatsapp_phone` em `platform.users`
- Tentativa de emitir JWT pra contact capturado

---

## 16. Casos de uso (cenários reais)

### Cenário 1 — Empresa nova contrata pacote Captar

Clínica ABC compra Captar (Quanto + Calenda). João é o dono.

```
INSERT platform.tenants:
  (id='clinica-abc', name='Clínica ABC', plan='captar')

INSERT platform.users:
  (id='u-001', email='joao@clinica-abc.com', name='João')

INSERT platform.tenant_users:
  (tenant='clinica-abc', user='u-001', role='admin')

INSERT platform.tenant_products:
  (tenant='clinica-abc', product=2 [quanto])
  (tenant='clinica-abc', product=5 [calenda])
```

No login, JWT do João carrega:
```json
{
  "sub": "u-001",
  "email": "joao@clinica-abc.com",
  "tenant_id": "clinica-abc",
  "is_master": false,
  "products": ["quanto", "calenda"],
  "permissions": {"quanto": ["quotes.send", ...], "calenda": [...]}
}
```

### Cenário 2 — Admin convida funcionário

João admin convida Ana atendente.

```
SE Ana existe em platform.users:
  Reusa linha existente (1 conta, vários tenants)
SENÃO:
  INSERT platform.users (id='u-099', email='ana@clinica-abc.com')

INSERT platform.tenant_users:
  (tenant='clinica-abc', user='u-099', role='user')

INSERT platform.audit_logs:
  (action='user.invited', user_id='u-001', entity_id='u-099')
```

Email é enviado pra Ana com link mágico pra definir senha.

### Cenário 3 — Consultora atende 3 clínicas com 1 login

Maria trabalha pra 3 clínicas. **1 linha em `users`, 3 linhas em `tenant_users`**.

```
platform.users:
  (id='u-150', email='maria@consult.com')

platform.tenant_users:
  (tenant='clinica-A', user='u-150', role='user')
  (tenant='clinica-B', user='u-150', role='user')
  (tenant='clinica-C', user='u-150', role='admin')
```

No login, Maria vê seletor de empresa. JWT carrega o tenant escolhido.

### Cenário 4 — Master Petra dá suporte à Clínica ABC

Carlos (master) precisa debugar.

```
Request: GET /api/leads
JWT: { sub: 'carlos', is_master: true, tenant_id: 'petra' }
Header: X-Tenant-Id: clinica-abc

SDK seta SESSION_CONTEXT:
  tenant_id = 'clinica-abc'
  is_master = 1

Resultado: vê só leads da Clínica ABC.
```

Sem o header, master veria **todos** os tenants juntos.

---

## 17. Restrições e o que NÃO faz

### Não cria tabelas de negócio
Cada sistema gerencia seu próprio schema. `petraplatform` só cuida do `platform.*` e
seta SESSION_CONTEXT — quem aplica o filtro é o Azure SQL via RLS.

### Não sabe quais tabelas o sistema tem
A CLI `generate-rls` gera SQL a partir de argumentos. O pacote em runtime não conhece
nem precisa conhecer as tabelas de domínio.

### Não tem frontend
É backend puro, pacote pip.

### Não substitui lógica de negócio
Só adiciona camada de tenant/auth. O dev continua escrevendo todo o código de domínio.

### Não emite JWT sozinho
Apenas valida. A emissão fica no `/login` de cada produto (em v0.2 pode centralizar).

### Não faz lookup em DB no request path (v0.1)
Tudo vem do JWT. Em v0.2 vai aceitar fallback Redis + DB pra permissões em tempo real.

### Não substitui `itvalleysecurity`
Importa como dependência. JWT continua sendo `itvalleysecurity`.

---

## 18. Roadmap (v0.2+)

### v0.2 — Resources + Storage + Cache
- `tenant.get_service('openai')` lendo Mongo Atlas (config flexível por tenant)
- `tenant.upload(file, path)` no Azure Blob com path resolution
- `tenant.track_usage(resource, **kwargs)` pra quotas
- Redis cache opcional do TenantContext (5 min TTL)
- Fix do bug 401 do `itvalleysecurity` upstream (PR no PyPI)

### v0.3 — Polish
- CLI `cache-invalidate`, `seed`
- Logging estruturado
- Métricas Prometheus
- Documentação completa e tutorial

### v1.0 — Production-grade
- Audit logs estruturados
- Componentes SvelteKit reutilizáveis (UserManagement, PermissionBadges)
- Manifest system (`register-product`)
- Auth-service central (`auth.petra.ai`) emitindo JWT pros 5 produtos
- Atlas Vector Search pra "AI brain" do Genesis

---

## 19. Glossário

| Termo | Definição |
|---|---|
| **Tenant** | Empresa cliente da Petra (organização). 1 linha em `platform.tenants`. |
| **User** | Pessoa física com login no ecossistema. 1 linha em `platform.users`. |
| **Contact** | Lead/prospect/paciente capturado pelo cliente. **Não loga**. Não vai em `platform.users`. |
| **Product** | Sistema da Petra (Genesis, Quanto, Vitrine, Polaris, Calenda). |
| **Permission** | Ação granular dentro de um produto (ex: `leads.view`). |
| **Role** | Conjunto nomeado de permissões. Aplicado por tenant_user (admin/user/viewer). |
| **Master** | Usuário interno da Petra com bypass de RLS (suporte, debug). JWT com `is_master=true`. |
| **RLS** | Row-Level Security — filtro de linhas aplicado pelo Azure SQL via Security Policy. |
| **SESSION_CONTEXT** | Mecanismo SQL Server pra setar valores por sessão de conexão. Read-only, ideal pra RLS. |
| **TenantContext** | Objeto Python entregue à rota com toda info do tenant + user atual. |
| **APP DB** | Banco do sistema (Genesis usa `dblumina`, etc.). Onde aplica RLS. |
| **PLATFORM DB** | Banco `dbpetra` com schema `platform.*`. Tocado só em /login e admin. |
| **Pacote (comercial)** | Atrair/Captar/Relacionar/Fidelizar. Marketing, não DDL. |

---

## Apêndice A — Estrutura de arquivos do pacote

```
petraplatform/
├── pyproject.toml
├── README.md
├── docs/
│   ├── index.html            # site de docs (Mermaid)
│   ├── style.css
│   └── PRD.md                # este documento
├── petraplatform/
│   ├── __init__.py           # lazy __getattr__ (CLI roda sem .env)
│   ├── config.py             # Settings frozen + load_dotenv interno
│   ├── exceptions.py         # HTTPException com status corretos
│   ├── auth.py               # wrapper sobre itvalleysecurity (corrige 401)
│   ├── tenant_context.py     # dataclass TenantContext
│   ├── middleware.py         # require_tenant, require_permission, require_product
│   ├── db.py                 # pyodbc lazy, set_session_context()
│   ├── cli/
│   │   ├── __init__.py       # entry point (click.group)
│   │   ├── init_platform.py  # DDL platform.* + seeds
│   │   └── generate_rls.py   # SQL de RLS por schema/tabelas
│   └── templates/
│       ├── platform_init.sql.jinja
│       └── rls.sql.jinja
├── sandbox/                  # FastAPI exemplo pra testar manualmente
│   ├── app.py
│   └── .env
└── tests/
    ├── conftest.py
    ├── test_auth_wrapper.py
    ├── test_require_tenant.py
    ├── test_master_bypass.py
    ├── test_require_permission.py
    ├── test_cli_generate_rls.py
    └── test_cli_init_platform.py
```

---

## Apêndice B — Comparação com soluções alternativas

| Solução | Como faz multi-tenancy | Por que não escolhemos |
|---|---|---|
| **Filtro manual no código** (`WHERE tenant_id = ?`) | Cada query passa o tenant_id | Risco enorme de vazamento (qualquer query esquecida) |
| **Discriminator coluna + ORM hook** (SQLAlchemy event listener) | ORM adiciona `WHERE` automaticamente | Acoplamento alto com ORM, foge pra raw SQL |
| **Database por tenant** | 1 banco SQL por cliente | Não escala (100 clientes = 100 bancos) |
| **Schema por tenant** | 1 schema SQL por cliente | Mesma dor de escalar + migrations complexas |
| **`petraplatform` (RLS + SESSION_CONTEXT)** | Filtro no banco, SDK seta contexto | ✅ Zero código no router, zero risco de esquecer, 1 banco compartilhado, master bypass nativo |

---

**Fim do PRD.**

Para continuar a leitura técnica do código real (que pode divergir deste documento se
houver atualizações sem sincronia), consultar:

- Repositório: https://github.com/cacaviana/petraplatform
- Docs visuais: https://app-petraplatform-docs.azurewebsites.net
- Snapshot da arquitetura geral Petra: https://github.com/cacaviana/architecture-petra-platform (privado)
