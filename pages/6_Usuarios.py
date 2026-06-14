import html as _html
import streamlit as st

import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)

# ── Sidebar dark (admin) + ajustes de layout ──────────────────────────────────
ui.render_sidebar("usuarios")
st.markdown("""
<style>
  [data-testid="stMainBlockContainer"] { padding-left: 252px !important; }
  div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) { display: none !important; }
  /* Linhas de usuário compactas com separador sutil (em vez de st.divider espaçado) */
  [class*="st-key-urow_"] {
    border-bottom: 1px solid #EEF3F5;
    padding: 10px 6px;
    transition: background 0.1s;
  }
  [class*="st-key-urow_"]:hover { background: #F5FAFB; }
</style>
""", unsafe_allow_html=True)

# ── Header compacto ───────────────────────────────────────────────────────────
st.markdown(
    '<div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;">'
    '<span style="display:inline-flex;align-items:center;justify-content:center;'
    'background:#E6F4F1;color:#003B4A;border:2px solid #003B4A;border-radius:10px;'
    'width:52px;height:52px;font-size:1.3rem;">\U0001f465</span>'
    '<div>'
    '<div style="font-size:1.25rem;font-weight:800;color:#1A2E33;'
    'font-family:Montserrat,sans-serif;line-height:1.2;">Gest\xe3o de Usu\xe1rios</div>'
    '<div style="font-size:0.84rem;color:#5A7E88;font-family:Montserrat,sans-serif;">'
    'Cadastro de solicitantes para vincula\xe7\xe3o nos chamados</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Inicializa states ─────────────────────────────────────────────────────────
for k, v in [("editar_uid", None), ("confirmar_del", None), ("msg_ok", None), ("msg_err", None)]:
    if k not in st.session_state:
        st.session_state[k] = v


@st.dialog("Editar usuário")
def _editar_usuario_dialog(u):
    with st.form("form_edit_dialog"):
        nome = st.text_input("Nome completo *", value=u["nome"])
        email = st.text_input("E-mail *", value=u["email"])
        depto = st.text_input("Departamento *", value=u["departamento"])
        ramal = st.text_input("Ramal", value=u.get("ramal") or "")
        senha = st.text_input("Senha *", value=u.get("senha") or "",
                              help="Vis\xedvel em texto (POC). Edite para alterar.")
        admin = st.checkbox("Administrador", value=bool(u.get("is_admin")))
        st.caption("\\* campos obrigat\xf3rios")
        _cs, _cc = st.columns(2)
        with _cs:
            salvar = st.form_submit_button("Salvar", type="primary", use_container_width=True)
        with _cc:
            cancelar = st.form_submit_button("Cancelar", use_container_width=True)
    if cancelar:
        st.rerun()
    if salvar:
        _faltam = [c for c, v in [("Nome", nome), ("E-mail", email),
                                  ("Departamento", depto), ("Senha", senha)] if not (v or "").strip()]
        if _faltam:
            st.warning("Preencha: " + ", ".join(_faltam) + ".")
        else:
            try:
                db.atualizar_usuario(u["id"], nome.strip(), email.strip().lower(), depto.strip(),
                                     ramal.strip() or None, senha=senha.strip(), is_admin=admin)
                st.session_state.msg_ok = f"Usuário #{u['id']} atualizado."
                st.rerun()
            except Exception as e:
                st.warning(f"Erro ao salvar (e-mail já existe?): {e}")

# Exibe mensagem de feedback (sucesso/erro) e limpa logo depois
if st.session_state.msg_ok:
    st.success(st.session_state.msg_ok)
    st.session_state.msg_ok = None
if st.session_state.msg_err:
    st.error(st.session_state.msg_err)
    st.session_state.msg_err = None

# ── Tabs ──────────────────────────────────────────────────────────────────────
aba_lista, aba_novo = st.tabs(["Lista de Usuários", "Novo Usuário"])

# ── Aba: Lista ────────────────────────────────────────────────────────────────
with aba_lista:
    usuarios = db.listar_usuarios()
    if not usuarios:
        st.info("Nenhum usuário cadastrado ainda.")
    else:
        _mostrar_senhas = st.toggle("👁 Mostrar senhas", key="show_pwd_list")
        for u in usuarios:
            uid = u["id"]
            with st.container(key="urow_" + str(uid)):
                c_info, c_edit, c_del = st.columns([6, 1, 1], vertical_alignment="center")
                with c_info:
                    _adm = ("&nbsp;<span style='background:#FEE8E8;color:#ED1C24;border:1px solid #ED1C24;"
                            "border-radius:10px;padding:1px 8px;font-size:0.66rem;font-weight:700;'>Admin</span>"
                            if u.get("is_admin") else "")
                    _senha_val = u.get("senha") or "—"
                    _senha_disp = _html.escape(_senha_val) if _mostrar_senhas else "•" * len(_senha_val)
                    st.markdown(
                        f"**{_html.escape(u['nome'])}**" + _adm + " &nbsp;·&nbsp; "
                        f"<span style='color:#5A7E88;font-size:0.88rem;'>{_html.escape(u['email'])}</span> &nbsp;·&nbsp; "
                        f"{_html.escape(u['departamento'])}"
                        + (f" &nbsp;·&nbsp; ramal {_html.escape(u['ramal'])}" if u.get("ramal") else "")
                        + f"  \n<span style='color:#7A9EA6;font-size:0.78rem;'>🔑 senha: "
                        f"<code style='color:#003B4A;'>{_senha_disp}</code></span>",
                        unsafe_allow_html=True,
                    )
                with c_edit:
                    if st.button("✏️", key=f"edit_{uid}", help="Editar"):
                        _editar_usuario_dialog(u)
                with c_del:
                    if st.session_state.confirmar_del == uid:
                        if st.button("✅ Confirmar", key=f"del_ok_{uid}"):
                            db.deletar_usuario(uid)
                            st.session_state.confirmar_del = None
                            st.session_state.msg_ok = f"Usuário #{uid} removido."
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"del_{uid}", help="Remover"):
                            st.session_state.confirmar_del = uid
                            st.rerun()

# ── Aba: Novo usuário (sem st.form, para o olho funcionar ao vivo) ────────────
with aba_novo:
    # Reset dos campos após cadastro bem-sucedido (antes de instanciar os widgets)
    if st.session_state.get("_reset_novo"):
        for _k in ["nu_nome", "nu_email", "nu_depto", "nu_ramal", "nu_admin", "nu_show", "nu_senha"]:
            st.session_state.pop(_k, None)
        st.session_state._reset_novo = False
    if "nu_senha" not in st.session_state:
        st.session_state.nu_senha = db.gerar_senha()

    st.markdown("#### Cadastrar novo usuário")
    nome = st.text_input("Nome completo *", key="nu_nome")
    email = st.text_input("E-mail corporativo *", key="nu_email")
    depto = st.text_input("Departamento *", key="nu_depto")
    ramal = st.text_input("Ramal (opcional)", key="nu_ramal")

    _cs, _co = st.columns([5, 1], vertical_alignment="bottom")
    with _co:
        _mostrar = st.toggle("👁", key="nu_show", help="Mostrar senha")
    with _cs:
        senha = st.text_input("Senha *", key="nu_senha",
                              type="default" if _mostrar else "password",
                              help="Senha aleat\xf3ria gerada automaticamente — edit\xe1vel.")
    admin = st.checkbox("Administrador (v\xea dashboard, filas, usu\xe1rios e hist\xf3rico)", key="nu_admin")
    st.caption("\\* campos obrigat\xf3rios")

    if st.button("Cadastrar", type="primary", use_container_width=True, key="nu_criar"):
        _faltam = [c for c, v in [("Nome", nome), ("E-mail", email),
                                  ("Departamento", depto), ("Senha", senha)] if not (v or "").strip()]
        if _faltam:
            st.session_state.msg_err = "Preencha os campos obrigat\xf3rios: " + ", ".join(_faltam) + "."
            st.rerun()
        else:
            try:
                novo = db.criar_usuario(nome.strip(), email.strip().lower(), depto.strip(),
                                        ramal.strip() or None, senha=senha.strip(), is_admin=admin)
                st.session_state.msg_ok = ("Usu\xe1rio " + novo['nome'] + " cadastrado (ID #"
                                           + str(novo['id']) + ", senha: " + (novo.get('senha') or '') + ").")
                st.session_state._reset_novo = True
                st.rerun()
            except Exception as e:
                st.session_state.msg_err = "Erro ao cadastrar (e-mail j\xe1 existe?): " + str(e)
                st.rerun()

ui.render_footer()
