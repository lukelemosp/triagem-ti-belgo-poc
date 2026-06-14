import html as _html
import streamlit as st

import database as db
import ai_agent as agent
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Lê o ticket_id da query string ou da session_state ────────────────────────
params = st.query_params
_ss_tid = st.session_state.get("current_ticket_id", "")
ticket_id_str = params.get("id", "") or (str(_ss_tid) if _ss_tid else "")

if not ticket_id_str:
    st.error("Nenhum chamado selecionado.")
    st.stop()

try:
    ticket_id = int(ticket_id_str)
except ValueError:
    st.error("ID inválido.")
    st.stop()

ticket = db.buscar_ticket(ticket_id)
if not ticket:
    st.error(f"Chamado #{ticket_id} não encontrado.")
    st.stop()

# ── Breadcrumb (origem dinâmica) ──────────────────────────────────────────────
_origem = st.session_state.get("ticket_origin", "")
_ORIG_MAP = {
    "n2": ("Fila N2", "/n2"),
    "n1": ("Fila N1", "/n1"),
    "chamados": ("Chamados", "/chamados"),
    "dashboard": ("Dashboard", "/"),
}
_origin_label, _origin_href = _ORIG_MAP.get(_origem, ("Dashboard", "/"))
_inc_str = ui.inc_id(ticket_id)
st.markdown(ui.breadcrumb_html([
    (_origin_label, _origin_href),
    (_inc_str, None),
]), unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
nivel = ticket.get("nivel") or "—"
nivel_label = {"N1": "N1 — Helpdesk", "N2": "N2 — Especialistas", "FORA_DE_ESCOPO": "Fora do Escopo"}.get(nivel, nivel)
st.markdown(ui.header_html(
    title=f"INC{ticket_id:06d} — {ticket['titulo']}",
    subtitle=nivel_label,
    tag=ticket.get("status", ""),
), unsafe_allow_html=True)

col_meta, col_acao = st.columns([1.2, 1], gap="large")

with col_meta:
    st.markdown(ui.ticket_detail_html(ticket, nivel), unsafe_allow_html=True)

with col_acao:
    # Resolução existente
    if ticket.get("resolucao"):
        st.markdown(
            f'<div class="result-label">Resolução</div>'
            f'<div class="result-value" style="white-space:pre-wrap;">'
            f'{_html.escape(ticket["resolucao"])}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Formulário de ação (só para tickets não fechados)
    if ticket["status"] not in ("FECHADO",):
        st.markdown("---")
        st.markdown("**Ação do analista**")

        novo_status = st.selectbox(
            "Alterar status para:",
            [ticket["status"]] + [s for s in ["ABERTO", "EM_ATENDIMENTO", "RESOLVIDO", "FECHADO"] if s != ticket["status"]],
            key=f"status_sel_{ticket_id}",
        )

        resolucao_texto = st.text_area(
            "Texto de resolução (obrigatório para RESOLVIDO):",
            value=ticket.get("resolucao") or "",
            height=120,
            key=f"res_text_{ticket_id}",
        )

        if st.button("Salvar", type="primary", use_container_width=True, key=f"save_{ticket_id}"):
            if novo_status == "RESOLVIDO" and not resolucao_texto.strip():
                st.warning("Informe o texto de resolução antes de marcar como Resolvido.")
            else:
                updates = {"status": novo_status}
                if resolucao_texto.strip():
                    updates["resolucao"] = resolucao_texto.strip()
                db.atualizar_ticket(ticket_id, **updates)
                st.success(f"INC{ticket_id:06d} atualizado para {novo_status}.")
                st.query_params["id"] = str(ticket_id)
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
_origin = st.session_state.get("ticket_origin", "")
_VOLTA = {
    "n2": ("← Voltar \xe0 Fila N2", "pages/4_Fila_N2.py"),
    "n1": ("← Voltar \xe0 Fila N1", "pages/3_Fila_N1.py"),
    "chamados": ("← Voltar aos Chamados", "pages/7_Chamados.py"),
}
_label, _destino = _VOLTA.get(_origin, ("← Voltar ao Dashboard", None))
if st.button(_label):
    st.session_state.pop("ticket_origin", None)
    st.session_state.pop("current_ticket_id", None)
    st.switch_page(_destino or st.session_state.get("_p_home", "pages/3_Fila_N1.py"))

ui.render_footer()
