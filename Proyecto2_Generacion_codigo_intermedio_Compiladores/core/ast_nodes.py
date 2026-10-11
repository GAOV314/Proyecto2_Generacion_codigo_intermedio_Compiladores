"""Nodos de AST para el subconjunto del lenguaje que cubre la parte de
Linar: clases, objetos (new/this/atributos/métodos/herencia) y listas.
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
