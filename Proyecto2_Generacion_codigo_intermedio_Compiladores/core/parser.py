"""Parser recursivo descendente para el subconjunto de .cps que cubre la
parte de Linar (clases, objetos, listas) y la parte de Gadiel (expresiones
con precedencia, control de flujo y funciones).
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
        if self.check("let") or self.check("const"):
            return self.parse_var_decl()
        if self.check("return"):
            return self.parse_return_stmt()
        if self.check("print"):
            return self.parse_print_stmt()
        if self.check("if"):
            return self.parse_if_stmt()
        if self.check("while"):
            return self.parse_while_stmt()
        if self.check("do"):
            return self.parse_do_while_stmt()
        if self.check("for"):
            return self.parse_for_stmt()
        if self.check("switch"):
            return self.parse_switch_stmt()
        if self.check("break"):
            return self.parse_break_stmt()
        if self.check("continue"):
            return self.parse_continue_stmt()
        if self.check("function"):
            return self.parse_function_decl()
        return self.parse_assign_or_expr_stmt()

    def _parse_var_decl_head(self) -> ast.VarDecl:
        is_const = self.check("const")
        line = self.advance().line  # consume 'let' o 'const'
        name = self.expect("IDENT").value
        type_name = None
        if self.match(":"):
            type_name = self.expect("IDENT").value
        initializer = None
        if self.match("="):
            initializer = self.parse_expr()
        return ast.VarDecl(line, name, type_name, initializer, is_const)

    def parse_var_decl(self) -> ast.VarDecl:
        decl = self._parse_var_decl_head()
        self.expect(";")
        return decl

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

    def _parse_assign_or_expr_head(self) -> ast.Stmt:
        line = self.current.line
        expr = self.parse_expr()
        if self.match("="):
            value = self.parse_expr()
            return ast.Assign(line, expr, value)
        return ast.ExprStmt(line, expr)

    def parse_assign_or_expr_stmt(self) -> ast.Stmt:
        stmt = self._parse_assign_or_expr_head()
        self.expect(";")
        return stmt

    # -- control de flujo ---------------------------------------------------
    def parse_if_stmt(self) -> ast.IfStmt:
        line = self.expect("if").line
        self.expect("(")
        cond = self.parse_expr()
        self.expect(")")
        then_body = self.parse_block()
        else_body: list[ast.Stmt] | None = None
        if self.match("else"):
            if self.check("if"):
                else_body = [self.parse_if_stmt()]
            else:
                else_body = self.parse_block()
        return ast.IfStmt(line, cond, then_body, else_body)

    def parse_while_stmt(self) -> ast.WhileStmt:
        line = self.expect("while").line
        self.expect("(")
        cond = self.parse_expr()
        self.expect(")")
        body = self.parse_block()
        return ast.WhileStmt(line, cond, body)

    def parse_do_while_stmt(self) -> ast.DoWhileStmt:
        line = self.expect("do").line
        body = self.parse_block()
        self.expect("while")
        self.expect("(")
        cond = self.parse_expr()
        self.expect(")")
        self.expect(";")
        return ast.DoWhileStmt(line, body, cond)

    def parse_for_stmt(self) -> ast.ForStmt:
        line = self.expect("for").line
        self.expect("(")
        init: ast.Stmt | None = None
        if not self.check(";"):
            if self.check("let") or self.check("const"):
                init = self._parse_var_decl_head()
            else:
                init = self._parse_assign_or_expr_head()
        self.expect(";")
        cond: ast.Expr | None = None
        if not self.check(";"):
            cond = self.parse_expr()
        self.expect(";")
        update: ast.Stmt | None = None
        if not self.check(")"):
            update = self._parse_assign_or_expr_head()
        self.expect(")")
        body = self.parse_block()
        return ast.ForStmt(line, init, cond, update, body)

    def parse_switch_stmt(self) -> ast.SwitchStmt:
        line = self.expect("switch").line
        self.expect("(")
        subject = self.parse_expr()
        self.expect(")")
        self.expect("{")
        cases: list[tuple[ast.Expr, list[ast.Stmt]]] = []
        default_body: list[ast.Stmt] | None = None
        while not self.check("}"):
            if self.match("case"):
                value = self.parse_expr()
                self.expect(":")
                cases.append((value, self._parse_case_body()))
            elif self.match("default"):
                self.expect(":")
                default_body = self._parse_case_body()
            else:
                raise ParseError(
                    f"Se esperaba 'case' o 'default' pero se encontró '{self.current.type}'",
                    self.current.line,
                )
        self.expect("}")
        return ast.SwitchStmt(line, subject, cases, default_body)

    def _parse_case_body(self) -> list[ast.Stmt]:
        body: list[ast.Stmt] = []
        while not self.check("case") and not self.check("default") and not self.check("}"):
            body.append(self.parse_stmt())
        return body

    def parse_break_stmt(self) -> ast.BreakStmt:
        line = self.expect("break").line
        self.expect(";")
        return ast.BreakStmt(line)

    def parse_continue_stmt(self) -> ast.ContinueStmt:
        line = self.expect("continue").line
        self.expect(";")
        return ast.ContinueStmt(line)

    # -- funciones ------------------------------------------------------------
    def parse_function_decl(self) -> ast.FunctionDecl:
        line = self.expect("function").line
        name = self.expect("IDENT").value
        self.expect("(")
        params: list[tuple[str, str | None]] = []
        if not self.check(")"):
            params.append(self.parse_param())
            while self.match(","):
                params.append(self.parse_param())
        self.expect(")")
        if self.match(":"):
            self.expect("IDENT")  # tipo de retorno anotado; no se valida (fuera de alcance)
        body = self.parse_block()
        return ast.FunctionDecl(line, name, params, body)

    # -- expresiones --------------------------------------------------------
    # Precedencia (de menor a mayor): || > && > comparación > aditiva >
    # multiplicativa > unaria (-, !) > postfijo (.attr, [i], llamada).
    def parse_expr(self) -> ast.Expr:
        return self.parse_logical_or()

    def parse_logical_or(self) -> ast.Expr:
        left = self.parse_logical_and()
        while self.check("||"):
            op = self.advance().type
            right = self.parse_logical_and()
            left = ast.LogicalOp(left.line, op, left, right)
        return left

    def parse_logical_and(self) -> ast.Expr:
        left = self.parse_comparison()
        while self.check("&&"):
            op = self.advance().type
            right = self.parse_comparison()
            left = ast.LogicalOp(left.line, op, left, right)
        return left

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
        left = self.parse_unary()
        while self.current.type in ("*", "/"):
            op = self.advance().type
            right = self.parse_unary()
            left = ast.BinaryOp(left.line, op, left, right)
        return left

    def parse_unary(self) -> ast.Expr:
        if self.current.type in ("-", "!"):
            op = self.advance()
            operand = self.parse_unary()
            return ast.UnaryOp(op.line, op.type, operand)
        return self.parse_postfix(self.parse_primary())

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
            if self.check("("):
                self.advance()
                args = self.parse_args()
                self.expect(")")
                return ast.CallExpr(tok.line, tok.value, args)
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
