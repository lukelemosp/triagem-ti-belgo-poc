# Agente de Triagem TI — Belgo Arames

POC de triagem automática de chamados de suporte N1/N2 usando IA.

## O que é

Um agente que lê a descrição de um chamado de TI e classifica automaticamente se ele deve ser atendido pelo **helpdesk (N1)** ou escalado para um **especialista (N2)** — junto com uma sugestão de resolução e o raciocínio por trás da decisão.

## Por que

A triagem manual consome tempo do analista, atrasa o SLA e gera escalonamentos desnecessários. Chamados chegam por múltiplos canais (portal, Teams, telefone) e todos convergem no ServiceNow — o agente atua nesse ponto de entrada.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run agente_triagem.py
```

Acesse `http://localhost:8501`.

## Funcionalidades

- Classificação N1 / N2 com nível de confiança e barra de progresso
- Sugestão de resolução gerada pelo modelo em linguagem natural
- **Chain of thought em tempo real** — raciocínio do agente aparece passo a passo enquanto Claude ainda está gerando a resposta (streaming via SDK Anthropic)
- **Idempotência** — botão e campo desabilitados durante o processamento; sem chamadas duplicadas à API; campo limpo automaticamente após a análise
- **Chamados fora de escopo** — detectados e apresentados com card visual distinto, sem campos N/A soltos
- Arquitetura da solução em modal (botão no rodapé)
- Modo claro forçado — sem conversão automática para dark mode
- Identidade visual Belgo Arames (Montserrat, paleta teal/vermelho/dourado)

## Stack

| Componente | Tecnologia |
|---|---|
| Interface | Python + Streamlit |
| LLM (produção) | Claude Sonnet — Anthropic API (streaming) |
| ITSM | ServiceNow REST API |
| Hospedagem | Azure Functions |
| Versionamento de prompts | Git |

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (obrigatória para análise real) |

Sem a chave, a aplicação entra em **modo demo** com tickets pré-configurados e animação de CoT simulada.

> Esta é uma POC. A integração com o ServiceNow e o deploy em Azure Functions são descritos no modal de arquitetura dentro da própria aplicação.

## Autor

Lucas Lemos · Belgo Arames, 2026
