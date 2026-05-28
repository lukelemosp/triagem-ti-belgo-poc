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

# ── Navbar CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"],
  [data-testid="collapsedControl"] { display: none !important; }

  /* Bloco horizontal que contém os page_links → barra teal */
  [data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) {
      background: #003B4A;
      border-radius: 10px;
      padding: 4px 6px;
      gap: 0 !important;
      margin-bottom: 12px;
  }
  /* Link base */
  [data-testid="stPageLink"] a {
      color: rgba(255,255,255,0.78) !important;
      font-family: 'Montserrat', sans-serif !important;
      font-weight: 600 !important;
      font-size: 0.80rem !important;
      text-decoration: none !important;
      border-radius: 7px !important;
      transition: background 0.15s, color 0.15s !important;
  }
  [data-testid="stPageLink"] a:hover {
      background: rgba(255,255,255,0.10) !important;
      color: #ffffff !important;
  }
  /* Página activa */
  [data-testid="stPageLink"][aria-current="page"] a,
  [data-testid="stPageLink"][aria-current="true"] a {
      background: rgba(255,255,255,0.15) !important;
      color: #ffffff !important;
  }
  [data-testid="stPageLink"] { border: none !important; background: transparent !important; }
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
    if recentes:
        NIVEL_EMOJI = {"N1": "🔵", "N2": "🔴", "FORA_DE_ESCOPO": "🟠"}
        STATUS_LABEL = {
            "ABERTO": "Aberto",
            "EM_ATENDIMENTO": "Em atendimento",
            "RESOLVIDO": "Resolvido",
            "FECHADO": "Fechado",
        }
        rows = []
        for t in recentes:
            nivel = t.get("nivel") or "—"
            emoji = NIVEL_EMOJI.get(nivel, "⚪")
            rows.append({
                "ID": t["id"],
                "Nível": f"{emoji} {nivel}",
                "Título": t["titulo"],
                "Status": STATUS_LABEL.get(t["status"], t["status"]),
                "Auto-resolvido": "Sim" if t.get("auto_resolvido") else "Não",
                "Criado em": (t.get("criado_em") or "")[:16].replace("T", " "),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum chamado registrado ainda. Use **Novo Chamado** no menu acima para criar o primeiro.")

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


_p_dash    = st.Page(_dashboard,                  title="Dashboard",        icon="📊", default=True)
_p_novo    = st.Page("pages/2_Novo_Chamado.py",   title="Novo Chamado",     icon="📋")
_p_n1      = st.Page("pages/3_Fila_N1.py",        title="Fila N1",          icon="🔵")
_p_n2      = st.Page("pages/4_Fila_N2.py",        title="Fila N2",          icon="🔴")
_p_chamado = st.Page("pages/5_Chamado.py",        title="Detalhe Chamado",  icon="🔍")
_p_users   = st.Page("pages/6_Usuarios.py",       title="Usuários",         icon="👥")
_p_triagem = st.Page("pages/1_Triagem.py",        title="Triagem IA",       icon="🤖")

# ── Navbar ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
with c1: st.page_link(_p_dash,    label="📊 Dashboard",       use_container_width=True)
with c2: st.page_link(_p_novo,    label="📋 Novo Chamado",     use_container_width=True)
with c3: st.page_link(_p_n1,      label="🔵 Fila N1",          use_container_width=True)
with c4: st.page_link(_p_n2,      label="🔴 Fila N2",          use_container_width=True)
with c5: st.page_link(_p_chamado, label="🔍 Chamado",          use_container_width=True)
with c6: st.page_link(_p_users,   label="👥 Usuários",         use_container_width=True)
with c7: st.page_link(_p_triagem, label="🤖 Triagem IA",       use_container_width=True)

# ── Navegação (sem sidebar) ───────────────────────────────────────────────────
pg = st.navigation(
    {"Sistema": [_p_dash, _p_novo, _p_n1, _p_n2, _p_chamado, _p_users],
     "Demo":    [_p_triagem]},
    position="hidden",
)
pg.run()
