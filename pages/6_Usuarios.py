import html as _html
import streamlit as st

import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)
st.markdown(ui.header_html(
    title="Gestão de Usuários",
    subtitle="Cadastro de solicitantes para vinculação nos chamados",
    tag="Admin",
), unsafe_allow_html=True)

# ── Inicializa states ─────────────────────────────────────────────────────────
for k, v in [("editar_uid", None), ("confirmar_del", None), ("msg_ok", None), ("msg_err", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

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
        for u in usuarios:
            uid = u["id"]
            with st.container():
                c_info, c_edit, c_del = st.columns([6, 1, 1])
                with c_info:
                    st.markdown(
                        f"**{_html.escape(u['nome'])}** &nbsp;·&nbsp; "
                        f"<span style='color:#5A7E88;font-size:0.88rem;'>{_html.escape(u['email'])}</span> &nbsp;·&nbsp; "
                        f"{_html.escape(u['departamento'])}"
                        + (f" &nbsp;·&nbsp; ramal {_html.escape(u['ramal'])}" if u.get("ramal") else ""),
                        unsafe_allow_html=True,
                    )
                with c_edit:
                    if st.button("✏️", key=f"edit_{uid}", help="Editar"):
                        st.session_state.editar_uid = uid
                        st.rerun()
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
            st.divider()

    # ── Painel de edição inline ──────────────────────────────────────────────
    if st.session_state.editar_uid:
        uid = st.session_state.editar_uid
        u = db.buscar_usuario_por_id(uid)
        if u:
            st.markdown(f"### Editar usuário #{uid}")
            with st.form(f"form_edit_{uid}"):
                nome = st.text_input("Nome completo", value=u["nome"])
                email = st.text_input("E-mail", value=u["email"])
                depto = st.text_input("Departamento", value=u["departamento"])
                ramal = st.text_input("Ramal", value=u.get("ramal") or "")
                c_save, c_cancel = st.columns(2)
                with c_save:
                    salvar = st.form_submit_button("Salvar", type="primary", use_container_width=True)
                with c_cancel:
                    cancelar = st.form_submit_button("Cancelar", use_container_width=True)
            if salvar:
                if not nome.strip() or not email.strip() or not depto.strip():
                    st.session_state.msg_err = "Nome, e-mail e departamento são obrigatórios."
                else:
                    try:
                        db.atualizar_usuario(uid, nome.strip(), email.strip(), depto.strip(), ramal.strip() or None)
                        st.session_state.editar_uid = None
                        st.session_state.msg_ok = f"Usuário #{uid} atualizado."
                        st.rerun()
                    except Exception as e:
                        st.session_state.msg_err = f"Erro ao salvar: {e}"
            if cancelar:
                st.session_state.editar_uid = None
                st.rerun()

# ── Aba: Novo usuário ─────────────────────────────────────────────────────────
with aba_novo:
    with st.form("form_novo_usuario", clear_on_submit=True):
        st.markdown("#### Cadastrar novo usuário")
        nome = st.text_input("Nome completo *")
        email = st.text_input("E-mail corporativo *")
        depto = st.text_input("Departamento *")
        ramal = st.text_input("Ramal (opcional)")
        criar = st.form_submit_button("Cadastrar", type="primary", use_container_width=True)

    if criar:
        if not nome.strip() or not email.strip() or not depto.strip():
            st.session_state.msg_err = "Nome, e-mail e departamento s\xe3o obrigat\xf3rios."
            st.rerun()
        else:
            try:
                novo = db.criar_usuario(nome.strip(), email.strip(), depto.strip(), ramal.strip() or None)
                st.session_state.msg_ok = "Usu\xe1rio " + novo['nome'] + " cadastrado com sucesso (ID #" + str(novo['id']) + ")."
                st.rerun()
            except Exception as e:
                st.session_state.msg_err = "Erro ao cadastrar (e-mail j\xe1 existe?): " + str(e)
                st.rerun()

ui.render_footer()
