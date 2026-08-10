import html as _html
import pandas as pd
import plotly.express as px
import streamlit as st
import database as db
import ui_components as ui
import ai_agent as agent
import analytics

st.set_page_config(
    page_title="Belgo TI · Sistema de Chamados",
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


# ── Modal do chat analítico (skill conversar_sobre_chamados) ──────────────────
@st.dialog("💬 Assistente de IA · Chamados", width="large")
def _chat_dialog():
    st.caption("Pergunte sobre a base de chamados: contagens, \xfaltimo chamado, rankings, "
               "por categoria/n\xedvel/status. Pressione Enter para enviar.")
    with st.form("chat_form", clear_on_submit=True):
        _ci, _cb = st.columns([5, 1], vertical_alignment="bottom")
        with _ci:
            _perg = st.text_input("Pergunta", label_visibility="collapsed",
                                  placeholder="Ex.: quantos chamados N2 est\xe3o abertos?")
        with _cb:
            _enviar = st.form_submit_button("Enviar", type="primary", use_container_width=True)
    if _enviar and _perg.strip():
        with st.spinner("Consultando a base com IA…"):
            _resp = agent.conversar_sobre_chamados(_perg.strip(), st.session_state.get("chat_hist", []))
        st.session_state.chat_hist.append({"role": "user", "content": _perg.strip()})
        st.session_state.chat_hist.append({"role": "assistant", "content": _resp})
    if st.session_state.get("chat_hist"):
        with st.container(height=360):
            for _m in st.session_state.chat_hist:
                with st.chat_message("user" if _m["role"] == "user" else "assistant"):
                    st.markdown(_m["content"])
        if st.button("🗑️ Limpar conversa"):
            st.session_state.chat_hist = []
            st.rerun()
    else:
        st.info("Nenhuma pergunta ainda. Experimente: \"qual o \xfaltimo chamado aberto?\"")


# ── Modal "como é calculado" dos indicadores de ROI ───────────────────────────
def _num(v: float, casas: int = 2) -> str:
    """Número no padrão pt-BR (vírgula decimal)."""
    return ("%.*f" % (casas, v)).replace(".", ",")


def _md(texto: str) -> str:
    """Escapa o cifrão para o Markdown do Streamlit não ler 'R$ …$' como LaTeX."""
    return texto.replace("R$", "R\\$")


@st.dialog("Como este indicador é calculado")
def _roi_info_dialog(metric: str):
    a = analytics
    stats = db.stats_roi()
    roi = a.calcular_roi(stats)
    fb = db.stats_feedback()
    auto = int(stats.get("auto_resolvidos") or 0)
    auto30 = int(stats.get("auto_resolvidos_30d") or 0)
    resolvidos = int(stats.get("resolvidos") or 0)
    pos = int(fb.get("positivos") or 0)
    neg = int(fb.get("negativos") or 0)
    custo_h = ("R$ %.2f" % a.CUSTO_HORA_N1).replace(".", ",")

    custo_ia = ("R$ %.2f" % a.CUSTO_CHAMADO_IA).replace(".", ",")
    csat_n = int(stats.get("csat_n") or 0)
    horas_por_chamado = a.TEMPO_MANUAL_N1_MIN / 60.0

    # (titulo, o que e, formula, exemplo com os dados atuais, passo a passo,
    #  variaveis: (nome, valor atual, de onde vem))
    INFO = {
        "deflexao": (
            "Taxa de deflexão",
            "Percentual de chamados **resolvidos sem intervenção humana** - "
            "ou seja, tratados automaticamente pela IA.",
            "**auto-resolvidos ÷ total de resolvidos × 100**",
            "%d ÷ %d = **%s**" % (auto, resolvidos, roi["deflexao"]),
            [
                "Conta os chamados marcados como `auto_resolvido` (a IA fechou "
                "sozinha, sem passar por analista): **%d**." % auto,
                "Conta a base de comparação - todos os chamados já encerrados "
                "(`RESOLVIDO` ou `FECHADO`): **%d**." % resolvidos,
                "Divide um pelo outro e multiplica por 100: **%s**." % roi["deflexao"],
                "Se ainda não houver chamados encerrados, o total de chamados "
                "entra como base para o indicador não ficar indefinido.",
            ],
            [
                ("auto-resolvidos", str(auto), "`tickets.auto_resolvido = 1`"),
                ("resolvidos", str(resolvidos),
                 "`tickets.status` em RESOLVIDO ou FECHADO"),
            ],
        ),
        "economia": (
            "Economia / mês",
            "Custo de mão de obra evitado pelas auto-resoluções dos **últimos 30 dias**, "
            "descontando o custo de IA por chamado.",
            "auto-resolvidos (30d) × (tempo manual × custo-hora do N1 − custo de IA)",
            "%d × (%d min × %s/h − %s) = **%s**"
            % (auto30, a.TEMPO_MANUAL_N1_MIN, custo_h, custo_ia, roi["economia_mes"]),
            [
                "Considera só os auto-resolvidos da janela de %d dias, para o "
                "número ser uma taxa mensal e não um acumulado: **%d**."
                % (a.DIAS_JANELA, auto30),
                "Converte o tempo de um atendimento manual em fração de hora: "
                "%d min ÷ 60 = **%s h**."
                % (a.TEMPO_MANUAL_N1_MIN, _num(horas_por_chamado)),
                "Multiplica pelo custo-hora do analista N1 para achar quanto "
                "custaria atender um desses chamados na mão: %s h × %s = "
                "**R$ %s**." % (_num(horas_por_chamado), custo_h,
                                _num(horas_por_chamado * a.CUSTO_HORA_N1)),
                "Desconta o custo de API/infra do chamado tratado pela IA (%s), "
                "porque a automação não é de graça." % custo_ia,
                "Multiplica a economia líquida por chamado pelo volume do mês: "
                "**%s**." % roi["economia_mes"],
            ],
            [
                ("auto-resolvidos (30d)", str(auto30),
                 "`tickets` auto-resolvidos nos últimos %d dias" % a.DIAS_JANELA),
                ("CUSTO_HORA_N1", custo_h + "/h",
                 "premissa em `analytics.py` (salário + encargos)"),
                ("TEMPO_MANUAL_N1_MIN", "%d min" % a.TEMPO_MANUAL_N1_MIN,
                 "premissa em `analytics.py` (tempo médio de um N1 manual)"),
                ("CUSTO_CHAMADO_IA", custo_ia,
                 "premissa em `analytics.py` (API + infra por chamado)"),
                ("DIAS_JANELA", "%d dias" % a.DIAS_JANELA,
                 "premissa em `analytics.py` (janela da projeção mensal)"),
            ],
        ),
        "horas": (
            "Horas N1 poupadas",
            "Tempo de analista N1 liberado pelas auto-resoluções da IA.",
            "auto-resolvidos × tempo médio de uma resolução manual de N1",
            "%d × %d min = **%s**" % (auto, a.TEMPO_MANUAL_N1_MIN, roi["horas_economizadas"]),
            [
                "Toma todos os chamados que a IA resolveu sozinha (acumulado, "
                "não só o mês): **%d**." % auto,
                "Assume que cada um deles consumiria %d min de um analista N1 "
                "se fosse tratado manualmente." % a.TEMPO_MANUAL_N1_MIN,
                "Multiplica e converte para horas: **%s**." % roi["horas_economizadas"],
                "É capacidade devolvida ao time, não redução de quadro: as horas "
                "voltam para atividades que exigem julgamento humano.",
            ],
            [
                ("auto-resolvidos", str(auto), "`tickets.auto_resolvido = 1`"),
                ("TEMPO_MANUAL_N1_MIN", "%d min" % a.TEMPO_MANUAL_N1_MIN,
                 "premissa em `analytics.py`"),
                ("tempo da IA", "~%d s" % a.TEMPO_IA_SEG,
                 "premissa em `analytics.py` (referência do comparativo)"),
            ],
        ),
        "csat": (
            "CSAT médio",
            "Satisfação média dos solicitantes (nota de 1 a 5) coletada após a "
            "resolução do chamado.",
            "média das notas de CSAT registradas",
            "média de %d avaliações = **%s / 5**" % (csat_n, roi["csat_media"]),
            [
                "Cada chamado encerrado pode receber uma nota de 1 a 5 do "
                "solicitante, gravada em `tickets.csat_nota`.",
                "Soma as notas e divide pela quantidade de avaliações: "
                "**%d avaliação(ões)** hoje." % csat_n,
                "Chamados sem nota não entram na conta - não contam como zero.",
                "É a única métrica do painel que vem direto do usuário final; "
                "as demais são medidas do sistema.",
            ],
            [
                ("csat_nota", "1 a 5", "estrelas no detalhe do chamado"),
                ("nº de avaliações", str(csat_n), "chamados com `csat_nota` preenchida"),
                ("média atual", str(roi["csat_media"]), "calculado em `analytics.calcular_roi`"),
            ],
        ),
        "acuracia": (
            "Acurácia percebida",
            "Quão certa a triagem da IA é, segundo o retorno humano (botões 👍/👎 "
            "no detalhe do chamado).",
            "feedback positivo ÷ (positivo + negativo) × 100",
            "%d 👍 ÷ %d avaliações = **%s**" % (pos, pos + neg, _acuracia_txt(fb)),
            [
                "No detalhe do chamado, o analista responde se a classificação da "
                "IA estava certa (👍) ou errada (👎).",
                "Conta os positivos (**%d**) e os negativos (**%d**)." % (pos, neg),
                "Divide os positivos pelo total avaliado e multiplica por 100: "
                "**%s**." % _acuracia_txt(fb),
                "É *percebida* porque mede a concordância do humano com a IA, não "
                "uma verdade absoluta - a medida cega e sem viés de tela está na "
                "página **Modo Sombra**.",
            ],
            [
                ("👍 positivos", str(pos), "`tickets.feedback_humano = 1`"),
                ("👎 negativos", str(neg), "`tickets.feedback_humano = -1`"),
                ("total avaliado", str(pos + neg), "chamados com feedback registrado"),
            ],
        ),
    }
    titulo, oque, formula, exemplo, passos, variaveis = INFO.get(
        metric, ("Indicador", "", "", "", [], []))
    st.markdown("### " + titulo)
    st.markdown(_md(oque))
    st.markdown("**Fórmula**")
    st.markdown(_md(formula))
    st.markdown("**Com os dados atuais**")
    st.info(_md(exemplo))

    if passos:
        st.markdown("---")
        st.markdown("#### Como o cálculo é feito, passo a passo")
        st.markdown(_md("\n".join("%d. %s" % (i, p) for i, p in enumerate(passos, 1))))

    if variaveis:
        st.markdown("#### Variáveis usadas")
        linhas = ["| Variável | Valor atual | De onde vem |", "|---|---|---|"]
        linhas += ["| `%s` | %s | %s |" % v for v in variaveis]
        st.markdown(_md("\n".join(linhas)))

    st.caption("Os parâmetros de negócio (custo-hora, tempo médio, custo de IA) são "
               "premissas editáveis em `analytics.py`. Os volumes vêm do banco em "
               "tempo real, então os números acompanham o uso da aplicação.")


def _acuracia_txt(fb: dict) -> str:
    return f"{fb['acuracia']:.0f}%" if fb.get("acuracia") is not None else "-"


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
    nivel = t.get("nivel") or "-"
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

    # ── Painel de Valor / ROI ────────────────────────────────────────────────
    _roi = analytics.calcular_roi(db.stats_roi())
    _fb = db.stats_feedback()
    _acuracia = f"{_fb['acuracia']:.0f}%" if _fb.get("acuracia") is not None else "-"
    st.markdown(
        '<div class="result-label" style="margin:6px 0 12px;">'
        '\U0001f4b0 Valor para o neg\xf3cio</div>',
        unsafe_allow_html=True,
    )
    _roi_cards = [
        ("deflexao", _roi["deflexao"], "Taxa de deflex\xe3o", "#7B1FA2"),
        ("economia", _roi["economia_mes"], "Economia / m\xeas", "#2E7D32"),
        ("horas", _roi["horas_economizadas"], "Horas N1 poupadas", "#003B4A"),
        ("csat", _roi["csat_media"] + " / 5", "CSAT m\xe9dio", "#F37021"),
        ("acuracia", _acuracia, "Acur\xe1cia percebida", "#1976D2"),
    ]
    # "i" circular no canto superior direito de cada card (abre o modal explicativo)
    st.markdown("""
<style>
  [class*="st-key-roicard_"] { position: relative; }
  [class*="st-key-roicard_"] [class*="st-key-roi_info_"] {
      position: absolute; top: 6px; right: 8px; width: auto; min-width: 0; margin: 0; z-index: 5; }
  [class*="st-key-roicard_"] [class*="st-key-roi_info_"] button {
      min-height: 0; height: 22px; width: 22px; padding: 0; border-radius: 50%;
      border: 1px solid #CBD8DC; background: #FFFFFF; color: #5A7E88;
      font-style: italic; font-weight: 700; font-size: 0.82rem; line-height: 1; }
  [class*="st-key-roicard_"] [class*="st-key-roi_info_"] button:hover {
      color: #003B4A; border-color: #003B4A; background: #F0F6F8; }
</style>
""", unsafe_allow_html=True)
    _roi_cols = st.columns(5)
    for _col, (_mid, _val, _lbl, _cor) in zip(_roi_cols, _roi_cards):
        with _col:
            with st.container(key="roicard_" + _mid):
                st.markdown(ui.stat_card_html(_val, _lbl, _cor), unsafe_allow_html=True)
                if st.button("i", key="roi_info_" + _mid, help="Como \xe9 calculado"):
                    _roi_info_dialog(_mid)

    # Comparativo de tempo médio de resolução: IA vs manual
    _mttr_fig = px.bar(
        x=[analytics.TEMPO_IA_SEG / 60.0, analytics.TEMPO_MANUAL_N1_MIN],
        y=["Resolu\xe7\xe3o IA", "Resolu\xe7\xe3o manual"],
        orientation="h",
        text=["~30 s", f"{analytics.TEMPO_MANUAL_N1_MIN} min"],
        color=["IA", "Manual"],
        color_discrete_map={"IA": "#2E7D32", "Manual": "#ED1C24"},
        title="Tempo m\xe9dio de resolu\xe7\xe3o · IA vs. manual (min)",
    )
    _mttr_fig.update_layout(
        font_family="Montserrat, sans-serif",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=0, l=0, r=0), showlegend=False, height=200,
        xaxis_title=None, yaxis_title=None,
    )
    _mttr_fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(_mttr_fig, use_container_width=True)
    st.markdown("<div style='margin-top:18px'></div>", unsafe_allow_html=True)

    # ── Seção de Gráficos (colapsável) ───────────────────────────────────────
    with st.expander("Análise de Chamados", expanded=False):
        # ── Chat analítico (skill MCP: conversar_sobre_chamados) — em modal ────
        st.markdown(
            '<div class="result-label" style="margin-bottom:8px;">'
            '💬 Assistente de IA sobre os chamados</div>',
            unsafe_allow_html=True,
        )
        if "chat_hist" not in st.session_state:
            st.session_state.chat_hist = []
        if st.button("💬  Abrir assistente de IA", key="chat_open", use_container_width=False):
            _chat_dialog()
        if st.session_state.chat_hist:
            st.caption(str(len(st.session_state.chat_hist) // 2) + " pergunta(s) nesta sessão.")
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

        _CAT_ENUMS = [
            "RESET_SENHA", "VPN_RECONEXAO", "IMPRESSORA_OFFLINE", "EMAIL_SYNC_CELULAR",
            "TEAMS_AUDIO", "OUTLOOK_CAIXA_CHEIA", "WIFI_RECONEXAO", "SAP_LOGIN_LENTO",
            "EXCEL_TRAVA", "WINDOWS_UPDATE_AVISO", "OUTRO",
        ]

        # Filtros (controlam todos os gráficos abaixo)
        _fk1, _fk2 = st.columns(2)
        with _fk1:
            _periodo = st.selectbox(
                "Período", list(_DIAS_MAP.keys()), index=1, key="dash_periodo"
            )
        with _fk2:
            _cat_box = st.selectbox(
                "Categoria", ["Todas"] + _CAT_ENUMS,
                format_func=lambda x: "Todas" if x == "Todas" else ui.fmt_categoria(x),
                key="dash_cat",
            )
        _fk3, _fk4 = st.columns(2)
        with _fk3:
            _niveis_sel = st.multiselect(
                "Nível", list(_NIVEL_LABELS.keys()),
                default=list(_NIVEL_LABELS.keys()),
                format_func=lambda x: _NIVEL_LABELS[x],
                key="dash_nivel",
            )
        with _fk4:
            _status_sel = st.multiselect(
                "Status", list(_STATUS_LABELS.keys()),
                default=list(_STATUS_LABELS.keys()),
                format_func=lambda x: _STATUS_LABELS[x],
                key="dash_status",
            )
        _cat_sel = None if _cat_box == "Todas" else _cat_box

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
                    hovertemplate="<b>%{y}</b> · %{fullData.name}<br>%{x} chamados<extra></extra>",
                )
                _fig4.update_layout(**_CHART_LAYOUT)
                st.plotly_chart(_fig4, use_container_width=True)

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
            nivel = t.get("nivel") or "-"
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
p_skills   = st.Page("pages/8_Skills.py",        title="Skills",       url_path="skills")
p_shadow   = st.Page("pages/9_Shadow.py",        title="Modo Sombra",  url_path="shadow")
p_kb       = st.Page("pages/10_Base_Conhecimento.py", title="Base de Conhecimento", url_path="kb")

if _IS_ADMIN:
    pg = st.navigation(
        {
            "Sistema":     [p_home, p_novo, p_n1, p_n2, p_chamados, p_chamado, p_usuarios],
            "Governan\xe7a": [p_skills, p_shadow, p_kb],
            "Demo":        [p_triagem],
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
    # Rótulos de grupo: separa o que o usuário comum acessa do que é exclusivo do admin
    # A classe belgo-navgroup permite ao CSS ocultar os rotulos quando a navbar
    # quebra em varias linhas (telas estreitas): o agrupamento por coluna deixa
    # de valer e os rotulos passariam a apontar para os itens errados.
    _grp_user = ("<div class=\"belgo-navgroup\" style=\"font-size:0.64rem;font-weight:700;"
                 "letter-spacing:0.08em;"
                 "text-transform:uppercase;color:#5A7E88;font-family:Montserrat,sans-serif;"
                 "padding:0 0 3px 8px;\">Atendimento</div>")
    _grp_admin = ("<div class=\"belgo-navgroup\" style=\"font-size:0.64rem;font-weight:700;"
                  "letter-spacing:0.08em;"
                  "text-transform:uppercase;color:#003B4A;font-family:Montserrat,sans-serif;"
                  "padding:0 0 3px 12px;border-left:2px solid #ED1C24;\">"
                  "\U0001f512 Acesso administrativo</div>")
    # Proporcoes espelham as colunas da barra abaixo (1.4 + divisor 0.25 + 8 itens)
    _lc1, _lc2 = st.columns([1.525, 8.125])
    with _lc1: st.markdown(_grp_user, unsafe_allow_html=True)
    with _lc2: st.markdown(_grp_admin, unsafe_allow_html=True)

    _divisor = ("<div class=\"belgo-navdivider\" style=\"height:34px;"
                "border-left:2px solid rgba(255,255,255,0.35);"
                "width:1px;margin:0 auto;\"></div>")
    # A pagina de Triagem (demo isolado) segue registrada e acessivel por URL,
    # mas saiu do menu: a triagem real acontece na abertura do chamado.
    _cols = st.columns([1.4, 0.25, 1, 1, 1, 1, 1, 1, 1, 1])
    # Grupo do usuário comum
    with _cols[0]: st.page_link(p_novo,    label="\U0001f4cb Novo Chamado", use_container_width=True)
    # Divisor visual
    with _cols[1]: st.markdown(_divisor, unsafe_allow_html=True)
    # Grupo exclusivo do admin
    with _cols[2]: st.page_link(p_home,     label="\U0001f4ca Dashboard",   use_container_width=True)
    with _cols[3]: st.page_link(p_n1,       label="\U0001f535 Fila N1",     use_container_width=True)
    with _cols[4]: st.page_link(p_n2,       label="\U0001f534 Fila N2",     use_container_width=True)
    with _cols[5]: st.page_link(p_chamados, label="\U0001f4c2 Chamados",    use_container_width=True)
    with _cols[6]: st.page_link(p_skills,   label="\U0001f9e9 Skills",      use_container_width=True)
    with _cols[7]: st.page_link(p_shadow,   label="\U0001f311 Sombra",      use_container_width=True)
    with _cols[8]: st.page_link(p_kb,       label="\U0001f4da KB",          use_container_width=True)
    with _cols[9]: st.page_link(p_usuarios, label="\U0001f465 Usu\xe1rios", use_container_width=True)
else:
    _cols = st.columns([1.4, 6])
    with _cols[0]: st.page_link(p_novo,    label="\U0001f4cb Novo Chamado", use_container_width=True)

pg.run()
