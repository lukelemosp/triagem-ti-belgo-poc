import streamlit as st
import database as db
import ui_components as ui

st.set_page_config(
    page_title="Belgo TI — Sistema de Chamados",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)
st.markdown(ui.header_html(
    title="Sistema de Chamados TI",
    subtitle="Triagem automática com IA · Filas N1/N2 · Gestão de usuários",
    tag="Belgo Arames",
), unsafe_allow_html=True)

# ── Métricas ──────────────────────────────────────────────────────────────────
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

# ── Chamados recentes ─────────────────────────────────────────────────────────
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
    st.info("Nenhum chamado registrado ainda. Use **Novo Chamado** no menu ao lado para criar o primeiro.")

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
