# -*- coding: utf-8 -*-
"""
E2E (AppTest) — Belgo Triagem TI.

Cobertura ampla e estável via streamlit.testing.v1.AppTest (sem navegador):
- todas as páginas renderizam sem exceção (admin);
- fluxos com widgets frágeis no Playwright: CRUD de KB e de Usuário, filtros do
  Histórico, busca por ID (caminho sem IA), criação por preset (sem IA);
- checagem de papéis (normal não acessa páginas admin pela navegação).

Uso:  python tests/e2e_apptest.py   (sai com código !=0 se algo falhar)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

ADMIN_EMAIL = "lucas.lemos@belgo.com.br"
ADMIN_SENHA = "adminbelgo"
NORMAL_EMAIL = "ana.souza@belgo.com.br"
NORMAL_SENHA = "belgo123"

PAGES = [
    "pages/1_Triagem.py", "pages/2_Novo_Chamado.py", "pages/3_Fila_N1.py",
    "pages/4_Fila_N2.py", "pages/5_Chamado.py", "pages/6_Usuarios.py",
    "pages/7_Chamados.py", "pages/8_Skills.py", "pages/9_Shadow.py",
    "pages/10_Base_Conhecimento.py",
]

_results = []


def check(name, fn):
    try:
        fn()
        _results.append((True, name, ""))
        print("PASS  " + name)
    except Exception as e:  # noqa: BLE001
        _results.append((False, name, repr(e)))
        print("FAIL  " + name + "  ->  " + repr(e))


def _app(user, page=None, **ss):
    at = AppTest.from_file("app.py", default_timeout=120)
    at.session_state["auth_user"] = user
    for k, v in ss.items():
        at.session_state[k] = v
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    return at


def _w(at, kind, key):
    for el in getattr(at, kind):
        if el.key == key:
            return el
    raise AssertionError(kind + "[" + key + "] não encontrado")


def _no_exc(at, ctx=""):
    # at.exception é uma ElementList (vazia quando não há exceção), não None.
    assert not at.exception, ctx + " exceção: " + str([e.value for e in at.exception])


def main():
    db.init_db()
    db.seed_demo(force=True)
    admin = db.autenticar(ADMIN_EMAIL, ADMIN_SENHA)
    normal = db.autenticar(NORMAL_EMAIL, NORMAL_SENHA)
    assert admin and normal, "seed/credenciais inválidos"

    # 1) Dashboard + todas as páginas (admin) sem exceção
    check("dashboard admin", lambda: _no_exc(_app(admin), "dashboard"))
    for p in PAGES:
        ss = {}
        if p == "pages/5_Chamado.py":
            ss = {"current_ticket_id": db.listar_tickets_recentes(1)[0]["id"],
                  "ticket_origin": "chamados"}
        check("render " + p, lambda p=p, ss=ss: _no_exc(_app(admin, p, **ss), p))

    # 2) KB — criar (UI form, categoria OUTRO p/ não bater na regra de unicidade)
    def kb_criar():
        at = _app(admin, "pages/10_Base_Conhecimento.py")
        _w(at, "text_input", "kb_nu_codigo").set_value("KB9001").run()
        _w(at, "text_input", "kb_nu_titulo").set_value("Artigo E2E").run()
        _w(at, "selectbox", "kb_nu_cat").set_value("OUTRO").run()
        _w(at, "text_area", "kb_nu_passos").set_value("Passo 1\nPasso 2").run()
        _w(at, "button", "kb_nu_criar").click().run()
        cods = {a["codigo"] for a in db.listar_kb()}
        assert "KB9001" in cods, "artigo não criado"
    check("KB criar (form)", kb_criar)

    # 3) KB — atualizar reflete na listagem (read path)
    def kb_editar():
        pk = [a for a in db.listar_kb() if a["codigo"] == "KB9001"][0]["id"]
        db.atualizar_kb(pk, titulo="Artigo E2E Editado")
        at = _app(admin, "pages/10_Base_Conhecimento.py")
        body = at.get("markdown")
        txt = " ".join(getattr(m, "value", "") for m in body)
        assert "Artigo E2E Editado" in txt, "edição não refletida na página"
    check("KB editar (reflete)", kb_editar)

    # 4) KB — deletar via botões (confirmação em 2 passos)
    def kb_deletar():
        pk = [a for a in db.listar_kb() if a["codigo"] == "KB9001"][0]["id"]
        at = _app(admin, "pages/10_Base_Conhecimento.py")
        _w(at, "button", "kbdel_" + str(pk)).click().run()
        _w(at, "button", "kbdelok_" + str(pk)).click().run()
        cods = {a["codigo"] for a in db.listar_kb()}
        assert "KB9001" not in cods, "artigo não removido"
    check("KB deletar (2 passos)", kb_deletar)

    # 5) KB — regra "1 ativo por categoria" bloqueia duplicata
    def kb_regra():
        at = _app(admin, "pages/10_Base_Conhecimento.py")
        _w(at, "text_input", "kb_nu_codigo").set_value("KB9002").run()
        _w(at, "text_input", "kb_nu_titulo").set_value("Dup Reset").run()
        _w(at, "selectbox", "kb_nu_cat").set_value("RESET_SENHA").run()
        _w(at, "button", "kb_nu_criar").click().run()
        cods = {a["codigo"] for a in db.listar_kb()}
        assert "KB9002" not in cods, "duplicata de categoria não foi bloqueada"
    check("KB regra 1/categoria", kb_regra)

    # 6) Usuário — criar (UI form)
    def user_criar():
        at = _app(admin, "pages/6_Usuarios.py")
        _w(at, "text_input", "nu_nome").set_value("Teste E2E").run()
        _w(at, "text_input", "nu_email").set_value("teste.e2e@belgo.com.br").run()
        _w(at, "text_input", "nu_depto").set_value("TI").run()
        _w(at, "button", "nu_criar").click().run()
        emails = {u["email"] for u in db.listar_usuarios()}
        assert "teste.e2e@belgo.com.br" in emails, "usuário não criado"
    check("Usuário criar (form)", user_criar)

    # 7) Histórico — filtro de status não quebra
    def hist_filtro():
        at = _app(admin, "pages/7_Chamados.py")
        _w(at, "multiselect", "ch_status").set_value(["RESOLVIDO"]).run()
        _no_exc(at, "histórico filtro")
    check("Histórico filtro status", hist_filtro)

    # 8) Busca por ID no dashboard (caminho SEM IA)
    def busca_id():
        at = _app(admin)
        _w(at, "text_input", "dash_busca").set_value("INC000001").run()
        _no_exc(at, "busca id")
    check("Busca por ID (sem IA)", busca_id)

    # 9) Novo Chamado — preset cria chamado auto-resolvido (sem IA)
    def preset_cria():
        antes = db.stats_tickets().get("total") or 0
        at = _app(admin, "pages/2_Novo_Chamado.py")
        _w(at, "button", "preset_0").click().run()
        at.run()
        depois = db.stats_tickets().get("total") or 0
        assert depois == antes + 1, "preset não criou chamado (antes=%s depois=%s)" % (antes, depois)
    check("Novo Chamado preset", preset_cria)

    # 10) Papéis — normal não vê páginas admin na navegação
    def papel_normal():
        at = _app(normal)
        _no_exc(at, "home normal")
        titles = {p.title for p in at.session_state.get("_nav_titles", [])} if False else None
        # Verifica via page_links renderizados na navbar
        labels = " ".join(getattr(pl, "label", "") for pl in at.get("page_link"))
        assert "Usu" not in labels and "Skills" not in labels and "KB" not in labels, \
            "usuário normal não deveria ver páginas admin: " + labels
    check("Papel normal sem admin", papel_normal)

    # ── Resumo ────────────────────────────────────────────────────────────────
    fails = [r for r in _results if not r[0]]
    print("\n=== AppTest: %d/%d PASS ===" % (len(_results) - len(fails), len(_results)))
    for ok, n, e in fails:
        print("  FAIL " + n + "  " + e)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
