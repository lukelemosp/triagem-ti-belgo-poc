import streamlit as st
import time
import os
import json
import re
import html as _html
import threading

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Dois níveis de controle para evitar flood na API durante a apresentação:
# 1. Cooldown por sessão: impede que um único usuário dispare múltiplas
#    requisições antes da anterior terminar (mínimo 12s entre chamadas).
# 2. Teto global/hora: limita o total de chamadas em todas as sessões abertas
#    simultaneamente no mesmo servidor (ex.: avaliadores abrindo em paralelo).
_COOLDOWN_S       = 12   # segundos mínimos entre requisições na mesma sessão
_MAX_GLOBAL_HOUR  = 40   # requisições máximas por hora em todas as sessões

@st.cache_resource
def _global_rate_store() -> dict:
    # cache_resource garante que o mesmo dict (e o mesmo Lock) é compartilhado
    # entre todas as sessões Streamlit rodando no mesmo processo.
    return {"times": [], "lock": threading.Lock()}

def _check_rate_limit() -> tuple[bool, str | None]:
    # Verifica ambos os limites SEM registrar a requisição — o registro só
    # acontece em _record_request(), após a validação passar. Isso evita
    # contabilizar chamadas bloqueadas.
    now = time.time()
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
            return False, f"🚫 Limite de uso atingido ({_MAX_GLOBAL_HOUR} req/hora). Disponível em {m}min {s}s."

    return True, None

def _record_request():
    # Registra o timestamp da requisição nas duas camadas (sessão e global).
    # Chamado somente após _check_rate_limit() retornar True.
    now = time.time()
    st.session_state.request_times.append(now)
    store = _global_rate_store()
    with store["lock"]:
        store["times"].append(now)

# ── Constantes / helpers de CoT ──────────────────────────────────────────────
def _cot_header(input_text: str = "") -> str:
    # Gera o cabeçalho do painel de raciocínio incluindo o input do usuário
    # como subtítulo, truncado para não ultrapassar a largura do painel.
    subtitle = ""
    if input_text:
        label = input_text if len(input_text) <= 80 else input_text[:77] + "…"
        subtitle = f'<div class="cot-subtitle">"{_html.escape(label)}"</div>'
    return (
        '<div class="cot-container">'
        '<div class="cot-title">Raciocínio do Agente</div>'
        f'{subtitle}'
        '<div class="cot-steps">'
    )

_COT_FTR = '</div></div>'
_COT_THINKING = (
    '<div class="cot-step">'
    '<div class="cot-dot" style="opacity:0.25;background:#9BB5BC;"></div>'
    '<div>'
    '<div class="cot-label" style="color:#9BB5BC;">Analisando chamado</div>'
    '<div class="cot-thinking"><span></span><span></span><span></span></div>'
    '</div></div>'
)

def _cot_step(p: dict, animated: bool = False) -> str:
    dot_cls = "cot-dot cot-dot-final" if p.get("final") else "cot-dot"
    style = ' style="animation:cot-appear 0.4s cubic-bezier(0.22,1,0.36,1);"' if animated else ""
    label = _html.escape(str(p.get("label", "")))
    texto = _html.escape(str(p.get("texto", "")))
    return (
        f'<div class="cot-step"{style}>'
        f'<div class="{dot_cls}"></div>'
        f'<div class="cot-label">{label}</div>'
        f'<div class="cot-text">{texto}</div>'
        f'</div>'
    )

def _extract_steps(text: str) -> list:
    # O modelo gera JSON via streaming, então o texto chega incompleto e cresce
    # token a token. Esta função extrai apenas os objetos de "pensamento" que já
    # estão completos (fechados com "}") dentro do array parcial.
    # Estratégia: rastrear profundidade de chaves para detectar objetos completos
    # sem depender de um parser JSON que quebraria em JSON incompleto.
    m = re.search(r'"pensamento"\s*:\s*\[', text)
    if not m:
        return []
    arr = text[m.end():]
    steps, depth, start = [], 0, None
    for i, ch in enumerate(arr):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                # Confirma que o objeto é seguido por "," ou "]" — ou seja,
                # está realmente completo e não truncado no meio do stream.
                rest = arr[i + 1:].lstrip()
                if rest and rest[0] in (",", "]"):
                    try:
                        steps.append(json.loads(arr[start:i + 1]))
                    except Exception:
                        pass
                start = None
    return steps

def _analisar_com_api(descricao: str, cot_slot=None) -> dict:
    # Núcleo do agente: chama a API Anthropic com streaming e exibe o
    # raciocínio passo a passo (Chain of Thought) em tempo real enquanto
    # o modelo ainda está gerando a resposta.
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    # Prompt de sistema versionado — este é o "prompt como código" que ficará
    # no Azure DevOps. Qualquer alteração no comportamento do agente (ex.: incluir
    # um novo sistema crítico da Belgo) deve passar por Pull Request aqui.
    # "pensamento" vem PRIMEIRO no JSON para que os passos apareçam durante
    # o streaming, antes de nivel/confianca/sugestao estarem completos.
    system = """\
Você é um agente de triagem de chamados de TI da Belgo Arames, empresa siderúrgica brasileira.

Classifique o chamado como N1 (helpdesk resolve) ou N2 (requer especialista) e sugira a resolução.

N1 — problemas individuais, senha/acesso, Office/hardware simples, solicitações de provisionamento de rotina.
N2 — sistemas críticos indisponíveis, múltiplos usuários afetados, infraestrutura de produção/planta, redes OT/IT, servidores SAP em produção.
FORA_DE_ESCOPO — qualquer coisa que não seja um chamado de TI legítimo (ex.: código de programação, questões pessoais, perguntas gerais, tarefas não relacionadas a suporte de TI).

Responda APENAS com JSON válido, sem markdown. Coloque "pensamento" PRIMEIRO para que
os passos apareçam em tempo real. Formato:
{
  "pensamento": [
    {"label": "label do passo", "texto": "explicação do raciocínio"},
    {"label": "Decisão → N1", "texto": "justificativa final", "final": true}
  ],
  "nivel": "N1",
  "confianca": 94,
  "motivo_confianca": "Frase curta (1-2 linhas) explicando objetivamente por que a confiança é esse valor — ex.: quais características do chamado tornaram a classificação clara ou ambígua.",
  "tempo": "15 – 30 min",
  "sugestao": "Cada etapa em linha separada, terminada por ponto e vírgula; o step anterior ao último deve ser encerrado com '; e'; o último step termina com ponto final. Exemplo:\nVerificar se o cabo está conectado;\nReiniciar a impressora;\ne confirmar na fila de impressão do Windows.",
  "acao": "texto curto da ação recomendada"
}

Para chamados FORA_DE_ESCOPO, use: "nivel": "FORA_DE_ESCOPO", "tempo": "N/A", "confianca": 99, "motivo_confianca": "explicação"."""

    # Exibe o indicador de "pensando..." antes do primeiro token chegar.
    _hdr = _cot_header(descricao)
    if cot_slot:
        cot_slot.markdown(_hdr + _COT_THINKING + _COT_FTR, unsafe_allow_html=True)

    full_text = ""
    shown: list = []   # passos do CoT já renderizados na tela
    steps_html = ""    # HTML acumulado dos passos renderizados

    # Streaming: cada delta é um fragmento de texto. Acumulamos em full_text
    # e tentamos extrair passos de pensamento completos a cada token recebido.
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": descricao}],
    ) as stream:
        for delta in stream.text_stream:
            full_text += delta
            if not cot_slot:
                continue
            current = _extract_steps(full_text)
            # Renderiza somente os passos novos (não os que já estão na tela).
            while len(current) > len(shown):
                p = current[len(shown)]
                # Antes do passo final, exibe o spinner "pensando..." para
                # indicar que ainda há processamento em curso.
                if p.get("final") and steps_html:
                    cot_slot.markdown(_hdr + steps_html + _COT_THINKING + _COT_FTR, unsafe_allow_html=True)
                    time.sleep(0.3)
                cot_slot.markdown(_hdr + steps_html + _cot_step(p, animated=True) + _COT_FTR, unsafe_allow_html=True)
                steps_html += _cot_step(p)
                shown.append(p)

    # Remove possível wrapper ```json ``` que o modelo às vezes adiciona
    # mesmo sendo instruído a não usar markdown.
    raw = full_text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw.strip())

st.set_page_config(
    page_title="Agente de Triagem TI — Belgo",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* Fonte Montserrat — identidade Belgo */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Montserrat', 'Segoe UI', sans-serif; }

    /* ── Paleta Belgo ──────────────────────────────────────────────────────
       #003B4A  teal escuro (primária)
       #ED1C24  vermelho    (acento)
       #FDB913  dourado     (gradiente decorativo)
       #F37021  laranja     (gradiente decorativo)
    ─────────────────────────────────────────────────────────────────────── */

    /* Header */
    .header-box {
        background: #003B4A;
        padding: 0;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 28px;
        box-shadow: 0 4px 16px rgba(0,59,74,0.18);
    }
    .header-accent {
        height: 5px;
        background: linear-gradient(90deg, #ED1C24 0%, #F37021 50%, #FDB913 100%);
    }
    .header-content {
        padding: 20px 28px 22px 28px;
        color: white;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .header-icon {
        font-size: 2.2rem;
        line-height: 1;
    }
    .header-text h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: #FFFFFF;
    }
    .header-text p {
        margin: 3px 0 0 0;
        font-size: 0.85rem;
        color: rgba(255,255,255,0.72);
        font-weight: 400;
    }
    .header-tag {
        margin-left: auto;
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.75rem;
        font-weight: 600;
        color: rgba(255,255,255,0.85);
        white-space: nowrap;
    }

    /* Botão de arquitetura no rodapé */
    div[data-testid="stButton"][data-key="btn_arq"] > button {
        background: #E6F4F1 !important;
        border: 1.5px solid #A8C8D0 !important;
        color: #003B4A !important;
        font-size: 1rem !important;
        padding: 3px 10px !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        width: auto !important;
        line-height: 1.3 !important;
        transition: background 0.18s, color 0.18s !important;
    }
    div[data-testid="stButton"][data-key="btn_arq"] > button:hover {
        background: #003B4A !important;
        color: #FFFFFF !important;
        border-color: #003B4A !important;
    }

    /* Botão primário "Analisar" */
    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stBaseButton-primary"] {
        background: #ED1C24 !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        font-family: 'Montserrat', sans-serif !important;
        border-radius: 8px !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover,
    div[data-testid="stBaseButton-primary"]:hover {
        background: #C8151C !important;
    }

    /* Badge N1 */
    .badge-n1 {
        display: inline-block;
        background: #E6F4F1;
        color: #003B4A;
        border: 2px solid #003B4A;
        border-radius: 8px;
        padding: 6px 20px;
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 12px;
        font-family: 'Montserrat', sans-serif;
        letter-spacing: 0.02em;
    }
    /* Badge N2 */
    .badge-n2 {
        display: inline-block;
        background: #FEE8E8;
        color: #ED1C24;
        border: 2px solid #ED1C24;
        border-radius: 8px;
        padding: 6px 20px;
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 12px;
        font-family: 'Montserrat', sans-serif;
        letter-spacing: 0.02em;
    }

    /* Card de resultado */
    .result-card {
        background: #FAFBFC;
        border: 1px solid #D6E2E5;
        border-top: 3px solid #003B4A;
        border-radius: 12px;
        padding: 24px 28px;
        animation: fadeIn 0.35s ease;
    }
    .result-label {
        font-size: 0.72rem;
        font-weight: 700;
        color: #003B4A;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
        font-family: 'Montserrat', sans-serif;
    }
    .result-value {
        font-size: 0.95rem;
        color: #1A2E33;
        margin-bottom: 18px;
        line-height: 1.55;
    }
    .acao-n1 {
        background: #E6F4F1;
        border-left: 4px solid #003B4A;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        color: #003B4A;
        font-size: 0.9rem;
        font-weight: 600;
        font-family: 'Montserrat', sans-serif;
    }
    .acao-n2 {
        background: #FEE8E8;
        border-left: 4px solid #ED1C24;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        color: #B8000A;
        font-size: 0.9rem;
        font-weight: 600;
        font-family: 'Montserrat', sans-serif;
    }

    /* Tooltip de confiança */
    .conf-tooltip {
        position: relative;
        display: inline-flex;
        align-items: center;
        cursor: help;
    }
    .conf-tooltip-icon {
        color: #7A9EA6;
        font-size: 0.8rem;
        margin-left: 5px;
        line-height: 1;
    }
    .conf-tooltip-box {
        visibility: hidden;
        opacity: 0;
        width: 260px;
        background: #1A2E33;
        color: #E8F0F2;
        text-align: left;
        border-radius: 8px;
        padding: 10px 14px;
        position: absolute;
        z-index: 9999;
        bottom: 130%;
        right: 0;
        font-size: 0.78rem;
        line-height: 1.6;
        font-family: 'Montserrat', sans-serif;
        box-shadow: 0 4px 16px rgba(0,0,0,0.35);
        transition: opacity 0.2s ease;
        pointer-events: none;
        white-space: normal;
    }
    .conf-tooltip:hover .conf-tooltip-box { visibility: visible; opacity: 1; }

    /* Barra de confiança */
    .conf-bar-bg {
        background: #D6E2E5;
        border-radius: 999px;
        height: 10px;
        margin-top: 6px;
    }
    .conf-bar-fill-n1 { background: #003B4A; height: 10px; border-radius: 999px; }
    .conf-bar-fill-n2 { background: #ED1C24; height: 10px; border-radius: 999px; }

    /* Chain of thought */
    .cot-container {
        margin-top: 16px;
        margin-bottom: 28px;
        background: #F7FAFB;
        border: 1px solid #D6E2E5;
        border-radius: 12px;
        padding: 20px 24px;
        animation: fadeIn 0.35s ease;
    }
    .cot-title {
        font-size: 0.78rem;
        font-weight: 700;
        color: #003B4A;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
        font-family: 'Montserrat', sans-serif;
    }
    .cot-subtitle {
        font-size: 0.78rem;
        color: #5A7E88;
        font-style: italic;
        font-family: 'Montserrat', sans-serif;
        margin-bottom: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .cot-steps { position: relative; padding-left: 28px; }
    .cot-steps::before {
        content: '';
        position: absolute;
        left: 7px;
        top: 8px;
        bottom: 8px;
        width: 2px;
        background: #C5D8DC;
    }
    .cot-step { position: relative; margin-bottom: 14px; }
    .cot-step:last-child { margin-bottom: 0; }
    .cot-dot {
        position: absolute;
        left: -24px;
        top: 4px;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #003B4A;
        border: 2px solid #fff;
        box-shadow: 0 0 0 2px #C5D8DC;
    }
    .cot-dot-final { background: #ED1C24; box-shadow: 0 0 0 2px #F5C0C2; }

    /* Fade-in ao exibir novos resultados */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Animações do chain of thought */
    @keyframes cot-appear {
        from { opacity: 0; transform: translateX(-12px); }
        to   { opacity: 1; transform: translateX(0); }
    }
    @keyframes cot-dot-pulse {
        0%, 80%, 100% { opacity: 0.2; transform: scale(0.7); }
        40%           { opacity: 1;   transform: scale(1.1); }
    }
    .cot-thinking {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        margin-top: 5px;
    }
    .cot-thinking span {
        display: inline-block;
        width: 7px; height: 7px;
        background: #003B4A;
        border-radius: 50%;
    }
    .cot-thinking span:nth-child(1) { animation: cot-dot-pulse 1.4s ease-in-out infinite 0.0s; }
    .cot-thinking span:nth-child(2) { animation: cot-dot-pulse 1.4s ease-in-out infinite 0.2s; }
    .cot-thinking span:nth-child(3) { animation: cot-dot-pulse 1.4s ease-in-out infinite 0.4s; }

    .cot-label {
        font-size: 0.8rem;
        font-weight: 700;
        color: #003B4A;
        font-family: 'Montserrat', sans-serif;
    }
    .cot-text {
        font-size: 0.83rem;
        color: #3D5A62;
        line-height: 1.5;
        margin-top: 1px;
        font-family: 'Montserrat', sans-serif;
    }

    /* Oculta elementos Streamlit */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Modal de Arquitetura ──────────────────────────────────────────────────────
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
               letter-spacing:0.08em;font-family:'Montserrat',sans-serif;margin-bottom:8px;">
            O Problema
          </div>
          <p style="font-size:0.93rem;color:#1A2E33;line-height:1.65;font-family:'Montserrat',sans-serif;">
            A equipe de TI da Belgo Arames recebe chamados por múltiplos canais (portal I Am Smart,
            Teams, telefone). Todos convergem no ServiceNow, mas a <strong>triagem manual</strong>
            entre N1 (helpdesk) e N2 (especialista) consome tempo do analista, atrasa o SLA e gera
            escalonamentos desnecessários.
          </p>
        </div>

        <div style="margin-bottom:28px;">
          <div style="font-size:0.72rem;font-weight:700;color:#003B4A;text-transform:uppercase;
               letter-spacing:0.08em;font-family:'Montserrat',sans-serif;margin-bottom:8px;">
            A Solução
          </div>
          <p style="font-size:0.93rem;color:#1A2E33;line-height:1.65;font-family:'Montserrat',sans-serif;">
            Um <strong>agente de IA</strong> que lê a descrição do chamado assim que ele é aberto,
            classifica automaticamente como N1 ou N2, sugere a resolução e registra de volta no ticket
            — tudo em menos de 3 segundos, sem intervenção humana na triagem.
          </p>
        </div>

        <div>
          <div style="font-size:0.72rem;font-weight:700;color:#003B4A;text-transform:uppercase;
               letter-spacing:0.08em;font-family:'Montserrat',sans-serif;margin-bottom:8px;">
            Stack Técnica
          </div>
          <table style="width:100%;border-collapse:collapse;font-family:'Montserrat',sans-serif;font-size:0.85rem;">
            <thead>
              <tr style="background:#003B4A;color:white;">
                <th style="padding:8px 12px;text-align:left;border-radius:6px 0 0 0;">Componente</th>
                <th style="padding:8px 12px;text-align:left;">Tecnologia</th>
                <th style="padding:8px 12px;text-align:left;border-radius:0 6px 0 0;">Por quê</th>
              </tr>
            </thead>
            <tbody>
              <tr style="background:#F7FAFB;">
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;font-weight:600;color:#003B4A;">LLM</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;">Claude (Anthropic)</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;color:#5A7E88;">Melhor reasoning em português; custo previsível por token</td>
              </tr>
              <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;font-weight:600;color:#003B4A;">Orquestração</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;">Python + SDK Anthropic</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;color:#5A7E88;">Controle total do prompt; versionamento no Azure DevOps</td>
              </tr>
              <tr style="background:#F7FAFB;">
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;font-weight:600;color:#003B4A;">Hospedagem</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;">Azure Functions</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;color:#5A7E88;">Serverless; integra com stack Azure já existente na Belgo</td>
              </tr>
              <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;font-weight:600;color:#003B4A;">ITSM</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;">ServiceNow REST API</td>
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;color:#5A7E88;">Sistema já adotado; leitura e escrita de tickets via webhook</td>
              </tr>
              <tr style="background:#F7FAFB;">
                <td style="padding:8px 12px;border-bottom:1px solid #E2EEF0;font-weight:600;color:#003B4A;">Prompts</td>
                <td style="padding:8px 12px;">Azure DevOps (Git)</td>
                <td style="padding:8px 12px;color:#5A7E88;">Rastreabilidade; rollback; revisão por Pull Request no ADO</td>
              </tr>
              <tr>
                <td style="padding:8px 12px;font-weight:600;color:#003B4A;">Catálogo</td>
                <td style="padding:8px 12px;">MCP Server (Belgo)</td>
                <td style="padding:8px 12px;color:#5A7E88;">Skill exposta via MCP — primeira entrada do Catálogo MCP Belgo no ADO</td>
              </tr>
            </tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="result-label" style="margin-bottom:10px;">Fluxo da Solução</div>',
                    unsafe_allow_html=True)
        st.code("""\
  Usuário abre chamado
  (portal / Teams / telefone)
         │
         ▼
  ┌─────────────────────┐
  │     ServiceNow      │  ← todos os canais convergem
  │  (Business Rule)    │
  └──────────┬──────────┘
             │ webhook (novo ticket)
             ▼
  ┌─────────────────────┐
  │   Azure Function    │  ← serverless, custo ~R$0/mês ocioso
  └──────────┬──────────┘
             │ chamada API
             ▼
  ┌─────────────────────┐
  │   Agente Claude     │
  │  · lê descrição     │
  │  · aplica prompt    │
  │    versionado       │
  │  · classifica N1/N2 │
  │  · gera sugestão    │
  └──────────┬──────────┘
             │ resultado
             ▼
  ┌─────────────────────┐
  │     ServiceNow      │  ← escreve: nível + sugestão
  │  (atualiza ticket)  │    no campo do ticket
  └─────────────────────┘
             │
             ▼
  Analista vê ticket já
  classificado e com
  sugestão de resolução\
""", language=None)

        st.markdown('<div class="result-label" style="margin:20px 0 10px;">Métricas de Sucesso (30 dias)</div>',
                    unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        m3, m4 = st.columns(2)
        with m1:
            st.markdown("""<div style="background:#E6F4F1;border-left:3px solid #003B4A;
                padding:12px 14px;border-radius:0 8px 8px 0;">
                <div style="font-size:1.5rem;font-weight:800;color:#003B4A;font-family:'Montserrat',sans-serif;">≥ 80%</div>
                <div style="font-size:0.78rem;color:#3D5A62;font-family:'Montserrat',sans-serif;">Acurácia N1/N2</div>
                </div>""", unsafe_allow_html=True)
        with m2:
            st.markdown("""<div style="background:#E6F4F1;border-left:3px solid #003B4A;
                padding:12px 14px;border-radius:0 8px 8px 0;">
                <div style="font-size:1.5rem;font-weight:800;color:#003B4A;font-family:'Montserrat',sans-serif;">&lt; R$ 0,50</div>
                <div style="font-size:0.78rem;color:#3D5A62;font-family:'Montserrat',sans-serif;">Custo/chamado</div>
                </div>""", unsafe_allow_html=True)
        with m3:
            st.markdown("""<div style="background:#FEE8E8;border-left:3px solid #ED1C24;
                padding:12px 14px;border-radius:0 8px 8px 0;margin-top:8px;">
                <div style="font-size:1.5rem;font-weight:800;color:#ED1C24;font-family:'Montserrat',sans-serif;">&lt; 3s</div>
                <div style="font-size:0.78rem;color:#3D5A62;font-family:'Montserrat',sans-serif;">Tempo de resposta</div>
                </div>""", unsafe_allow_html=True)
        with m4:
            st.markdown("""<div style="background:#FEE8E8;border-left:3px solid #ED1C24;
                padding:12px 14px;border-radius:0 8px 8px 0;margin-top:8px;">
                <div style="font-size:1.5rem;font-weight:800;color:#ED1C24;font-family:'Montserrat',sans-serif;">100%</div>
                <div style="font-size:0.78rem;color:#3D5A62;font-family:'Montserrat',sans-serif;">Prompts em Git</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<div class="result-label" style="margin:22px 0 10px;">Decisões de Design</div>',
                    unsafe_allow_html=True)
        st.markdown("""
**Shadow mode primeiro** — O agente classifica, mas o analista valida manualmente nos primeiros 30 dias.
Garante confiança antes de qualquer automação completa.

**Sem fine-tuning** — Prompt engineering com exemplos históricos da Belgo (few-shot).
Mais rápido de ajustar; zero custo de treinamento.

**Prompts como código** — Toda mudança no comportamento do agente passa por Pull Request no Azure DevOps.
Rastreabilidade total e rollback em segundos.

**Exposição via MCP** — Esta skill será publicada no Catálogo MCP da Belgo no Azure DevOps, com dono, SLA e custo/mês documentados — primeira entrada do catálogo.
""")


# ── Estado da sessão ────────────────────────────────────────────────────────
# O Streamlit re-executa o script inteiro a cada interação do usuário.
# session_state é o único lugar que persiste valores entre re-runs.
# A lógica de análise é dividida em 3 fases separadas por st.rerun() para
# garantir que o spinner/CoT apareça antes do resultado final:
#   Fase 1 (captura): usuário clica → enfileira o texto em pending_input e reroda
#   Fase 2 (executa): pending_input presente → chama a API com streaming e reroda
#   Fase 3 (exibe):   resultado presente → renderiza o card de resultado estático
if "resultado" not in st.session_state:
    st.session_state.resultado = None
if "processando" not in st.session_state:
    st.session_state.processando = False
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None
if "clear_input" not in st.session_state:
    # Sinaliza que o text_area deve ser limpo antes de ser renderizado.
    # É necessário remover a key do session_state ANTES de instanciar o widget,
    # pois o Streamlit não permite alterar o valor de um widget já renderizado.
    st.session_state.clear_input = False
if "request_times" not in st.session_state:
    st.session_state.request_times = []
if "input_key" not in st.session_state:
    # Contador que força um novo elemento DOM no text_area a cada análise,
    # garantindo que o campo apareça vazio após o submit.
    st.session_state.input_key = 0
if "last_input" not in st.session_state:
    st.session_state.last_input = ""

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-box">
  <div class="header-accent"></div>
  <div class="header-content">
    <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQ3IiBoZWlnaHQ9Ijc1IiB2aWV3Qm94PSIwIDAgMTQ3IDc1IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPg0KPGcgY2xpcC1wYXRoPSJ1cmwoI2NsaXAwXzIyMzdfMjQ5KSI+DQo8ZyBjbGlwLXBhdGg9InVybCgjY2xpcDFfMjIzN18yNDkpIj4NCjxnIGNsaXAtcGF0aD0idXJsKCNjbGlwMl8yMjM3XzI0OSkiPg0KPHBhdGggZD0iTTEuNjUwNiA0MC44MTcyQzEuNDQ0NTQgNDAuNDE5NSAwLjAzNDE3OTcgMzUuNzYwNiAwLjAzNDE3OTcgMzYuMjA4VjUwLjQ4OUMwLjAzNDE3OTcgNTIuOTg2NCAyLjAwNDY5IDU1LjA5NjIgNC41MTUzMyA1NS4xNjU4QzcuMTIwMDEgNTUuMjM3MyA5LjI1NjU2IDUzLjE1OTQgOS4yNTY1NiA1MC41ODQ0VjUwLjE4NDdDOS4yNTY1NiA0OS45MDA0IDkuMDk4NTEgNDkuNjM5OSA4Ljg0ODQ1IDQ5LjUwMDdDNS40ODc1OSA0Ny42Mjc2IDMuNDc1MDcgNDQuMzQ0NyAxLjY1MDYgNDAuODE3MloiIGZpbGw9IndoaXRlIi8+DQo8cGF0aCBkPSJNOS4yNTY1MSAxOS4wODY0VjQuNTExMDlDOS4yNTY1MSAxLjk3OTgxIDcuMTkzOTggLTAuMDcyMjY1NiA0LjY0NzMyIC0wLjA3MjI2NTZDMi4xMDA2NiAtMC4wNzIyNjU2IDAuMDM2MTMyOCAxLjk3OTgxIDAuMDM2MTMyOCA0LjUxMTA5VjMzLjkzNEMwLjQyMDIzMiAyNy43OTk3IDMuODgxMTIgMjIuMTkyMyA5LjI1ODUxIDE5LjA4NjRIOS4yNTY1MVoiIGZpbGw9IiNFRDFDMjQiLz4NCjxwYXRoIGQ9Ik0xOC42MTg3IDI1Ljc3OTlDMjMuNzg4IDI1Ljc3OTkgMjcuOTc5MSAyOS45NDU3IDI3Ljk3OTEgMzUuMDgzOEMyNy45NzkxIDM4LjUxMTkgMjYuMTEyNiA0MS41MDQ1IDIzLjMzNzkgNDMuMTE5MUMyOC45NjU0IDQwLjA5ODYgMzIuMDIyMiAzMy41NzI2IDMwLjMzMzcgMjcuMTQ3OUMyOC43MzczIDIxLjA3MzIgMjMuNDc2IDE2LjgxNCAxNy40MTg0IDE2LjYxOTFDMTYuMjU2MSAxNi42OTQ3IDE1LjA4MzggMTYuODc5NiAxMy45MTU1IDE3LjE4MzlDMTIuMjQzMSAxNy42MTczIDEwLjY4NDcgMTguMjY1NiA5LjI1ODMgMTkuMDg4OFYzNS4wODU4QzkuMjU4MyAyOS45NDc3IDEzLjQ0OTQgMjUuNzgxOSAxOC42MTg3IDI1Ljc4MTlWMjUuNzc5OVoiIGZpbGw9InVybCgjcGFpbnQwX3JhZGlhbF8yMjM3XzI0OSkiLz4NCjxwYXRoIGQ9Ik0zNi42Mjc0IDMwLjQwNzZDMzQuMzM0OCAyMS42ODIzIDI2LjE0NDcgMTYuMDQ3MSAxNy40MTY0IDE2LjYxNzhDMjMuNDc0IDE2LjgxMjcgMjguNzM1MyAyMS4wNjk5IDMwLjMzMTggMjcuMTQ2NkMzMi4wMjAyIDMzLjU3MTIgMjguOTY1NCA0MC4wOTkzIDIzLjMzNiA0My4xMTc3QzIxLjk0OTYgNDMuOTIzMSAyMC4zMzkyIDQ0LjM4ODQgMTguNjE2NyA0NC4zODg0QzEzLjQ0NzQgNDQuMzg4NCA5LjI1NjMyIDQwLjIyMjYgOS4yNTYzMiAzNS4wODQ0VjE5LjA4NTRDMy44ODA5NCAyMi4xOTE0IDAuNDE4MDQ1IDI3Ljc5ODggMC4wMzU5NDY1IDMzLjkzMzFDLTAuMDg0MDg0NCAzNS44NDQgMC4wOTM5NjE1IDM3LjgwNjYgMC42MDgwOTQgMzkuNzU5M0MzLjIwNjc2IDQ5LjY0NTggMTMuMzc1NCA1NS41Njc0IDIzLjMyMTkgNTIuOTg0NEMzMy4yNjg1IDUwLjQwMTQgMzkuMjI2IDQwLjI5NDIgMzYuNjI3NCAzMC40MDc2WiIgZmlsbD0idXJsKCNwYWludDFfcmFkaWFsXzIyMzdfMjQ5KSIvPg0KPHBhdGggZD0iTTY4LjcxNzggMzQuMTYxNkM2OC43MTc4IDMyLjAxNDEgNjguNDA3NyAzMC4wNTU1IDY3Ljc4NzYgMjguMjg1N0M2Ny4xNjc0IDI2LjUxNiA2Ni4yNTcyIDI1LjAwNDggNjUuMDU2OSAyMy43NTIxQzYzLjg1NjUgMjIuNDk5NCA2Mi4zOTYyIDIxLjUyNSA2MC42NzU3IDIwLjgyOTFDNTguOTU1MyAyMC4xMzMxIDU2Ljk5NDggMTkuNzg1MiA1NC43OTQyIDE5Ljc4NTJDNTIuODczNyAxOS43ODUyIDUxLjA1MzIgMjAuMDgzNCA0OS4zMzI4IDIwLjY4QzQ3LjYxMjQgMjEuMjc2NSA0Ni4wOTIgMjIuMTMxNSA0NC43NzE2IDIzLjI0NUM0My40NTEzIDI0LjM1ODYgNDIuMzkxIDI1LjY5MDggNDEuNTkwOCAyNy4yNDE4QzQwLjc5MDYgMjguNzkyOCA0MC4zNTA1IDMwLjUyMjcgNDAuMjcwNSAzMi40MzE2QzQwLjIzMDUgMzIuODY5MSA0MC4yMTA0IDMzLjMyNjQgNDAuMjEwNCAzMy44MDM3VjM1Ljk1MTJDNDAuMjEwNCA0MS4wMDE4IDQxLjUxMDggNDQuODE5NiA0NC4xMTE1IDQ3LjQwNDZDNDYuNTkwMSA0OS44NjgzIDUwLjE1OSA1MS4xNTQ4IDU0LjgxNjIgNTEuMjcwMUM1NC44NDIyIDUxLjI3MDEgNTUuMjU0MyA1MS4yNzgxIDU1LjcxNjQgNTEuMjc0MUM2MC4xOTU2IDUxLjE5NDYgNjMuMjM0NCA1MC4zODkyIDY2LjAzMTEgNDcuMDA0OUM2Ny4wNTM0IDQ1Ljc2ODEgNjYuODcxMyA0My45NDA3IDY1LjYyNyA0Mi45MjY2QzY0LjM4MjcgNDEuOTEwNSA2Mi41NDQyIDQyLjA5MTUgNjEuNTIzOSA0My4zMjgzQzYwLjMzNTYgNDQuNzY3OSA1OS40MTU0IDQ1LjQwODIgNTUuNjE4NCA0NS40Nzc4QzU1LjM5NDQgNDUuNDgxOCA1NS4wNTQzIDQ1LjQ4NTggNTQuMzcwMSA0NS40NDJDNTMuMjcxOCA0NS4zNjA1IDUyLjMxMTYgNDUuMTc5NSA1MS40OTU0IDQ0Ljg5OTJDNTAuMzM1MSA0NC41MDE1IDQ5LjQwNDggNDMuOTU0NyA0OC43MDQ2IDQzLjI1ODdDNDguMDA0NSA0Mi41NjI3IDQ3LjUwNDMgNDEuNzI3NiA0Ny4yMDQzIDQwLjc1MzNDNDYuOTA0MiAzOS43Nzg5IDQ2Ljc1NDEgMzguNzE1MSA0Ni43NTQxIDM3LjU2MThINjguNzE5OFYzNC4xNjE2SDY4LjcxNzhaTTQ2Ljc1MjEgMzIuMDE0MUM0Ni43NTIxIDMwLjkwMDUgNDYuOTgyMiAyOS45MzYxIDQ3LjQ0MjMgMjkuMTIwOUM0Ny45MDI0IDI4LjMwNTYgNDguNTEyNiAyNy42Mjk2IDQ5LjI3MjggMjcuMDkyN0M1MC4wMzMgMjYuNTU1OCA1MC44OTMyIDI2LjE2OCA1MS44NTM1IDI1LjkyOTRDNTIuODEzNyAyNS42OTA4IDUzLjc5MzkgMjUuNTcxNSA1NC43OTQyIDI1LjU3MTVDNTUuODc0NSAyNS41NzE1IDU2Ljg2NDcgMjUuNzMwNiA1Ny43NjUgMjYuMDQ4N0M1OC42NjUyIDI2LjM2NjkgNTkuNDQ1NCAyNi44MDQ0IDYwLjEwNTYgMjcuMzYxMUM2MC43NjU3IDI3LjkxNzkgNjEuMjc1OSAyOC41OTM5IDYxLjYzNiAyOS4zODkzQzYxLjk5NjEgMzAuMTg0NyA2Mi4xNzYxIDMxLjA1OTYgNjIuMTc2MSAzMi4wMTQxSDQ2Ljc1MjFaIiBmaWxsPSJ3aGl0ZSIvPg0KPHBhdGggZD0iTTgyLjU2MSA0NS40OTQxQzgwLjA4MDMgNDUuNDk0MSA3OC44NCA0NC4zMDEgNzguODQgNDEuOTE0OVYyMi45MDE0VjExLjU3MzNDNzguODQgOS43Nzk3MiA3Ny4zNzU2IDguMzI2MTcgNzUuNTY5MiA4LjMyNjE3QzczLjc2MjcgOC4zMjYxNyA3Mi4yOTgzIDkuNzc5NzIgNzIuMjk4MyAxMS41NzMzVjE1LjI2MTlWNDMuODgzNUM3Mi4yOTgzIDQ0Ljk1NzIgNzIuNDg4NCA0NS45NTE0IDcyLjg2ODUgNDYuODY2MUM3My4yNDg2IDQ3Ljc4MDggNzMuNzg4NyA0OC41NjYyIDc0LjQ4ODkgNDkuMjIyNEM3NS4xODkxIDQ5Ljg3ODYgNzYuMDA5MyA1MC4zODU3IDc2Ljk0OTUgNTAuNzQzNkM3Ny44ODk4IDUxLjEwMTUgNzguOTIgNTEuMjgwNSA4MC4wNDAzIDUxLjI4MDVDODAuNzIwNSA1MS4yODA1IDgxLjU0MDcgNTEuMjEwOSA4Mi41MDEgNTEuMDcxN0M4My40NjEyIDUwLjkzMjUgODQuMjYxNCA1MC43NjM1IDg0LjkwMTYgNTAuNTY0NlY0NS40OTQxSDgyLjU2MVoiIGZpbGw9IndoaXRlIi8+DQo8cGF0aCBkPSJNMTEzLjI0OSAyMS45MzI3QzExMS40ODkgMjEuMTc3MSAxMDkuNTc4IDIwLjYzMDIgMTA3LjUxOCAyMC4yOTIyQzEwNS40NTcgMTkuOTU0MiAxMDMuNDY3IDE5Ljc4NTIgMTAxLjU0NiAxOS43ODUyQzk2LjU0NDggMTkuNzg1MiA5Mi43MzM4IDIwLjk3ODIgOTAuMTEzMSAyMy4zNjQzQzg3LjQ5MjUgMjUuNzUwNSA4Ni4xODIxIDI5LjQ0OSA4Ni4xODIxIDM0LjQ1OThWMzcuNTYxOEM4Ni4xODIxIDQxLjU3ODUgODcuMjYyNCA0NC43NSA4OS40MjMgNDcuMDc2NUM5MS41ODM1IDQ5LjQwMyA5NC43MjQzIDUwLjU2NjIgOTguODQ1NCA1MC41NjYyQzEwMC40ODYgNTAuNTY2MiAxMDEuOTI2IDUwLjE4ODQgMTAzLjE2NyA0OS40MzI4QzEwNC40MDcgNDguNjc3MiAxMDUuNTg3IDQ3Ljc0MjYgMTA2LjcwNyA0Ni42MjkxVjQ4Ljg5NTlDMTA2LjcwNyA0OC44OTU5IDEwNi43MDcgNDguOTA3OSAxMDYuNzA3IDQ4LjkxNThDMTA2LjcxMSA0OC45MTU4IDEwNi43MTMgNDguOTExOCAxMDYuNzE1IDQ4LjkwOThDMTA2LjY5MyA1Mi42MDY0IDEwNi4yOTUgNTMuNTk2NiAxMDQuNDIxIDU0LjkxMjlDMTAzLjA5MiA1NS44NDU1IDk3LjIzNyA1Ny41OTE0IDkxLjExMTQgNTQuNjQyNUM4OS40ODcgNTMuODYxMSA4Ny41MzQ1IDU0LjUzNTEgODYuNzQ4MyA1Ni4xNDk4Qzg1Ljk2MjEgNTcuNzYyNCA4Ni42NDAyIDU5LjcwNTEgODguMjY0NyA2MC40ODY1QzkxLjY3MzUgNjIuMTI3IDk1LjE2NjQgNjIuNzYxMyA5OC4zMjEzIDYyLjc2MTNDMTAyLjU3IDYyLjc2MTMgMTA2LjIwNyA2MS42MSAxMDguMTkyIDYwLjIxNjFDMTEyLjg2OSA1Ni45MjkyIDExMy4yNDkgNTIuOTk4MSAxMTMuMjQ5IDQ4LjU3MThWNDcuOTIzNlYyMS45MzI3Wk0xMDMuMjU3IDQzLjQwNzhDMTAxLjk5NiA0NC4zMjI1IDEwMC41MjYgNDQuNzc5OSA5OC44NDU0IDQ0Ljc3OTlDOTcuNTI1MSA0NC43Nzk5IDk2LjQ2NDggNDQuNjEwOCA5NS42NjQ2IDQ0LjI3MjhDOTQuODY0NCA0My45MzQ4IDk0LjI0NDIgNDMuNDM3NyA5My44MDQxIDQyLjc4MTVDOTMuMzY0IDQyLjEyNTMgOTMuMDczOSA0MS4zMjk5IDkyLjkzMzkgNDAuMzk1M0M5Mi43OTM4IDM5LjQ2MDggOTIuNzIzOCAzOC4zOTcgOTIuNzIzOCAzNy4yMDM5VjM0LjU3OTJDOTIuNzIzOCAzMi45MDg5IDkyLjg3MzkgMzEuNTA3IDkzLjE3MzkgMzAuMzczNkM5My40NzQgMjkuMjQwMiA5My45NzQxIDI4LjMxNTYgOTQuNjc0MyAyNy41OTk3Qzk1LjM3NDUgMjYuODgzOSA5Ni4yOTQ3IDI2LjM2NjkgOTcuNDM1IDI2LjA0ODdDOTguNTc1MyAyNS43MzA2IDk5Ljk4NTcgMjUuNTcxNSAxMDEuNjY2IDI1LjU3MTVDMTAyLjYyNiAyNS41NzE1IDEwMy40NzcgMjUuNjQxMSAxMDQuMjE3IDI1Ljc4MDNDMTA0Ljk1NyAyNS45MTk1IDEwNS43ODcgMjYuMTQ4MiAxMDYuNzA3IDI2LjQ2NjNWMzYuODAyMlY0MC4wMDc2QzEwNS42NjcgNDEuMzU5NyAxMDQuNTE3IDQyLjQ5MzEgMTAzLjI1NyA0My40MDc4WiIgZmlsbD0id2hpdGUiLz4NCjxwYXRoIGQ9Ik0xMzIuMTAyIDUxLjI4MjFDMTI5LjcwMiA1MS4yODIxIDEyNy41ODEgNTAuODc0NCAxMjUuNzQxIDUwLjA1OTJDMTIzLjkgNDkuMjQzOSAxMjIuMzYgNDguMTMwNCAxMjEuMTE5IDQ2LjcxODZDMTE5Ljg3OSA0NS4zMDY4IDExOC45MzkgNDMuNjQ2NCAxMTguMjk5IDQxLjczNzVDMTE3LjY1OCAzOS44Mjg2IDExNy4zMzggMzcuNzYwNyAxMTcuMzM4IDM1LjUzMzZWMzQuNDAwMkMxMTcuMzc4IDMyLjI5MjQgMTE3Ljc0OCAzMC4zNDM4IDExOC40NDkgMjguNTU0MkMxMTkuMTQ5IDI2Ljc2NDYgMTIwLjEzOSAyNS4yMjM1IDEyMS40MTkgMjMuOTMxMUMxMjIuNyAyMi42Mzg2IDEyNC4yNCAyMS42MjQ1IDEyNi4wNDEgMjAuODg4N0MxMjcuODQxIDIwLjE1MyAxMjkuODYyIDE5Ljc4NTIgMTMyLjEwMiAxOS43ODUyQzEzNC4yMjMgMTkuNzg1MiAxMzYuMTkzIDIwLjE1MyAxMzguMDE0IDIwLjg4ODdDMTM5LjgzNCAyMS42MjQ1IDE0MS40MjUgMjIuNjI4NiAxNDIuNzg1IDIzLjkwMTJDMTQ0LjE0NSAyNS4xNzM4IDE0NS4yMDYgMjYuNzA0OSAxNDUuOTY2IDI4LjQ5NDVDMTQ2LjcyNiAzMC4yODQxIDE0Ny4xMDYgMzIuMjEyOSAxNDcuMTA2IDM0LjI4MDlWMzUuNTMzNkMxNDcuMTA2IDM3Ljc2MDcgMTQ2Ljc3NiAzOS44Mjg2IDE0Ni4xMTYgNDEuNzM3NUMxNDUuNDU2IDQzLjY0NjQgMTQ0LjQ4NSA0NS4zMDY4IDE0My4yMDUgNDYuNzE4NkMxNDEuOTI1IDQ4LjEzMDQgMTQwLjM1NCA0OS4yNDM5IDEzOC40OTQgNTAuMDU5MkMxMzYuNjMzIDUwLjg3NDQgMTM0LjUwMyA1MS4yODIxIDEzMi4xMDIgNTEuMjgyMVpNMTQwLjkyNCAzNS41MzM2VjM0LjM0MDVDMTQwLjkyNCAzMS43MTU4IDE0MC4yMjQgMjkuNTg4MiAxMzguODI0IDI3Ljk1NzZDMTM3LjQyNCAyNi4zMjcxIDEzNS4yMDMgMjUuNTExOSAxMzIuMTYyIDI1LjUxMTlDMTI5LjEyMSAyNS41MTE5IDEyNi45MjEgMjYuMzI3MSAxMjUuNTYxIDI3Ljk1NzZDMTI0LjIgMjkuNTg4MiAxMjMuNTIgMzEuNzM1NyAxMjMuNTIgMzQuNDAwMlYzNS43NzIyQzEyMy41MiAzNy4yMDM5IDEyMy42NCAzOC41MDYzIDEyMy44OCAzOS42Nzk1QzEyNC4xMiA0MC44NTI3IDEyNC41NiA0MS44NzY3IDEyNS4yIDQyLjc1MTZDMTI1Ljg0MSA0My42MjY2IDEyNi43MjEgNDQuMzAyNiAxMjcuODQxIDQ0Ljc3OTlDMTI4Ljk2MSA0NS4yNTcxIDEzMC40MDIgNDUuNDk1NyAxMzIuMTYyIDQ1LjQ5NTdDMTMzLjkyMyA0NS40OTU3IDEzNS4zNjMgNDUuMjQ3MSAxMzYuNDgzIDQ0Ljc1QzEzNy42MDQgNDQuMjUyOSAxMzguNDk0IDQzLjU1NyAxMzkuMTU0IDQyLjY2MjJDMTM5LjgxNCA0MS43Njc0IDE0MC4yNzQgNDAuNzEzNSAxNDAuNTM0IDM5LjUwMDVDMTQwLjc5NCAzOC4yODc2IDE0MC45MjQgMzYuOTY1MyAxNDAuOTI0IDM1LjUzMzZaIiBmaWxsPSJ3aGl0ZSIvPg0KPHBhdGggZD0iTTkuMzE0NjIgNzQuNjYwOFY3NC43MzY0SDcuNzc4MjJDNy43MDIyIDc0LjUyNTYgNy42MjQxOCA3NC4zMzQ3IDcuNTg2MTcgNzQuMTI1OUM2Ljc5Nzk3IDc0LjU4MzMgNS41MTE2NCA3NC45MjczIDQuNTExMzggNzQuOTI3M0MyLjIyNDc5IDc0LjkyNzMgMC45MTg0NTcgNzMuODM5NiAwLjkxODQ1NyA3MS43OTU1QzAuOTE4NDU3IDY5LjkyNDMgMi41MzI4NyA2OC42NjM3IDUuMjAzNTYgNjguNjYzN0M2LjEwNzc5IDY4LjY2MzcgNi43MDE5NSA2OC43MjEzIDcuMzE2MSA2OC44MTY4VjY4LjM5NzJDNy4zMTYxIDY2Ljc1NDggNi4zOTM4NyA2Ni4wMTExIDQuODU3NDcgNjYuMDExMUMzLjg3NzIyIDY2LjAxMTEgMi44NTg5NiA2Ni4xODIxIDEuODYwNyA2Ni41NDZMMS4zODA1OCA2NS4zNDNDMi42NDg5IDY0Ljg0NTkgMy44MDEyIDY0LjYxNzIgNC45NzM1IDY0LjYxNzJDNi40MzM4OCA2NC42MTcyIDcuMzM2MTEgNjQuOTk5IDcuOTcwMjcgNjUuNjA5NEM4LjYyNDQ0IDY2LjI1OTYgOC44NzI1MSA2Ny4xMzY1IDguODcyNTEgNjguMjY0VjcxLjcwMkM4Ljg3MjUxIDcyLjYzODYgOC45Njg1MyA3My43MDY0IDkuMzE0NjIgNzQuNjYyOFY3NC42NjA4Wk00LjcwMzQzIDczLjU1MzJDNS41ODc2NiA3My41NTMyIDYuNTY1OTEgNzMuMzQyNSA3LjMxNjEgNzIuOTIyOVY3MC4wNTc2QzYuNjYzOTQgNjkuOTQyMiA2LjI1OTgzIDY5Ljg4NjYgNS4yNDE1NyA2OS44ODY2QzMuNDE1MSA2OS44ODY2IDIuNTMyODcgNzAuNjEyMyAyLjUzMjg3IDcxLjc5NTVDMi41MzI4NyA3Mi45Nzg2IDMuMjgxMDcgNzMuNTUzMiA0LjcwMzQzIDczLjU1MzJaIiBmaWxsPSJ3aGl0ZSIvPg0KPHBhdGggZD0iTTE0LjczNDEgNjcuMzI3NVY3NC43MzY0SDEzLjE1NzdWNjQuODA2MUgxNC41OTgxVjY1Ljk3MTRDMTUuNTU4MyA2NS4zNDEgMTcuMDc2NyA2NC43ODgyIDE4LjIyOSA2NC42MTUyTDE4LjQ5OTEgNjYuMDA5MUMxNy4zMDg4IDY2LjIgMTUuODQ2NCA2Ni42NzcyIDE0LjczNDEgNjcuMzI3NVoiIGZpbGw9IndoaXRlIi8+DQo8cGF0aCBkPSJNMjguODU1NiA3NC42NjA4Vjc0LjczNjRIMjcuMzE5MkMyNy4yNDMyIDc0LjUyNTYgMjcuMTY1MiA3NC4zMzQ3IDI3LjEyNzIgNzQuMTI1OUMyNi4zMzkgNzQuNTgzMyAyNS4wNTI3IDc0LjkyNzMgMjQuMDUyNCA3NC45MjczQzIxLjc2NTggNzQuOTI3MyAyMC40NTk1IDczLjgzOTYgMjAuNDU5NSA3MS43OTU1QzIwLjQ1OTUgNjkuOTI0MyAyMi4wNzM5IDY4LjY2MzcgMjQuNzQ0NiA2OC42NjM3QzI1LjY0ODggNjguNjYzNyAyNi4yNDMgNjguNzIxMyAyNi44NTcxIDY4LjgxNjhWNjguMzk3MkMyNi44NTcxIDY2Ljc1NDggMjUuOTM0OSA2Ni4wMTExIDI0LjM5ODUgNjYuMDExMUMyMy40MTgyIDY2LjAxMTEgMjIuNCA2Ni4xODIxIDIxLjQwMTcgNjYuNTQ2TDIwLjkyMTYgNjUuMzQzQzIyLjE4OTkgNjQuODQ1OSAyMy4zNDIyIDY0LjYxNzIgMjQuNTE0NSA2NC42MTcyQzI1Ljk3NDkgNjQuNjE3MiAyNi44NzcxIDY0Ljk5OSAyNy41MTEzIDY1LjYwOTRDMjguMTY1NSA2Ni4yNTk2IDI4LjQxMzUgNjcuMTM2NSAyOC40MTM1IDY4LjI2NFY3MS43MDJDMjguNDEzNSA3Mi42Mzg2IDI4LjUwOTUgNzMuNzA2NCAyOC44NTU2IDc0LjY2MjhWNzQuNjYwOFpNMjQuMjQ0NCA3My41NTMyQzI1LjEyODcgNzMuNTUzMiAyNi4xMDY5IDczLjM0MjUgMjYuODU3MSA3Mi45MjI5VjcwLjA1NzZDMjYuMjA1IDY5Ljk0MjIgMjUuODAwOCA2OS44ODY2IDI0Ljc4MjYgNjkuODg2NkMyMi45NTYxIDY5Ljg4NjYgMjIuMDczOSA3MC42MTIzIDIyLjA3MzkgNzEuNzk1NUMyMi4wNzM5IDcyLjk3ODYgMjIuODIyMSA3My41NTMyIDI0LjI0NDQgNzMuNTUzMloiIGZpbGw9IndoaXRlIi8+DQo8cGF0aCBkPSJNNDcuMjQyNSA2OC4xMjg4Vjc0LjczNjRINDUuNjY2MVY2OC4yNjJDNDUuNjY2MSA2Ni44NjgxIDQ0Ljc0MzkgNjUuOTcxNCA0My4zNDE1IDY1Ljk3MTRDNDIuNDc3MyA2NS45NzE0IDQxLjQzOSA2Ni4yMzc4IDQwLjc0NjkgNjYuNjU5NFY3NC43MzY0SDM5LjE5MDRWNjguMTY2NkMzOS4xOTA0IDY2LjYxOTYgMzguNDAyMiA2NS45NzE0IDM3LjAxOTkgNjUuOTcxNEMzNi4xNzM3IDY1Ljk3MTQgMzUuMTM3NCA2Ni4yNTc3IDM0LjI3MzIgNjYuNzkyNlY3NC43MzY0SDMyLjY5NjhWNjQuODA2MUgzNC4xMzcxVjY1LjUxMkMzNS4wMDE0IDY0Ljk3NzEgMzYuMjMxNyA2NC42MTUyIDM3LjQyMiA2NC42MTUyQzM4LjQwMjIgNjQuNjE1MiAzOS40MDA1IDY0Ljk1OTIgNDAuMTMwNyA2NS41ODk2QzQxLjExMDkgNjQuOTc5MSA0Mi40MTczIDY0LjYxNTIgNDMuNzQxNiA2NC42MTUyQzQ0Ljg3NTkgNjQuNjE1MiA0NS43NzgxIDY0Ljk1OTIgNDYuMzU0MyA2NS41MzE5QzQ2Ljk4ODUgNjYuMTYyMiA0Ny4yMzg1IDY2Ljk2MzYgNDcuMjM4NSA2OC4xMjg4SDQ3LjI0MjVaIiBmaWxsPSJ3aGl0ZSIvPg0KPHBhdGggZD0iTTU5Ljg2NTYgNzAuMjg2M0g1Mi4zMzM3QzUyLjU0NTcgNzIuMzY4MiA1My45ODYxIDczLjUzMzQgNTUuOTg0NiA3My41MzM0QzU2Ljk4MjkgNzMuNTMzNCA1OC4xMTcyIDczLjMwNDggNTkuMDE5NCA3Mi45NDA5TDU5LjQyMzUgNzQuMTgxN0M1OC4yNzEyIDc0LjY1ODkgNTcuMTc0OSA3NC45MjUzIDU1LjgzMDYgNzQuOTI1M0M1Mi45Njc4IDc0LjkyNTMgNTAuNzM5MyA3My4wNTQyIDUwLjczOTMgNjkuNzY5M0M1MC43MzkzIDY2LjQ4NDQgNTMuMTU5OSA2NC42MTMzIDU1LjUyMjUgNjQuNjEzM0M1OC4wOTcyIDY0LjYxMzMgNTkuOTIxNiA2Ni40ODQ0IDU5LjkyMTYgNjkuNDA3NEM1OS45MjE2IDY5LjY3MzkgNTkuOTAxNiA3MC4xMTMzIDU5Ljg2MzYgNzAuMjg2M0g1OS44NjU2Wk01Mi4zNTM3IDY4Ljk4NzlINTguMzA5MkM1OC4yNTEyIDY3LjA1OTEgNTcuMDYwOSA2NS45ODkzIDU1LjUyMjUgNjUuOTg5M0M1My44OTAxIDY1Ljk4OTMgNTIuNjIxNyA2Ni45ODE1IDUyLjM1MTcgNjguOTg3OUg1Mi4zNTM3WiIgZmlsbD0id2hpdGUiLz4NCjxwYXRoIGQ9Ik02OS44MDAxIDY1LjI0NTZMNjkuMzU4IDY2LjQ2ODVDNjguNDczNyA2Ni4xNDQzIDY3LjYwOTUgNjUuOTUzNSA2Ni41NTMyIDY1Ljk1MzVDNjUuMjg0OSA2NS45NTM1IDY0LjQ5NjcgNjYuNDUwNiA2NC40OTY3IDY3LjIzMkM2NC40OTY3IDY4LjAxMzUgNjQuODgwOCA2OC40OTI3IDY2LjY2NzMgNjguOTVDNjkuNDM0IDY5LjY1NTkgNzAuNDMyMiA3MC41MTY5IDcwLjQzMjIgNzIuMDQ0QzcwLjQzMjIgNzMuODAxOCA2OC45MTM4IDc0LjkyNzMgNjYuMzU5MiA3NC45MjczQzY1LjA5MDkgNzQuOTI3MyA2My44MDQ1IDc0LjY3ODcgNjIuNTU0MiA3NC4yNzkxTDYyLjk5NjMgNzMuMDU2MkM2NC4wOTA2IDczLjQwMDIgNjUuMjYyOSA3My41OTExIDY2LjM1OTIgNzMuNTkxMUM2OC4wMjk2IDczLjU5MTEgNjguODc1OCA3My4wNTYyIDY4Ljg3NTggNzIuMTE5NkM2OC44NzU4IDcxLjM5MzggNjguMjQxNyA3MC44MjEyIDY2LjE2NzEgNzAuMzA2MkM2My42NTA1IDY5LjY3NTggNjIuOTM4MyA2OC43NTkxIDYyLjkzODMgNjcuMzY1MkM2Mi45MzgzIDY1Ljc5ODQgNjQuMzIyNyA2NC42MTUyIDY2LjU1MTIgNjQuNjE1MkM2Ny44MTk2IDY0LjYxNTIgNjguNzc5OCA2NC44NjM4IDY5Ljc5ODEgNjUuMjQ1Nkg2OS44MDAxWiIgZmlsbD0id2hpdGUiLz4NCjwvZz4NCjwvZz4NCjwvZz4NCjxkZWZzPg0KPHJhZGlhbEdyYWRpZW50IGlkPSJwYWludDBfcmFkaWFsXzIyMzdfMjQ5IiBjeD0iMCIgY3k9IjAiIHI9IjEiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIiBncmFkaWVudFRyYW5zZm9ybT0idHJhbnNsYXRlKDMwLjM3NzcgMzUuMTQ5NCkgc2NhbGUoMjMuODQ4MSAyMy43MDQyKSI+DQo8c3RvcCBvZmZzZXQ9IjAuMTciIHN0b3AtY29sb3I9IiNGREI5MTMiLz4NCjxzdG9wIG9mZnNldD0iMC42NiIgc3RvcC1jb2xvcj0iI0YzNzAyMSIvPg0KPC9yYWRpYWxHcmFkaWVudD4NCjxyYWRpYWxHcmFkaWVudCBpZD0icGFpbnQxX3JhZGlhbF8yMjM3XzI0OSIgY3g9IjAiIGN5PSIwIiByPSIxIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSIgZ3JhZGllbnRUcmFuc2Zvcm09InRyYW5zbGF0ZSgyMi44OTM4IDI1LjM2NDkpIHNjYWxlKDIzLjE2IDIzLjAyMDIpIj4NCjxzdG9wIG9mZnNldD0iMC40MSIgc3RvcC1jb2xvcj0iIzk2MkYzNCIvPg0KPHN0b3Agb2Zmc2V0PSIwLjk5IiBzdG9wLWNvbG9yPSIjRUQxQzI0Ii8+DQo8L3JhZGlhbEdyYWRpZW50Pg0KPGNsaXBQYXRoIGlkPSJjbGlwMF8yMjM3XzI0OSI+DQo8cmVjdCB3aWR0aD0iMTQ3IiBoZWlnaHQ9Ijc1IiBmaWxsPSJ3aGl0ZSIvPg0KPC9jbGlwUGF0aD4NCjxjbGlwUGF0aCBpZD0iY2xpcDFfMjIzN18yNDkiPg0KPHJlY3Qgd2lkdGg9IjE0Ny4xMDYiIGhlaWdodD0iNzUiIGZpbGw9IndoaXRlIi8+DQo8L2NsaXBQYXRoPg0KPGNsaXBQYXRoIGlkPSJjbGlwMl8yMjM3XzI0OSI+DQo8cmVjdCB3aWR0aD0iMTQ3LjEwNiIgaGVpZ2h0PSI3NSIgZmlsbD0id2hpdGUiIHRyYW5zZm9ybT0idHJhbnNsYXRlKDAgLTAuMDcyMjY1NikiLz4NCjwvY2xpcFBhdGg+DQo8L2RlZnM+DQo8L3N2Zz4NCg=="
         style="height:38px;width:auto;flex-shrink:0;" alt="Belgo Mineira" />
    <div style="width:1px;height:36px;background:rgba(255,255,255,0.2);margin:0 4px;flex-shrink:0;"></div>
    <div class="header-text">
      <h1>Agente de Triagem TI</h1>
      <p>Agente de triagem exposto via MCP — classifica chamados N1/N2 em tempo real</p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Layout principal ─────────────────────────────────────────────────────────
col_esq, col_dir = st.columns([1, 1.2], gap="large")

with col_esq:
    # Incrementa o contador para forçar um novo widget DOM (key diferente = campo vazio)
    if st.session_state.clear_input:
        st.session_state.input_key += 1
        st.session_state.clear_input = False

    st.markdown("**Descreva o chamado:**")
    ticket_input = st.text_area(
        label="Descrição",
        key=f"ticket_input_{st.session_state.input_key}",
        height=160,
        placeholder="Ex.: Impressora da sala de reunião não imprime após troca de cartucho...",
        label_visibility="collapsed",
        disabled=st.session_state.processando,
    )

    analisar = st.button(
        "🔍  Analisar chamado",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.processando,
    )

    # Indicador de cooldown / uso
    _now = time.time()
    _sess_recent = [t for t in st.session_state.request_times if _now - t < 3600]
    _store = _global_rate_store()
    with _store["lock"]:
        _global_count = len([t for t in _store["times"] if _now - t < 3600])
    _remaining = _MAX_GLOBAL_HOUR - _global_count
    if _sess_recent and (_now - _sess_recent[-1]) < _COOLDOWN_S:
        _wait = int(_COOLDOWN_S - (_now - _sess_recent[-1])) + 1
        st.caption(f"⏱ Cooldown: {_wait}s · {_remaining} req disponíveis esta hora")
    elif _remaining <= 0:
        st.caption("🚫 Limite de uso atingido esta hora")
    elif _global_count > 0:
        st.caption(f"✓ {_remaining}/{_MAX_GLOBAL_HOUR} análises disponíveis esta hora")

with col_dir:
    # ── Fase 1: captura o clique e enfileira ──────────────────────────────
    if analisar and ticket_input.strip() and not st.session_state.processando:
        allowed, reason = _check_rate_limit()
        if not allowed:
            st.warning(reason)
        else:
            _record_request()
            st.session_state.pending_input = ticket_input.strip()
            st.session_state.last_input = ticket_input.strip()
            st.session_state.processando = True
            st.session_state.resultado = None
            st.session_state.clear_input = True
            st.rerun()

    # ── Fase 2: executa análise (streaming ou demo) ───────────────────────
    if st.session_state.processando and st.session_state.pending_input:
        texto = st.session_state.pending_input
        resultado = None

        if ANTHROPIC_KEY and ANTHROPIC_KEY != "cole_sua_chave_aqui":
            cot_slot = st.empty()
            try:
                resultado = _analisar_com_api(texto, cot_slot=cot_slot)
            except Exception as e:
                st.error(f"Erro na API: {e}")
        else:
            st.warning("⚠ Chave da API Anthropic não configurada. Defina a variável de ambiente `ANTHROPIC_API_KEY` para usar o agente.")

        st.session_state.resultado = resultado
        st.session_state.pending_input = None
        st.session_state.processando = False
        st.rerun()

    # ── Fase 3: exibe resultado estático ─────────────────────────────────
    elif st.session_state.resultado:
        r = st.session_state.resultado

        # CoT acima do card de resultado
        if r.get("pensamento"):
            steps_html = "".join(_cot_step(p) for p in r["pensamento"])
            st.markdown(_cot_header(st.session_state.get("last_input", "")) + steps_html + _COT_FTR, unsafe_allow_html=True)

        nivel = r.get("nivel", "N1")
        fora_de_escopo = nivel == "FORA_DE_ESCOPO"

        # Escapa tudo que vem da API para não quebrar o HTML
        sugestao_safe   = _html.escape(str(r.get("sugestao", ""))).replace("\n", "<br>")
        acao_safe       = _html.escape(str(r.get("acao", "")))
        tempo_safe      = _html.escape(str(r.get("tempo", "")))
        confianca       = int(r.get("confianca", 0))
        motivo_conf     = _html.escape(str(r.get("motivo_confianca", "")))

        if fora_de_escopo:
            st.markdown(f"""
            <div class="result-card" style="border-top-color:#F37021;">
              <span style="display:inline-block;background:#FFF4E5;color:#B45309;border:2px solid #F37021;
                border-radius:8px;padding:6px 20px;font-size:1.4rem;font-weight:800;margin-bottom:12px;
                font-family:'Montserrat',sans-serif;letter-spacing:0.02em;">⚠ Fora do Escopo</span>

              <div style="margin-top:6px;margin-bottom:18px;">
                <div class="result-label">O que foi enviado</div>
                <div class="result-value">{sugestao_safe if sugestao_safe else
                    "Esse chamado não parece ser um problema de TI. Por favor, descreva uma solicitação ou incidente de TI para que o agente possa classificá-lo corretamente."}</div>
              </div>

              <div style="background:#FFF4E5;border-left:4px solid #F37021;padding:10px 14px;
                border-radius:0 8px 8px 0;color:#92400E;font-size:0.9rem;font-weight:600;
                font-family:'Montserrat',sans-serif;">
                ⚡ {acao_safe if acao_safe else "Reenviar como chamado de TI válido"}
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            badge_class = "badge-n1" if nivel == "N1" else "badge-n2"
            bar_class   = "conf-bar-fill-n1" if nivel == "N1" else "conf-bar-fill-n2"
            acao_class  = "acao-n1" if nivel == "N1" else "acao-n2"
            label_nivel = "N1 — Helpdesk" if nivel == "N1" else "N2 — Especialista"
            tempo_html  = f"""
              <div style="margin-top:18px;">
                <div class="result-label">Tempo estimado de resolução</div>
                <div class="result-value">{tempo_safe}</div>
              </div>""" if tempo_safe and tempo_safe != "N/A" else ""

            st.markdown(f"""
            <div class="result-card">
              <span class="{badge_class}">{nivel}</span>&nbsp;&nbsp;
              <span style="font-size:1.1rem;font-weight:600;color:#334155;">{label_nivel}</span>

              <div style="margin-top:18px;">
                <div class="result-label">Confiança da classificação</div>
                <div style="display:flex;align-items:center;gap:12px;">
                  <div class="conf-bar-bg" style="flex:1;">
                    <div class="{bar_class}" style="width:{confianca}%;"></div>
                  </div>
                  <span class="conf-tooltip">
                    <span style="font-weight:700;color:#1E293B;">{confianca}%</span>
                    <span class="conf-tooltip-icon">ⓘ</span>
                    <span class="conf-tooltip-box">{motivo_conf}</span>
                  </span>
                </div>
              </div>
              {tempo_html}
              <div style="margin-top:18px;">
                <div class="result-label">Sugestão de resolução</div>
                <div class="result-value">{sugestao_safe}</div>
              </div>

              <div class="{acao_class}">⚡ {acao_safe}</div>
            </div>
            """, unsafe_allow_html=True)

    elif not st.session_state.processando:
        st.markdown("""
        <div style="
            border: 2px dashed #C5D8DC;
            border-radius: 12px;
            padding: 48px 32px;
            text-align: center;
            color: #7A9EA6;
            background: #F7FAFB;
        ">
            <div style="font-size:2.5rem;margin-bottom:12px;">⚙️</div>
            <div style="font-size:0.97rem;font-family:'Montserrat',sans-serif;font-weight:500;">
                Descreva um chamado de TI ao lado<br>e clique em <strong style="color:#003B4A;">Analisar</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<hr style="border:none;border-top:1px solid #D6E2E5;margin:0 0 10px;">', unsafe_allow_html=True)
ft_l, ft_r = st.columns([2, 1])
with ft_l:
    st.markdown("""
    <span style="background:#FEE8E8;border:1px solid #ED1C24;color:#B8000A;border-radius:4px;
        padding:3px 10px;font-size:0.72rem;font-weight:700;font-family:'Montserrat',sans-serif;
        letter-spacing:0.06em;text-transform:uppercase;white-space:nowrap;">
        ⚠ Uso Interno — Não Divulgar
    </span>
    """, unsafe_allow_html=True)
with ft_r:
    c_txt, c_btn = st.columns([5, 1], gap="small")
    with c_txt:
        st.markdown("""
        <div style="text-align:right;padding-top:6px;">
            <span style="font-size:0.78rem;color:#7A9EA6;font-family:'Montserrat',sans-serif;">
                Desenvolvido por <strong style="color:#003B4A;">Lucas Lemos</strong> &nbsp;·&nbsp;
                Belgo Arames, 2026
            </span>
        </div>
        """, unsafe_allow_html=True)
    with c_btn:
        if st.button("📐", key="btn_arq", help="Ver arquitetura da solução"):
            _modal_arquitetura()


