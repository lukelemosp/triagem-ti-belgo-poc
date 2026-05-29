# Sistema de Chamados TI — Belgo Arames

POC de sistema completo de suporte de TI com triagem automática por IA generativa, filas N1/N2, gestão de usuários e servidor MCP.

## O que é

Um sistema multi-página que recebe chamados de TI, classifica automaticamente em **N1 (helpdesk)** ou **N2 (especialista)** via Claude API, exibe o raciocínio passo a passo em tempo real e alimenta filas de atendimento com ações de assumir, liberar e resolver. Inclui resolução instantânea por preset para categorias recorrentes e exposição via MCP Server para consumo por outros agentes.

## Por que

A triagem manual consome tempo do analista, atrasa o SLA e gera escalonamentos desnecessários. O agente atua no ponto de entrada dos chamados em menos de 3 segundos. Categorias recorrentes (reset de senha, VPN, Office 365…) são resolvidas sem nenhuma chamada à IA — um clique cria e fecha o chamado automaticamente.

Em produção, a lógica de triagem seria empacotada como **Skill no Catálogo MCP da Belgo** no Azure DevOps, exposta via webhook do ServiceNow e consumida por uma Azure Function.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Acesse `http://localhost:8501`.
Defina `ANTHROPIC_API_KEY` no ambiente (ou em `.env`) para análise real.

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

## Funcionalidades

| Feature | Detalhe |
|---|---|
| **Classificação N1 / N2 / Fora de escopo** | Confiança, tempo estimado, sugestão de resolução e ação do analista |
| **Chain of Thought em tempo real** | Raciocínio do agente aparece passo a passo durante o streaming |
| **Atendimento Automático via IA** | 10 categorias recorrentes viram presets — 1 clique cria e resolve sem chamar a IA |
| **IDs no formato ServiceNow** | Chamados identificados como INC000001, INC000002… |
| **Filas N1 e N2** | Assumir, liberar e resolver com texto de resolução obrigatório |
| **Dashboard com métricas** | Total, fila N1/N2, resolvidos, % auto-resolvidos; tabela de chamados recentes clicável |
| **Detalhe do chamado** | Sugestão IA, ação, solicitante, datas, formulário de atualização de status |
| **Gestão de usuários** | CRUD completo — nome, email, setor, cargo |
| **Modal de Arquitetura** | Botão 📐 em todas as telas abre modal com problema, solução, stack, fluxo, métricas e catálogo de 6 skills |
| **Rodapé padronizado** | Badge "Uso Interno", crédito e botão de arquitetura presentes em todas as 7 telas |
| **Skeleton loading** | Shimmer animado enquanto o agente processa |
| **Fade-in entre páginas** | Conteúdo entra com animação suave a cada navegação |
| **Navbar nativa** | `st.page_link()` — sem iframe, sem JavaScript; navegação SPA sem reload |
| **MCP Server** | Expõe `criar_chamado`, `consultar_chamado` e `listar_fila` para agentes externos |
| **Identidade visual Belgo** | Montserrat, teal `#003B4A`, vermelho `#ED1C24`, dourado `#FDB913`; favicon oficial Belgo |

## Segurança

| Camada | Implementação |
|---|---|
| **Separação system/user** | Input do usuário vai em `messages[role=user]`, nunca concatenado ao system prompt |
| **HTML escaping** | Todos os campos da API escapados com `html.escape()` antes de injetar no DOM |
| **Whitelist de `nivel`** | Valores fora de `{N1, N2, FORA_DE_ESCOPO}` fazem fallback seguro |
| **`confianca` clampeado** | `max(0, min(100, int(...)))` com try/except |
| **Validação de estrutura JSON** | Verifica estrutura mínima antes de renderizar |
| **Sanitização de input** | Remove null bytes e caracteres de controle antes de enviar à API |
| **Limite de 2.000 caracteres** | Bloqueado no submit com contador visual |
| **Erro genérico ao usuário** | Stack trace vai apenas para o log do servidor |
| **Guardrails no prompt** | Instruções explícitas contra jailbreak, extração do prompt, roleplay e injeção via chamado |

## Stack

| Componente | Tecnologia |
|---|---|
| Interface | Python + Streamlit (multi-page com `st.navigation()`) |
| LLM | Claude Sonnet — Anthropic API (streaming) |
| Banco de dados | SQLite (`sqlite3` nativo — WAL mode) |
| MCP Server | FastMCP stdio |
| ITSM (produção) | ServiceNow REST API via webhook |
| Hospedagem (produção) | Azure Functions |
| Exposição como Skill | MCP Server — Catálogo MCP Belgo no Azure DevOps |
| Versionamento de prompts | Git (prompt como código — mudanças via Pull Request) |

## Estrutura

```
app.py                  # Entry point — navbar, dashboard, st.navigation()
agente_triagem.py       # Demo standalone original (intocado)
ai_agent.py             # Lógica de triagem IA reutilizável
database.py             # SQLite WAL — CRUD tickets e usuários
ui_components.py        # BELGO_CSS, header_html, render_footer, modal_arquitetura, componentes HTML
mcp_server.py           # MCP Server (FastMCP stdio)
favicon.ico             # Favicon oficial Belgo Arames
pages/
  1_Triagem.py          # Demo de triagem isolada
  2_Novo_Chamado.py     # Abertura de chamado + presets automáticos
  3_Fila_N1.py          # Fila helpdesk
  4_Fila_N2.py          # Fila especialistas
  5_Chamado.py          # Detalhe e resolução
  6_Usuarios.py         # Gestão de usuários
```

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (obrigatória para análise real) |

## Auto-resolução (sem chamada à IA)

Categorias que disparam resolução automática instantânea via preset:

`RESET_SENHA` · `VPN_RECONEXAO` · `IMPRESSORA_OFFLINE` · `EMAIL_SYNC_CELULAR` · `TEAMS_AUDIO` · `OUTLOOK_CAIXA_CHEIA` · `WIFI_RECONEXAO` · `SAP_LOGIN_LENTO` · `EXCEL_TRAVA` · `WINDOWS_UPDATE_AVISO`

Critério para auto-resolução via IA: `nivel=N1` + `confiança≥90%` + categoria na lista acima.

## Autor

Lucas Lemos · Belgo Arames, 2026
