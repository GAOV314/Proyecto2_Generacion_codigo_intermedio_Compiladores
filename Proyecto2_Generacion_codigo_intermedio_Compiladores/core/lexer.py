"""Lexer mínimo para el subconjunto de .cps que necesita la parte de Linar
(clases, objetos, listas). No cubre control de flujo ni tipos completos:
eso corresponde a otros integrantes del equipo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from core.errors import LexError

KEYWORDS = {
    "class", "extends", "new", "this", "let", "function",
    "return", "print", "true", "false", "null",
}

TOKEN_SPEC = [
    ("SKIP", r"[ \t\r]+"),
    ("NEWLINE", r"\n"),
    ("COMMENT", r"//[^\n]*"),
    ("NUMBER", r"\d+(\.\d+)?"),
    ("STRING", r'"(?:[^"\\]|\\.)*"'),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("EQEQ", r"=="),
    ("NEQ", r"!="),
    ("LE", r"<="),
    ("GE", r">="),
    ("OP", r"[+\-*/=<>.,;:(){}\[\]]"),
]

MASTER_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))


@dataclass
class Token:
    type: str
    value: str
    line: int

    def __repr__(self) -> str:
        return f"Token({self.type!r}, {self.value!r}, L{self.line})"


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    line = 1
    pos = 0
    length = len(source)
    while pos < length:
        match = MASTER_RE.match(source, pos)
        if not match:
            raise LexError(f"Carácter inesperado: {source[pos]!r}", line)
        kind = match.lastgroup
        text = match.group()
        if kind == "NEWLINE":
            line += 1
        elif kind in ("SKIP", "COMMENT"):
            pass
        elif kind == "IDENT" and text in KEYWORDS:
            tokens.append(Token(text, text, line))
        elif kind == "IDENT":
            tokens.append(Token("IDENT", text, line))
        elif kind == "STRING":
            tokens.append(Token("STRING", text[1:-1], line))
        elif kind == "NUMBER":
            tokens.append(Token("NUMBER", text, line))
        else:
            tokens.append(Token(text, text, line))
        pos = match.end()
    tokens.append(Token("EOF", "", line))
    return tokens
