"""Parser recursivo descendente para el subconjunto de .cps de la parte de
Linar (clases, objetos, listas). No implementa control de flujo
(if/while/for), eso es responsabilidad de la parte de Gadiel.
"""
from __future__ import annotations

from core import ast_nodes as ast
from core.errors import ParseError
from core.lexer import Token, tokenize


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # -- utilidades -----------------------------------------------------
    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != "EOF":
            self.pos += 1
        return tok

    def check(self, type_: str) -> bool:
        return self.current.type == type_

    def match(self, *types: str) -> bool:
        if self.current.type in types:
            self.advance()
            return True
        return False

    def expect(self, type_: str) -> Token:
        if self.current.type != type_:
            raise ParseError(
                f"Se esperaba '{type_}' pero se encontró '{self.current.type}'",
                self.current.line,
            )
        return self.advance()

    # -- gramática --------------------------------------------------------
    def parse_program(self) -> ast.Program:
        line = self.current.line
        classes: list[ast.ClassDecl] = []
        statements: list[ast.Stmt] = []
        while not self.check("EOF"):
            if self.check("class"):
                classes.append(self.parse_class_decl())
            else:
                statements.append(self.parse_stmt())
        return ast.Program(line, classes, statements)

    def parse_class_decl(self) -> ast.ClassDecl:
        line = self.expect("class").line
        name = self.expect("IDENT").value
        parent = None
        if self.match("extends"):
            parent = self.expect("IDENT").value
        self.expect("{")
        fields: list[ast.FieldDecl] = []
        methods: list[ast.MethodDecl] = []
        while not self.check("}"):
            if self.check("let"):
                fields.append(self.parse_field_decl())
            elif self.check("function"):
                methods.append(self.parse_method_decl())
            else:
                raise ParseError(
                    f"Miembro de clase inesperado: '{self.current.type}'", self.current.line
                )
        self.expect("}")
        return ast.ClassDecl(line, name, parent, fields, methods)

    def parse_field_decl(self) -> ast.FieldDecl:
        line = self.expect("let").line
        name = self.expect("IDENT").value
        type_name = None
        if self.match(":"):
            type_name = self.expect("IDENT").value
        self.expect(";")
        return ast.FieldDecl(line, name, type_name)

    def parse_method_decl(self) -> ast.MethodDecl:
        line = self.expect("function").line
        name = self.expect("IDENT").value
        self.expect("(")
        params: list[tuple[str, str | None]] = []
        if not self.check(")"):
            params.append(self.parse_param())
            while self.match(","):
                params.append(self.parse_param())
        self.expect(")")
        body = self.parse_block()
        return ast.MethodDecl(line, name, params, body)

    def parse_param(self) -> tuple[str, str | None]:
        name = self.expect("IDENT").value
        type_name = None
        if self.match(":"):
            type_name = self.expect("IDENT").value
        return (name, type_name)

    def parse_block(self) -> list[ast.Stmt]:
        self.expect("{")
        stmts = []
        while not self.check("}"):
            stmts.append(self.parse_stmt())
        self.expect("}")
        return stmts

    def parse_stmt(self) -> ast.Stmt:
        if self.check("let"):
            return self.parse_var_decl()
        if self.check("return"):
            return self.parse_return_stmt()
        if self.check("print"):
            return self.parse_print_stmt()
        return self.parse_assign_or_expr_stmt()

    def parse_var_decl(self) -> ast.VarDecl:
        line = self.expect("let").line
        name = self.expect("IDENT").value
        type_name = None
        if self.match(":"):
            type_name = self.expect("IDENT").value
        initializer = None
        if self.match("="):
            initializer = self.parse_expr()
        self.expect(";")
        return ast.VarDecl(line, name, type_name, initializer)

    def parse_return_stmt(self) -> ast.ReturnStmt:
        line = self.expect("return").line
        value = None
        if not self.check(";"):
            value = self.parse_expr()
        self.expect(";")
        return ast.ReturnStmt(line, value)

    def parse_print_stmt(self) -> ast.PrintStmt:
        line = self.expect("print").line
        self.expect("(")
        value = self.parse_expr()
        self.expect(")")
        self.expect(";")
        return ast.PrintStmt(line, value)

    def parse_assign_or_expr_stmt(self) -> ast.Stmt:
        line = self.current.line
        expr = self.parse_expr()
        if self.match("="):
            value = self.parse_expr()
            self.expect(";")
            return ast.Assign(line, expr, value)
        self.expect(";")
        return ast.ExprStmt(line, expr)

    # -- expresiones (precedencia: comparación > aditiva > multiplicativa) --
    def parse_expr(self) -> ast.Expr:
        return self.parse_comparison()

    def parse_comparison(self) -> ast.Expr:
        left = self.parse_additive()
        while self.current.type in ("==", "!=", "<=", ">=", "<", ">"):
            op = self.advance().type
            right = self.parse_additive()
            left = ast.BinaryOp(left.line, op, left, right)
        return left

    def parse_additive(self) -> ast.Expr:
        left = self.parse_multiplicative()
        while self.current.type in ("+", "-"):
            op = self.advance().type
            right = self.parse_multiplicative()
            left = ast.BinaryOp(left.line, op, left, right)
        return left

    def parse_multiplicative(self) -> ast.Expr:
        left = self.parse_postfix(self.parse_primary())
        while self.current.type in ("*", "/"):
            op = self.advance().type
            right = self.parse_postfix(self.parse_primary())
            left = ast.BinaryOp(left.line, op, left, right)
        return left

    def parse_postfix(self, expr: ast.Expr) -> ast.Expr:
        while True:
            if self.check("."):
                self.advance()
                name = self.expect("IDENT").value
                if self.check("("):
                    self.advance()
                    args = self.parse_args()
                    self.expect(")")
                    expr = ast.MethodCall(expr.line, expr, name, args)
                else:
                    expr = ast.AttrAccess(expr.line, expr, name)
            elif self.check("["):
                self.advance()
                index = self.parse_expr()
                self.expect("]")
                expr = ast.IndexExpr(expr.line, expr, index)
            else:
                break
        return expr

    def parse_args(self) -> list[ast.Expr]:
        args: list[ast.Expr] = []
        if not self.check(")"):
            args.append(self.parse_expr())
            while self.match(","):
                args.append(self.parse_expr())
        return args

    def parse_primary(self) -> ast.Expr:
        tok = self.current
        if tok.type == "NUMBER":
            self.advance()
            value = float(tok.value) if "." in tok.value else int(tok.value)
            return ast.Literal(tok.line, value)
        if tok.type == "STRING":
            self.advance()
            return ast.Literal(tok.line, tok.value)
        if tok.type == "true":
            self.advance()
            return ast.Literal(tok.line, True)
        if tok.type == "false":
            self.advance()
            return ast.Literal(tok.line, False)
        if tok.type == "null":
            self.advance()
            return ast.Literal(tok.line, None)
        if tok.type == "this":
            self.advance()
            return ast.ThisExpr(tok.line)
        if tok.type == "new":
            self.advance()
            class_name = self.expect("IDENT").value
            self.expect("(")
            args = self.parse_args()
            self.expect(")")
            return ast.NewExpr(tok.line, class_name, args)
        if tok.type == "IDENT":
            self.advance()
            return ast.Identifier(tok.line, tok.value)
        if tok.type == "(":
            self.advance()
            expr = self.parse_expr()
            self.expect(")")
            return expr
        if tok.type == "[":
            self.advance()
            elements: list[ast.Expr] = []
            if not self.check("]"):
                elements.append(self.parse_expr())
                while self.match(","):
                    elements.append(self.parse_expr())
            self.expect("]")
            return ast.ListLiteral(tok.line, elements)
        raise ParseError(f"Expresión inesperada: '{tok.type}'", tok.line)


def parse(source: str) -> ast.Program:
    tokens = tokenize(source)
    return Parser(tokens).parse_program()
