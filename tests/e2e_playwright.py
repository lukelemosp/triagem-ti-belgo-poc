# -*- coding: utf-8 -*-
"""
E2E (Playwright) — Belgo Triagem TI.

Navegação real no navegador: sobe o app, faz login por clique, percorre todas as
páginas (navegando por href, estável entre navbar e sidebar), exercita fluxos de
botão (preset), valida acesso por papel e tira screenshots. Varre o body por
marcadores de erro do Streamlit.

Uso:  python tests/e2e_playwright.py   (sai !=0 se algo falhar)
Requer: playwright instalado (pip install playwright && playwright install chromium).
"""
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PORT = int(os.environ.get("BELGO_PORT", "8612"))
BASE = "http://localhost:%d" % PORT
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")

ERR_MARKERS = ["Traceback", "encountered an error", "AttributeError",
               "KeyError", "IntegrityError", "ModuleNotFoundError", "NameError"]

_results = []


def check(name, ok, detail=""):
    _results.append((ok, name, detail))
    print(("PASS  " if ok else "FAIL  ") + name + (("  ->  " + detail) if detail else ""))


def _wait_health(timeout=60):
    for _ in range(timeout * 2):
        try:
            with urllib.request.urlopen(BASE + "/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    return False


def _scan_errors(page, ctx):
    body = page.inner_text("body")
    hit = [m for m in ERR_MARKERS if m in body]
    check("sem erros em " + ctx, not hit, ("marcadores: " + ", ".join(hit)) if hit else "")


def _shot(page, name):
    os.makedirs(SHOTS, exist_ok=True)
    page.screenshot(path=os.path.join(SHOTS, name + ".png"), full_page=True)


def _login(page, email, senha):
    page.goto(BASE, wait_until="networkidle")
    time.sleep(2)
    page.locator("input").first.fill(email)
    page.locator("input[type='password']").first.fill(senha)
    page.get_by_role("button", name="Entrar").first.click()
    time.sleep(4)


def _goto_href(page, suffix):
    # hrefs do st.page_link são relativos sem barra ('novo','n1',…); em páginas
    # internas o link da navbar fica oculto e o visível é o da sidebar.
    page.locator("a[href$='%s']:visible" % suffix).first.click()
    time.sleep(3.5)


def run():
    from playwright.sync_api import sync_playwright

    # Estado limpo e servidor
    import database as db
    db.init_db()
    db.seed_demo(force=True)

    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", str(PORT), "--server.headless", "true",
         "--server.runOnSave", "false"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not _wait_health():
            check("servidor no ar", False, "health check falhou")
            return
        check("servidor no ar", True)

        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={"width": 1440, "height": 1000})

            # ── Admin ──────────────────────────────────────────────────────────
            _login(page, "lucas.lemos@belgo.com.br", "adminbelgo")
            body = page.inner_text("body")
            check("login admin", "Sair" in body, "" if "Sair" in body else "topbar sem 'Sair'")
            check("painel ROI no dashboard", "VALOR PARA O" in body.upper())
            _scan_errors(page, "dashboard")
            _shot(page, "01_dashboard")

            # Percorre páginas por href (estável entre navbar/sidebar)
            for suffix, nome in [("novo", "novo"), ("n1", "fila_n1"), ("n2", "fila_n2"),
                                 ("chamados", "chamados"), ("skills", "skills"),
                                 ("shadow", "shadow"), ("kb", "kb"),
                                 ("usuarios", "usuarios"), ("triagem", "triagem")]:
                try:
                    _goto_href(page, suffix)
                    _scan_errors(page, nome)
                    _shot(page, "page_" + nome)
                    check("navegou para " + nome, True)
                except Exception as e:  # noqa: BLE001
                    check("navegou para " + nome, False, repr(e))

            # KB visível
            _goto_href(page, "kb")
            kb_body = page.inner_text("body")
            check("KB lista artigos", "Base de Conhecimento" in kb_body and "KB0001" in kb_body)

            # Fluxo: preset cria chamado auto-resolvido
            _goto_href(page, "novo")
            try:
                page.get_by_role("button", name="Reset de Senha").first.click()
                time.sleep(4)
                nb = page.inner_text("body")
                check("preset auto-resolve", "Atendimento Autom" in nb,
                      "" if "Atendimento Autom" in nb else "card de auto-resolução não apareceu")
                _scan_errors(page, "novo_chamado_preset")
                _shot(page, "preset_resultado")
            except Exception as e:  # noqa: BLE001
                check("preset auto-resolve", False, repr(e))

            # Logout
            page.get_by_role("button", name="Sair").first.click()
            time.sleep(3)

            # ── Normal: navbar sem páginas admin ────────────────────────────────
            _login(page, "ana.souza@belgo.com.br", "belgo123")
            hrefs = page.locator("a").evaluate_all("els => els.map(e => e.getAttribute('href'))")
            hrefs = [h or "" for h in hrefs]
            tem_admin = any(h.endswith(s) for h in hrefs
                            for s in ("skills", "shadow", "kb", "usuarios", "n1", "n2"))
            check("normal sem páginas admin", not tem_admin,
                  "hrefs admin visíveis: " + str([h for h in hrefs if h]))
            _scan_errors(page, "home_normal")
            _shot(page, "10_home_normal")

            b.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            proc.kill()

    fails = [r for r in _results if not r[0]]
    print("\n=== Playwright: %d/%d PASS ===" % (len(_results) - len(fails), len(_results)))
    for ok, n, d in fails:
        print("  FAIL " + n + "  " + d)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    run()
