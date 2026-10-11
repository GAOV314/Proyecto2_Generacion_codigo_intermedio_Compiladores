"""Driver mínimo: fuente .cps -> TAC, para la parte de clases/objetos/listas.

Uso: python driver.py archivo.cps
"""
from __future__ import annotations

import sys

from core.codegen import CodeGenerator
from core.errors import CompilerError
from core.parser import parse


def compile_source(source: str) -> str:
    program = parse(source)
    generator = CodeGenerator()
    tac_program = generator.generate(program)
    return tac_program.render()


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python driver.py archivo.cps", file=sys.stderr)
        return 2
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        source = f.read()
    try:
        print(compile_source(source))
    except CompilerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
