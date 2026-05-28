import streamlit as st

import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)
st.markdown(ui.header_html(
    title="Fila N2 — Especialistas",
    subtitle="Chamados que requerem intervenção de especialista",
    tag="N2",
), unsafe_allow_html=True)

STATUS_LABEL = {
    "ABERTO": "🟡 Aberto",
    "EM_ATENDIMENTO": "🔴 Em atendimento",
    "RESOLVIDO": "✅ Resolvido",
    "FECHADO": "⬛ Fechado",
}

if "msg_fila2" not in st.session_state:
    st.session_state.msg_fila2 = None
if st.session_state.msg_fila2:
    st.success(st.session_state.msg_fila2)
    st.session_state.msg_fila2 = None

tickets = db.listar_fila("N2")

if not tickets:
    st.info("Nenhum chamado pendente na fila N2 no momento.")
else:
    st.caption(f"{len(tickets)} chamado(s) pendente(s)")

    for t in tickets:
        tid = t["id"]
        confianca = t.get("confianca") or 0
        # N2 com baixa confiança merece destaque — pode ser escalação incerta
        incerto = confianca < 70
        borda = "#ED1C24" if not incerto else "#F37021"

        with st.container():
            c_id, c_info, c_conf, c_status, c_assumir, c_ver = st.columns([0.6, 4, 1.2, 1.5, 1.2, 1])

            with c_id:
                st.markdown(
                    f'<div style="font-size:0.85rem;font-weight:800;color:#ED1C24;'
                    f'font-family:Montserrat,sans-serif;padding-top:6px;">INC{tid:06d}</div>',
                    unsafe_allow_html=True,
                )

            with c_info:
                cat = t.get("categoria") or "OUTRO"
                alerta = " · ⚠️ Confiança baixa" if incerto else ""
                st.markdown(
                    f"**{t['titulo']}**  \n"
                    f"<span style='font-size:0.78rem;color:#5A7E88;'>{cat}{alerta}</span>",
                    unsafe_allow_html=True,
                )

            with c_conf:
                cor = "#ED1C24" if incerto else "#003B4A"
                st.markdown(
                    f'<div style="text-align:center;padding-top:6px;">'
                    f'<span style="font-weight:700;color:{cor};font-size:0.9rem;">{confianca}%</span>'
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
                    if st.button("Assumir", key=f"assumir2_{tid}", use_container_width=True):
                        db.atualizar_ticket(tid, status="EM_ATENDIMENTO")
                        st.session_state.msg_fila2 = f"Chamado INC{tid:06d} assumido."
                        st.rerun()
                elif t["status"] == "EM_ATENDIMENTO":
                    if st.button("Liberar", key=f"liberar2_{tid}", use_container_width=True):
                        db.atualizar_ticket(tid, status="ABERTO", atribuido_para=None)
                        st.session_state.msg_fila2 = f"Chamado INC{tid:06d} devolvido à fila."
                        st.rerun()

            with c_ver:
                if st.button("🔍 Ver", key=f"ver2_{tid}", use_container_width=True):
                    st.query_params["id"] = str(tid)
                    st.switch_page("pages/5_Chamado.py")

        st.divider()
