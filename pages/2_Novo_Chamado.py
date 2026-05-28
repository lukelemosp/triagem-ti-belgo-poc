import streamlit as st

import ai_agent as agent
import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)
st.markdown(ui.header_html(
    title="Novo Chamado",
    subtitle="Abre chamado, classifica com IA e enfileira automaticamente",
), unsafe_allow_html=True)

_MAX_LEN = 2000

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [
    ("nc_processando", False), ("nc_pending", None), ("nc_resultado", None),
    ("nc_ticket", None), ("nc_clear", False), ("nc_input_key", 0),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Formulário ────────────────────────────────────────────────────────────────
col_form, col_result = st.columns([1, 1.2], gap="large")

with col_form:
    if st.session_state.nc_clear:
        st.session_state.nc_input_key += 1
        st.session_state.nc_clear = False

    usuarios = db.listar_usuarios()
    opcoes_usuario = ["— Não informado —"] + [f"{u['nome']} ({u['email']})" for u in usuarios]

    st.markdown("**Título do chamado:**")
    titulo = st.text_input(
        "Título",
        key=f"nc_titulo_{st.session_state.nc_input_key}",
        placeholder="Ex.: VPN não conecta após atualização",
        label_visibility="collapsed",
        disabled=st.session_state.nc_processando,
    )

    st.markdown("**Descrição detalhada:**")
    descricao = st.text_area(
        "Descrição",
        key=f"nc_desc_{st.session_state.nc_input_key}",
        height=160,
        placeholder="Descreva o problema com o máximo de detalhes possível...",
        label_visibility="collapsed",
        disabled=st.session_state.nc_processando,
    )

    _cc = len(descricao)
    _cor = "#ED1C24" if _cc > _MAX_LEN else "#F37021" if _cc > _MAX_LEN * 0.85 else "#7A9EA6"
    st.markdown(
        f'<div style="text-align:right;font-size:0.7rem;color:{_cor};'
        f'font-family:Montserrat,sans-serif;margin-top:-10px;margin-bottom:8px;">'
        f'{_cc}/{_MAX_LEN}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Solicitante:**")
    sel_usuario = st.selectbox(
        "Solicitante",
        opcoes_usuario,
        label_visibility="collapsed",
        disabled=st.session_state.nc_processando,
    )

    btn_abrir = st.button(
        "📋  Abrir chamado e classificar",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.nc_processando,
    )

with col_result:
    # Fase 1: captura clique
    if btn_abrir and titulo.strip() and descricao.strip() and not st.session_state.nc_processando:
        if len(descricao.strip()) > _MAX_LEN:
            st.warning(f"Descrição muito longa — máximo {_MAX_LEN} caracteres.")
        elif not agent.ANTHROPIC_KEY or agent.ANTHROPIC_KEY == "cole_sua_chave_aqui":
            st.warning("⚠ Chave da API Anthropic não configurada.")
        else:
            # Resolve usuário selecionado
            usuario_id = None
            if sel_usuario != "— Não informado —":
                idx = opcoes_usuario.index(sel_usuario) - 1
                if 0 <= idx < len(usuarios):
                    usuario_id = usuarios[idx]["id"]

            texto = agent._sanitizar_input(descricao.strip())
            st.session_state.nc_pending = {
                "titulo": titulo.strip(),
                "descricao": texto,
                "usuario_id": usuario_id,
            }
            st.session_state.nc_processando = True
            st.session_state.nc_resultado = None
            st.session_state.nc_ticket = None
            st.session_state.nc_clear = True
            st.rerun()

    # Fase 2: chama IA com streaming e grava no DB
    if st.session_state.nc_processando and st.session_state.nc_pending:
        p = st.session_state.nc_pending
        cot_slot = st.empty()
        result_slot = st.empty()
        result_slot.markdown(agent._skeleton_card_html(), unsafe_allow_html=True)
        resultado = None
        try:
            resultado = agent.analisar(p["descricao"], cot_slot=cot_slot)
        except Exception as e:
            print(f"[ERROR] analisar: {e}")
            result_slot.empty()
            st.error("Erro na classificação. Tente novamente.")
            st.session_state.nc_processando = False
            st.session_state.nc_pending = None
            st.stop()

        # Determina auto-resolução
        nivel = resultado.get("nivel", "FORA_DE_ESCOPO")
        if nivel not in agent._NIVEIS_VALIDOS:
            nivel = "FORA_DE_ESCOPO"
        categoria = resultado.get("categoria", "OUTRO") or "OUTRO"
        try:
            confianca = max(0, min(100, int(resultado.get("confianca", 0))))
        except (TypeError, ValueError):
            confianca = 0
        auto = (
            nivel == "N1"
            and confianca >= agent.AUTO_RESOLVE_THRESHOLD
            and categoria in agent.AUTO_RESOLVABLE
        )

        ticket = db.criar_ticket(
            titulo=p["titulo"],
            descricao=p["descricao"],
            nivel=nivel,
            categoria=categoria,
            confianca=confianca,
            criado_por=p["usuario_id"],
            status="RESOLVIDO" if auto else "ABERTO",
            resolucao=resultado.get("sugestao") if auto else None,
            auto_resolvido=auto,
            sugestao_ia=resultado.get("sugestao"),
            acao_ia=resultado.get("acao"),
            tempo_estimado=resultado.get("tempo"),
        )

        st.session_state.nc_resultado = resultado
        st.session_state.nc_ticket = ticket
        st.session_state.nc_pending = None
        st.session_state.nc_processando = False
        st.rerun()

    # Fase 3: exibe resultado
    elif st.session_state.nc_resultado and st.session_state.nc_ticket:
        r = st.session_state.nc_resultado
        t = st.session_state.nc_ticket

        # CoT
        if r.get("pensamento"):
            steps_html = "".join(agent._cot_step(p) for p in r["pensamento"])
            st.markdown(
                agent._cot_header(t.get("descricao", "")) + steps_html + agent._COT_FTR,
                unsafe_allow_html=True,
            )

        # Banner de auto-resolução
        if t.get("auto_resolvido"):
            st.markdown(f"""
<div style="background:#E8F5E9;border:1px solid #4CAF50;border-radius:10px;padding:14px 18px;
     margin-bottom:14px;display:flex;align-items:center;gap:12px;">
  <span style="font-size:1.6rem;">✅</span>
  <div>
    <div style="font-weight:700;color:#1B5E20;font-family:'Montserrat',sans-serif;">
      Chamado auto-resolvido pela IA
    </div>
    <div style="font-size:0.83rem;color:#2E7D32;font-family:'Montserrat',sans-serif;">
      Ticket #{t['id']} · Confiança {t.get('confianca')}% · Categoria: {t.get('categoria')}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            nivel_label = {"N1": "Fila N1 — Helpdesk", "N2": "Fila N2 — Especialistas",
                          "FORA_DE_ESCOPO": "Fora do Escopo"}.get(t.get("nivel", ""), t.get("nivel", ""))
            st.markdown(f"""
<div style="background:#E3F2FD;border:1px solid #1976D2;border-radius:10px;padding:14px 18px;
     margin-bottom:14px;display:flex;align-items:center;gap:12px;">
  <span style="font-size:1.6rem;">📬</span>
  <div>
    <div style="font-weight:700;color:#0D47A1;font-family:'Montserrat',sans-serif;">
      Chamado #{t['id']} adicionado à fila
    </div>
    <div style="font-size:0.83rem;color:#1565C0;font-family:'Montserrat',sans-serif;">
      {nivel_label} · Confiança {t.get('confianca')}%
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown(ui.render_result_card(r), unsafe_allow_html=True)

        if st.button("Abrir novo chamado", use_container_width=True):
            st.session_state.nc_resultado = None
            st.session_state.nc_ticket = None
            st.rerun()

    elif not st.session_state.nc_processando:
        st.markdown(ui.render_empty_state(), unsafe_allow_html=True)
