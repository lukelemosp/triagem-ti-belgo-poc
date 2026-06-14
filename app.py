import html as _html
import pandas as pd
import plotly.express as px
import streamlit as st
import database as db
import ui_components as ui
import ai_agent as agent

st.set_page_config(
    page_title="Belgo TI — Sistema de Chamados",
    page_icon="favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()
db.seed_demo()  # popula massa de demonstração no banco efêmero (idempotente: só quando total < 50)
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Esconde sidebar ───────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"],
  [data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ── Gate de login ──────────────────────────────────────────────────────────────
def _render_login():
    _l, _c, _r = st.columns([1, 1.3, 1])
    with _c:
        with st.container(key="login_box"):
            st.markdown(ui.login_header_html(), unsafe_allow_html=True)
            with st.form("login_form"):
                _email = st.text_input("E-mail", placeholder="seu.email@belgo.com.br")
                _senha = st.text_input("Senha", type="password", placeholder="Sua senha")
                _entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
            if _entrar:
                _u = db.autenticar(_email, _senha)
                if _u:
                    st.session_state.auth_user = _u
                    st.rerun()
                else:
                    st.error("E-mail ou senha inv\xe1lidos.")
            st.markdown(
                '<div class="belgo-login-hint">Demo · admin: '
                'lucas.lemos@belgo.com.br / adminbelgo</div>',
                unsafe_allow_html=True,
            )


if not st.session_state.get("auth_user"):
    _render_login()
    st.stop()

_USER = st.session_state["auth_user"]
_IS_ADMIN = bool(_USER.get("is_admin"))
_PRIMEIRO_NOME = (_USER.get("nome") or "Usu\xe1rio").split()[0]


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
    _nome = (st.session_state.get("auth_user", {}).get("nome") or "Analista").split()[0]
    st.markdown(ui.welcome_banner_html(_nome), unsafe_allow_html=True)
    ui.render_fab("➕  Novo Chamado", "pages/2_Novo_Chamado.py")

    termo = st.text_input(
        "Busca",
        key="dash_busca",
        placeholder="Buscar ou perguntar \xe0 IA…",
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
        _key_ok = bool(agent.ANTHROPIC_KEY) and agent.ANTHROPIC_KEY != "cole_sua_chave_aqui"
        usar_ia = _key_ok and agent.deve_usar_ia(termo_limpo)
        explicacao = ""
        if usar_ia:
            with st.spinner("Interpretando sua busca com IA…"):
                filtros = agent.interpretar_busca(termo_limpo)
            explicacao = filtros.pop("explicacao", "")
            resultados = db.buscar_tickets_avancado(**filtros)
        else:
            resultados = db.buscar_tickets(termo_limpo)

        if explicacao:
            st.markdown(ui.ai_search_chip_html(explicacao), unsafe_allow_html=True)
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
        # ── Chat analítico (skill MCP: conversar_sobre_chamados) ──────────────
        st.markdown(
            '<div class="result-label" style="margin-bottom:8px;">'
            '💬 Pergunte à IA sobre os chamados</div>',
            unsafe_allow_html=True,
        )
        if "chat_hist" not in st.session_state:
            st.session_state.chat_hist = []
        _cg_in, _cg_btn, _cg_clr = st.columns([5, 1, 1])
        with _cg_in:
            _pergunta = st.text_input(
                "Pergunta IA", key="chat_input",
                placeholder="Ex.: qual o último chamado? quantos N2 estão abertos?",
                label_visibility="collapsed",
            )
        with _cg_btn:
            _perguntar = st.button("Perguntar", key="chat_ask", use_container_width=True, type="primary")
        with _cg_clr:
            if st.button("Limpar", key="chat_clear", use_container_width=True):
                st.session_state.chat_hist = []
                st.rerun()
        if _perguntar and _pergunta.strip():
            with st.spinner("Consultando a base com IA…"):
                _resp = agent.conversar_sobre_chamados(_pergunta.strip(), st.session_state.chat_hist)
            st.session_state.chat_hist.append({"role": "user", "content": _pergunta.strip()})
            st.session_state.chat_hist.append({"role": "assistant", "content": _resp})
        for _m in st.session_state.chat_hist[-8:]:
            with st.chat_message("user" if _m["role"] == "user" else "assistant"):
                st.markdown(_m["content"])
        st.markdown("<hr style='border:none;border-top:1px solid #E2EEF0;margin:14px 0;'>", unsafe_allow_html=True)

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

        # ── Cliques nos gráficos alteram os filtros (via callbacks de on_select) ──
        _STATUS_LABEL_TO_ENUM = {v: k for k, v in _STATUS_LABELS.items()}
        _NIVEL_LABEL_TO_ENUM = {v: k for k, v in _NIVEL_LABELS.items()}
        _CAT_ENUMS = [
            "RESET_SENHA", "VPN_RECONEXAO", "IMPRESSORA_OFFLINE", "EMAIL_SYNC_CELULAR",
            "TEAMS_AUDIO", "OUTLOOK_CAIXA_CHEIA", "WIFI_RECONEXAO", "SAP_LOGIN_LENTO",
            "EXCEL_TRAVA", "WINDOWS_UPDATE_AVISO", "OUTRO",
        ]
        _CAT_LABEL_TO_ENUM = {ui.fmt_categoria(c): c for c in _CAT_ENUMS}

        def _pts(gkey):
            sel = st.session_state.get(gkey)
            if isinstance(sel, dict):
                return sel.get("selection", {}).get("points", []) or []
            return []

        def _cb_cat_label():
            p = _pts("g_cat")
            if p:
                lbl = p[0].get("label")
                st.session_state["dash_cat_sel"] = (
                    None if lbl in (None, "Sem categoria") else _CAT_LABEL_TO_ENUM.get(lbl)
                )

        def _cb_cat_y():
            p = _pts("g_conf")
            if p:
                st.session_state["dash_cat_sel"] = _CAT_LABEL_TO_ENUM.get(p[0].get("y"))

        def _cb_status():
            p = _pts("g_status")
            if p:
                e = _STATUS_LABEL_TO_ENUM.get(p[0].get("x"))
                if e:
                    st.session_state["dash_status"] = [e]

        def _cb_nivel():
            p = _pts("g_nivel")
            if p:
                e = _NIVEL_LABEL_TO_ENUM.get(p[0].get("y"))
                if e:
                    st.session_state["dash_nivel"] = [e]

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

        # Filtro de categoria vindo de clique no gráfico (chip com limpar)
        _cat_sel = st.session_state.get("dash_cat_sel")
        if _cat_sel:
            _chip_c, _chip_b = st.columns([4, 1])
            with _chip_c:
                st.markdown(
                    '<div style="display:inline-flex;align-items:center;gap:8px;'
                    'background:#E6F4F1;border:1px solid #A8C8D0;border-radius:20px;'
                    'padding:5px 14px;font-family:Montserrat,sans-serif;font-size:0.8rem;'
                    'color:#003B4A;font-weight:600;margin:4px 0 8px;">'
                    '\U0001f4ca Categoria: <strong>' + ui.fmt_categoria(_cat_sel) + '</strong></div>',
                    unsafe_allow_html=True,
                )
            with _chip_b:
                if st.button("✕ Limpar", key="clr_cat", use_container_width=True):
                    st.session_state["dash_cat_sel"] = None
                    st.rerun()

        _raw = db.listar_tickets_graficos(_DIAS_MAP[_periodo])
        _df = pd.DataFrame(_raw) if _raw else pd.DataFrame()
        if not _df.empty and _niveis_sel:
            _df = _df[_df["nivel"].isin(_niveis_sel)]
        if not _df.empty and _status_sel:
            _df = _df[_df["status"].isin(_status_sel)]
        if not _df.empty and _cat_sel:
            _df = _df[_df["categoria"] == _cat_sel]

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
                st.plotly_chart(_fig1, use_container_width=True, on_select=_cb_cat_label, key="g_cat")

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
                st.plotly_chart(_fig2, use_container_width=True, on_select=_cb_status, key="g_status")

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
                    st.plotly_chart(_fig3, use_container_width=True, on_select=_cb_cat_y, key="g_conf")

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
                st.plotly_chart(_fig4, use_container_width=True, on_select=_cb_nivel, key="g_nivel")

    # ── Divisor antes da tabela ───────────────────────────────────────────────
    st.markdown(
        '<div class="result-label" style="margin:18px 0 10px;border-top:1px solid #E2EEF0;padding-top:20px;">Chamados recentes</div>',
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


# ── Páginas registradas (default depende do papel) ────────────────────────────
p_home     = st.Page(_dashboard,                title="Dashboard",    default=_IS_ADMIN)
st.session_state["_p_home"] = p_home
p_novo     = st.Page("pages/2_Novo_Chamado.py", title="Novo Chamado", url_path="novo", default=not _IS_ADMIN)
p_n1       = st.Page("pages/3_Fila_N1.py",      title="Fila N1",      url_path="n1")
p_n2       = st.Page("pages/4_Fila_N2.py",      title="Fila N2",      url_path="n2")
p_chamado  = st.Page("pages/5_Chamado.py",       title="Chamado",      url_path="chamado")
p_chamados = st.Page("pages/7_Chamados.py",      title="Chamados",     url_path="chamados")
p_usuarios = st.Page("pages/6_Usuarios.py",      title="Usu\xe1rios",  url_path="usuarios")
p_triagem  = st.Page("pages/1_Triagem.py",       title="Triagem IA",   url_path="triagem")

if _IS_ADMIN:
    pg = st.navigation(
        {
            "Sistema": [p_home, p_novo, p_n1, p_n2, p_chamados, p_chamado, p_usuarios],
            "Demo":    [p_triagem],
        },
        position="hidden",
    )
else:
    pg = st.navigation(
        {"Atendimento": [p_novo], "Demo": [p_triagem]},
        position="hidden",
    )

# ── Topbar de sessão (saudação + Sair) — sem page_link, aparece em todas as telas
_tb_l, _tb_r = st.columns([6, 1])
with _tb_l:
    st.markdown(ui.userchip_html(_USER.get("nome", ""), _IS_ADMIN), unsafe_allow_html=True)
with _tb_r:
    if st.button("Sair", key="btn_logout", use_container_width=True):
        st.session_state.pop("auth_user", None)
        st.rerun()

# ── Navbar nativa (st.page_link) — itens conforme o papel ────────────────────
if _IS_ADMIN:
    _cols = st.columns(7)
    with _cols[0]: st.page_link(p_home,     label="\U0001f4ca Dashboard",    use_container_width=True)
    with _cols[1]: st.page_link(p_novo,     label="\U0001f4cb Novo Chamado", use_container_width=True)
    with _cols[2]: st.page_link(p_n1,       label="\U0001f535 Fila N1",      use_container_width=True)
    with _cols[3]: st.page_link(p_n2,       label="\U0001f534 Fila N2",      use_container_width=True)
    with _cols[4]: st.page_link(p_chamados, label="\U0001f4c2 Chamados",     use_container_width=True)
    with _cols[5]: st.page_link(p_usuarios, label="\U0001f465 Usu\xe1rios",  use_container_width=True)
    with _cols[6]: st.page_link(p_triagem,  label="\U0001f916 Triagem IA",   use_container_width=True)
else:
    _cols = st.columns(2)
    with _cols[0]: st.page_link(p_novo,    label="\U0001f4cb Novo Chamado", use_container_width=True)
    with _cols[1]: st.page_link(p_triagem, label="\U0001f916 Triagem IA",   use_container_width=True)

pg.run()
