"""Driver y CLI: fuente .cps -> TAC. Integra el front-end completo (clases,
objetos, listas, expresiones, control de flujo, funciones) y, opcionalmente,
el reporte de la tabla de símbolos extendida (direcciones, registros de
activación y resolución de closures).

Uso: python driver.py archivo.cps [--symbols]
"""
from __future__ import annotations

import sys

from core.codegen import CodeGenerator
from core.errors import CompilerError
from core.parser import parse


def compile_source(source: str) -> str:
    _, tac = compile_with_symbols(source)
    return tac


def compile_with_symbols(source: str) -> tuple[CodeGenerator, str]:
    """Compila y devuelve (generador, TAC). El generador expone
    `generator.symtab.render_report()` con el estado de la tabla de
    símbolos (direcciones, registros de activación, closures)."""
    program = parse(source)
    generator = CodeGenerator()
    tac_program = generator.generate(program)
    return generator, tac_program.render()


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--symbols"]
    show_symbols = "--symbols" in sys.argv[1:]
    if len(args) != 1:
        print("Uso: python driver.py archivo.cps [--symbols]", file=sys.stderr)
        return 2
    path = args[0]
    with open(path, encoding="utf-8") as f:
        source = f.read()
    try:
        generator, tac = compile_with_symbols(source)
        print(tac)
        if show_symbols:
            report = generator.symtab.render_report()
            if report:
                print(report)
    except CompilerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
