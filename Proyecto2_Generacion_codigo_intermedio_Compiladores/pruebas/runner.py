"""Runner de la batería de pruebas de TAC para clases, objetos y listas
(parte de Linar).

- pruebas/casos/validos/*.cps   -> deben compilar sin errores.
- pruebas/casos/invalidos/*.cps -> deben fallar; la primera línea del
  archivo debe ser un comentario `// ERROR: <subcadena esperada>` que se
  compara (sin distinguir mayúsculas/minúsculas) contra el mensaje de error
  producido por el compilador.

Uso: python pruebas/runner.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.errors import CompilerError  # noqa: E402
from driver import compile_source  # noqa: E402

CASOS_DIR = Path(__file__).resolve().parent / "casos"
VALIDOS_DIR = CASOS_DIR / "validos"
INVALIDOS_DIR = CASOS_DIR / "invalidos"


def run_validos() -> tuple[int, int]:
    passed = failed = 0
    for path in sorted(VALIDOS_DIR.glob("*.cps")):
        source = path.read_text(encoding="utf-8")
        try:
            compile_source(source)
            print(f"PASS  {path.name}")
            passed += 1
        except CompilerError as e:
            print(f"FAIL  {path.name}: se esperaba éxito, pero falló con: {e}")
            failed += 1
    return passed, failed


def run_invalidos() -> tuple[int, int]:
    passed = failed = 0
    for path in sorted(INVALIDOS_DIR.glob("*.cps")):
        source = path.read_text(encoding="utf-8")
        first_line = source.splitlines()[0] if source else ""
        if not first_line.strip().startswith("// ERROR:"):
            print(f"FAIL  {path.name}: falta el comentario '// ERROR: ...' en la primera línea")
            failed += 1
            continue
        expected = first_line.split("// ERROR:", 1)[1].strip().lower()
        try:
            compile_source(source)
            print(f"FAIL  {path.name}: se esperaba un error ('{expected}') pero compiló bien")
            failed += 1
        except CompilerError as e:
            if expected in str(e).lower():
                print(f"PASS  {path.name}")
                passed += 1
            else:
                print(f"FAIL  {path.name}: se esperaba error con '{expected}' pero fue: {e}")
                failed += 1
    return passed, failed


def main() -> int:
    print("== Casos válidos ==")
    v_pass, v_fail = run_validos()
    print("\n== Casos inválidos ==")
    i_pass, i_fail = run_invalidos()

    total_pass = v_pass + i_pass
    total_fail = v_fail + i_fail
    total = total_pass + total_fail
    print(f"\nResumen: {total_pass}/{total} pruebas pasaron ({total_fail} fallidas)")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
