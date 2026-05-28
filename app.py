import html as _html
import streamlit as st
import database as db
import ui_components as ui

st.set_page_config(
    page_title="Belgo TI — Sistema de Chamados",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Esconde sidebar ───────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"],
  [data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Definição das páginas ─────────────────────────────────────────────────────
def _dashboard():
    st.markdown(ui.header_html(
        title="Sistema de Chamados TI",
        subtitle="Triagem automática com IA · Filas N1/N2 · Gestão de usuários",
        tag="Belgo Arames",
    ), unsafe_allow_html=True)

    stats = db.stats_tickets()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(ui.stat_card_html(stats.get("total") or 0, "Total de chamados"), unsafe_allow_html=True)
    with c2:
        st.markdown(ui.stat_card_html(stats.get("fila_n1") or 0, "Na fila N1"), unsafe_allow_html=True)
    with c3:
        st.markdown(ui.stat_card_html(stats.get("fila_n2") or 0, "Na fila N2", "#ED1C24"), unsafe_allow_html=True)
    with c4:
        st.markdown(ui.stat_card_html(stats.get("resolvidos") or 0, "Resolvidos", "#2E7D32"), unsafe_allow_html=True)
    with c5:
        pct = 0
        total = stats.get("total") or 0
        if total:
            pct = round(stats.get("auto_resolvidos", 0) / total * 100)
        st.markdown(ui.stat_card_html(f"{pct}%", "Auto-resolvidos pela IA", "#7B1FA2"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="result-label" style="margin-bottom:10px;">Chamados recentes</div>',
        unsafe_allow_html=True,
    )
    recentes = db.listar_tickets_recentes(10)
    if not recentes:
        st.info("Nenhum chamado registrado ainda. Use **Novo Chamado** acima para criar o primeiro.")
    else:
        _STATUS = {
            "ABERTO": "\U0001f7e1 Aberto",
            "EM_ATENDIMENTO": "\U0001f535 Em atendimento",
            "RESOLVIDO": "✅ Resolvido",
            "FECHADO": "⬛ Fechado",
        }
        _NIVEL_EMOJI = {"N1": "\U0001f535", "N2": "\U0001f534", "FORA_DE_ESCOPO": "\U0001f7e0"}
        _HDR = ('<span style="font-size:0.72rem;font-weight:700;color:#7A9EA6;'
                'font-family:Montserrat,sans-serif;text-transform:uppercase;letter-spacing:0.05em;">')

        h1, h2, h3, h4, h5 = st.columns([1.2, 0.7, 4.5, 1.8, 2])
        h1.markdown(_HDR + "ID</span>", unsafe_allow_html=True)
        h2.markdown(_HDR + "N\xedvel</span>", unsafe_allow_html=True)
        h3.markdown(_HDR + "T\xedtulo</span>", unsafe_allow_html=True)
        h4.markdown(_HDR + "Status</span>", unsafe_allow_html=True)
        h5.markdown(_HDR + "Aberto em</span>", unsafe_allow_html=True)
        st.divider()

        for t in recentes:
            tid = int(t["id"])
            nivel = t.get("nivel") or "—"
            emoji = _NIVEL_EMOJI.get(nivel, "⚪")
            auto_badge = " ✅" if t.get("auto_resolvido") else ""
            c1, c2, c3, c4, c5 = st.columns([1.2, 0.7, 4.5, 1.8, 2])
            with c1:
                if st.button(ui.inc_id(tid), key="dash_" + str(tid), use_container_width=True):
                    st.session_state["current_ticket_id"] = tid
                    st.switch_page("pages/5_Chamado.py")
            with c2:
                st.markdown(
                    '<span style="font-size:0.85rem;">' + emoji + " " + nivel + "</span>",
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    '<span style="font-size:0.85rem;color:#1A2E33;">'
                    + _html.escape(t["titulo"]) + auto_badge + "</span>",
                    unsafe_allow_html=True,
                )
            with c4:
                st.markdown(
                    '<span style="font-size:0.82rem;">'
                    + _STATUS.get(t["status"], t["status"]) + "</span>",
                    unsafe_allow_html=True,
                )
            with c5:
                st.markdown(
                    '<span style="font-size:0.82rem;color:#5A7E88;">'
                    + ui.fmt_dt(t.get("criado_em") or "") + "</span>",
                    unsafe_allow_html=True,
                )
            st.divider()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<hr style="border:none;border-top:1px solid #D6E2E5;">', unsafe_allow_html=True)
    st.markdown("""
<div style="text-align:center;">
  <span style="font-size:0.78rem;color:#7A9EA6;font-family:'Montserrat',sans-serif;">
    Desenvolvido por <strong style="color:#003B4A;">Lucas Lemos</strong> &nbsp;·&nbsp;
    Belgo Arames, 2026
  </span>
</div>
""", unsafe_allow_html=True)


# ── Páginas registradas ───────────────────────────────────────────────────────
p_home     = st.Page(_dashboard,                title="Dashboard",    default=True)
p_novo     = st.Page("pages/2_Novo_Chamado.py", title="Novo Chamado", url_path="novo")
p_n1       = st.Page("pages/3_Fila_N1.py",      title="Fila N1",      url_path="n1")
p_n2       = st.Page("pages/4_Fila_N2.py",      title="Fila N2",      url_path="n2")
p_chamado  = st.Page("pages/5_Chamado.py",       title="Chamado",      url_path="chamado")
p_usuarios = st.Page("pages/6_Usuarios.py",      title="Usu\xe1rios",  url_path="usuarios")
p_triagem  = st.Page("pages/1_Triagem.py",       title="Triagem IA",   url_path="triagem")

pg = st.navigation(
    {
        "Sistema": [p_home, p_novo, p_n1, p_n2, p_chamado, p_usuarios],
        "Demo":    [p_triagem],
    },
    position="hidden",
)

# ── Navbar nativa (st.page_link — sem iframe, sem JS) ────────────────────────
_c1, _c2, _c3, _c4, _c5, _c6 = st.columns(6)
with _c1: st.page_link(p_home,     label="\U0001f4ca Dashboard",    use_container_width=True)
with _c2: st.page_link(p_novo,     label="\U0001f4cb Novo Chamado", use_container_width=True)
with _c3: st.page_link(p_n1,       label="\U0001f535 Fila N1",      use_container_width=True)
with _c4: st.page_link(p_n2,       label="\U0001f534 Fila N2",      use_container_width=True)
with _c5: st.page_link(p_usuarios, label="\U0001f465 Usu\xe1rios",  use_container_width=True)
with _c6: st.page_link(p_triagem,  label="\U0001f916 Triagem IA",   use_container_width=True)

pg.run()
