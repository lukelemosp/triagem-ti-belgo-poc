import streamlit as st

import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Sidebar dark + ajustes de layout da página ────────────────────────────────
ui.render_sidebar("n2")
st.markdown("""
<style>
  [data-testid="stMainBlockContainer"] { padding-left: 252px !important; }
  div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) { display: none !important; }
  [class*="st-key-qrow_"] {
    border-bottom: 1px solid #EEF3F5;
    padding: 2px 8px;
    transition: background 0.1s;
  }
  [class*="st-key-qrow_"]:hover { background: #FFF5F5; }
  div[data-key^="assumir2_"] > button {
    background: #ED1C24 !important; color: white !important; border: none !important;
    font-size: 0.78rem !important; font-weight: 700 !important; border-radius: 6px !important;
  }
  div[data-key^="liberar2_"] > button {
    background: transparent !important; color: #ED1C24 !important;
    border: 1.5px solid #ED1C24 !important; font-size: 0.78rem !important;
    font-weight: 700 !important; border-radius: 6px !important;
  }
  div[data-key^="ver2_"] > button {
    background: transparent !important; color: #003B4A !important;
    border: 1.5px solid #A8C8D0 !important; font-size: 0.78rem !important;
    font-weight: 700 !important; border-radius: 6px !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Header compacto ───────────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;">'
    '<span style="display:inline-flex;align-items:center;justify-content:center;'
    'background:#FEE8E8;color:#ED1C24;border:2px solid #ED1C24;border-radius:10px;'
    'width:52px;height:52px;font-size:1.4rem;font-weight:800;'
    'font-family:Montserrat,sans-serif;">N2</span>'
    '<div>'
    '<div style="font-size:1.25rem;font-weight:800;color:#1A2E33;'
    'font-family:Montserrat,sans-serif;line-height:1.2;">Fila N2 &mdash; Especialistas</div>'
    '<div style="font-size:0.84rem;color:#5A7E88;font-family:Montserrat,sans-serif;">'
    'Chamados que requerem interven\xe7\xe3o de especialista</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

_COLS = [1.0, 3.5, 1.0, 1.45, 1.3, 1.2, 0.95]
_GRID_TPL = " ".join(str(c) + "fr" for c in _COLS)

if "msg_fila2" not in st.session_state:
    st.session_state.msg_fila2 = None
if st.session_state.msg_fila2:
    st.success(st.session_state.msg_fila2)
    st.session_state.msg_fila2 = None

tickets = db.listar_fila("N2")

if not tickets:
    st.info("Nenhum chamado pendente na fila N2 no momento.")
else:
    _filtrados = ui.render_filtros_fila(tickets, "fl_n2")
    st.caption(f"{len(_filtrados)} de {len(tickets)} chamado(s) pendente(s)")

    st.markdown(
        '<div class="bq-table-header" style="grid-template-columns:' + _GRID_TPL + ';">'
        '<div class="bq-table-header-cell">ID</div>'
        '<div class="bq-table-header-cell">Chamado</div>'
        '<div class="bq-table-header-cell" style="text-align:center;">Confian\xe7a</div>'
        '<div class="bq-table-header-cell">Status</div>'
        '<div class="bq-table-header-cell">SLA</div>'
        '<div class="bq-table-header-cell">A\xe7\xe3o</div>'
        '<div class="bq-table-header-cell">Ver</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not _filtrados:
        st.info("Nenhum chamado para os filtros selecionados.")

    for t in _filtrados:
        tid = t["id"]
        confianca = t.get("confianca") or 0
        # N2 com baixa confiança merece destaque — pode ser escalação incerta
        incerto = confianca < 70

        with st.container(key="qrow_" + str(tid)):
            c_id, c_info, c_conf, c_status, c_sla, c_assumir, c_ver = st.columns(_COLS, gap="small")

            with c_id:
                st.markdown(
                    f'<div style="font-size:0.85rem;font-weight:800;color:#ED1C24;'
                    f'font-family:Montserrat,sans-serif;padding-top:8px;white-space:nowrap;">INC{tid:06d}</div>',
                    unsafe_allow_html=True,
                )

            with c_info:
                cat = ui.fmt_categoria(t.get("categoria"))
                alerta = " · ⚠️ Confiança baixa" if incerto else ""
                canal = ui.canal_badge_html(t.get("canal"))
                st.markdown(
                    f"**{t['titulo']}**  \n"
                    f"<span style='font-size:0.78rem;color:#5A7E88;'>{cat}{alerta} · {canal}</span>",
                    unsafe_allow_html=True,
                )

            with c_conf:
                cor = "#ED1C24" if incerto else "#003B4A"
                st.markdown(
                    f'<div style="text-align:center;padding-top:8px;">'
                    f'<span style="font-weight:700;color:{cor};font-size:0.9rem;">{confianca}%</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with c_status:
                st.markdown(
                    '<div style="padding-top:6px;">' + ui.ticket_status_badge(t["status"]) + '</div>',
                    unsafe_allow_html=True,
                )

            with c_sla:
                st.markdown(
                    '<div style="padding-top:6px;">' + ui.sla_badge_html(t) + '</div>',
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
                    st.session_state["current_ticket_id"] = tid
                    st.session_state["ticket_origin"] = "n2"
                    st.switch_page("pages/5_Chamado.py")

ui.render_footer()
