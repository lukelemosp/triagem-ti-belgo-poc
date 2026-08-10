import streamlit as st

import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Sidebar dark + ajustes de layout ──────────────────────────────────────────
ui.render_sidebar("chamados")
st.markdown("""
<style>
  [data-testid="stMainBlockContainer"] { padding-left: 252px !important; }
  div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) { display: none !important; }
  [class*="st-key-crow_"] {
    border-bottom: 1px solid #EEF3F5;
    padding: 8px;
    transition: background 0.1s;
  }
  [class*="st-key-crow_"]:hover { background: #EFF7F9; }
  div[data-key^="cver_"] > button {
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
    'width:52px;height:52px;font-size:1.4rem;">\U0001f4c2</span>'
    '<div>'
    '<div style="font-size:1.25rem;font-weight:800;color:#1A2E33;'
    'font-family:Montserrat,sans-serif;line-height:1.2;">Chamados &middot; Hist\xf3rico</div>'
    '<div style="font-size:0.84rem;color:#5A7E88;font-family:Montserrat,sans-serif;">'
    'Todos os chamados, com filtros e ordena\xe7\xe3o avan\xe7ados</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Filtros ───────────────────────────────────────────────────────────────────
_CAT_ENUMS = [
    "RESET_SENHA", "VPN_RECONEXAO", "IMPRESSORA_OFFLINE", "EMAIL_SYNC_CELULAR",
    "TEAMS_AUDIO", "OUTLOOK_CAIXA_CHEIA", "WIFI_RECONEXAO", "SAP_LOGIN_LENTO",
    "EXCEL_TRAVA", "WINDOWS_UPDATE_AVISO", "OUTRO",
]
_STATUS_OPC = ["ABERTO", "EM_ATENDIMENTO", "RESOLVIDO", "FECHADO"]
_STATUS_LBL = {"ABERTO": "Aberto", "EM_ATENDIMENTO": "Em atendimento",
               "RESOLVIDO": "Resolvido", "FECHADO": "Fechado"}
_NIVEL_OPC = ["N1", "N2", "FORA_DE_ESCOPO"]
_NIVEL_LBL = {"N1": "N1", "N2": "N2", "FORA_DE_ESCOPO": "Fora de escopo"}
_DIAS_MAP = {"Todo o histórico": None, "Últimos 7 dias": 7,
             "Últimos 30 dias": 30, "Últimos 90 dias": 90}

_usuarios = db.listar_usuarios()
_sol_opcoes = ["Todos"] + [u["nome"] for u in _usuarios]
_sol_por_nome = {u["nome"]: u for u in _usuarios}

_f1, _f2, _f3 = st.columns([2, 1, 1], vertical_alignment="bottom")
with _f1:
    _busca = st.text_input("Buscar", placeholder="Título, descrição ou ID…", key="ch_busca")
with _f2:
    _periodo = st.selectbox("Período", list(_DIAS_MAP.keys()), index=0, key="ch_periodo")
with _f3:
    _solic = st.selectbox("Solicitante", _sol_opcoes, index=0, key="ch_solic")

_f4, _f5, _f6 = st.columns(3, vertical_alignment="bottom")
with _f4:
    _status_sel = st.multiselect("Status", _STATUS_OPC, default=[],
                                 format_func=lambda x: _STATUS_LBL[x], key="ch_status",
                                 placeholder="Todos os status")
with _f5:
    _nivel_sel = st.multiselect("Nível", _NIVEL_OPC, default=[],
                                format_func=lambda x: _NIVEL_LBL[x], key="ch_nivel",
                                placeholder="Todos os níveis")
with _f6:
    _cat_sel = st.selectbox("Categoria", ["Todas"] + _CAT_ENUMS,
                            format_func=lambda x: "Todas" if x == "Todas" else ui.fmt_categoria(x),
                            key="ch_cat")

# ── Ordenação ─────────────────────────────────────────────────────────────────
_SORT_FIELDS = {
    "Aberto em": "criado_em", "ID": "id", "Nível": "nivel", "Título": "titulo",
    "Status": "status", "Categoria": "categoria", "Confiança": "confianca",
}
_o1, _o2, _o3 = st.columns([1, 1, 4])
with _o1:
    _ord_campo = st.selectbox("Ordenar por", list(_SORT_FIELDS.keys()), index=0, key="ch_ord")
with _o2:
    _ord_dir = st.selectbox("Direção", ["Decrescente", "Crescente"], index=0, key="ch_dir")

# ── Consulta ──────────────────────────────────────────────────────────────────
_resultados = db.buscar_tickets_avancado(
    texto=_busca.strip() or None,
    categoria=None if _cat_sel == "Todas" else _cat_sel,
    nivel=_nivel_sel or None,
    status=_status_sel or None,
    periodo_dias=_DIAS_MAP[_periodo],
    limit=500,
)
if _solic != "Todos":
    _email = _sol_por_nome.get(_solic, {}).get("email")
    _resultados = [t for t in _resultados if t.get("solicitante_email") == _email]

_campo = _SORT_FIELDS[_ord_campo]
_num = _campo in ("id", "confianca")
_resultados.sort(
    key=lambda t: (t.get(_campo) or (0 if _num else "")) if _num else str(t.get(_campo) or "").lower(),
    reverse=(_ord_dir == "Decrescente"),
)

st.caption(f"{len(_resultados)} chamado(s) encontrado(s)")

# ── Data grid ─────────────────────────────────────────────────────────────────
_COLS = [0.9, 3.1, 0.75, 0.9, 1.35, 1.25, 1.3, 0.85]
_GRID_TPL = " ".join(str(c) + "fr" for c in _COLS)
st.markdown(
    '<div class="bq-table-header" style="grid-template-columns:' + _GRID_TPL + ';">'
    '<div class="bq-table-header-cell">ID</div>'
    '<div class="bq-table-header-cell">Chamado</div>'
    '<div class="bq-table-header-cell">N\xedvel</div>'
    '<div class="bq-table-header-cell" style="text-align:center;">Confian\xe7a</div>'
    '<div class="bq-table-header-cell">Status</div>'
    '<div class="bq-table-header-cell">SLA</div>'
    '<div class="bq-table-header-cell">Aberto em</div>'
    '<div class="bq-table-header-cell">Ver</div>'
    '</div>',
    unsafe_allow_html=True,
)

_NIVEL_EMOJI = {"N1": "\U0001f535", "N2": "\U0001f534", "FORA_DE_ESCOPO": "\U0001f7e0"}

if not _resultados:
    st.info("Nenhum chamado encontrado para os filtros selecionados.")
else:
    for t in _resultados[:200]:
        tid = t["id"]
        nivel = t.get("nivel") or "-"
        emoji = _NIVEL_EMOJI.get(nivel, "⚪")
        confianca = t.get("confianca") or 0
        cor_conf = "#003B4A" if confianca >= 80 else "#F37021" if confianca >= 60 else "#ED1C24"
        with st.container(key="crow_" + str(tid)):
            c_id, c_info, c_niv, c_conf, c_status, c_sla, c_dt, c_ver = st.columns(_COLS, gap="small")
            with c_id:
                st.markdown(
                    f'<div style="font-size:0.85rem;font-weight:800;color:#003B4A;'
                    f'font-family:Montserrat,sans-serif;padding-top:8px;white-space:nowrap;">INC{tid:06d}</div>',
                    unsafe_allow_html=True,
                )
            with c_info:
                cat = ui.fmt_categoria(t.get("categoria"))
                canal = ui.canal_badge_html(t.get("canal"))
                st.markdown(
                    f"**{t['titulo']}**  \n"
                    f"<span style='font-size:0.78rem;color:#5A7E88;'>{cat} · {canal}</span>",
                    unsafe_allow_html=True,
                )
            with c_niv:
                st.markdown(
                    f'<div style="padding-top:8px;font-size:0.82rem;">{emoji} {nivel}</div>',
                    unsafe_allow_html=True,
                )
            with c_conf:
                st.markdown(
                    f'<div style="text-align:center;padding-top:8px;">'
                    f'<span style="font-weight:700;color:{cor_conf};font-size:0.9rem;">{confianca}%</span></div>',
                    unsafe_allow_html=True,
                )
            with c_status:
                st.markdown(
                    '<div style="padding-top:6px;">' + ui.ticket_status_badge(t["status"]) + '</div>',
                    unsafe_allow_html=True,
                )
            with c_sla:
                st.markdown(
                    '<div style="padding-top:6px;">' + ui.sla_badge_html(t) + '</div>',
                    unsafe_allow_html=True,
                )
            with c_dt:
                st.markdown(
                    f'<div style="padding-top:8px;font-size:0.8rem;color:#5A7E88;">'
                    f'{ui.fmt_dt(t.get("criado_em") or "")}</div>',
                    unsafe_allow_html=True,
                )
            with c_ver:
                if st.button("🔍 Ver", key=f"cver_{tid}", use_container_width=True):
                    st.session_state["current_ticket_id"] = tid
                    st.session_state["ticket_origin"] = "chamados"
                    st.switch_page("pages/5_Chamado.py")

ui.render_footer()
