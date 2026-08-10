import streamlit as st
import plotly.express as px

import database as db
import ui_components as ui

db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Sidebar dark + ajustes de layout ──────────────────────────────────────────
ui.render_sidebar("shadow")
st.markdown("""
<style>
  [data-testid="stMainBlockContainer"] { padding-left: 252px !important; }
  div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) { display: none !important; }
  [class*="st-key-shrow_"] { border-bottom: 1px solid #EEF3F5; padding: 8px;
    transition: background 0.1s; }
  [class*="st-key-shrow_"]:hover { background: #F5F2FA; }
</style>
""", unsafe_allow_html=True)

# ── Header compacto ───────────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">'
    '<span style="display:inline-flex;align-items:center;justify-content:center;'
    'background:#EDE7F6;color:#7B1FA2;border:2px solid #7B1FA2;border-radius:10px;'
    'width:52px;height:52px;font-size:1.4rem;">\U0001f311</span>'
    '<div>'
    '<div style="font-size:1.25rem;font-weight:800;color:#1A2E33;'
    'font-family:Montserrat,sans-serif;line-height:1.2;">Modo Sombra (Shadow Mode)</div>'
    '<div style="font-size:0.84rem;color:#5A7E88;font-family:Montserrat,sans-serif;">'
    'A IA classifica em paralelo ao analista, sem atuar &middot; medindo concord\xe2ncia antes de promover</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div style="background:#F5F2FA;border-left:4px solid #7B1FA2;border-radius:0 8px 8px 0;'
    'padding:10px 14px;margin:12px 0 20px;font-size:0.82rem;color:#4A2E66;'
    'font-family:Montserrat,sans-serif;">'
    'Pr\xe1tica de governan\xe7a: por 30 dias o agente roda em paralelo aos humanos, '
    'sem decidir. S\xf3 promovemos para atua\xe7\xe3o aut\xf4noma quando a concord\xe2ncia se sustenta.'
    '</div>',
    unsafe_allow_html=True,
)

_sh = db.stats_shadow()
_regs = db.listar_shadow(200)

if not _sh.get("total"):
    st.info("Nenhum registro de modo sombra ainda.")
    ui.render_footer()
    st.stop()

# ── KPIs de concordância ──────────────────────────────────────────────────────
def _pct(v):
    return f"{v:.1f}%".replace(".", ",") if v is not None else "-"

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(ui.stat_card_html(str(_sh["total"]), "Compara\xe7\xf5es (30 dias)", "#003B4A"),
                unsafe_allow_html=True)
with k2:
    st.markdown(ui.stat_card_html(_pct(_sh["concordancia_nivel"]), "Concord\xe2ncia de n\xedvel", "#2E7D32"),
                unsafe_allow_html=True)
with k3:
    st.markdown(ui.stat_card_html(_pct(_sh["concordancia_categoria"]), "Concord\xe2ncia de categoria", "#7B1FA2"),
                unsafe_allow_html=True)

st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)

# ── Gráfico de concordância por categoria ─────────────────────────────────────
import pandas as pd

_df = pd.DataFrame(_regs)
_df["ok_cat"] = _df["ia_categoria"] == _df["humano_categoria"]
_agg = (_df.groupby("humano_categoria")["ok_cat"]
        .agg(["mean", "count"]).reset_index())
_agg["pct"] = (_agg["mean"] * 100).round(0)
_agg["cat_label"] = _agg["humano_categoria"].apply(ui.fmt_categoria)
_agg = _agg.sort_values("pct")

_fig = px.bar(
    _agg, x="pct", y="cat_label", orientation="h",
    text=_agg["pct"].astype(int).astype(str) + "%",
    title="Concord\xe2ncia de categoria IA \xd7 humano (por categoria)",
    color_discrete_sequence=["#7B1FA2"],
)
_fig.update_layout(
    font_family="Montserrat, sans-serif",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=40, b=0, l=0, r=0), showlegend=False,
    xaxis_title=None, yaxis_title=None, xaxis_range=[0, 105],
)
_fig.update_traces(textposition="outside", cliponaxis=False)
st.plotly_chart(_fig, use_container_width=True)

st.markdown(
    '<div class="result-label" style="margin:18px 0 10px;">'
    'Compara\xe7\xf5es recentes &middot; IA sugeriu \xd7 humano decidiu</div>',
    unsafe_allow_html=True,
)

# ── Tabela IA x humano ────────────────────────────────────────────────────────
_COLS = [4.2, 1.9, 1.9, 1.0]
_GRID_TPL = " ".join(str(c) + "fr" for c in _COLS)
st.markdown(
    '<div class="bq-table-header" style="grid-template-columns:' + _GRID_TPL + ';">'
    '<div class="bq-table-header-cell">Chamado</div>'
    '<div class="bq-table-header-cell">IA sugeriu</div>'
    '<div class="bq-table-header-cell">Humano decidiu</div>'
    '<div class="bq-table-header-cell" style="text-align:center;">Resultado</div>'
    '</div>',
    unsafe_allow_html=True,
)

for r in _regs[:80]:
    ok = (r["ia_nivel"] == r["humano_nivel"]) and (r["ia_categoria"] == r["humano_categoria"])
    marca = ('<span style="color:#2E7D32;font-weight:800;">✓ concordou</span>' if ok
             else '<span style="color:#C62828;font-weight:800;">✗ divergiu</span>')
    ia_txt = (r["ia_nivel"] or "-") + " · " + ui.fmt_categoria(r["ia_categoria"])
    hu_txt = (r["humano_nivel"] or "-") + " · " + ui.fmt_categoria(r["humano_categoria"])
    with st.container(key="shrow_" + str(r["id"])):
        c_desc, c_ia, c_hu, c_res = st.columns(_COLS, gap="small")
        with c_desc:
            st.markdown(
                f"<div style='padding-top:6px;font-size:0.82rem;color:#1A2E33;'>{r['descricao']}</div>",
                unsafe_allow_html=True,
            )
        with c_ia:
            st.markdown(f"<div style='padding-top:6px;font-size:0.8rem;color:#5A7E88;'>{ia_txt}</div>",
                        unsafe_allow_html=True)
        with c_hu:
            st.markdown(f"<div style='padding-top:6px;font-size:0.8rem;color:#5A7E88;'>{hu_txt}</div>",
                        unsafe_allow_html=True)
        with c_res:
            st.markdown(f"<div style='padding-top:6px;text-align:center;font-size:0.78rem;'>{marca}</div>",
                        unsafe_allow_html=True)

ui.render_footer()
