import streamlit as st

import database as db
import ui_components as ui
import skills_data

db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Sidebar dark + ajustes de layout ──────────────────────────────────────────
ui.render_sidebar("skills")
st.markdown("""
<style>
  [data-testid="stMainBlockContainer"] { padding-left: 252px !important; }
  div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) { display: none !important; }
  .skill-meta { display:flex; flex-wrap:wrap; gap:4px 16px; margin-top:10px;
    padding-top:10px; border-top:1px solid #E2EEF0; }
  .skill-meta-item { font-size:0.72rem; color:#5A7E88; font-family:'Montserrat',sans-serif; }
  .skill-meta-item b { color:#1A2E33; font-weight:700; }
  .skill-status { display:inline-block; border-radius:12px; padding:1px 10px;
    font-size:0.66rem; font-weight:700; font-family:'Montserrat',sans-serif; }
  .skill-status-ativo  { background:#E8F5E9; color:#2E7D32; border:1px solid #A5D6A7; }
  .skill-status-shadow { background:#FFF4E5; color:#B45309; border:1px solid #FBBF77; }
</style>
""", unsafe_allow_html=True)

# ── Header compacto ───────────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;">'
    '<span style="display:inline-flex;align-items:center;justify-content:center;'
    'background:#EDE7F6;color:#7B1FA2;border:2px solid #7B1FA2;border-radius:10px;'
    'width:52px;height:52px;font-size:1.4rem;">\U0001f9e9</span>'
    '<div>'
    '<div style="font-size:1.25rem;font-weight:800;color:#1A2E33;'
    'font-family:Montserrat,sans-serif;line-height:1.2;">Cat\xe1logo de Skills MCP</div>'
    '<div style="font-size:0.84rem;color:#5A7E88;font-family:Montserrat,sans-serif;">'
    'Agentes publicados no Cat\xe1logo do Azure DevOps &mdash; dono, SLA, custo e uso</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

_stats = db.stats_tickets()
_skills = skills_data.SKILLS
_ativas = sum(1 for s in _skills if s["status"] == "Ativo")
_shadow = sum(1 for s in _skills if s["status"] == "Shadow")
_total_exec = sum(skills_data.execucoes(s, _stats) for s in _skills)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(ui.stat_card_html(len(_skills), "Skills publicadas", "#7B1FA2"), unsafe_allow_html=True)
with k2:
    st.markdown(ui.stat_card_html(_ativas, "Ativas", "#2E7D32"), unsafe_allow_html=True)
with k3:
    st.markdown(ui.stat_card_html(_shadow, "Em modo sombra", "#F37021"), unsafe_allow_html=True)
with k4:
    st.markdown(ui.stat_card_html(f"{_total_exec:,}".replace(",", "."), "Execu\xe7\xf5es (acum.)", "#003B4A"),
                unsafe_allow_html=True)

st.markdown("<div style='margin-top:18px'></div>", unsafe_allow_html=True)


def _titulo(s: dict) -> str:
    if s.get("code"):
        return ('<code style="background:#EDE7F6;color:#7B1FA2;border-radius:3px;'
                'padding:1px 6px;font-size:0.8rem;">' + s["nome"] + "</code>")
    return s["nome"]


def _card(s: dict) -> str:
    base = ui.skill_card(_titulo(s), s["color"], s["tipo"], s["desc"])
    st_cls = "skill-status-shadow" if s["status"] == "Shadow" else "skill-status-ativo"
    execs = skills_data.execucoes(s, _stats)
    meta = (
        '<div class="skill-meta">'
        '<span class="skill-meta-item">Dono: <b>' + s["dono"] + "</b></span>"
        '<span class="skill-meta-item">SLA: <b>' + s["sla"] + "</b></span>"
        '<span class="skill-meta-item">Custo: <b>' + s["custo"] + "</b></span>"
        '<span class="skill-meta-item">Execu\xe7\xf5es: <b>' + f"{execs:,}".replace(",", ".") + "</b></span>"
        '<span class="skill-status ' + st_cls + '">' + s["status"] + "</span>"
        "</div>"
    )
    # Injeta a faixa de metadados antes do fechamento do card.
    return base[:-6] + meta + "</div>"


# Grade de 3 colunas
for _i in range(0, len(_skills), 3):
    cols = st.columns(3, gap="small")
    for _c, _s in zip(cols, _skills[_i:_i + 3]):
        with _c:
            st.markdown(_card(_s), unsafe_allow_html=True)
    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

ui.render_footer()
