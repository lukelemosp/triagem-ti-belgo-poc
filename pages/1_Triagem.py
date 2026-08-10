"""
Página de triagem - demo interativo do agente.
Funcionalidade idêntica ao agente_triagem.py standalone.
"""
import html as _html
import random
import time

import streamlit as st

import ai_agent as agent
import ui_components as ui


_PLACEHOLDERS = [
    "Não consigo acessar o SAP com meu usuário desde esta manhã...",
    "A transação MB51 do SAP está travando ao gerar relatório de movimentações...",
    "Erro 'RFC connection failed' ao tentar abrir o SAP GUI na minha estação...",
    "Não estou conseguindo lançar nota fiscal no SAP - autorização negada...",
    "SAP está lento demais no setor de compras, travando a cada 2 minutos...",
    "Preciso de acesso ao módulo PP do SAP para acompanhar ordens de produção...",
    "A impressão de etiquetas via SAP parou de funcionar na linha 3...",
    "Erro ao executar a transação ME23N - 'Object not found' no SAP...",
    "Não consigo fazer login no SAP Logon - tela fica carregando indefinidamente...",
    "Relatório de estoque MB52 no SAP está gerando valores incorretos...",
    "Não consigo acessar o Salesforce - tela de login retorna erro 401...",
    "Dados de oportunidades do Salesforce não estão sincronizando com o SAP...",
    "Preciso de acesso de edição nos registros de conta do Salesforce para meu perfil...",
    "Fluxo de aprovação de pedido no Salesforce está rejeitando automaticamente...",
    "Relatórios de pipeline do Salesforce estão gerando dados duplicados...",
    "Sem conexão de rede no ramal B2, todos os computadores do setor offline...",
    "VPN não conecta fora do escritório - erro 'Network timeout' após atualização...",
    "Wi-Fi do escritório cai constantemente, especialmente na sala de reunião 204...",
    "Switch do andar 3 parece ter reiniciado sozinho, setor inteiro sem rede...",
    "Link de internet da fábrica caiu - produção parada aguardando reconexão...",
    "Monitor do computador ficou com tela preta e não responde...",
    "Teclado e mouse USB pararam de funcionar após reiniciar o Windows...",
    "Bateria do notebook não carrega mais - fica em 4% mesmo plugado na tomada...",
    "Headset não funciona no Teams - áudio saindo pelo alto-falante do computador...",
    "Senha expirou e o sistema não permite criar nova - link de redefinição falha...",
    "Conta do AD bloqueada por excesso de tentativas - preciso de reset urgente...",
    "VPN não conecta fora do escritório - erro 'Network timeout' após atualização...",
    "E-mail corporativo não sincroniza no celular após troca de senha...",
    "Teams trava ao iniciar videoconferência com mais de 5 participantes...",
    "Caixa de entrada do Outlook cheia - não consigo receber novos e-mails...",
    "Impressora do setor de expedição offline - fila há 3 horas sem imprimir...",
    "Impressora HP 4525 não conecta na rede após ser movida de sala...",
    "Sistema de supervisão SCADA perdeu comunicação com CLP da linha 4...",
    "Computador de controle da prensa 7 não inicializa o software de automação...",
    "Rede OT da fábrica sem comunicação com servidor de historiador de dados...",
    "Antivírus bloqueando instalação de software homologado pela TI - como liberar...",
    "Computador com Windows 7 precisa ser atualizado - aviso de suporte encerrado...",
    "Backup noturno falhou - log indica espaço insuficiente no servidor...",
    "Power BI não atualiza dados automaticamente - relatório de vendas desatualizado...",
]

_COOLDOWN_S = 12
_MAX_GLOBAL_HOUR = 40
_MAX_INPUT_LEN = 2000


@st.cache_resource
def _global_rate_store() -> dict:
    import threading
    return {"times": [], "lock": threading.Lock()}


def _check_rate_limit():
    import time as _t
    now = _t.time()
    sess = [t for t in st.session_state.get("request_times", []) if now - t < 3600]
    st.session_state.request_times = sess
    if sess and (now - sess[-1]) < _COOLDOWN_S:
        wait = int(_COOLDOWN_S - (now - sess[-1])) + 1
        return False, f"⏱ Aguarde **{wait}s** antes da próxima análise."
    store = _global_rate_store()
    with store["lock"]:
        store["times"] = [t for t in store["times"] if now - t < 3600]
        if len(store["times"]) >= _MAX_GLOBAL_HOUR:
            reset = int(3600 - (now - min(store["times"])))
            m, s = divmod(reset, 60)
            return False, f"🚫 Limite atingido. Disponível em {m}min {s}s."
    return True, None


def _record_request():
    import time as _t
    now = _t.time()
    st.session_state.request_times.append(now)
    store = _global_rate_store()
    with store["lock"]:
        store["times"].append(now)


# ── Inicializa session state ──────────────────────────────────────────────────
for key, val in [
    ("resultado", None), ("processando", False), ("pending_input", None),
    ("clear_input", False), ("request_times", []), ("input_key", 0),
    ("last_input", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = val

if "placeholder_idx" not in st.session_state:
    st.session_state.placeholder_idx = random.randrange(len(_PLACEHOLDERS))

# ── CSS + header ──────────────────────────────────────────────────────────────
st.markdown(ui.BELGO_CSS, unsafe_allow_html=True)
st.markdown(ui.enter_to_submit_js(), unsafe_allow_html=True)
st.markdown(ui.header_html(), unsafe_allow_html=True)
_is_admin = bool(st.session_state.get("auth_user", {}).get("is_admin"))
_crumb = [("Dashboard", "/"), ("Triagem IA", None)] if _is_admin else [("Triagem IA", None)]
st.markdown(ui.breadcrumb_html(_crumb), unsafe_allow_html=True)



# ── Layout principal ──────────────────────────────────────────────────────────
col_esq, col_dir = st.columns([1, 1.2], gap="large")

with col_esq:
    if st.session_state.clear_input:
        st.session_state.input_key += 1
        st.session_state.clear_input = False

    st.markdown("**Descreva o chamado:**")
    ticket_input = st.text_area(
        label="Descrição",
        key=f"ticket_input_{st.session_state.input_key}",
        height=160,
        placeholder=_PLACEHOLDERS[st.session_state.placeholder_idx],
        label_visibility="collapsed",
        disabled=st.session_state.processando,
    )

    btn_analisar = st.button(
        "🔍  Analisar chamado",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.processando,
    )

    _char_count = len(ticket_input)
    _char_color = (
        "#ED1C24" if _char_count > _MAX_INPUT_LEN else
        "#F37021" if _char_count > _MAX_INPUT_LEN * 0.85 else "#7A9EA6"
    )
    st.markdown(
        f'<div style="text-align:right;font-size:0.7rem;color:{_char_color};'
        f'font-family:Montserrat,sans-serif;margin-top:-10px;margin-bottom:4px;">'
        f'{_char_count}/{_MAX_INPUT_LEN}</div>',
        unsafe_allow_html=True,
    )

    _now = time.time()
    _sess = [t for t in st.session_state.request_times if _now - t < 3600]
    _store = _global_rate_store()
    with _store["lock"]:
        _gcnt = len([t for t in _store["times"] if _now - t < 3600])
    _rem = _MAX_GLOBAL_HOUR - _gcnt
    if _sess and (_now - _sess[-1]) < _COOLDOWN_S:
        _wait = int(_COOLDOWN_S - (_now - _sess[-1])) + 1
        st.caption(f"⏱ Cooldown: {_wait}s · {_rem} req disponíveis esta hora")
    elif _rem <= 0:
        st.caption("🚫 Limite de uso atingido esta hora")
    elif _gcnt > 0:
        st.caption(f"✓ {_rem}/{_MAX_GLOBAL_HOUR} análises disponíveis esta hora")

with col_dir:
    # Fase 1: captura clique
    if btn_analisar and ticket_input.strip() and not st.session_state.processando:
        if len(ticket_input.strip()) > _MAX_INPUT_LEN:
            st.warning(f"Descrição muito longa - limite de {_MAX_INPUT_LEN} caracteres.")
        else:
            ok, reason = _check_rate_limit()
            if not ok:
                st.warning(reason)
            else:
                _record_request()
                texto = agent._sanitizar_input(ticket_input.strip())
                st.session_state.pending_input = texto
                st.session_state.last_input = texto
                st.session_state.processando = True
                st.session_state.resultado = None
                st.session_state.clear_input = True
                st.rerun()

    # Fase 2: executa análise com streaming
    if st.session_state.processando and st.session_state.pending_input:
        texto = st.session_state.pending_input
        resultado = None
        if agent.ANTHROPIC_KEY and agent.ANTHROPIC_KEY != "cole_sua_chave_aqui":
            cot_slot = st.empty()
            result_slot = st.empty()
            result_slot.markdown(agent._skeleton_card_html(), unsafe_allow_html=True)
            try:
                resultado = agent.analisar(texto, cot_slot=cot_slot)
            except Exception as e:
                print(f"[ERROR] analisar: {e}")
                result_slot.empty()
                st.error("Erro ao processar a análise. Tente novamente.")
        else:
            st.warning("⚠ Chave da API Anthropic não configurada. Defina `ANTHROPIC_API_KEY`.")
        st.session_state.resultado = resultado
        st.session_state.pending_input = None
        st.session_state.processando = False
        st.rerun()

    # Fase 3: exibe resultado estático
    elif st.session_state.resultado:
        r = st.session_state.resultado
        if not isinstance(r, dict) or "nivel" not in r:
            st.error("Resposta inválida do agente. Tente novamente.")
            st.stop()
        if r.get("pensamento"):
            steps_html = "".join(agent._cot_step(p) for p in r["pensamento"])
            st.markdown(
                agent._cot_header(st.session_state.get("last_input", "")) + steps_html + agent._COT_FTR,
                unsafe_allow_html=True,
            )
        st.markdown(ui.render_result_card(r), unsafe_allow_html=True)

    elif not st.session_state.processando:
        st.markdown(ui.render_empty_state(), unsafe_allow_html=True)

# ── Rodapé ────────────────────────────────────────────────────────────────────
ui.render_footer()

# Auto-refresh durante cooldown
if not st.session_state.processando:
    _cd_now = time.time()
    _cd_sess = [t for t in st.session_state.request_times if _cd_now - t < 3600]
    if _cd_sess and (_cd_now - _cd_sess[-1]) < _COOLDOWN_S:
        time.sleep(1)
        st.rerun()
