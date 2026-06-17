# -*- coding: utf-8 -*-
"""
Catálogo de Skills — Belgo Triagem TI.

Metadados de governança de cada skill/agente publicado no Catálogo MCP
(Azure DevOps): dono, SLA, custo/mês, status (Ativo / Shadow) e contagem de
execuções. Materializa o conceito de "fleet governado" do discurso de GPM.

O campo `metric` indica de onde vem a contagem de execuções "viva":
- "total"  → total de chamados (proxy de criar_chamado / triagem)
- "auto"   → chamados auto-resolvidos pela IA
- None     → usa o número estático em `execucoes`
"""

SKILLS = [
    {
        "nome": "Triagem Automática", "code": False, "tipo": "IA Interna",
        "color": "#003B4A",
        "desc": "Classifica chamados como N1, N2 ou Fora do Escopo usando Claude "
                "Sonnet com raciocínio encadeado (CoT) visível em tempo real.",
        "dono": "Squad IA & Automação", "sla": "≤ 30 s",
        "custo": "R$ 0,40 / chamado", "status": "Ativo", "metric": "total",
    },
    {
        "nome": "Auto-resolução IA", "code": False, "tipo": "IA Interna",
        "color": "#2E7D32",
        "desc": "Resolve automaticamente chamados N1 com confiança ≥ 90% em 10 "
                "categorias (reset de senha, VPN, impressora, Teams…).",
        "dono": "Squad IA & Automação", "sla": "Imediato",
        "custo": "R$ 0,40 / chamado", "status": "Ativo", "metric": "auto",
    },
    {
        "nome": "criar_chamado", "code": True, "tipo": "MCP Skill",
        "color": "#7B1FA2",
        "desc": "Cria novo chamado via protocolo MCP — exposta no Catálogo do "
                "Azure DevOps para outros agentes consumirem.",
        "dono": "Plataforma de Agentes", "sla": "≤ 5 s",
        "custo": "R$ 0,40 / chamado", "status": "Ativo", "metric": "total",
    },
    {
        "nome": "consultar_chamado", "code": True, "tipo": "MCP Skill",
        "color": "#7B1FA2",
        "desc": "Retorna estado, nível IA, confiança, sugestão e resolução de "
                "qualquer chamado por ID — permite auditoria e integração.",
        "dono": "Plataforma de Agentes", "sla": "≤ 2 s",
        "custo": "R$ 0,02 / consulta", "status": "Ativo",
        "metric": None, "execucoes": 312,
    },
    {
        "nome": "listar_fila", "code": True, "tipo": "MCP Skill",
        "color": "#7B1FA2",
        "desc": "Lista chamados pendentes na fila N1 ou N2 com status, confiança "
                "e categoria — permite orquestrar prioridades entre agentes.",
        "dono": "Plataforma de Agentes", "sla": "≤ 2 s",
        "custo": "R$ 0,02 / consulta", "status": "Ativo",
        "metric": None, "execucoes": 184,
    },
    {
        "nome": "buscar_chamados", "code": True, "tipo": "MCP Skill · IA",
        "color": "#7B1FA2",
        "desc": "Busca por linguagem natural: a IA (Claude Haiku) interpreta a "
                "intenção e converte em filtros de status, nível, categoria e período.",
        "dono": "Squad IA & Automação", "sla": "≤ 4 s",
        "custo": "R$ 0,08 / busca", "status": "Ativo",
        "metric": None, "execucoes": 96,
    },
    {
        "nome": "conversar_sobre_chamados", "code": True, "tipo": "MCP Skill · IA",
        "color": "#7B1FA2",
        "desc": "Chat analítico: a IA (Claude Sonnet) responde perguntas sobre a "
                "base (último chamado, contagens, rankings) usando os dados como contexto.",
        "dono": "Squad IA & Automação", "sla": "≤ 6 s",
        "custo": "R$ 0,15 / pergunta", "status": "Ativo",
        "metric": None, "execucoes": 58,
    },
    {
        "nome": "Predição de SLA", "code": False, "tipo": "IA Interna",
        "color": "#F37021",
        "desc": "Estima risco de estouro de SLA por chamado a partir de histórico e "
                "carga das filas. Em modo sombra (shadow), ainda sem atuar.",
        "dono": "Squad IA & Automação", "sla": "≤ 30 s",
        "custo": "—", "status": "Shadow",
        "metric": None, "execucoes": 26,
    },
]


def execucoes(skill: dict, stats: dict) -> int:
    """Resolve a contagem de execuções da skill (viva via stats ou estática)."""
    metric = skill.get("metric")
    if metric == "total":
        return int(stats.get("total") or 0)
    if metric == "auto":
        return int(stats.get("auto_resolvidos") or 0)
    return int(skill.get("execucoes") or 0)
