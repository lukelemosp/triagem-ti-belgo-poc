# -*- coding: utf-8 -*-
"""
Runner E2E — executa a suíte AppTest e, em seguida, a Playwright.
Sai com código !=0 se qualquer uma falhar.

Uso:  python tests/run_e2e.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _run(script):
    print("\n" + "=" * 60 + "\n>>> " + script + "\n" + "=" * 60)
    return subprocess.call([sys.executable, os.path.join(HERE, script)])


if __name__ == "__main__":
    rc1 = _run("e2e_apptest.py")
    rc2 = _run("e2e_playwright.py")
    total = rc1 or rc2
    print("\n=== RESULTADO E2E: " + ("VERDE" if total == 0 else "FALHAS") + " ===")
    sys.exit(total)
