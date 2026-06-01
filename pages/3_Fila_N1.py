import streamlit as st

import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)
st.markdown(ui.header_html(
    title="Fila N1 — Helpdesk",
    subtitle="Chamados aguardando atendimento do nível 1",
    tag="N1",
), unsafe_allow_html=True)


def _fila_page(nivel: str):
    STATUS_LABEL = {
        "ABERTO": "🟡 Aberto",
        "EM_ATENDIMENTO": "🔵 Em atendimento",
        "RESOLVIDO": "✅ Resolvido",
        "FECHADO": "⬛ Fechado",
    }

    if "msg_fila" not in st.session_state:
        st.session_state.msg_fila = None
    if st.session_state.msg_fila:
        st.success(st.session_state.msg_fila)
        st.session_state.msg_fila = None

    tickets = db.listar_fila(nivel)

    if not tickets:
        st.info(f"Nenhum chamado pendente na fila {nivel} no momento.")
        return

    st.caption(f"{len(tickets)} chamado(s) pendente(s)")

    for t in tickets:
        tid = t["id"]
        confianca = t.get("confianca") or 0
        cor_conf = "#003B4A" if confianca >= 80 else "#F37021" if confianca >= 60 else "#ED1C24"

        with st.container():
            c_id, c_info, c_conf, c_status, c_assumir, c_ver = st.columns([0.6, 4, 1.2, 1.5, 1.2, 1])

            with c_id:
                st.markdown(
                    f'<div style="font-size:0.85rem;font-weight:800;color:#003B4A;'
                    f'font-family:Montserrat,sans-serif;padding-top:6px;">INC{tid:06d}</div>',
                    unsafe_allow_html=True,
                )

            with c_info:
                cat = ui.fmt_categoria(t.get("categoria"))
                auto = " · ✅ Auto-resolvido" if t.get("auto_resolvido") else ""
                st.markdown(
                    f"**{t['titulo']}**  \n"
                    f"<span style='font-size:0.78rem;color:#5A7E88;'>{cat}{auto}</span>",
                    unsafe_allow_html=True,
                )

            with c_conf:
                st.markdown(
                    f'<div style="text-align:center;padding-top:6px;">'
                    f'<span style="font-weight:700;color:{cor_conf};font-size:0.9rem;">{confianca}%</span>'
                    f'<br><span style="font-size:0.68rem;color:#7A9EA6;">confiança</span></div>',
                    unsafe_allow_html=True,
                )

            with c_status:
                st.markdown(
                    f'<div style="padding-top:8px;font-size:0.82rem;">'
                    f'{STATUS_LABEL.get(t["status"], t["status"])}</div>',
                    unsafe_allow_html=True,
                )

            with c_assumir:
                if t["status"] == "ABERTO":
                    if st.button("Assumir", key=f"assumir_{tid}_{nivel}", use_container_width=True):
                        db.atualizar_ticket(tid, status="EM_ATENDIMENTO")
                        st.session_state.msg_fila = f"Chamado INC{tid:06d} assumido."
                        st.rerun()
                elif t["status"] == "EM_ATENDIMENTO":
                    if st.button("Liberar", key=f"liberar_{tid}_{nivel}", use_container_width=True):
                        db.atualizar_ticket(tid, status="ABERTO", atribuido_para=None)
                        st.session_state.msg_fila = f"Chamado INC{tid:06d} devolvido à fila."
                        st.rerun()

            with c_ver:
                if st.button("🔍 Ver", key=f"ver_{tid}_{nivel}", use_container_width=True):
                    st.session_state["current_ticket_id"] = tid
                    st.session_state["ticket_origin"] = "n1"
                    st.switch_page("pages/5_Chamado.py")

        st.divider()


_fila_page("N1")
ui.render_footer()
