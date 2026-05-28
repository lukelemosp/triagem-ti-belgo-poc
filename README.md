# Agente de Triagem TI — Belgo Arames

POC de triagem automática de chamados de suporte N1/N2 usando IA generativa, com raciocínio transparente em tempo real.

## O que é

Um agente que lê a descrição de um chamado de TI e classifica automaticamente se deve ser atendido pelo **helpdesk (N1)** ou escalado para um **especialista (N2)** — com sugestão de resolução, nível de confiança explicado e raciocínio passo a passo visível ao analista enquanto o modelo ainda processa.

## Por que

A triagem manual consome tempo do analista, atrasa o SLA e gera escalonamentos desnecessários. Chamados chegam por múltiplos canais (portal, Teams, telefone) e convergem no ServiceNow — o agente atua nesse ponto de entrada, em menos de 3 segundos por chamado.

Em produção, esta lógica seria empacotada como uma **Skill no Catálogo MCP da Belgo** no Azure DevOps, exposta via webhook do ServiceNow e consumida por uma Azure Function.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run agente_triagem.py
```

Acesse `http://localhost:8501`.  
Defina `ANTHROPIC_API_KEY` no ambiente (ou em `.env`) para análise real.

## Funcionalidades

| Feature | Detalhe |
|---|---|
| **Classificação N1 / N2 / Fora de escopo** | Com confiança, tempo estimado e sugestão de resolução |
| **Chain of Thought em tempo real** | Raciocínio do agente aparece passo a passo durante o streaming (parsing incremental de JSON parcial) |
| **Tooltip de confiança** | Ícone ao lado do label explica por que a confiança é aquele valor |
| **Skeleton loading** | Card de resultado exibe shimmer animado enquanto o agente processa |
| **Sugestão em steps formatados** | Cada etapa em linha separada, encadeadas por ponto e vírgula |
| **Fade-in** | CoT e card de resultado entram com animação suave ao aparecer |
| **Campo limpo após análise** | Input resetado via contador de chave do widget |
| **Cooldown em tempo real** | Contador desce ao vivo durante o período de espera |
| **Rate limiting em dois níveis** | 12s de cooldown por sessão + cap de 40 req/hora global entre sessões |
| **100 placeholders rotativos** | Campo de descrição sorteia um exemplo diferente por sessão (SAP, Salesforce, rede, hardware…) |
| **Modal de arquitetura** | Problema, solução, stack, fluxo, métricas e decisões de design — ícone 📐 no rodapé |
| **Prompt visível no modal** | Seção colapsável com o system prompt completo e botão de copiar |
| **Identidade visual Belgo** | Montserrat, paleta teal `#003B4A` / vermelho `#ED1C24` / dourado `#FDB913` |

## Segurança

| Camada | Implementação |
|---|---|
| **Separação system/user** | Input do usuário vai em `messages[role=user]`, nunca concatenado ao system prompt |
| **HTML escaping** | Todos os campos da API são escapados com `html.escape()` antes de injetar no DOM |
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
| Interface | Python + Streamlit |
| LLM | Claude Sonnet — Anthropic API (streaming) |
| ITSM (produção) | ServiceNow REST API via webhook |
| Hospedagem (produção) | Azure Functions |
| Exposição como Skill | MCP Server — Catálogo MCP Belgo no Azure DevOps |
| Versionamento de prompts | Git (prompt como código — mudanças via Pull Request) |

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (obrigatória para análise real) |

## Estrutura do prompt

O system prompt vive em `_SYSTEM_PROMPT` (constante de módulo em `agente_triagem.py`) e pode ser visualizado diretamente no modal de arquitetura da aplicação. Qualquer alteração no comportamento do agente deve ser feita aqui e revisada via Pull Request — rastreabilidade total.

O JSON de resposta tem `"pensamento"` **primeiro** para que os steps do CoT apareçam durante o streaming, antes de `nivel`, `confianca` e `sugestao` estarem completos.

> Esta é uma POC. A integração com ServiceNow e o deploy em Azure Functions são descritos em detalhe no modal de arquitetura dentro da própria aplicação.

## Autor

Lucas Lemos · Belgo Arames, 2026
