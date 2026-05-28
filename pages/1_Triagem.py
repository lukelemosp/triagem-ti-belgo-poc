"""
Página de triagem — demo interativo do agente.
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
    "Não estou conseguindo lançar nota fiscal no SAP — autorização negada...",
    "SAP está lento demais no setor de compras, travando a cada 2 minutos...",
    "Preciso de acesso ao módulo PP do SAP para acompanhar ordens de produção...",
    "A impressão de etiquetas via SAP parou de funcionar na linha 3...",
    "Erro ao executar a transação ME23N — 'Object not found' no SAP...",
    "Não consigo fazer login no SAP Logon — tela fica carregando indefinidamente...",
    "Relatório de estoque MB52 no SAP está gerando valores incorretos...",
    "Não consigo acessar o Salesforce — tela de login retorna erro 401...",
    "Dados de oportunidades do Salesforce não estão sincronizando com o SAP...",
    "Preciso de acesso de edição nos registros de conta do Salesforce para meu perfil...",
    "Fluxo de aprovação de pedido no Salesforce está rejeitando automaticamente...",
    "Relatórios de pipeline do Salesforce estão gerando dados duplicados...",
    "Sem conexão de rede no ramal B2, todos os computadores do setor offline...",
    "VPN não conecta fora do escritório — erro 'Network timeout' após atualização...",
    "Wi-Fi do escritório cai constantemente, especialmente na sala de reunião 204...",
    "Switch do andar 3 parece ter reiniciado sozinho, setor inteiro sem rede...",
    "Link de internet da fábrica caiu — produção parada aguardando reconexão...",
    "Monitor do computador ficou com tela preta e não responde...",
    "Teclado e mouse USB pararam de funcionar após reiniciar o Windows...",
    "Bateria do notebook não carrega mais — fica em 4% mesmo plugado na tomada...",
    "Headset não funciona no Teams — áudio saindo pelo alto-falante do computador...",
    "Senha expirou e o sistema não permite criar nova — link de redefinição falha...",
    "Conta do AD bloqueada por excesso de tentativas — preciso de reset urgente...",
    "VPN não conecta fora do escritório — erro 'Network timeout' após atualização...",
    "E-mail corporativo não sincroniza no celular após troca de senha...",
    "Teams trava ao iniciar videoconferência com mais de 5 participantes...",
    "Caixa de entrada do Outlook cheia — não consigo receber novos e-mails...",
    "Impressora do setor de expedição offline — fila há 3 horas sem imprimir...",
    "Impressora HP 4525 não conecta na rede após ser movida de sala...",
    "Sistema de supervisão SCADA perdeu comunicação com CLP da linha 4...",
    "Computador de controle da prensa 7 não inicializa o software de automação...",
    "Rede OT da fábrica sem comunicação com servidor de historiador de dados...",
    "Antivírus bloqueando instalação de software homologado pela TI — como liberar...",
    "Computador com Windows 7 precisa ser atualizado — aviso de suporte encerrado...",
    "Backup noturno falhou — log indica espaço insuficiente no servidor...",
    "Power BI não atualiza dados automaticamente — relatório de vendas desatualizado...",
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
st.markdown(ui.header_html(), unsafe_allow_html=True)

# ── Modal de arquitetura ──────────────────────────────────────────────────────
@st.dialog("📐 Arquitetura da Solução", width="large")
def _modal_arquitetura():
    st.markdown("""
    <div style="border-bottom:3px solid #ED1C24;padding-bottom:10px;margin-bottom:24px;">
      <p style="margin:0;color:#5A7E88;font-size:0.9rem;font-family:'Montserrat',sans-serif;">
        Agente de Triagem N1/N2 · Belgo Arames, 2026
      </p>
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.markdown("""
        <div style="margin-bottom:28px;">
          <div style="font-size:0.72rem;font-weight:700;color:#003B4A;text-transform:uppercase;
               letter-spacing:0.08em;font-family:'Montserrat',sans-serif;margin-bottom:8px;">O Problema</div>
          <p style="font-size:0.93rem;color:#1A2E33;line-height:1.65;font-family:'Montserrat',sans-serif;">
            A equipe de TI da Belgo Arames recebe chamados por múltiplos canais. Todos convergem no
            ServiceNow, mas a <strong>triagem manual</strong> entre N1 e N2 consome tempo do analista,
            atrasa o SLA e gera escalonamentos desnecessários.
          </p>
        </div>
        <div style="margin-bottom:28px;">
          <div style="font-size:0.72rem;font-weight:700;color:#003B4A;text-transform:uppercase;
               letter-spacing:0.08em;font-family:'Montserrat',sans-serif;margin-bottom:8px;">A Solução</div>
          <p style="font-size:0.93rem;color:#1A2E33;line-height:1.65;font-family:'Montserrat',sans-serif;">
            Um <strong>agente de IA</strong> que lê a descrição do chamado assim que ele é aberto,
            classifica automaticamente como N1 ou N2 e sugere a resolução — tudo em menos de 3 segundos.
          </p>
        </div>
        <div>
          <div style="font-size:0.72rem;font-weight:700;color:#003B4A;text-transform:uppercase;
               letter-spacing:0.08em;font-family:'Montserrat',sans-serif;margin-bottom:8px;">Stack Técnica</div>
          <table style="width:100%;border-collapse:collapse;font-family:'Montserrat',sans-serif;font-size:0.85rem;">
            <thead><tr style="background:#003B4A;color:white;">
              <th style="padding:8px 12px;text-align:left;">Componente</th>
              <th style="padding:8px 12px;text-align:left;">Tecnologia</th>
              <th style="padding:8px 12px;text-align:left;">Por quê</th>
            </tr></thead>
            <tbody>
              <tr style="background:#F7FAFB;"><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;font-weight:600;color:#003B4A;">LLM</td><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;">Claude Sonnet 4.6</td><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;color:#5A7E88;">Melhor reasoning em português; custo previsível</td></tr>
              <tr><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;font-weight:600;color:#003B4A;">Banco</td><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;">SQLite + WAL</td><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;color:#5A7E88;">Zero infra; acesso concorrente com Streamlit e MCP</td></tr>
              <tr style="background:#F7FAFB;"><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;font-weight:600;color:#003B4A;">MCP</td><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;">FastMCP (stdio)</td><td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;color:#5A7E88;">Skill exposta no Catálogo MCP Belgo</td></tr>
              <tr><td style="padding:8px 12px;font-weight:600;color:#003B4A;">Prompts</td><td style="padding:8px 12px;">Azure DevOps (Git)</td><td style="padding:8px 12px;color:#5A7E88;">Rastreabilidade; revisão por Pull Request</td></tr>
            </tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("Conheça o prompt deste Agente", expanded=False):
            st.code(agent._SYSTEM_PROMPT, language=None)
    with c2:
        st.markdown('<div class="result-label" style="margin-bottom:10px;">Fluxo da Solução</div>', unsafe_allow_html=True)
        st.code("""\
  Usuário abre chamado
         │
         ▼
  ┌─────────────────────┐
  │     ServiceNow      │
  └──────────┬──────────┘
             │ webhook
             ▼
  ┌─────────────────────┐
  │   Azure Function    │
  └──────────┬──────────┘
             │ MCP Tool
             ▼
  ┌─────────────────────┐
  │   Agente Claude     │
  │  · classifica N1/N2 │
  │  · gera sugestão    │
  │  · auto-resolve     │
  └──────────┬──────────┘
             │ resultado
             ▼
  ┌─────────────────────┐
  │     ServiceNow      │
  │  (atualiza ticket)  │
  └─────────────────────┘\
""", language=None)
        st.markdown('<div class="result-label" style="margin:20px 0 10px;">Métricas de Sucesso (30 dias)</div>', unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        with m1:
            st.markdown("""<div style="background:#E6F4F1;border-left:3px solid #003B4A;padding:12px 14px;border-radius:0 8px 8px 0;"><div style="font-size:1.5rem;font-weight:800;color:#003B4A;font-family:'Montserrat',sans-serif;">≥ 80%</div><div style="font-size:0.78rem;color:#3D5A62;font-family:'Montserrat',sans-serif;">Acurácia N1/N2</div></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown("""<div style="background:#E6F4F1;border-left:3px solid #003B4A;padding:12px 14px;border-radius:0 8px 8px 0;"><div style="font-size:1.5rem;font-weight:800;color:#003B4A;font-family:'Montserrat',sans-serif;">&lt; R$ 0,50</div><div style="font-size:0.78rem;color:#3D5A62;font-family:'Montserrat',sans-serif;">Custo/chamado</div></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown("""<div style="background:#FEE8E8;border-left:3px solid #ED1C24;padding:12px 14px;border-radius:0 8px 8px 0;margin-top:8px;"><div style="font-size:1.5rem;font-weight:800;color:#ED1C24;font-family:'Montserrat',sans-serif;">&lt; 3s</div><div style="font-size:0.78rem;color:#3D5A62;font-family:'Montserrat',sans-serif;">Tempo de resposta</div></div>""", unsafe_allow_html=True)
        with m4:
            st.markdown("""<div style="background:#FEE8E8;border-left:3px solid #ED1C24;padding:12px 14px;border-radius:0 8px 8px 0;margin-top:8px;"><div style="font-size:1.5rem;font-weight:800;color:#ED1C24;font-family:'Montserrat',sans-serif;">100%</div><div style="font-size:0.78rem;color:#3D5A62;font-family:'Montserrat',sans-serif;">Prompts em Git</div></div>""", unsafe_allow_html=True)
    st.markdown("""
<div style="border-top:1px solid #D6E2E5;margin-top:24px;padding-top:16px;text-align:center;">
  <a href="https://github.com/lukelemosp/triagem-ti-belgo-poc" target="_blank"
     style="display:inline-flex;align-items:center;gap:8px;text-decoration:none;
            color:#003B4A;font-size:0.82rem;font-family:'Montserrat',sans-serif;font-weight:600;">
    Conheça o código-fonte no GitHub
  </a>
</div>
""", unsafe_allow_html=True)


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
            st.warning(f"Descrição muito longa — limite de {_MAX_INPUT_LEN} caracteres.")
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
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<hr style="border:none;border-top:1px solid #D6E2E5;margin:0 0 10px;">', unsafe_allow_html=True)
ft_l, ft_r = st.columns([2, 1])
with ft_l:
    st.markdown("""
    <span style="background:#FEE8E8;border:1px solid #ED1C24;color:#B8000A;border-radius:4px;
        padding:3px 10px;font-size:0.72rem;font-weight:700;font-family:'Montserrat',sans-serif;
        letter-spacing:0.06em;text-transform:uppercase;">⚠ Uso Interno — Não Divulgar</span>
    """, unsafe_allow_html=True)
with ft_r:
    c_txt, c_btn = st.columns([5, 1], gap="small")
    with c_txt:
        st.markdown("""
        <div style="text-align:right;padding-top:6px;">
            <span style="font-size:0.78rem;color:#7A9EA6;font-family:'Montserrat',sans-serif;">
                <strong style="color:#003B4A;">Lucas Lemos</strong> · Belgo Arames, 2026
            </span>
        </div>""", unsafe_allow_html=True)
    with c_btn:
        if st.button("📐", key="btn_arq", help="Ver arquitetura da solução"):
            _modal_arquitetura()

# Auto-refresh durante cooldown
if not st.session_state.processando:
    _cd_now = time.time()
    _cd_sess = [t for t in st.session_state.request_times if _cd_now - t < 3600]
    if _cd_sess and (_cd_now - _cd_sess[-1]) < _COOLDOWN_S:
        time.sleep(1)
        st.rerun()
