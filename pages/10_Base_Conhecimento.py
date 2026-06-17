import html as _html
import streamlit as st

import database as db
import ui_components as ui

db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Sidebar dark (admin) + ajustes de layout ──────────────────────────────────
ui.render_sidebar("kb")
st.markdown("""
<style>
  [data-testid="stMainBlockContainer"] { padding-left: 252px !important; }
  div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) { display: none !important; }
  [class*="st-key-kbrow_"] {
    border-bottom: 1px solid #EEF3F5;
    padding: 10px 6px;
    transition: background 0.1s;
  }
  [class*="st-key-kbrow_"]:hover { background: #F5FAFB; }
  .kb-badge { display:inline-block; border-radius:12px; padding:1px 9px;
    font-size:0.66rem; font-weight:700; font-family:'Montserrat',sans-serif; }
  .kb-badge-on  { background:#E8F5E9; color:#2E7D32; border:1px solid #A5D6A7; }
  .kb-badge-off { background:#ECEFF1; color:#546E7A; border:1px solid #CFD8DC; }
</style>
""", unsafe_allow_html=True)

# ── Header compacto ───────────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;">'
    '<span style="display:inline-flex;align-items:center;justify-content:center;'
    'background:#E3F2FD;color:#0D47A1;border:2px solid #1976D2;border-radius:10px;'
    'width:52px;height:52px;font-size:1.4rem;">\U0001f4da</span>'
    '<div>'
    '<div style="font-size:1.25rem;font-weight:800;color:#1A2E33;'
    'font-family:Montserrat,sans-serif;line-height:1.2;">Base de Conhecimento</div>'
    '<div style="font-size:0.84rem;color:#5A7E88;font-family:Montserrat,sans-serif;">'
    'Artigos de KB que o agente cita ao resolver chamados &mdash; um por categoria</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# Categorias auto-resolvíveis (mesma lista do agente) + OUTRO
_CATEGORIAS = [
    "RESET_SENHA", "VPN_RECONEXAO", "IMPRESSORA_OFFLINE", "EMAIL_SYNC_CELULAR",
    "TEAMS_AUDIO", "OUTLOOK_CAIXA_CHEIA", "WIFI_RECONEXAO", "SAP_LOGIN_LENTO",
    "EXCEL_TRAVA", "WINDOWS_UPDATE_AVISO", "OUTRO",
]

# ── States ────────────────────────────────────────────────────────────────────
for k, v in [("kb_confirm_del", None), ("kb_msg_ok", None), ("kb_msg_err", None)]:
    if k not in st.session_state:
        st.session_state[k] = v


def _categoria_em_uso(categoria: str, exceto_pk: int = None) -> bool:
    """Há outro artigo ATIVO para esta categoria? (regra: 1 artigo por categoria)."""
    if not categoria or categoria == "OUTRO":
        return False
    for a in db.listar_kb():
        if a["categoria"] == categoria and a["ativo"] and a["id"] != exceto_pk:
            return True
    return False


@st.dialog("Editar artigo de KB")
def _editar_kb_dialog(a):
    with st.form("form_edit_kb"):
        codigo = st.text_input("Código *", value=a.get("codigo") or "")
        titulo = st.text_input("Título *", value=a.get("titulo") or "")
        _cat_atual = a.get("categoria") or "OUTRO"
        _idx = _CATEGORIAS.index(_cat_atual) if _cat_atual in _CATEGORIAS else len(_CATEGORIAS) - 1
        categoria = st.selectbox("Categoria", _CATEGORIAS, index=_idx,
                                 format_func=ui.fmt_categoria)
        passos = st.text_area("Passos (um por linha)",
                              value="\n".join(a.get("passos") or []), height=140)
        ativo = st.checkbox("Ativo", value=bool(a.get("ativo")))
        st.caption("\\* campos obrigatórios")
        _cs, _cc = st.columns(2)
        with _cs:
            salvar = st.form_submit_button("Salvar", type="primary", use_container_width=True)
        with _cc:
            cancelar = st.form_submit_button("Cancelar", use_container_width=True)
    if cancelar:
        st.rerun()
    if salvar:
        if not titulo.strip() or not codigo.strip():
            st.warning("Preencha Código e Título.")
        elif ativo and _categoria_em_uso(categoria, exceto_pk=a["id"]):
            st.warning("Já existe um artigo ativo para a categoria "
                       + ui.fmt_categoria(categoria) + ". Desative-o antes (1 por categoria).")
        else:
            _passos = [p.strip() for p in passos.splitlines() if p.strip()]
            try:
                db.atualizar_kb(a["id"], codigo=codigo.strip(), titulo=titulo.strip(),
                                categoria=categoria, passos=_passos, ativo=ativo)
                st.session_state.kb_msg_ok = "Artigo " + codigo.strip() + " atualizado."
                st.rerun()
            except Exception as e:
                st.warning("Erro ao salvar (código já existe?): " + str(e))


# ── Feedback ──────────────────────────────────────────────────────────────────
if st.session_state.kb_msg_ok:
    st.success(st.session_state.kb_msg_ok)
    st.session_state.kb_msg_ok = None
if st.session_state.kb_msg_err:
    st.error(st.session_state.kb_msg_err)
    st.session_state.kb_msg_err = None

# ── KPIs ──────────────────────────────────────────────────────────────────────
_arts = db.listar_kb()
_resolv = db.contar_resolvidos_por_kb()
_ativos = sum(1 for a in _arts if a["ativo"])
_cats = len({a["categoria"] for a in _arts if a["categoria"] and a["ativo"]})
_total_resolv = sum(_resolv.values())

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(ui.stat_card_html(len(_arts), "Artigos", "#1976D2"), unsafe_allow_html=True)
with k2:
    st.markdown(ui.stat_card_html(_ativos, "Ativos", "#2E7D32"), unsafe_allow_html=True)
with k3:
    st.markdown(ui.stat_card_html(_cats, "Categorias cobertas", "#7B1FA2"), unsafe_allow_html=True)
with k4:
    st.markdown(ui.stat_card_html(_total_resolv, "Resolvidos via KB", "#003B4A"), unsafe_allow_html=True)

st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)

aba_lista, aba_novo = st.tabs(["Artigos", "Novo artigo"])

# ── Aba: Lista (R / U / D) ────────────────────────────────────────────────────
with aba_lista:
    if not _arts:
        st.info("Nenhum artigo cadastrado ainda.")
    else:
        for a in _arts:
            pk = a["id"]
            with st.container(key="kbrow_" + str(pk)):
                c_info, c_edit, c_del = st.columns([6, 1, 1], vertical_alignment="center")
                with c_info:
                    _badge = ('<span class="kb-badge kb-badge-on">Ativo</span>' if a["ativo"]
                              else '<span class="kb-badge kb-badge-off">Inativo</span>')
                    _n = _resolv.get(a["codigo"], 0)
                    st.markdown(
                        f"<code style='color:#0D47A1;'>{_html.escape(a['codigo'] or '—')}</code> "
                        f"&nbsp;**{_html.escape(a['titulo'])}**&nbsp; {_badge}  \n"
                        f"<span style='color:#5A7E88;font-size:0.82rem;'>"
                        f"{ui.fmt_categoria(a['categoria'])} &nbsp;·&nbsp; {_n} resolvido(s) via este KB</span>",
                        unsafe_allow_html=True,
                    )
                    if a["passos"]:
                        with st.expander("Ver passos"):
                            st.markdown(
                                "".join("- " + _html.escape(p) + "\n" for p in a["passos"])
                            )
                with c_edit:
                    if st.button("✏️", key=f"kbedit_{pk}", help="Editar"):
                        _editar_kb_dialog(a)
                with c_del:
                    if st.session_state.kb_confirm_del == pk:
                        if st.button("✅ Confirmar", key=f"kbdelok_{pk}"):
                            db.deletar_kb(pk)
                            st.session_state.kb_confirm_del = None
                            st.session_state.kb_msg_ok = "Artigo removido."
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"kbdel_{pk}", help="Remover"):
                            st.session_state.kb_confirm_del = pk
                            st.rerun()

# ── Aba: Novo artigo (C) ──────────────────────────────────────────────────────
with aba_novo:
    if st.session_state.get("_kb_reset_novo"):
        for _k in ["kb_nu_codigo", "kb_nu_titulo", "kb_nu_cat", "kb_nu_passos", "kb_nu_ativo"]:
            st.session_state.pop(_k, None)
        st.session_state._kb_reset_novo = False
    if "kb_nu_codigo" not in st.session_state:
        st.session_state.kb_nu_codigo = db.proximo_codigo_kb()

    st.markdown("#### Cadastrar novo artigo")
    codigo = st.text_input("Código (automático)", key="kb_nu_codigo", disabled=True,
                           help="Gerado automaticamente em sequência (KB0001, KB0002, …).")
    titulo = st.text_input("Título *", key="kb_nu_titulo")
    categoria = st.selectbox("Categoria", _CATEGORIAS, key="kb_nu_cat",
                             format_func=ui.fmt_categoria)
    passos = st.text_area("Passos (um por linha)", key="kb_nu_passos", height=140,
                          placeholder="Ex.:\nConfirmar a identidade do colaborador.\nRedefinir a senha no AD.")
    ativo = st.checkbox("Ativo", value=True, key="kb_nu_ativo")
    st.caption("\\* campos obrigatórios · regra: um artigo ativo por categoria")

    if st.button("Cadastrar artigo", type="primary", use_container_width=True, key="kb_nu_criar"):
        if not (codigo or "").strip() or not (titulo or "").strip():
            st.session_state.kb_msg_err = "Preencha Código e Título."
            st.rerun()
        elif ativo and _categoria_em_uso(categoria):
            st.session_state.kb_msg_err = ("Já existe artigo ativo para "
                                           + ui.fmt_categoria(categoria) + " (1 por categoria).")
            st.rerun()
        else:
            _passos = [p.strip() for p in (passos or "").splitlines() if p.strip()]
            try:
                novo = db.criar_kb(titulo.strip(), categoria=categoria, passos=_passos,
                                   codigo=codigo.strip(), ativo=ativo)
                st.session_state.kb_msg_ok = "Artigo " + novo["codigo"] + " cadastrado."
                st.session_state._kb_reset_novo = True
                st.rerun()
            except Exception as e:
                st.session_state.kb_msg_err = "Erro ao cadastrar (código já existe?): " + str(e)
                st.rerun()

ui.render_footer()
