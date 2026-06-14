"""
MCP Server — Belgo Triagem TI

Expõe 3 tools via FastMCP (protocolo stdio):
  criar_chamado     — abre ticket, classifica com IA, auto-resolve se elegível
  consultar_chamado — retorna status e detalhes de um ticket pelo ID
  listar_fila       — lista tickets ABERTO/EM_ATENDIMENTO de uma fila (N1 ou N2)

Uso:
  python mcp_server.py              (produção — stdio)
  fastmcp dev mcp_server.py         (desenvolvimento — inspector UI)
"""

from fastmcp import FastMCP

import database as db
import ai_agent as agent

db.init_db()

mcp = FastMCP("belgo-triagem-ti")


@mcp.tool()
def criar_chamado(titulo: str, descricao: str, usuario_email: str = "") -> dict:
    """
    Cria um chamado de TI, executa a classificação por IA e retorna o resultado.
    Se o chamado for elegível para auto-resolução (N1, confiança >= 90 e categoria
    conhecida), é marcado como RESOLVIDO imediatamente com a resolução da IA.

    Args:
        titulo: Título curto do chamado (ex.: "VPN não conecta")
        descricao: Descrição detalhada do problema (máx. 2000 caracteres)
        usuario_email: E-mail do solicitante (opcional; vincula ao usuário no banco)

    Returns:
        ticket_id, nivel, categoria, confianca, auto_resolvido, status
    """
    descricao = agent._sanitizar_input(descricao.strip())
    if not descricao:
        return {"erro": "Descrição do chamado não pode estar vazia."}

    usuario = db.buscar_usuario_por_email(usuario_email) if usuario_email else None
    criado_por = usuario["id"] if usuario else None

    try:
        resultado = agent.analisar(descricao, cot_slot=None)
    except Exception as exc:
        return {"erro": f"Falha na classificação: {exc}"}

    nivel = resultado.get("nivel", "FORA_DE_ESCOPO")
    if nivel not in agent._NIVEIS_VALIDOS:
        nivel = "FORA_DE_ESCOPO"

    categoria = resultado.get("categoria", "OUTRO") or "OUTRO"
    confianca = resultado.get("confianca", 0)
    try:
        confianca = max(0, min(100, int(confianca)))
    except (TypeError, ValueError):
        confianca = 0

    auto = (
        nivel == "N1"
        and confianca >= agent.AUTO_RESOLVE_THRESHOLD
        and categoria in agent.AUTO_RESOLVABLE
    )

    ticket = db.criar_ticket(
        titulo=titulo,
        descricao=descricao,
        nivel=nivel,
        categoria=categoria,
        confianca=confianca,
        criado_por=criado_por,
        status="RESOLVIDO" if auto else "ABERTO",
        resolucao=resultado.get("sugestao") if auto else None,
        auto_resolvido=auto,
        sugestao_ia=resultado.get("sugestao"),
        acao_ia=resultado.get("acao"),
        tempo_estimado=resultado.get("tempo"),
    )

    return {
        "ticket_id": ticket["id"],
        "nivel": nivel,
        "categoria": categoria,
        "confianca": confianca,
        "auto_resolvido": auto,
        "status": ticket["status"],
        "tempo_estimado": resultado.get("tempo"),
        "acao": resultado.get("acao"),
    }


@mcp.tool()
def consultar_chamado(ticket_id: int) -> dict:
    """
    Retorna o status e os detalhes completos de um chamado pelo ID.

    Args:
        ticket_id: Identificador numérico do ticket

    Returns:
        Todos os campos do ticket, ou {"erro": "..."} se não encontrado
    """
    ticket = db.buscar_ticket(ticket_id)
    if not ticket:
        return {"erro": f"Chamado #{ticket_id} não encontrado."}
    return ticket


@mcp.tool()
def buscar_chamados(consulta: str) -> dict:
    """
    Busca chamados a partir de uma consulta em LINGUAGEM NATURAL.

    Uma IA (Claude Haiku) interpreta a intenção da consulta e a converte em
    filtros estruturados (texto, categoria, nível, status, período, auto-resolução),
    que são aplicados sobre a base de chamados. Ideal para perguntas como
    "chamados de VPN ainda abertos", "tickets N2 resolvidos este mês" ou
    "problemas de impressora da última semana".

    Para busca por número de chamado (ex.: "INC000007"), prefira consultar_chamado.

    Args:
        consulta: Pergunta/descrição em linguagem natural do que se deseja encontrar.

    Returns:
        dict com: interpretacao (o que a IA entendeu), filtros (aplicados),
        total (quantidade) e resultados (lista de tickets).
    """
    consulta = (consulta or "").strip()
    if not consulta:
        return {"erro": "Consulta não pode estar vazia."}

    filtros = agent.interpretar_busca(consulta)
    explicacao = filtros.pop("explicacao", "")
    resultados = db.buscar_tickets_avancado(**filtros)
    return {
        "interpretacao": explicacao,
        "filtros": filtros,
        "total": len(resultados),
        "resultados": resultados,
    }


@mcp.tool()
def conversar_sobre_chamados(pergunta: str) -> dict:
    """
    Responde uma pergunta em LINGUAGEM NATURAL exclusivamente sobre a base de
    chamados (analítico/conversacional). Ex.: "qual o último chamado aberto?",
    "quantos chamados N2 estão pendentes?", "quais categorias mais aparecem?".

    Uma IA recebe um resumo estatístico + a lista de chamados e responde em texto.
    Diferente de buscar_chamados (que retorna uma lista filtrada), esta tool
    retorna uma resposta textual analítica.

    Args:
        pergunta: Pergunta em linguagem natural sobre os chamados.

    Returns:
        dict com a pergunta e a resposta textual da IA.
    """
    pergunta = (pergunta or "").strip()
    if not pergunta:
        return {"erro": "A pergunta não pode estar vazia."}
    resposta = agent.conversar_sobre_chamados(pergunta)
    return {"pergunta": pergunta, "resposta": resposta}


@mcp.tool()
def listar_fila(nivel: str) -> list[dict]:
    """
    Retorna os chamados pendentes (ABERTO ou EM_ATENDIMENTO) de uma fila.

    Args:
        nivel: 'N1' (helpdesk) ou 'N2' (especialistas)

    Returns:
        Lista de tickets ordenada por data de criação (mais antigos primeiro)
    """
    if nivel not in ("N1", "N2"):
        return [{"erro": "nivel deve ser 'N1' ou 'N2'."}]
    return db.listar_fila(nivel=nivel, statuses=["ABERTO", "EM_ATENDIMENTO"])


if __name__ == "__main__":
    mcp.run()
