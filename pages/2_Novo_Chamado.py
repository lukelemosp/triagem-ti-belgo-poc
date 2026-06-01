import streamlit as st

import ai_agent as agent
import database as db
import ui_components as ui


db.init_db()
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)
st.markdown(ui.enter_to_submit_js(), unsafe_allow_html=True)
st.markdown(ui.header_html(
    title="Novo Chamado",
    subtitle="Abre chamado, classifica com IA e enfileira automaticamente",
), unsafe_allow_html=True)

_MAX_LEN = 2000

_PRESETS = [
    {
        "categoria": "RESET_SENHA",
        "emoji": "\U0001f511",
        "label": "Reset de Senha",
        "titulo": "Reset de senha de acesso ao sistema",
        "descricao": "Usu\xe1rio solicita reset de senha de acesso aos sistemas corporativos.",
        "sugestao_ia": (
            "Acessar o Active Directory;\n"
            "selecionar o usu\xe1rio e redefinir a senha;\n"
            "e enviar a nova senha tempor\xe1ria por e-mail corporativo."
        ),
        "acao_ia": "Senha redefinida via AD. Nova senha enviada por e-mail.",
    },
    {
        "categoria": "VPN_RECONEXAO",
        "emoji": "\U0001f310",
        "label": "VPN N\xe3o Conecta",
        "titulo": "VPN corporativa n\xe3o conecta",
        "descricao": "VPN corporativa apresenta erro de conex\xe3o ou timeout.",
        "sugestao_ia": (
            "Desconectar completamente o cliente VPN;\n"
            "verificar atualiza\xe7\xf5es pendentes do sistema;\n"
            "reinici\xe1-lo e reconectar;\n"
            "e renovar o IP via ipconfig /renew se necess\xe1rio."
        ),
        "acao_ia": "Guia de reconex\xe3o enviado. Cliente VPN reiniciado.",
    },
    {
        "categoria": "IMPRESSORA_OFFLINE",
        "emoji": "\U0001f5a8",
        "label": "Impressora Offline",
        "titulo": "Impressora do setor offline",
        "descricao": "Impressora do setor est\xe1 aparecendo como offline e n\xe3o imprime.",
        "sugestao_ia": (
            "Verificar se o cabo de rede da impressora est\xe1 conectado;\n"
            "reiniciar a impressora pelo bot\xe3o de energia;\n"
            "e limpar a fila de impress\xe3o no Windows."
        ),
        "acao_ia": "Impressora reconectada \xe0 rede. Fila de impress\xe3o limpa.",
    },
    {
        "categoria": "EMAIL_SYNC_CELULAR",
        "emoji": "\U0001f4f1",
        "label": "E-mail no Celular",
        "titulo": "E-mail corporativo n\xe3o sincroniza no celular",
        "descricao": "E-mail corporativo parou de sincronizar no dispositivo m\xf3vel.",
        "sugestao_ia": (
            "Remover a conta de e-mail corporativo no celular;\n"
            "reinserir as credenciais atualizadas;\n"
            "e aguardar a sincroniza\xe7\xe3o autom\xe1tica (at\xe9 5 minutos)."
        ),
        "acao_ia": "Configura\xe7\xe3o de e-mail no celular corrigida.",
    },
    {
        "categoria": "TEAMS_AUDIO",
        "emoji": "\U0001f3a7",
        "label": "Teams sem \xc1udio",
        "titulo": "Microsoft Teams sem \xe1udio em reuni\xf5es",
        "descricao": "Microfone e/ou alto-falante n\xe3o funcionam no Teams.",
        "sugestao_ia": (
            "Acessar Configura\xe7\xf5es do Teams → Dispositivos;\n"
            "selecionar o microfone e alto-falante corretos;\n"
            "e testar o \xe1udio na chamada."
        ),
        "acao_ia": "Dispositivos de \xe1udio do Teams reconfigurados.",
    },
    {
        "categoria": "OUTLOOK_CAIXA_CHEIA",
        "emoji": "\U0001f4ee",
        "label": "Outlook Caixa Cheia",
        "titulo": "Caixa do Outlook atingiu limite de armazenamento",
        "descricao": "Outlook exibe aviso de caixa cheia e n\xe3o recebe novos e-mails.",
        "sugestao_ia": (
            "Arquivar e-mails mais antigos para pasta local;\n"
            "excluir itens do Lixo Eletr\xf4nico e Itens Enviados;\n"
            "e esvaziar a Lixeira do Outlook."
        ),
        "acao_ia": "Caixa do Outlook liberada. Arquivamento autom\xe1tico configurado.",
    },
    {
        "categoria": "WIFI_RECONEXAO",
        "emoji": "\U0001f4f6",
        "label": "Wi-Fi Inst\xe1vel",
        "titulo": "Conex\xe3o Wi-Fi inst\xe1vel — queda frequente",
        "descricao": "Conex\xe3o Wi-Fi cai frequentemente ou apresenta lat\xeancia elevada.",
        "sugestao_ia": (
            "Esquecer a rede Wi-Fi atual;\n"
            "reiniciar o adaptador (ipconfig /release + renew);\n"
            "reiniciar o computador;\n"
            "e reconectar \xe0 rede correta."
        ),
        "acao_ia": "Adaptador Wi-Fi redefinido. Conex\xe3o estabilizada.",
    },
    {
        "categoria": "SAP_LOGIN_LENTO",
        "emoji": "\U0001f3ed",
        "label": "SAP GUI Lento",
        "titulo": "Login no SAP GUI est\xe1 lento para autenticar",
        "descricao": "O processo de login no SAP GUI est\xe1 demorando mais do que o normal.",
        "sugestao_ia": (
            "Limpar o cache do SAP GUI em Options → Local Data;\n"
            "verificar atualiza\xe7\xf5es do cliente SAP GUI;\n"
            "e reconectar via SAP Logon Pad."
        ),
        "acao_ia": "Cache do SAP GUI limpo. Autentica\xe7\xe3o normalizada.",
    },
    {
        "categoria": "EXCEL_TRAVA",
        "emoji": "\U0001f4ca",
        "label": "Excel Travando",
        "titulo": "Microsoft Excel travando ao editar planilhas",
        "descricao": "Excel trava ou fecha inesperadamente ao abrir ou trabalhar em planilhas.",
        "sugestao_ia": (
            "Abrir o Excel em modo seguro (excel /safe);\n"
            "desativar suplementos em Arquivo → Op\xe7\xf5es → Suplementos;\n"
            "e reparar o Office pelo Painel de Controle."
        ),
        "acao_ia": "Excel reparado. Suplementos conflitantes desativados.",
    },
    {
        "categoria": "WINDOWS_UPDATE_AVISO",
        "emoji": "\U0001fa9f",
        "label": "Windows Update",
        "titulo": "Aviso de atualiza\xe7\xe3o pendente do Windows",
        "descricao": "Windows exibe aviso de atualiza\xe7\xe3o obrigat\xf3ria pendente.",
        "sugestao_ia": (
            "Acessar Configura\xe7\xf5es → Windows Update;\n"
            "instalar as atualiza\xe7\xf5es dispon\xedveis;\n"
            "e agendar o re\xednicio para fora do hor\xe1rio de trabalho."
        ),
        "acao_ia": "Windows Update agendado para fora do hor\xe1rio de expedi\xeante.",
    },
]

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [
    ("nc_processando", False), ("nc_pending", None), ("nc_resultado", None),
    ("nc_ticket", None), ("nc_clear", False), ("nc_input_key", 0), ("nc_preset_idx", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.nc_processando and not st.session_state.nc_pending:
    st.session_state.nc_processando = False

# ── Dados de solicitantes (necessário antes dos presets) ──────────────────────
usuarios = db.listar_usuarios()
opcoes_usuario = ["— N\xe3o informado —"] + [
    u["nome"] + " (" + u["email"] + ")" for u in usuarios
]


def _usuario_id():
    val = st.session_state.get("nc_sol", opcoes_usuario[0])
    if val == opcoes_usuario[0]:
        return None
    try:
        idx = opcoes_usuario.index(val) - 1
        return usuarios[idx]["id"] if 0 <= idx < len(usuarios) else None
    except (ValueError, IndexError):
        return None


# ── Processa preset clicado ────────────────────────────────────────────────────
if st.session_state.nc_preset_idx is not None and not st.session_state.nc_resultado:
    _pi = st.session_state.nc_preset_idx
    _pp = _PRESETS[_pi]
    _ticket = db.criar_ticket(
        titulo=_pp["titulo"],
        descricao=_pp["descricao"],
        nivel="N1",
        categoria=_pp["categoria"],
        confianca=95,
        criado_por=_usuario_id(),
        status="RESOLVIDO",
        resolucao=_pp["sugestao_ia"],
        auto_resolvido=True,
        sugestao_ia=_pp["sugestao_ia"],
        acao_ia=_pp["acao_ia"],
        tempo_estimado="Imediato",
    )
    st.session_state.nc_resultado = {
        "nivel": "N1",
        "categoria": _pp["categoria"],
        "confianca": 95,
        "sugestao": _pp["sugestao_ia"],
        "acao": _pp["acao_ia"],
        "tempo": "Imediato",
        "pensamento": [],
        "motivo_confianca": "Categoria de atendimento autom\xe1tico com resolu\xe7\xe3o pr\xe9-definida.",
    }
    st.session_state.nc_ticket = _ticket
    st.session_state.nc_preset_idx = None
    st.rerun()

# ── Seção de atendimento automático ───────────────────────────────────────────
st.markdown(
    "<div style=\"margin:16px 0 8px;display:flex;align-items:center;gap:8px;\">"
    "<span style=\"font-size:0.72rem;font-weight:700;color:#003B4A;"
    "font-family:'Montserrat',sans-serif;text-transform:uppercase;letter-spacing:0.08em;\">"
    "✨ Atendimento Autom\xe1tico via IA</span>"
    "<span style=\"font-size:0.72rem;color:#7A9EA6;font-family:'Montserrat',sans-serif;\">"
    "— clique para resolver instantaneamente</span>"
    "</div>",
    unsafe_allow_html=True,
)

st.markdown("""
<style>
div[data-testid="stButton"][data-key^="preset_"] > button {
    background: #F0F9F7 !important;
    border: 1.5px solid #A8C8D0 !important;
    color: #003B4A !important;
    font-family: 'Montserrat', sans-serif !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
    padding: 10px 6px !important;
    height: auto !important;
    line-height: 1.4 !important;
    white-space: normal !important;
}
div[data-testid="stButton"][data-key^="preset_"] > button:hover {
    background: #003B4A !important;
    color: white !important;
    border-color: #003B4A !important;
}
</style>
""", unsafe_allow_html=True)

_r1 = st.columns(5)
for _i, _p in enumerate(_PRESETS[:5]):
    with _r1[_i]:
        if st.button(
            _p["emoji"] + " " + _p["label"],
            key="preset_" + str(_i),
            use_container_width=True,
            disabled=st.session_state.nc_processando,
        ):
            st.session_state.nc_preset_idx = _i
            st.rerun()

_r2 = st.columns(5)
for _i, _p in enumerate(_PRESETS[5:], start=5):
    with _r2[_i - 5]:
        if st.button(
            _p["emoji"] + " " + _p["label"],
            key="preset_" + str(_i),
            use_container_width=True,
            disabled=st.session_state.nc_processando,
        ):
            st.session_state.nc_preset_idx = _i
            st.rerun()

st.markdown('<hr style="border:none;border-top:1px solid #D6E2E5;margin:16px 0;">', unsafe_allow_html=True)

# ── Form manual + resultado ────────────────────────────────────────────────────
col_form, col_result = st.columns([1, 1.2], gap="large")

with col_form:
    if st.session_state.nc_clear:
        st.session_state.nc_input_key += 1
        st.session_state.nc_clear = False

    st.markdown("**T\xedtulo do chamado:**")
    titulo = st.text_input(
        "T\xedtulo",
        key="nc_titulo_" + str(st.session_state.nc_input_key),
        placeholder="Ex.: VPN n\xe3o conecta ap\xf3s atualiza\xe7\xe3o",
        label_visibility="collapsed",
        disabled=st.session_state.nc_processando,
    )

    st.markdown("**Descri\xe7\xe3o detalhada:**")
    descricao = st.text_area(
        "Descri\xe7\xe3o",
        key="nc_desc_" + str(st.session_state.nc_input_key),
        height=160,
        placeholder="Descreva o problema com o m\xe1ximo de detalhes poss\xedvel...",
        label_visibility="collapsed",
        disabled=st.session_state.nc_processando,
    )

    _cc = len(descricao)
    _cor = "#ED1C24" if _cc > _MAX_LEN else "#F37021" if _cc > _MAX_LEN * 0.85 else "#7A9EA6"
    st.markdown(
        "<div style=\"text-align:right;font-size:0.7rem;color:" + _cor + ";"
        "font-family:Montserrat,sans-serif;margin-top:-10px;margin-bottom:8px;\">"
        + str(_cc) + "/" + str(_MAX_LEN) + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("**Solicitante:**")
    st.selectbox(
        "Solicitante",
        opcoes_usuario,
        key="nc_sol",
        label_visibility="collapsed",
        disabled=st.session_state.nc_processando,
    )

    btn_abrir = st.button(
        "\U0001f4cb  Abrir chamado e classificar",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.nc_processando,
    )

with col_result:
    # Fase 1: captura clique
    if btn_abrir and titulo.strip() and descricao.strip() and not st.session_state.nc_processando:
        if len(descricao.strip()) > _MAX_LEN:
            st.warning("Descri\xe7\xe3o muito longa — m\xe1ximo " + str(_MAX_LEN) + " caracteres.")
        elif not agent.ANTHROPIC_KEY or agent.ANTHROPIC_KEY == "cole_sua_chave_aqui":
            st.warning("⚠ Chave da API Anthropic n\xe3o configurada.")
        else:
            texto = agent._sanitizar_input(descricao.strip())
            st.session_state.nc_pending = {
                "titulo": titulo.strip(),
                "descricao": texto,
                "usuario_id": _usuario_id(),
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
            print("[ERROR] analisar: " + str(e))
            result_slot.empty()
            st.error("Erro na classifica\xe7\xe3o. Tente novamente.")
            st.session_state.nc_processando = False
            st.session_state.nc_pending = None
            st.stop()

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

        if nivel == "FORA_DE_ESCOPO":
            ticket = None
        else:
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
    elif st.session_state.nc_resultado:
        r = st.session_state.nc_resultado
        t = st.session_state.nc_ticket  # None quando FORA_DE_ESCOPO

        if r.get("pensamento"):
            _cot_desc = t.get("descricao", "") if t else ""
            steps_html = "".join(agent._cot_step(p) for p in r["pensamento"])
            st.markdown(
                agent._cot_header(_cot_desc) + steps_html + agent._COT_FTR,
                unsafe_allow_html=True,
            )

        if r.get("nivel") == "FORA_DE_ESCOPO":
            st.markdown(
                "<div style=\"background:#FFF3E0;border:1px solid #FF9800;border-radius:10px;"
                "padding:14px 18px;margin-bottom:14px;display:flex;align-items:center;gap:12px;\">"
                "<span style=\"font-size:1.6rem;\">\U0001f6ab</span>"
                "<div>"
                "<div style=\"font-weight:700;color:#E65100;font-family:'Montserrat',sans-serif;\">"
                "Solicita\xe7\xe3o fora do escopo de TI"
                "</div>"
                "<div style=\"font-size:0.83rem;color:#BF360C;font-family:'Montserrat',sans-serif;\">"
                "Nenhum chamado foi aberto. Redirecionamento sugerido abaixo."
                "</div>"
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        elif t and t.get("auto_resolvido"):
            cat_label = ui.fmt_categoria(t.get("categoria"))
            st.markdown(
                "<div style=\"background:#E8F5E9;border:1px solid #4CAF50;border-radius:10px;"
                "padding:14px 18px;margin-bottom:14px;display:flex;align-items:center;gap:12px;\">"
                "<span style=\"font-size:1.6rem;\">✨</span>"
                "<div>"
                "<div style=\"font-weight:700;color:#1B5E20;font-family:'Montserrat',sans-serif;\">"
                "Atendimento Autom\xe1tico via IA"
                "</div>"
                "<div style=\"font-size:0.83rem;color:#2E7D32;font-family:'Montserrat',sans-serif;\">"
                + ui.inc_id(t["id"]) + " \xb7 Confian\xe7a "
                + str(t.get("confianca")) + "% \xb7 " + cat_label
                + "</div>"
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        elif t:
            nivel_label = {
                "N1": "Fila N1 — Helpdesk",
                "N2": "Fila N2 — Especialistas",
            }.get(t.get("nivel", ""), t.get("nivel", ""))
            st.markdown(
                "<div style=\"background:#E3F2FD;border:1px solid #1976D2;border-radius:10px;"
                "padding:14px 18px;margin-bottom:14px;display:flex;align-items:center;gap:12px;\">"
                "<span style=\"font-size:1.6rem;\">\U0001f4ec</span>"
                "<div>"
                "<div style=\"font-weight:700;color:#0D47A1;font-family:'Montserrat',sans-serif;\">"
                + ui.inc_id(t["id"]) + " adicionado \xe0 fila"
                + "</div>"
                "<div style=\"font-size:0.83rem;color:#1565C0;font-family:'Montserrat',sans-serif;\">"
                + nivel_label + " \xb7 Confian\xe7a " + str(t.get("confianca")) + "%"
                + "</div>"
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown(ui.render_result_card(r), unsafe_allow_html=True)

        if st.button("Abrir novo chamado", use_container_width=True):
            st.session_state.nc_resultado = None
            st.session_state.nc_ticket = None
            st.rerun()

    elif not st.session_state.nc_processando:
        st.markdown(ui.render_empty_state(), unsafe_allow_html=True)

ui.render_footer()
