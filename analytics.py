# -*- coding: utf-8 -*-
"""
Lógica de negócio para métricas de valor (ROI), SLA e indicadores.

Sem dependência de Streamlit nem do banco — recebe dados já agregados
(`database.stats_roi()`) e devolve números prontos para exibição. Os parâmetros
de negócio ficam em constantes editáveis no topo: ajuste aqui um único lugar
para refletir os números reais da Belgo.
"""

from datetime import datetime, timezone, timedelta

# ── Parâmetros de negócio (EDITÁVEIS) ────────────────────────────────────────────
# Defaults plausíveis para um help desk corporativo no Brasil. Ajuste conforme
# os números reais da operação de TI da Belgo.
CUSTO_HORA_N1 = 35.0          # R$/h de um analista N1 (salário + encargos)
TEMPO_MANUAL_N1_MIN = 25      # minutos médios para resolver um N1 manualmente
TEMPO_IA_SEG = 30            # segundos médios da resolução automática pela IA
CUSTO_CHAMADO_IA = 0.40      # custo de API/infra por chamado tratado pela IA (R$)
DIAS_JANELA = 30             # janela de referência para a projeção mensal

# ── SLA por nível (horas). Auto-resolvidos = imediato (0). ───────────────────────
SLA_HORAS = {"N1": 4, "N2": 8, "FORA_DE_ESCOPO": 4}
SLA_WARN_FRAC = 0.25         # restando ≤25% do prazo => "estourando"


def sla_horas_para(nivel: str | None, categoria: str | None = None,
                   auto_resolvido: bool = False) -> int:
    """Horas de SLA aplicáveis ao chamado (0 para auto-resolvidos pela IA)."""
    if auto_resolvido:
        return 0
    return SLA_HORAS.get(nivel or "", 4)


def _parse(iso: str | None):
    if not iso:
        return None
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def status_sla(ticket: dict, agora: datetime | None = None) -> tuple[str, str]:
    """Classifica o SLA de um chamado.

    Retorna (classe, rótulo) onde classe ∈ {ok, warn, late, none}.
    - Encerrados (RESOLVIDO/FECHADO): comparam resolvido_em x prazo.
    - Em aberto: medem o tempo restante até o prazo.
    - Auto-resolvidos (sla_horas == 0) são sempre "ok / Imediato".
    """
    agora = agora or datetime.now(timezone.utc)
    prazo = _parse(ticket.get("sla_prazo"))
    horas = ticket.get("sla_horas")
    status = ticket.get("status")

    if horas == 0:
        return ("ok", "Imediato")
    if prazo is None:
        return ("none", "—")

    if status in ("RESOLVIDO", "FECHADO"):
        resolvido = _parse(ticket.get("resolvido_em"))
        if resolvido is None or resolvido <= prazo:
            return ("ok", "No prazo")
        return ("late", "Fora do prazo")

    restante = (prazo - agora).total_seconds()
    if restante < 0:
        return ("late", "Estourado")
    total = (horas or 4) * 3600
    if restante <= total * SLA_WARN_FRAC:
        return ("warn", "Estourando")
    return ("ok", "No prazo")


# ── ROI ──────────────────────────────────────────────────────────────────────────

def _moeda(v: float) -> str:
    """Formata em reais no padrão pt-BR (R$ 12.345,67)."""
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def _horas_legivel(h: float) -> str:
    if h >= 1:
        return f"{h:.1f} h".replace(".", ",")
    return f"{int(round(h * 60))} min"


def calcular_roi(stats: dict) -> dict:
    """Converte os agregados de `database.stats_roi()` em KPIs de negócio.

    Retorna valores já formatados (pt-BR) e também os números crus (sufixo _num)
    para quem precisar montar gráficos.
    """
    auto = int(stats.get("auto_resolvidos") or 0)
    auto_30d = int(stats.get("auto_resolvidos_30d") or 0)
    total = int(stats.get("total") or 0)
    resolvidos = int(stats.get("resolvidos") or 0)
    csat_media = stats.get("csat_media")
    csat_n = int(stats.get("csat_n") or 0)
    mttr_manual_h = stats.get("mttr_manual_horas")

    # Taxa de deflexão: % de chamados resolvidos sem intervenção humana.
    base_def = resolvidos or total or 1
    deflexao = 100.0 * auto / base_def

    # Horas de N1 economizadas (todas as auto-resoluções já realizadas).
    horas_economizadas = auto * (TEMPO_MANUAL_N1_MIN / 60.0)
    horas_economizadas_30d = auto_30d * (TEMPO_MANUAL_N1_MIN / 60.0)

    # Economia financeira: custo manual evitado menos o custo da IA.
    economia_total = auto * (
        (TEMPO_MANUAL_N1_MIN / 60.0) * CUSTO_HORA_N1 - CUSTO_CHAMADO_IA
    )
    economia_mes = auto_30d * (
        (TEMPO_MANUAL_N1_MIN / 60.0) * CUSTO_HORA_N1 - CUSTO_CHAMADO_IA
    )

    # MTTR: tempo médio de resolução IA vs manual.
    mttr_ia_h = TEMPO_IA_SEG / 3600.0
    mttr_manual_h = float(mttr_manual_h) if mttr_manual_h else (TEMPO_MANUAL_N1_MIN / 60.0)

    return {
        "deflexao": f"{deflexao:.0f}%",
        "deflexao_num": deflexao,
        "auto_resolvidos": auto,
        "horas_economizadas": _horas_legivel(horas_economizadas),
        "horas_economizadas_num": horas_economizadas,
        "horas_economizadas_mes": _horas_legivel(horas_economizadas_30d),
        "economia_total": _moeda(economia_total),
        "economia_total_num": economia_total,
        "economia_mes": _moeda(economia_mes),
        "economia_mes_num": economia_mes,
        "mttr_ia": "~30 s",
        "mttr_manual": _horas_legivel(mttr_manual_h),
        "mttr_manual_num": mttr_manual_h,
        "csat_media": (f"{csat_media:.1f}".replace(".", ",") if csat_media else "—"),
        "csat_media_num": float(csat_media) if csat_media else 0.0,
        "csat_n": csat_n,
    }
