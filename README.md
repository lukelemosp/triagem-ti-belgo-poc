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

- Classificação N1 / N2 com nível de confiança
- Sugestão de resolução por tipo de chamado
- Chain of thought — raciocínio do agente visível
- Página de arquitetura da solução (`?p=arq`)
- Identidade visual Belgo Arames

## Stack

| Componente | Tecnologia |
|---|---|
| Interface | Python + Streamlit |
| LLM (produção) | Claude — Anthropic API |
| ITSM | ServiceNow REST API |
| Hospedagem | Azure Functions |
| Versionamento de prompts | Git |

> Esta é uma POC com respostas pré-configuradas. A integração com a Anthropic API e o ServiceNow é descrita na [página de arquitetura](http://localhost:8501/?p=arq) da própria aplicação.

## Autor

Lucas Lemos · Belgo Arames, 2026
