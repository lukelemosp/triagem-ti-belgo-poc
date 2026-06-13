import html as _html
import pandas as pd
import plotly.express as px
import streamlit as st
import database as db
import ui_components as ui

st.set_page_config(
    page_title="Belgo TI — Sistema de Chamados",
    page_icon="favicon.ico",
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
def _render_ticket_row(t, key_prefix):
    """Renderiza uma linha de chamado (id clicável, nível, título, status, data)."""
    _STATUS = {
        "ABERTO": "\U0001f7e1 Aberto",
        "EM_ATENDIMENTO": "\U0001f535 Em atendimento",
        "RESOLVIDO": "✅ Resolvido",
        "FECHADO": "⬛ Fechado",
    }
    _NIVEL_EMOJI = {"N1": "\U0001f535", "N2": "\U0001f534", "FORA_DE_ESCOPO": "\U0001f7e0"}
    tid = int(t["id"])
    nivel = t.get("nivel") or "—"
    emoji = _NIVEL_EMOJI.get(nivel, "⚪")
    auto_badge = " ✅" if t.get("auto_resolvido") else ""
    c1, c2, c3, c4, c5 = st.columns([1.2, 0.7, 4.5, 1.8, 2])
    with c1:
        if st.button(ui.inc_id(tid), key=key_prefix + str(tid), use_container_width=True):
            st.session_state["current_ticket_id"] = tid
            st.session_state["ticket_origin"] = "dashboard"
            st.switch_page("pages/5_Chamado.py")
    with c2:
        st.markdown('<span style="font-size:0.85rem;">' + emoji + " " + nivel + "</span>", unsafe_allow_html=True)
    with c3:
        st.markdown(
            '<span style="font-size:0.85rem;color:#1A2E33;">'
            + _html.escape(t["titulo"]) + auto_badge + "</span>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            '<span style="font-size:0.82rem;">' + _STATUS.get(t["status"], t["status"]) + "</span>",
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            '<span style="font-size:0.82rem;color:#5A7E88;">' + ui.fmt_dt(t.get("criado_em") or "") + "</span>",
            unsafe_allow_html=True,
        )


def _dashboard():
    st.markdown(ui.welcome_banner_html("Analista"), unsafe_allow_html=True)
    st.markdown(ui.fab_html("Novo Chamado", "/novo"), unsafe_allow_html=True)

    termo = st.text_input(
        "Busca",
        key="dash_busca",
        placeholder="\U0001f50d  Buscar por ID (INC000007), t\xedtulo, categoria ou solicitante...",
        label_visibility="collapsed",
    )

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

    st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)

    # ── Modo busca: substitui gráficos + recentes pelos resultados ────────────
    termo_limpo = (termo or "").strip()
    if termo_limpo:
        resultados = db.buscar_tickets(termo_limpo)
        _termo_safe = _html.escape(termo_limpo)
        st.markdown(
            '<div class="result-label" style="margin-bottom:10px;">'
            'Resultados da busca por "' + _termo_safe + '" \xb7 ' + str(len(resultados)) + ' encontrado(s)</div>',
            unsafe_allow_html=True,
        )
        if not resultados:
            st.info("Nenhum chamado encontrado. Tente outro termo (ID, t\xedtulo, categoria ou solicitante).")
        else:
            for t in resultados:
                _render_ticket_row(t, "srch_")
                st.divider()
        ui.render_footer()
        return

    # ── Seção de Gráficos (colapsável) ───────────────────────────────────────
    with st.expander("Análise de Chamados", expanded=False):
        _DIAS_MAP = {
            "Últimos 7 dias": 7,
            "Últimos 30 dias": 30,
            "Últimos 90 dias": 90,
            "Todo o histórico": None,
        }
        _NIVEL_LABELS = {"N1": "N1", "N2": "N2", "FORA_DE_ESCOPO": "Fora de Escopo"}
        _STATUS_LABELS = {
            "ABERTO": "Aberto",
            "EM_ATENDIMENTO": "Em Atendimento",
            "RESOLVIDO": "Resolvido",
            "FECHADO": "Fechado",
        }

        _fk1, _fk2, _fk3 = st.columns(3)
        with _fk1:
            _periodo = st.selectbox(
                "Período", list(_DIAS_MAP.keys()), index=1, key="dash_periodo"
            )
        with _fk2:
            _niveis_sel = st.multiselect(
                "Nível", list(_NIVEL_LABELS.keys()),
                default=list(_NIVEL_LABELS.keys()),
                format_func=lambda x: _NIVEL_LABELS[x],
                key="dash_nivel",
            )
        with _fk3:
            _status_sel = st.multiselect(
                "Status", list(_STATUS_LABELS.keys()),
                default=list(_STATUS_LABELS.keys()),
                format_func=lambda x: _STATUS_LABELS[x],
                key="dash_status",
            )

        _raw = db.listar_tickets_graficos(_DIAS_MAP[_periodo])
        _df = pd.DataFrame(_raw) if _raw else pd.DataFrame()
        if not _df.empty and _niveis_sel:
            _df = _df[_df["nivel"].isin(_niveis_sel)]
        if not _df.empty and _status_sel:
            _df = _df[_df["status"].isin(_status_sel)]

        if _df.empty:
            st.info("Nenhum dado para o período e filtros selecionados.")
        else:
            _BELGO_COLORS = [
                "#003B4A", "#ED1C24", "#2E7D32", "#7B1FA2",
                "#F9A825", "#1976D2", "#00695C", "#E64A19",
                "#5D4037", "#455A64",
            ]
            _CHART_LAYOUT = dict(
                font_family="Montserrat, sans-serif",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=36, b=0, l=0, r=0),
            )

            _gc1, _gc2 = st.columns(2)

            # Donut — Chamados por Categoria
            with _gc1:
                _cat = (
                    _df.groupby("categoria", dropna=False)
                    .size()
                    .reset_index(name="total")
                )
                _cat["categoria"] = _cat["categoria"].apply(lambda x: ui.fmt_categoria(x) if x else "Sem categoria")
                _fig1 = px.pie(
                    _cat, names="categoria", values="total",
                    hole=0.52,
                    color_discrete_sequence=_BELGO_COLORS,
                    title="Tipos de Chamado",
                )
                _fig1.update_traces(
                    textposition="inside", textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>%{value} chamados (%{percent})<extra></extra>",
                )
                _fig1.update_layout(**_CHART_LAYOUT, showlegend=False)
                st.plotly_chart(_fig1, use_container_width=True)

            # Barras verticais — Chamados por Status
            with _gc2:
                _st_order = ["ABERTO", "EM_ATENDIMENTO", "RESOLVIDO", "FECHADO"]
                _st_colors = {"ABERTO": "#F9A825", "EM_ATENDIMENTO": "#1976D2",
                              "RESOLVIDO": "#2E7D32", "FECHADO": "#455A64"}
                _sts = (
                    _df.groupby("status")
                    .size()
                    .reindex(_st_order, fill_value=0)
                    .reset_index(name="total")
                )
                _sts["label"] = _sts["status"].map(_STATUS_LABELS)
                _fig2 = px.bar(
                    _sts, x="label", y="total",
                    color="status",
                    color_discrete_map={s: _st_colors[s] for s in _st_order},
                    title="Chamados por Status",
                    labels={"label": "", "total": "Qtd."},
                )
                _fig2.update_traces(
                    hovertemplate="<b>%{x}</b><br>%{y} chamados<extra></extra>",
                )
                _fig2.update_layout(**_CHART_LAYOUT, showlegend=False)
                st.plotly_chart(_fig2, use_container_width=True)

            _gc3, _gc4 = st.columns(2)

            # Barras horizontais — Confiança média da IA por categoria
            with _gc3:
                _conf = (
                    _df[_df["confianca"].notna()]
                    .groupby("categoria")["confianca"]
                    .mean()
                    .round(1)
                    .reset_index()
                    .rename(columns={"confianca": "conf_media"})
                    .sort_values("conf_media", ascending=True)
                )
                _conf["categoria"] = _conf["categoria"].apply(lambda x: ui.fmt_categoria(x) if x else "Sem categoria")
                if _conf.empty:
                    st.caption("Sem dados de confiança para o filtro atual.")
                else:
                    _fig3 = px.bar(
                        _conf, x="conf_media", y="categoria",
                        orientation="h",
                        range_x=[0, 100],
                        title="Confiança Média da IA por Categoria (%)",
                        labels={"conf_media": "Confiança (%)", "categoria": ""},
                        color="conf_media",
                        color_continuous_scale=["#ED1C24", "#F9A825", "#2E7D32"],
                        range_color=[0, 100],
                    )
                    _fig3.update_traces(
                        hovertemplate="<b>%{y}</b><br>Confiança: %{x:.1f}%<extra></extra>",
                    )
                    _fig3.update_layout(**_CHART_LAYOUT, coloraxis_showscale=False)
                    st.plotly_chart(_fig3, use_container_width=True)

            # Barras horizontais empilhadas — Resolução por Nível
            with _gc4:
                _nv = (
                    _df.groupby(["nivel", "auto_resolvido"])
                    .size()
                    .reset_index(name="total")
                )
                _nv["tipo"] = _nv["auto_resolvido"].map(
                    {1: "Auto-resolvido (IA)", 0: "Manual"}
                )
                _nv["nivel_label"] = _nv["nivel"].map(
                    lambda x: _NIVEL_LABELS.get(x, x)
                )
                _fig4 = px.bar(
                    _nv, x="total", y="nivel_label",
                    color="tipo", orientation="h",
                    title="Resolução por Nível",
                    labels={"total": "Qtd.", "nivel_label": "", "tipo": ""},
                    color_discrete_map={
                        "Auto-resolvido (IA)": "#7B1FA2",
                        "Manual": "#003B4A",
                    },
                    barmode="stack",
                )
                _fig4.update_traces(
                    hovertemplate="<b>%{y}</b> — %{fullData.name}<br>%{x} chamados<extra></extra>",
                )
                _fig4.update_layout(**_CHART_LAYOUT)
                st.plotly_chart(_fig4, use_container_width=True)

    # ── Divisor antes da tabela ───────────────────────────────────────────────
    st.divider()

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

        # Sort state
        if "dash_sort_col" not in st.session_state:
            st.session_state["dash_sort_col"] = "criado_em"
        if "dash_sort_dir" not in st.session_state:
            st.session_state["dash_sort_dir"] = "desc"

        def _toggle_sort(col):
            if st.session_state["dash_sort_col"] == col:
                st.session_state["dash_sort_dir"] = (
                    "asc" if st.session_state["dash_sort_dir"] == "desc" else "desc"
                )
            else:
                st.session_state["dash_sort_col"] = col
                st.session_state["dash_sort_dir"] = "asc"

        _sc = st.session_state["dash_sort_col"]
        _sd = st.session_state["dash_sort_dir"]

        def _lbl(text, col):
            if _sc == col:
                return text + (" ▼" if _sd == "desc" else " ▲")
            return text

        _SORT_KEYS = {
            "id":       lambda t: t.get("id") or 0,
            "nivel":    lambda t: t.get("nivel") or "",
            "titulo":   lambda t: (t.get("titulo") or "").lower(),
            "status":   lambda t: t.get("status") or "",
            "criado_em": lambda t: t.get("criado_em") or "",
        }
        recentes = sorted(recentes, key=_SORT_KEYS[_sc], reverse=(_sd == "desc"))

        st.markdown("""
<style>
  button[data-testid="stBaseButton-tertiary"] {
    padding: 0 !important;
    justify-content: flex-start !important;
    min-height: unset !important;
    height: auto !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
  }
  button[data-testid="stBaseButton-tertiary"] p {
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    color: #7A9EA6 !important;
    font-family: Montserrat, sans-serif !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    text-align: left !important;
  }
  button[data-testid="stBaseButton-tertiary"]:hover p {
    color: #003B4A !important;
  }
</style>
""", unsafe_allow_html=True)

        h1, h2, h3, h4, h5 = st.columns([1.2, 0.7, 4.5, 1.8, 2])
        with h1:
            st.button(_lbl("ID", "id"), key="s_id", type="tertiary",
                      on_click=_toggle_sort, args=("id",), use_container_width=True)
        with h2:
            st.button(_lbl("Nível", "nivel"), key="s_nivel", type="tertiary",
                      on_click=_toggle_sort, args=("nivel",), use_container_width=True)
        with h3:
            st.button(_lbl("Título", "titulo"), key="s_titulo", type="tertiary",
                      on_click=_toggle_sort, args=("titulo",), use_container_width=True)
        with h4:
            st.button(_lbl("Status", "status"), key="s_status", type="tertiary",
                      on_click=_toggle_sort, args=("status",), use_container_width=True)
        with h5:
            st.button(_lbl("Aberto em", "criado_em"), key="s_criado_em", type="tertiary",
                      on_click=_toggle_sort, args=("criado_em",), use_container_width=True)
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
                    st.session_state["ticket_origin"] = "dashboard"
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

    ui.render_footer()


# ── Páginas registradas ───────────────────────────────────────────────────────
p_home     = st.Page(_dashboard,                title="Dashboard",    default=True)
st.session_state["_p_home"] = p_home
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
