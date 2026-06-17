# Testes E2E — Belgo Triagem TI

Suíte de testes ponta a ponta que valida o app inteiro. **Não** faz parte do
deploy (Playwright é dependência só de teste — não vai para `requirements.txt`).

## Pré-requisitos (uma vez)

```bash
pip install playwright
playwright install chromium
```

## Como rodar

```bash
python tests/run_e2e.py        # roda tudo (AppTest + Playwright)
python tests/e2e_apptest.py    # só AppTest (rápido, sem navegador)
python tests/e2e_playwright.py # só Playwright (sobe o app e navega de verdade)
```

Cada script sai com código `!=0` se algo falhar. Os scripts **resetam o banco**
(`seed_demo(force=True)`) para um estado determinístico antes de rodar.

## O que cada um cobre

- **`e2e_apptest.py`** (estável, sem navegador): renderização de todas as páginas
  como admin; CRUD de KB (criar via form, editar, deletar em 2 passos, regra de
  1 artigo ativo por categoria); criação de usuário; filtros do Histórico; busca
  por ID (caminho sem IA); criação por preset; e checagem de papéis (usuário normal
  não vê páginas admin na navegação).
- **`e2e_playwright.py`** (navegador real): login por clique, navegação por todas as
  páginas (via `href`, só elementos visíveis), painel de ROI no dashboard, listagem
  de KB, preset que auto-resolve, varredura do `body` por marcadores de erro, e
  acesso por papel. Salva imagens em `tests/screenshots/` (ignoradas pelo git).

## Notas

- A IA depende de `ANTHROPIC_API_KEY` válida; localmente ela costuma ser inválida
  (401). Os testes cobrem os caminhos **sem IA** (presets, busca por ID, navegação)
  e asseguram que os fluxos com IA **degradam com aviso** em vez de quebrar.
- Login no Streamlit é por sessão: nos testes Playwright, sempre navegar por clique
  (nunca `page.goto` para trocar de página).
