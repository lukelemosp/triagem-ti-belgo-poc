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
  .belgo-nav a:hover { background: rgba(255,255,255,0.13) !important; }
</style>
""", unsafe_allow_html=True)

# ── Navbar HTML puro (sem depender de seletores do Streamlit) ─────────────────
_LINK = (
    "flex:1;min-width:80px;text-align:center;padding:8px 6px;"
    "border-radius:8px;color:rgba(255,255,255,0.88);"
    "font-family:'Montserrat',sans-serif;font-weight:600;"
    "font-size:0.78rem;text-decoration:none;white-space:nowrap;"
    "transition:background 0.15s;"
)

st.markdown(f"""
<nav class="belgo-nav" style="
    background:#003B4A;border-radius:10px;
    padding:6px 10px;margin-bottom:20px;
    display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
  <a href="/"         style="{_LINK}">📊 Dashboard</a>
  <a href="/novo"     style="{_LINK}">📋 Novo Chamado</a>
  <a href="/n1"       style="{_LINK}">🔵 Fila N1</a>
  <a href="/n2"       style="{_LINK}">🔴 Fila N2</a>
  <a href="/chamado"  style="{_LINK}">🔍 Chamado</a>
  <a href="/usuarios" style="{_LINK}">👥 Usuários</a>
  <a href="/triagem"  style="{_LINK}">🤖 Triagem IA</a>
</nav>
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
        st.info("Nenhum chamado registrado ainda. Use **Novo Chamado** acima para criar o primeiro.")

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


# ── Navegação (url_path = URLs dos links acima) ───────────────────────────────
pg = st.navigation(
    {
        "Sistema": [
            st.Page(_dashboard,                title="Dashboard",    default=True),
            st.Page("pages/2_Novo_Chamado.py", title="Novo Chamado", url_path="novo"),
            st.Page("pages/3_Fila_N1.py",      title="Fila N1",      url_path="n1"),
            st.Page("pages/4_Fila_N2.py",      title="Fila N2",      url_path="n2"),
            st.Page("pages/5_Chamado.py",      title="Chamado",      url_path="chamado"),
            st.Page("pages/6_Usuarios.py",     title="Usuários",     url_path="usuarios"),
        ],
        "Demo": [
            st.Page("pages/1_Triagem.py",      title="Triagem IA",   url_path="triagem"),
        ],
    },
    position="hidden",
)
pg.run()
