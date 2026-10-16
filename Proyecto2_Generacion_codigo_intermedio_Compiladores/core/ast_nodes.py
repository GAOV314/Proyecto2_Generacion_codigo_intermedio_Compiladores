"""Nodos de AST para el subconjunto del lenguaje que cubre la parte de
Linar (clases, objetos, herencia, listas) y la parte de Gadiel
(expresiones con precedencia, control de flujo y funciones).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Node:
    line: int


# ---- Programa ---------------------------------------------------------

@dataclass
class Program(Node):
    classes: list["ClassDecl"]
    statements: list["Stmt"]


# ---- Clases -------------------------------------------------------------

@dataclass
class FieldDecl(Node):
    name: str
    type_name: str | None


@dataclass
class MethodDecl(Node):
    name: str
    params: list[tuple[str, str | None]]  # (nombre, tipo opcional)
    body: list["Stmt"]


@dataclass
class ClassDecl(Node):
    name: str
    parent: str | None
    fields: list[FieldDecl]
    methods: list[MethodDecl]


# ---- Sentencias -----------------------------------------------------------

class Stmt(Node):
    pass


@dataclass
class VarDecl(Stmt):
    name: str
    type_name: str | None
    initializer: "Expr | None"
    is_const: bool = False


@dataclass
class Assign(Stmt):
    target: "Expr"  # Identifier | AttrAccess | IndexExpr
    value: "Expr"


@dataclass
class ReturnStmt(Stmt):
    value: "Expr | None"


@dataclass
class PrintStmt(Stmt):
    value: "Expr"


@dataclass
class ExprStmt(Stmt):
    expr: "Expr"


# ---- Control de flujo (parte de Gadiel) ------------------------------------

@dataclass
class IfStmt(Stmt):
    cond: "Expr"
    then_body: list["Stmt"]
    else_body: "list[Stmt] | None"


@dataclass
class WhileStmt(Stmt):
    cond: "Expr"
    body: list["Stmt"]


@dataclass
class DoWhileStmt(Stmt):
    body: list["Stmt"]
    cond: "Expr"


@dataclass
class ForStmt(Stmt):
    init: "Stmt | None"
    cond: "Expr | None"
    update: "Stmt | None"
    body: list["Stmt"]


@dataclass
class SwitchStmt(Stmt):
    subject: "Expr"
    cases: list[tuple["Expr", list["Stmt"]]]
    default_body: "list[Stmt] | None"


@dataclass
class BreakStmt(Stmt):
    pass


@dataclass
class ContinueStmt(Stmt):
    pass


# ---- Funciones (parte de Gadiel) -------------------------------------------
# FunctionDecl es un Stmt (no un miembro de Program aparte) para que pueda
# aparecer en cualquier lista de sentencias: nivel de programa, cuerpo de
# otra función (función anidada) o incluso dentro de un bloque if/while.


@dataclass
class FunctionDecl(Stmt):
    name: str
    params: list[tuple[str, str | None]]
    body: list["Stmt"]


# ---- Expresiones ----------------------------------------------------------

class Expr(Node):
    pass


@dataclass
class Literal(Expr):
    value: object


@dataclass
class Identifier(Expr):
    name: str


@dataclass
class ThisExpr(Expr):
    pass


@dataclass
class NewExpr(Expr):
    class_name: str
    args: list[Expr]


@dataclass
class AttrAccess(Expr):
    obj: Expr
    attr: str


@dataclass
class MethodCall(Expr):
    obj: Expr
    method: str
    args: list[Expr]


@dataclass
class ListLiteral(Expr):
    elements: list[Expr]


@dataclass
class IndexExpr(Expr):
    obj: Expr
    index: Expr


@dataclass
class BinaryOp(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass
class UnaryOp(Expr):
    op: str  # "-" | "!"
    operand: Expr


@dataclass
class LogicalOp(Expr):
    """Operadores lógicos de cortocircuito ('&&' / '||'), separados de
    BinaryOp para que el generador de código evalúe el operando derecho
    solo cuando sea necesario."""
    op: str
    left: Expr
    right: Expr


@dataclass
class CallExpr(Expr):
    """Llamada a una función libre o anidada por nombre (no un método de
    objeto, eso es MethodCall)."""
    name: str
    args: list[Expr]
