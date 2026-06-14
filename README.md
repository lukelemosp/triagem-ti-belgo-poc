# Sistema de Chamados TI — Belgo Arames

POC de sistema completo de suporte de TI com **login por papéis**, triagem automática por IA generativa, **busca e chat analítico com IA**, filas N1/N2, histórico com filtros avançados, gestão de usuários e servidor MCP.

## O que é

Um sistema multi-página, **protegido por tela de login**, que recebe chamados de TI e os classifica automaticamente em **N1 (helpdesk)** ou **N2 (especialista)** via Claude API, exibindo o raciocínio passo a passo em tempo real. Alimenta filas de atendimento (assumir, liberar, resolver), oferece resolução instantânea por preset para categorias recorrentes, **busca em linguagem natural**, um **assistente de IA conversacional sobre a base** e uma página de **histórico com filtros e ordenação**. Toda a inteligência é exposta via **MCP Server** para consumo por outros agentes.

## Por que

A triagem manual consome tempo do analista, atrasa o SLA e gera escalonamentos desnecessários. O agente atua no ponto de entrada dos chamados em menos de 3 segundos. Categorias recorrentes (reset de senha, VPN, Office 365…) são resolvidas sem nenhuma chamada à IA — um clique cria e fecha o chamado automaticamente. Em produção, a lógica seria empacotada como **Skill no Catálogo MCP da Belgo** no Azure DevOps, exposta via webhook do ServiceNow e consumida por uma Azure Function.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Acesse `http://localhost:8501`. Defina `ANTHROPIC_API_KEY` no ambiente (ou em `.env`) para a IA real (triagem, busca em linguagem natural e chat analítico).

A base é populada automaticamente na primeira execução (banco efêmero): ~55 chamados de demonstração (N1/N2, variados) e usuários de exemplo.

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
| **Administrador** | Dashboard, Novo Chamado, Fila N1, Fila N2, Chamados (histórico), Usuários, Triagem IA |
| **Colaborador** | Novo Chamado e Triagem IA |

A navegação (navbar e rotas) é montada conforme o papel; a saudação no topo reflete o primeiro nome do usuário logado.

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
app.py                  # Entry point — login, navbar/rotas por papel, dashboard, busca
agente_triagem.py       # Demo standalone original (intocado)
ai_agent.py             # Triagem IA, busca NL e chat analítico (prompts versionados)
database.py             # SQLite WAL — CRUD tickets/usuários, autenticação, seed
seed_data.py            # Massa de demonstração (usuários + ~55 chamados)
ui_components.py        # BELGO_CSS, login, sidebar, modais, componentes HTML
mcp_server.py           # MCP Server (FastMCP stdio) — 5 tools
favicon.ico             # Favicon oficial Belgo Arames
pages/
  1_Triagem.py          # Demo de triagem isolada
  2_Novo_Chamado.py     # Abertura de chamado + presets automáticos
  3_Fila_N1.py          # Fila helpdesk (com filtros)
  4_Fila_N2.py          # Fila especialistas (com filtros)
  5_Chamado.py          # Detalhe e resolução
  6_Usuarios.py         # Gestão de usuários (senha, admin)
  7_Chamados.py         # Histórico com filtros avançados e ordenação
```

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (obrigatória para IA real: triagem, busca NL e chat) |

## Auto-resolução (sem chamada à IA)

Categorias que disparam resolução automática instantânea via preset:

`RESET_SENHA` · `VPN_RECONEXAO` · `IMPRESSORA_OFFLINE` · `EMAIL_SYNC_CELULAR` · `TEAMS_AUDIO` · `OUTLOOK_CAIXA_CHEIA` · `WIFI_RECONEXAO` · `SAP_LOGIN_LENTO` · `EXCEL_TRAVA` · `WINDOWS_UPDATE_AVISO`

Critério para auto-resolução via IA: `nivel=N1` + `confiança≥90%` + categoria na lista acima.

## Autor

Lucas Lemos · Belgo Arames, 2026
