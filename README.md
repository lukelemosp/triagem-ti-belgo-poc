# Sistema de Chamados TI — Belgo Arames

POC de sistema completo de suporte de TI com **login por papéis**, triagem automática por IA generativa, **busca e chat analítico com IA**, filas N1/N2, **SLA e multicanal**, **painel de valor (ROI)**, **catálogo de skills**, **modo sombra (shadow mode)**, **base de conhecimento (CRUD)**, **feedback humano e CSAT**, histórico com filtros avançados, gestão de usuários e servidor MCP.

## O que é

Um sistema multi-página, **protegido por tela de login**, que recebe chamados de TI e os classifica automaticamente em **N1 (helpdesk)** ou **N2 (especialista)** via Claude API, exibindo o raciocínio passo a passo em tempo real. Alimenta filas de atendimento (assumir, liberar, resolver) com **SLA** e **canal de entrada** (Portal/E-mail/Teams/WhatsApp), oferece resolução instantânea por preset para categorias recorrentes, **busca em linguagem natural** e um **assistente de IA conversacional sobre a base**.

Além do operacional, traz a camada de **gestão e governança**: um **painel de Valor/ROI** (deflexão, economia, horas poupadas, CSAT, acurácia — cada KPI com explicação de cálculo), um **catálogo de skills** com dono/SLA/custo, uma tela de **modo sombra** (concordância IA × humano antes de promover o agente), uma **base de conhecimento editável** que o agente cita ao resolver, e coleta de **feedback humano (👍/👎)** e **CSAT**. Toda a inteligência é exposta via **MCP Server** para consumo por outros agentes.

## Por que

A triagem manual consome tempo do analista, atrasa o SLA e gera escalonamentos desnecessários. O agente atua no ponto de entrada dos chamados em menos de 3 segundos. Categorias recorrentes (reset de senha, VPN, Office 365…) são resolvidas sem nenhuma chamada à IA — um clique cria e fecha o chamado automaticamente. Em produção, a lógica seria empacotada como **Skill no Catálogo MCP da Belgo** no Azure DevOps, exposta via webhook do ServiceNow e consumida por uma Azure Function.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Acesse `http://localhost:8501`. Defina `ANTHROPIC_API_KEY` no ambiente (ou em `.env`) para a IA real (triagem, busca em linguagem natural e chat analítico).

A base é populada automaticamente na primeira execução (banco efêmero): ~58 chamados de demonstração (N1/N2, variados, com SLA/canal/CSAT), ~26 registros de modo sombra, 10 artigos de KB e usuários de exemplo.

### Credenciais de demonstração

| Papel | E-mail | Senha |
|---|---|---|
| **Administrador** | `lucas.lemos@belgo.com.br` | `adminbelgo` |
| **Colaborador** | `ana.souza@belgo.com.br` | `belgo123` |

As senhas dos demais usuários são aleatórias e podem ser vistas (e editadas) pelo admin na tela de Usuários.

### Demo standalone (triagem isolada)

```bash
streamlit run agente_triagem.py
```

### Servidor MCP

```bash
python mcp_server.py
# ou
fastmcp dev mcp_server.py
```

## Acesso por papel

| Papel | O que vê |
|---|---|
| **Administrador** | Dashboard (com painel de ROI), Novo Chamado, Fila N1, Fila N2, Chamados (histórico), Skills, Modo Sombra, Base de Conhecimento, Usuários, Triagem IA |
| **Colaborador** | Novo Chamado e Triagem IA |

A navegação (navbar e rotas) é montada conforme o papel; a saudação no topo reflete o primeiro nome do usuário logado. Na navbar do admin, os itens são agrupados visualmente em **Atendimento** (o que o colaborador também acessa) e **Acesso administrativo** (o restante).

## Funcionalidades

| Feature | Detalhe |
|---|---|
| **Login com papéis** | Toda a aplicação atrás de tela de login com identidade Belgo; papéis admin/colaborador com exibição condicional de menu; botão Sair |
| **Classificação N1 / N2 / Fora de escopo** | Confiança, tempo estimado, sugestão de resolução e ação do analista |
| **Chain of Thought em tempo real** | Raciocínio do agente aparece passo a passo durante o streaming |
| **Atendimento Automático via IA** | 10 categorias recorrentes viram presets — 1 clique cria e resolve sem chamar a IA |
| **Busca inteligente (linguagem natural)** | A barra do dashboard interpreta a intenção com IA (Claude Haiku) e converte em filtros; busca direta por ID/termo não aciona a IA |
| **Assistente de IA sobre os chamados** | Chat em modal (skill MCP) que responde perguntas analíticas sobre a base — contagens, último chamado, rankings — usando os dados como contexto |
| **Histórico de chamados** | Página "Chamados" (admin) com todos os chamados e filtros avançados (busca, período, solicitante, status, nível, categoria) + ordenação |
| **Filas N1 e N2** | Assumir, liberar e resolver; filtros (busca, categoria, status) e ordenação |
| **Dashboard com métricas** | Total, fila N1/N2, resolvidos, % auto-resolvidos; seção de Análise colapsável; tabela de recentes ordenável por coluna |
| **Painel de Valor / ROI** | KPIs de negócio no dashboard: taxa de deflexão, economia/mês, horas N1 poupadas, CSAT médio e acurácia percebida; cada card tem um "i" que abre modal com a fórmula e o cálculo atual; gráfico IA vs. manual. Premissas editáveis em `analytics.py` |
| **SLA + Multicanal** | Cada chamado tem prazo de SLA (badge No prazo/Estourando/Estourado) e canal de entrada (Portal/E-mail/Teams/WhatsApp), exibidos nas filas, histórico e detalhe |
| **Catálogo de Skills (governança)** | Página admin com as skills publicadas — dono, SLA, custo/mês, status (Ativo/Shadow) e nº de execuções |
| **Modo Sombra (shadow mode)** | Página admin que mede a concordância IA × humano (nível e categoria) antes de promover o agente à atuação autônoma |
| **Base de Conhecimento (CRUD)** | Página admin para criar/editar/excluir artigos de KB (1 por categoria); o agente cita o artigo usado ao resolver o chamado (explicabilidade) |
| **Feedback humano (HITL) + CSAT** | No detalhe: 👍/👎 sobre a triagem (alimenta a acurácia percebida) e avaliação por estrelas pós-resolução (alimenta o CSAT médio) |
| **Análise de Chamados** | Filtros por período, categoria, nível e status; 4 gráficos Plotly: donut de tipos, barras por status, confiança média da IA por categoria e resolução por nível (manual vs. IA) |
| **IDs no formato ServiceNow** | Chamados identificados como INC000001, INC000002… |
| **Detalhe do chamado** | Sugestão IA, ação, solicitante, datas, formulário de atualização de status; breadcrumb conforme a origem |
| **Gestão de usuários** | CRUD em modal — nome, e-mail, departamento, ramal, **senha (com olho)** e **flag de administrador**; senha aleatória no cadastro; toggle "Mostrar senhas" |
| **Modal de Arquitetura** | Botão 📐 abre modal com problema, solução, stack, fluxo, métricas e catálogo de 8 skills |
| **Skeleton loading + fade-in** | Shimmer enquanto a IA processa; transição suave entre páginas |
| **Navegação SPA** | `st.page_link()` / `st.switch_page()` — sem iframe, sem reload; sidebar dark nas telas administrativas |
| **MCP Server** | Expõe `criar_chamado`, `consultar_chamado`, `listar_fila`, `buscar_chamados` e `conversar_sobre_chamados` |
| **Identidade visual Belgo** | Montserrat, teal `#003B4A`, vermelho `#ED1C24`, dourado `#FDB913`; favicon oficial |

## Skills MCP

| Tool | Função |
|---|---|
| `criar_chamado` | Cria chamado, classifica com IA e auto-resolve se elegível |
| `consultar_chamado` | Retorna estado e detalhes de um chamado por ID |
| `listar_fila` | Lista chamados pendentes de uma fila (N1/N2) |
| `buscar_chamados` | Busca por linguagem natural → filtros estruturados (Claude Haiku) |
| `conversar_sobre_chamados` | Chat analítico sobre a base de chamados (Claude Sonnet) |

## Segurança

| Camada | Implementação |
|---|---|
| **Login** | Toda a aplicação atrás de gate de autenticação; papéis controlam as rotas registradas |
| **Separação system/user** | Input do usuário vai em `messages[role=user]`, nunca concatenado ao system prompt |
| **HTML escaping** | Todos os campos da API escapados com `html.escape()` antes de injetar no DOM |
| **Whitelist de `nivel`** | Valores fora de `{N1, N2, FORA_DE_ESCOPO}` fazem fallback seguro |
| **`confianca` clampeado** | `max(0, min(100, int(...)))` com try/except |
| **Sanitização de input** | Remove null bytes e caracteres de controle antes de enviar à API |
| **Limite de 2.000 caracteres** | Bloqueado no submit com contador visual |
| **Erro genérico ao usuário** | Stack trace vai apenas para o log do servidor |
| **Guardrails no prompt** | Instruções explícitas contra jailbreak, extração do prompt, roleplay e injeção via chamado; o chat analítico responde apenas sobre a base |

> Nota: por ser uma POC sem dados sensíveis, as senhas são armazenadas em texto plano (para permitir o "olho" na tela de Usuários). Em produção, usar hash + provedor de identidade.

## Stack

| Componente | Tecnologia |
|---|---|
| Interface | Python + Streamlit (multi-page com `st.navigation()`) |
| LLM | Claude Sonnet (triagem/chat) e Haiku (busca) — Anthropic API |
| Banco de dados | SQLite (`sqlite3` nativo — WAL mode) |
| MCP Server | FastMCP stdio |
| ITSM (produção) | ServiceNow REST API via webhook |
| Hospedagem (produção) | Azure Functions |
| Exposição como Skill | MCP Server — Catálogo MCP Belgo no Azure DevOps |
| Versionamento de prompts | Git (prompt como código — mudanças via Pull Request) |

## Estrutura

```
app.py                  # Entry point — login, navbar/rotas por papel, dashboard + ROI, busca
agente_triagem.py       # Demo standalone original (intocado)
ai_agent.py             # Triagem IA, busca NL e chat analítico (prompts versionados)
analytics.py            # Premissas de negócio + cálculo de ROI e status de SLA
kb_data.py              # Semente da base de conhecimento (10 artigos iniciais)
skills_data.py          # Metadados de governança das skills (catálogo)
database.py             # SQLite WAL — CRUD tickets/usuários/KB, shadow_log, stats, seed
seed_data.py            # Massa de demonstração (usuários + ~58 chamados + 26 shadow)
ui_components.py        # BELGO_CSS, login, sidebar, modais, badges SLA/canal, KB, componentes
mcp_server.py           # MCP Server (FastMCP stdio) — 5 tools
favicon.ico             # Favicon oficial Belgo Arames
pages/
  1_Triagem.py          # Demo de triagem isolada
  2_Novo_Chamado.py     # Abertura de chamado + presets automáticos + canal
  3_Fila_N1.py          # Fila helpdesk (com filtros, SLA e canal)
  4_Fila_N2.py          # Fila especialistas (com filtros, SLA e canal)
  5_Chamado.py          # Detalhe, resolução, feedback (HITL) e CSAT
  6_Usuarios.py         # Gestão de usuários (senha, admin)
  7_Chamados.py         # Histórico com filtros avançados e ordenação
  8_Skills.py           # Catálogo de skills (governança) — admin
  9_Shadow.py           # Modo sombra: concordância IA × humano — admin
  10_Base_Conhecimento.py  # CRUD da base de conhecimento — admin
tests/
  e2e_apptest.py        # E2E via AppTest (páginas, CRUD, papéis)
  e2e_playwright.py     # E2E no navegador (navegação, fluxos, screenshots)
  run_e2e.py            # Runner das duas suítes
```

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (obrigatória para IA real: triagem, busca NL e chat) |

## Testes (E2E)

Suíte ponta a ponta que valida o app inteiro (não faz parte do deploy — Playwright é dependência só de teste):

```bash
pip install playwright && playwright install chromium
python tests/run_e2e.py        # AppTest + Playwright
```

- **AppTest** (sem navegador): render de todas as páginas, CRUD de KB e de usuário, filtros, busca por ID, criação por preset e checagem de papéis.
- **Playwright** (navegador real): login por clique, navegação por todas as páginas, painel de ROI, KB, preset, varredura de erros e acesso por papel; gera screenshots em `tests/screenshots/`.

## Auto-resolução (sem chamada à IA)

Categorias que disparam resolução automática instantânea via preset:

`RESET_SENHA` · `VPN_RECONEXAO` · `IMPRESSORA_OFFLINE` · `EMAIL_SYNC_CELULAR` · `TEAMS_AUDIO` · `OUTLOOK_CAIXA_CHEIA` · `WIFI_RECONEXAO` · `SAP_LOGIN_LENTO` · `EXCEL_TRAVA` · `WINDOWS_UPDATE_AVISO`

Critério para auto-resolução via IA: `nivel=N1` + `confiança≥90%` + categoria na lista acima.

## Autor

Lucas Lemos · Belgo Arames, 2026
