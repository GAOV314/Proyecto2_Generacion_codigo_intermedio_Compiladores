"""Generador de TAC para la parte de Linar: new/constructor, atributos,
métodos, this, herencia y listas (creación + acceso indexado).

Resolución de métodos: estática, siguiendo la cadena de herencia en tiempo
de compilación (no se implementa una vtable dinámica). Se documenta como
simplificación consciente dado el alcance de esta parte.

El tipo estático de una expresión solo se seguiste "hacia adelante"
(declaración/anotación inicial); no hay refinamiento de tipos tras
reasignaciones. Cuando el tipo es desconocido, las validaciones de
atributos/métodos/indexación se omiten (asunción documentada).
"""
from __future__ import annotations

from core import ast_nodes as ast
from core.errors import SemanticError
from core.symbols import SymbolTable
from core.tac import TACFunction, TACProgram, TempManager

# Sentinel de tipo estático para listas. No puede chocar con ningún nombre de
# clase de usuario porque `<` y `>` no forman parte de un IDENT válido
# (core/lexer.py), a diferencia de usar literalmente "list".
LIST_TYPE = "<list>"


class Scope:
    def __init__(self, parent: "Scope | None" = None) -> None:
        self.vars: dict[str, str | None] = {}
        self.declared: set[str] = set()
        self.parent = parent

    def declare(self, name: str, type_: str | None) -> None:
        self.declared.add(name)
        self.vars[name] = type_

    def is_declared(self, name: str) -> bool:
        if name in self.declared:
            return True
        return self.parent.is_declared(name) if self.parent else False

    def lookup_type(self, name: str) -> str | None:
        if name in self.vars:
            return self.vars[name]
        return self.parent.lookup_type(name) if self.parent else None


def _literal_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


class CodeGenerator:
    def __init__(self, symtab: SymbolTable | None = None) -> None:
        self.symtab = symtab or SymbolTable()
        self.temps = TempManager()
        self.program = TACProgram()

    def generate(self, program: ast.Program) -> TACProgram:
        self.symtab.register_classes(program.classes)
        for class_decl in program.classes:
            self._gen_class(class_decl)
        scope = Scope()
        for stmt in program.statements:
            self._gen_stmt(stmt, self.program.main, scope, current_class=None)
        return self.program

    # -- clases -----------------------------------------------------------
    def _gen_class(self, decl: ast.ClassDecl) -> None:
        info = self.symtab.classes[decl.name]
        for method in decl.methods:
            func = self.program.new_function(f"{decl.name}.{method.name}")
            scope = Scope()
            scope.declare("this", decl.name)
            for pname, ptype in method.params:
                scope.declare(pname, ptype)
            for stmt in method.body:
                self._gen_stmt(stmt, func, scope, current_class=info)

    # -- sentencias ---------------------------------------------------------
    def _gen_stmt(self, stmt: ast.Stmt, func: TACFunction, scope: Scope, current_class) -> None:
        if isinstance(stmt, ast.VarDecl):
            self._gen_var_decl(stmt, func, scope, current_class)
        elif isinstance(stmt, ast.Assign):
            self._gen_assign(stmt, func, scope, current_class)
        elif isinstance(stmt, ast.ReturnStmt):
            if stmt.value is not None:
                place, _ = self._gen_expr(stmt.value, func, scope, current_class)
                func.emit(f"return {place}")
            else:
                func.emit("return")
        elif isinstance(stmt, ast.PrintStmt):
            place, _ = self._gen_expr(stmt.value, func, scope, current_class)
            func.emit(f"param {place}")
            func.emit("call print, 1")
        elif isinstance(stmt, ast.ExprStmt):
            self._gen_expr(stmt.expr, func, scope, current_class)
        else:
            raise SemanticError(f"Sentencia no soportada: {type(stmt).__name__}", stmt.line)

    def _gen_var_decl(self, stmt: ast.VarDecl, func: TACFunction, scope: Scope, current_class) -> None:
        declared_type = stmt.type_name
        if stmt.initializer is not None:
            place, inferred_type = self._gen_expr(stmt.initializer, func, scope, current_class)
            declared_type = declared_type or inferred_type
            func.emit(f"{stmt.name} = {place}")
        scope.declare(stmt.name, declared_type)

    def _gen_assign(self, stmt: ast.Assign, func: TACFunction, scope: Scope, current_class) -> None:
        target = stmt.target

        # Se evalúan primero las subexpresiones del target (objeto/índice) y
        # al final el valor, respetando el orden izquierda-a-derecha del
        # código fuente cuando ambos lados tienen efectos secundarios.
        if isinstance(target, ast.Identifier):
            if not scope.is_declared(target.name):
                raise SemanticError(f"Variable '{target.name}' no declarada", target.line)
            value_place, _ = self._gen_expr(stmt.value, func, scope, current_class)
            func.emit(f"{target.name} = {value_place}")
        elif isinstance(target, ast.AttrAccess):
            obj_place, obj_type = self._gen_expr(target.obj, func, scope, current_class)
            self._check_attr(obj_type, target.attr, target.line)
            value_place, _ = self._gen_expr(stmt.value, func, scope, current_class)
            func.emit(f"{obj_place}.{target.attr} = {value_place}")
        elif isinstance(target, ast.IndexExpr):
            obj_place, obj_type = self._gen_expr(target.obj, func, scope, current_class)
            self._check_indexable(obj_type, target.line)
            idx_place, _ = self._gen_expr(target.index, func, scope, current_class)
            value_place, _ = self._gen_expr(stmt.value, func, scope, current_class)
            func.emit(f"{obj_place}[{idx_place}] = {value_place}")
        else:
            raise SemanticError("Destino de asignación inválido", target.line)

    # -- expresiones ------------------------------------------------------
    def _gen_expr(self, expr: ast.Expr, func: TACFunction, scope: Scope, current_class):
        if isinstance(expr, ast.Literal):
            return _literal_text(expr.value), None

        if isinstance(expr, ast.Identifier):
            if not scope.is_declared(expr.name):
                raise SemanticError(f"Variable '{expr.name}' no declarada", expr.line)
            return expr.name, scope.lookup_type(expr.name)

        if isinstance(expr, ast.ThisExpr):
            if current_class is None:
                raise SemanticError("'this' usado fuera de un método", expr.line)
            return "this", current_class.name

        if isinstance(expr, ast.NewExpr):
            return self._gen_new(expr, func, scope, current_class)

        if isinstance(expr, ast.AttrAccess):
            obj_place, obj_type = self._gen_expr(expr.obj, func, scope, current_class)
            self._check_attr(obj_type, expr.attr, expr.line)
            temp = self.temps.new_temp()
            func.emit(f"{temp} = {obj_place}.{expr.attr}")
            return temp, self._field_type(obj_type, expr.attr)

        if isinstance(expr, ast.MethodCall):
            return self._gen_method_call(expr, func, scope, current_class)

        if isinstance(expr, ast.ListLiteral):
            return self._gen_list_literal(expr, func, scope, current_class)

        if isinstance(expr, ast.IndexExpr):
            obj_place, obj_type = self._gen_expr(expr.obj, func, scope, current_class)
            self._check_indexable(obj_type, expr.line)
            idx_place, _ = self._gen_expr(expr.index, func, scope, current_class)
            temp = self.temps.new_temp()
            func.emit(f"{temp} = {obj_place}[{idx_place}]")
            return temp, None

        if isinstance(expr, ast.BinaryOp):
            left_place, _ = self._gen_expr(expr.left, func, scope, current_class)
            right_place, _ = self._gen_expr(expr.right, func, scope, current_class)
            temp = self.temps.new_temp()
            func.emit(f"{temp} = {left_place} {expr.op} {right_place}")
            return temp, None

        raise SemanticError(f"Expresión no soportada: {type(expr).__name__}", expr.line)

    def _gen_new(self, expr: ast.NewExpr, func: TACFunction, scope: Scope, current_class):
        class_info = self.symtab.get_class(expr.class_name, expr.line)
        temp = self.temps.new_temp()
        func.emit(f"{temp} = new {expr.class_name}")

        arg_places = [self._gen_expr(a, func, scope, current_class)[0] for a in expr.args]
        constructor = class_info.resolve_method("constructor")

        if constructor is None:
            if expr.args:
                raise SemanticError(
                    f"La clase '{expr.class_name}' no define constructor pero se pasaron argumentos",
                    expr.line,
                )
        else:
            def_class, method = constructor
            expected = len(method.params)
            got = len(expr.args)
            if expected != got:
                raise SemanticError(
                    f"El constructor de '{expr.class_name}' espera {expected} argumento(s) "
                    f"pero se pasaron {got}",
                    expr.line,
                )
            func.emit(f"param {temp}")
            for place in arg_places:
                func.emit(f"param {place}")
            func.emit(f"call {def_class}.constructor, {got + 1}")

        return temp, expr.class_name

    def _gen_method_call(self, expr: ast.MethodCall, func: TACFunction, scope: Scope, current_class):
        obj_place, obj_type = self._gen_expr(expr.obj, func, scope, current_class)
        if obj_type == LIST_TYPE:
            raise SemanticError("No se puede invocar métodos sobre una lista", expr.line)

        arg_places = [self._gen_expr(a, func, scope, current_class)[0] for a in expr.args]

        call_target = f"{obj_type}.{expr.method}" if obj_type else expr.method
        if obj_type is not None:
            class_info = self.symtab.classes.get(obj_type)
            if class_info is not None:
                resolved = class_info.resolve_method(expr.method)
                if resolved is None:
                    raise SemanticError(
                        f"La clase '{obj_type}' no tiene el método '{expr.method}'", expr.line
                    )
                def_class, method_decl = resolved
                if len(method_decl.params) != len(expr.args):
                    raise SemanticError(
                        f"El método '{expr.method}' de '{obj_type}' espera "
                        f"{len(method_decl.params)} argumento(s) pero se pasaron {len(expr.args)}",
                        expr.line,
                    )
                call_target = f"{def_class}.{expr.method}"

        func.emit(f"param {obj_place}")
        for place in arg_places:
            func.emit(f"param {place}")
        temp = self.temps.new_temp()
        func.emit(f"{temp} = call {call_target}, {len(arg_places) + 1}")
        return temp, None

    def _gen_list_literal(self, expr: ast.ListLiteral, func: TACFunction, scope: Scope, current_class):
        elem_places = [self._gen_expr(e, func, scope, current_class)[0] for e in expr.elements]
        temp = self.temps.new_temp()
        func.emit(f"{temp} = newlist {len(elem_places)}")
        for i, place in enumerate(elem_places):
            func.emit(f"{temp}[{i}] = {place}")
        return temp, LIST_TYPE

    # -- validaciones auxiliares --------------------------------------------
    def _check_attr(self, obj_type: str | None, attr: str, line: int) -> None:
        if obj_type is None:
            # Tipo genuinamente desconocido (sin anotación/inferencia): se
            # omite la validación, como documenta el módulo.
            return
        if obj_type == LIST_TYPE:
            raise SemanticError("No se puede acceder a atributos de una lista", line)
        class_info = self.symtab.classes.get(obj_type)
        if class_info is None:
            # Tipo conocido (p. ej. Int, String) pero no es una clase: no
            # tiene atributos, a diferencia de un tipo realmente desconocido.
            raise SemanticError(
                f"No se puede acceder a atributos de un valor de tipo '{obj_type}'", line
            )
        if not class_info.has_field(attr):
            raise SemanticError(f"La clase '{obj_type}' no tiene el atributo '{attr}'", line)

    def _field_type(self, obj_type: str | None, attr: str) -> str | None:
        if not obj_type:
            return None
        class_info = self.symtab.classes.get(obj_type)
        return class_info.field_type(attr) if class_info else None

    def _check_indexable(self, obj_type: str | None, line: int) -> None:
        if obj_type is None or obj_type == LIST_TYPE:
            return
        raise SemanticError(
            f"No se puede indexar un valor de tipo '{obj_type}' (no es una lista)", line
        )
