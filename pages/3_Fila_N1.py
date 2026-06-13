import streamlit as st

import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Sidebar dark + ajustes de layout da página ────────────────────────────────
st.markdown(ui.sidebar_html("n1"), unsafe_allow_html=True)
st.markdown("""
<style>
  [data-testid="stMainBlockContainer"] { padding-left: 252px !important; }
  /* Esconde a navbar horizontal nativa — navegação vai pela sidebar dark */
  div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) { display: none !important; }
  /* Linhas do data grid (apenas containers com key qrow_) */
  [class*="st-key-qrow_"] {
    border-bottom: 1px solid #EEF3F5;
    padding: 2px 8px;
    transition: background 0.1s;
  }
  [class*="st-key-qrow_"]:hover { background: #EFF7F9; }
  div[data-key^="assumir_"] > button {
    background: #003B4A !important; color: white !important; border: none !important;
    font-size: 0.78rem !important; font-weight: 700 !important; border-radius: 6px !important;
  }
  div[data-key^="liberar_"] > button {
    background: transparent !important; color: #ED1C24 !important;
    border: 1.5px solid #ED1C24 !important; font-size: 0.78rem !important;
    font-weight: 700 !important; border-radius: 6px !important;
  }
  div[data-key^="ver_"] > button {
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
    'background:#E6F4F1;color:#003B4A;border:2px solid #003B4A;border-radius:10px;'
    'width:52px;height:52px;font-size:1.4rem;font-weight:800;'
    'font-family:Montserrat,sans-serif;">N1</span>'
    '<div>'
    '<div style="font-size:1.25rem;font-weight:800;color:#1A2E33;'
    'font-family:Montserrat,sans-serif;line-height:1.2;">Fila N1 &mdash; Helpdesk</div>'
    '<div style="font-size:0.84rem;color:#5A7E88;font-family:Montserrat,sans-serif;">'
    'Chamados aguardando atendimento do n\xedvel 1</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# Proporções compartilhadas entre o cabeçalho HTML e as colunas das linhas
_COLS = [0.7, 4, 1.2, 1.6, 1.2, 1]
_GRID_TPL = " ".join(str(c) + "fr" for c in _COLS)


def _fila_page(nivel: str):
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

    # Cabeçalho do data grid
    st.markdown(
        '<div class="bq-table-header" style="grid-template-columns:' + _GRID_TPL + ';">'
        '<div class="bq-table-header-cell">ID</div>'
        '<div class="bq-table-header-cell">Chamado</div>'
        '<div class="bq-table-header-cell" style="text-align:center;">Confian\xe7a</div>'
        '<div class="bq-table-header-cell">Status</div>'
        '<div class="bq-table-header-cell">A\xe7\xe3o</div>'
        '<div class="bq-table-header-cell">Ver</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    for t in tickets:
        tid = t["id"]
        confianca = t.get("confianca") or 0
        cor_conf = "#003B4A" if confianca >= 80 else "#F37021" if confianca >= 60 else "#ED1C24"

        with st.container(key="qrow_" + str(tid)):
            c_id, c_info, c_conf, c_status, c_assumir, c_ver = st.columns(_COLS, gap="small")

            with c_id:
                st.markdown(
                    f'<div style="font-size:0.85rem;font-weight:800;color:#003B4A;'
                    f'font-family:Montserrat,sans-serif;padding-top:8px;">INC{tid:06d}</div>',
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
                    f'<div style="text-align:center;padding-top:8px;">'
                    f'<span style="font-weight:700;color:{cor_conf};font-size:0.9rem;">{confianca}%</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with c_status:
                st.markdown(
                    '<div style="padding-top:6px;">' + ui.ticket_status_badge(t["status"]) + '</div>',
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


_fila_page("N1")
ui.render_footer()
