import html as _html
import streamlit as st

import database as db
import ai_agent as agent
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Lê o ticket_id da query string ou da session_state ────────────────────────
params = st.query_params
ticket_id_str = params.get("id", "") or str(st.session_state.pop("current_ticket_id", ""))

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

# ── Header ────────────────────────────────────────────────────────────────────
nivel = ticket.get("nivel") or "—"
nivel_label = {"N1": "N1 — Helpdesk", "N2": "N2 — Especialistas", "FORA_DE_ESCOPO": "Fora do Escopo"}.get(nivel, nivel)
st.markdown(ui.header_html(
    title=f"INC{ticket_id:06d} — {ticket['titulo']}",
    subtitle=nivel_label,
    tag=ticket.get("status", ""),
), unsafe_allow_html=True)

STATUS_LABEL = {
    "ABERTO": "🟡 Aberto",
    "EM_ATENDIMENTO": "🔵 Em atendimento",
    "RESOLVIDO": "✅ Resolvido",
    "FECHADO": "⬛ Fechado",
}

col_meta, col_acao = st.columns([1.2, 1], gap="large")

with col_meta:
    # Metadados
    st.markdown(
        f'<div class="result-label">Descrição do chamado</div>'
        f'<div class="result-value" style="white-space:pre-wrap;">'
        f'{_html.escape(ticket["descricao"])}</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Status", STATUS_LABEL.get(ticket["status"], ticket["status"]))
    with c2:
        st.metric("Nível IA", nivel)
    with c3:
        st.metric("Confiança", f"{ticket.get('confianca') or 0}%")

    st.markdown(
        f'<div style="font-size:0.78rem;color:#5A7E88;margin-top:8px;">'
        f'Categoria: <strong>{ticket.get("categoria") or "—"}</strong>'
        + (" · ✅ <strong>Auto-resolvido pela IA</strong>" if ticket.get("auto_resolvido") else "")
        + (f'<br>Solicitante: <strong>{_html.escape(ticket["solicitante_nome"])}</strong>'
           f' — {_html.escape(ticket.get("solicitante_email",""))}' if ticket.get("solicitante_nome") else "")
        + f'<br>Aberto em: {ui.fmt_dt(ticket.get("criado_em",""))}'
        + (f'<br>Resolvido em: {ui.fmt_dt(ticket.get("resolvido_em",""))}' if ticket.get("resolvido_em") else "")
        + '</div>',
        unsafe_allow_html=True,
    )

    # Sugestão da IA
    if ticket.get("sugestao_ia"):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="result-label">Sugestão da IA</div>'
            f'<div class="result-value">'
            f'{_html.escape(ticket["sugestao_ia"]).replace(chr(10),"<br>")}'
            f'</div>',
            unsafe_allow_html=True,
        )
    if ticket.get("acao_ia"):
        nivel_key = ticket.get("nivel", "N1")
        cls = "acao-n1" if nivel_key == "N1" else "acao-n2"
        st.markdown(
            f'<div class="{cls}">⚡ {_html.escape(ticket["acao_ia"])}</div>',
            unsafe_allow_html=True,
        )

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
_label = "← Voltar à Fila N2" if _origin == "n2" else "← Voltar à Fila N1" if _origin == "n1" else "← Voltar ao Dashboard"
if st.button(_label):
    st.session_state.pop("ticket_origin", None)
    if _origin == "n2":
        st.switch_page("pages/4_Fila_N2.py")
    elif _origin == "n1":
        st.switch_page("pages/3_Fila_N1.py")
    else:
        st.switch_page("app.py")
