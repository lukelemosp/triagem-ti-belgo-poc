import base64 as _base64
import html as _html
import re as _re
import pathlib as _pathlib


def _load_logo() -> str:
    try:
        src = _pathlib.Path(__file__).parent / "agente_triagem.py"
        m = _re.search(r'base64,([A-Za-z0-9+/=]+)"', src.read_text(encoding="utf-8"))
        if not m:
            return ""
        svg = _base64.b64decode(m.group(1)).decode("utf-8").strip()
        return _re.sub(r'^<svg ', '<svg style="height:38px;width:auto;" ', svg, count=1)
    except Exception:
        return ""


_LOGO_SVG = _load_logo()


BELGO_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Montserrat', 'Segoe UI', sans-serif; }

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

    .conf-tooltip {
        position: relative;
        display: inline-flex;
        align-items: center;
        cursor: help;
    }
    .conf-tooltip-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 15px;
        height: 15px;
        background: #7A9EA6;
        border-radius: 50%;
        color: white;
        font-size: 0.62rem;
        font-weight: 800;
        font-style: italic;
        margin-left: 6px;
        line-height: 1;
        flex-shrink: 0;
        vertical-align: middle;
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

    .conf-bar-bg {
        background: #D6E2E5;
        border-radius: 999px;
        height: 10px;
        margin-top: 6px;
    }
    .conf-bar-fill-n1 { background: #003B4A; height: 10px; border-radius: 999px; }
    .conf-bar-fill-n2 { background: #ED1C24; height: 10px; border-radius: 999px; }

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

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
        0%   { background-position: -600px 0; }
        100% { background-position:  600px 0; }
    }
    .skeleton-line {
        background: linear-gradient(90deg, #E8F0F2 25%, #C5D8DC 50%, #E8F0F2 75%);
        background-size: 1200px 100%;
        animation: shimmer 1.8s infinite ease-in-out;
        border-radius: 4px;
    }
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

    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }

    [data-testid="stMainBlockContainer"] {
        animation: belgo-fade-in 0.22s ease-out;
    }
    @keyframes belgo-fade-in {
        from { opacity: 0; transform: translateY(5px); }
        to   { opacity: 1; transform: none; }
    }

    /* ── Navbar via st.page_link ──────────────────────────────────────────── */
    div[data-testid="stHorizontalBlock"]:has([data-testid="stPageLink"]) {
        background: #003B4A;
        border-radius: 10px;
        padding: 2px 8px;
        margin-bottom: 12px;
        gap: 2px !important;
        align-items: center !important;
    }
    [data-testid="stPageLink"] a {
        color: rgba(255,255,255,0.88) !important;
        font-family: 'Montserrat',sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        text-decoration: none !important;
        border-radius: 8px !important;
        transition: background 0.15s !important;
        justify-content: center !important;
        display: flex !important;
        padding: 6px 4px !important;
        text-align: center !important;
    }
    [data-testid="stPageLink"] a:hover {
        background: rgba(255,255,255,0.13) !important;
        color: white !important;
    }
    [data-testid="stPageLink"] p {
        color: inherit !important;
        font-family: inherit !important;
        font-weight: inherit !important;
        font-size: inherit !important;
        margin: 0 !important;
        line-height: 1.3 !important;
    }
    [data-testid="stPageLink"] a[aria-current="page"] {
        background: rgba(255,255,255,0.18) !important;
        color: white !important;
    }
</style>
"""


def header_html(title: str = "Agente de Triagem TI", subtitle: str = None, tag: str = None) -> str:
    sub = subtitle or "Agente de triagem exposto via MCP — classifica chamados N1/N2 em tempo real"
    tag_html = f'<span class="header-tag">{_html.escape(tag)}</span>' if tag else ""
    logo = f'<div style="flex-shrink:0;">{_LOGO_SVG}</div>'
    return f"""
<div class="header-box">
  <div class="header-accent"></div>
  <div class="header-content">
    {logo}
    <div style="width:1px;height:36px;background:rgba(255,255,255,0.2);margin:0 4px;flex-shrink:0;"></div>
    <div class="header-text">
      <h1>{_html.escape(title)}</h1>
      <p>{_html.escape(sub)}</p>
    </div>
    {tag_html}
  </div>
</div>
"""


def render_result_card(r: dict) -> str:
    """Retorna o HTML do card de resultado N1/N2/FORA_DE_ESCOPO."""
    nivel = r.get("nivel", "FORA_DE_ESCOPO")
    if nivel not in {"N1", "N2", "FORA_DE_ESCOPO"}:
        nivel = "FORA_DE_ESCOPO"
    fora = nivel == "FORA_DE_ESCOPO"

    sugestao = _html.escape(str(r.get("sugestao", ""))).replace("\n", "<br>")
    acao = _html.escape(str(r.get("acao", "")))
    tempo = _html.escape(str(r.get("tempo", "")))
    try:
        conf = max(0, min(100, int(r.get("confianca", 0))))
    except (TypeError, ValueError):
        conf = 0
    motivo = _html.escape(str(r.get("motivo_confianca", "")))

    if fora:
        return f"""
<div class="result-card" style="border-top-color:#F37021;">
  <span style="display:inline-block;background:#FFF4E5;color:#B45309;border:2px solid #F37021;
    border-radius:8px;padding:6px 20px;font-size:1.4rem;font-weight:800;margin-bottom:12px;
    font-family:'Montserrat',sans-serif;letter-spacing:0.02em;">⚠ Fora do Escopo</span>
  <div style="margin-top:6px;margin-bottom:18px;">
    <div class="result-label">O que foi enviado</div>
    <div class="result-value">{sugestao if sugestao else "Esse chamado não parece ser um problema de TI."}</div>
  </div>
  <div style="background:#FFF4E5;border-left:4px solid #F37021;padding:10px 14px;
    border-radius:0 8px 8px 0;color:#92400E;font-size:0.9rem;font-weight:600;
    font-family:'Montserrat',sans-serif;">
    ⚡ {acao if acao else "Reenviar como chamado de TI válido"}
  </div>
</div>"""

    badge = "badge-n1" if nivel == "N1" else "badge-n2"
    bar = "conf-bar-fill-n1" if nivel == "N1" else "conf-bar-fill-n2"
    acao_cls = "acao-n1" if nivel == "N1" else "acao-n2"
    label = "N1 — Helpdesk" if nivel == "N1" else "N2 — Especialista"
    tempo_html = f"""
  <div style="margin-top:18px;">
    <div class="result-label">Tempo estimado de resolução</div>
    <div class="result-value">{tempo}</div>
  </div>""" if tempo and tempo != "N/A" else ""

    return f"""
<div class="result-card">
  <span class="{badge}">{nivel}</span>&nbsp;&nbsp;
  <span style="font-size:1.1rem;font-weight:600;color:#334155;">{label}</span>
  <div style="margin-top:18px;">
    <div style="display:flex;align-items:center;margin-bottom:4px;">
      <div class="result-label" style="margin-bottom:0;">Confiança da classificação</div>
      <span class="conf-tooltip">
        <span class="conf-tooltip-icon">i</span>
        <span class="conf-tooltip-box">{motivo}</span>
      </span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
      <div class="conf-bar-bg" style="flex:1;margin-top:0;">
        <div class="{bar}" style="width:{conf}%;"></div>
      </div>
      <span style="font-weight:700;color:#1E293B;">{conf}%</span>
    </div>
  </div>
  {tempo_html}
  <div style="margin-top:18px;">
    <div class="result-label">Sugestão de resolução</div>
    <div class="result-value">{sugestao}</div>
  </div>
  <div class="{acao_cls}">⚡ {acao}</div>
</div>"""


def render_empty_state() -> str:
    return """
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
</div>"""


def inc_id(ticket_id) -> str:
    return f"INC{int(ticket_id):06d}"


def recent_tickets_html(recentes: list) -> str:
    NIVEL_EMOJI = {"N1": "\U0001F535", "N2": "\U0001F534", "FORA_DE_ESCOPO": "\U0001F7E0"}
    STATUS_LABEL = {
        "ABERTO": "Aberto",
        "EM_ATENDIMENTO": "Em atendimento",
        "RESOLVIDO": "Resolvido",
        "FECHADO": "Fechado",
    }
    rows = ""
    for t in recentes:
        nivel = t.get("nivel") or "—"
        emoji = NIVEL_EMOJI.get(nivel, "⚪")
        iid = inc_id(t["id"])
        tid = int(t["id"])
        auto_str = "Sim" if t.get("auto_resolvido") else "N\xe3o"
        status_str = STATUS_LABEL.get(t["status"], t["status"])
        titulo_str = _html.escape(t["titulo"])
        dt_str = fmt_dt(t.get("criado_em") or "")
        rows += (
            "<tr>"
            "<td><a href=\"/chamado?id=" + str(tid) + "\" style=\"color:#003B4A;font-weight:700;"
            "text-decoration:none;font-family:Montserrat,sans-serif;\">" + iid + "</a></td>"
            "<td>" + emoji + " " + nivel + "</td>"
            "<td style=\"max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;\">"
            + titulo_str + "</td>"
            "<td>" + status_str + "</td>"
            "<td>" + auto_str + "</td>"
            "<td>" + dt_str + "</td>"
            "</tr>"
        )
    css = (
        "<style>"
        ".inc-tbl{width:100%;border-collapse:collapse;font-family:Montserrat,sans-serif;font-size:0.84rem;}"
        ".inc-tbl th{background:#003B4A;color:#fff;padding:7px 12px;text-align:left;"
        "font-size:0.73rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;}"
        ".inc-tbl td{padding:7px 12px;border-bottom:1px solid #E2EEF0;color:#1A2E33;vertical-align:middle;}"
        ".inc-tbl tr:hover td{background:#F0F7F9;}"
        "</style>"
    )
    table = (
        "<table class=\"inc-tbl\">"
        "<thead><tr>"
        "<th>Chamado</th><th>N\xedvel</th><th>T\xedtulo</th>"
        "<th>Status</th><th>Auto-res.</th><th>Criado em</th>"
        "</tr></thead>"
        "<tbody>" + rows + "</tbody>"
        "</table>"
    )
    return css + table


def enter_to_submit_js() -> str:
    """JS que faz Enter submeter o formulário; Shift+Enter insere quebra de linha."""
    return """
<script>
(function() {
  document.addEventListener('keydown', function(e) {
    if (e.key !== 'Enter' || e.shiftKey || e.target.tagName !== 'TEXTAREA') return;
    var btn = document.querySelector('[data-testid="baseButton-primary"]:not([disabled])');
    if (btn) { e.preventDefault(); btn.click(); }
  }, true);
})();
</script>
"""


def fmt_dt(iso: str) -> str:
    if not iso:
        return "—"
    iso = iso[:16].replace("T", " ")
    try:
        d, t = iso.split(" ")
        y, m, day = d.split("-")
        return f"{day}/{m}/{y} {t}"
    except Exception:
        return iso


def stat_card_html(value: str, label: str, color: str = "#003B4A") -> str:
    return f"""
<div style="background:#FAFBFC;border:1px solid #D6E2E5;border-top:3px solid {color};
     border-radius:10px;padding:16px 20px;">
  <div style="font-size:1.8rem;font-weight:800;color:{color};font-family:'Montserrat',sans-serif;">
    {_html.escape(str(value))}
  </div>
  <div style="font-size:0.78rem;color:#5A7E88;font-family:'Montserrat',sans-serif;margin-top:2px;">
    {_html.escape(label)}
  </div>
</div>"""
