# Documentação visual — petraplatform

Site estático single-page com diagramas Mermaid explicando a arquitetura.

## Como abrir

**Local (mais simples):**
```bash
open docs/index.html
```

**Servidor local (se o navegador bloquear algum recurso):**
```bash
cd docs && python3 -m http.server 8000
# abre http://localhost:8000
```

**Publicar no GitHub Pages:**
1. Settings → Pages → Source: `main` branch, `/docs` folder
2. URL fica: `https://<org>.github.io/petraplatform/`

## Conteúdo

- Visão geral
- Arquitetura macro (diagrama de fluxo Mermaid)
- Fluxo de auth (sequence diagram)
- Dois bancos (tabela + explicação)
- RLS & SESSION_CONTEXT
- Master bypass
- Schema `platform.*` (ER diagram)
- DX do dev (antes/depois)
- CLI
- Workflow recomendado
- FAQ

## Edição

Tudo HTML/CSS puro, zero build step. Edita direto e abre no navegador.
Mermaid carrega via CDN — precisa de internet para renderizar os diagramas.
