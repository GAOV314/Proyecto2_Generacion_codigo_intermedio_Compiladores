"""Errores del compilador para la parte de clases/objetos/listas (Linar)."""


class CompilerError(Exception):
    def __init__(self, message: str, line: int | None = None):
        self.message = message
        self.line = line
        location = f" (línea {line})" if line is not None else ""
        super().__init__(f"{message}{location}")


class LexError(CompilerError):
    pass


class ParseError(CompilerError):
    pass


class SemanticError(CompilerError):
    pass
