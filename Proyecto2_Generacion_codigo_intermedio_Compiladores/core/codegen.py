"""Generador de TAC para:
  - la parte de Linar: new/constructor, atributos, métodos, this, herencia
    y listas (creación + acceso indexado).
  - la parte de Gadiel: expresiones con precedencia/cortocircuito, control
    de flujo (if/while/do-while/for/switch/break/continue) y funciones
    (definición, llamada, retorno, recursión, funciones anidadas/closures).

Resolución de métodos: estática, siguiendo la cadena de herencia en tiempo
de compilación (no se implementa una vtable dinámica). Se documenta como
simplificación consciente dado el alcance de esta parte.

El tipo estático de una expresión solo se sigue "hacia adelante"
(declaración/anotación inicial); no hay refinamiento de tipos tras
reasignaciones. Cuando el tipo es desconocido, las validaciones de
atributos/métodos/indexación se omiten (asunción documentada).

Closures y funciones anidadas: el TAC que genera este módulo es simbólico
(usa nombres de variable, no direcciones/desplazamientos de un registro de
activación real; eso es responsabilidad de Wachuuu15). Por eso una función
anidada puede referirse directamente por nombre a una variable de la
función que la contiene: el "enlace de acceso" real entre registros de
activación es, de forma consciente, responsabilidad de esa otra parte del
proyecto. Aquí solo se resuelve correctamente el *alcance léxico* (qué
nombre es visible dónde) y el nombre calificado de la función a invocar.
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
        self.consts: set[str] = set()
        # Funciones visibles léxicamente desde este ámbito hacia adentro:
        # nombre corto -> (nombre_calificado_en_TAC, aridad).
        self.functions: dict[str, tuple[str, int]] = {}
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

    def is_const(self, name: str) -> bool:
        if name in self.declared:
            return name in self.consts
        return self.parent.is_const(name) if self.parent else False

    def declare_function(self, name: str, qualified_name: str, arity: int) -> None:
        self.functions[name] = (qualified_name, arity)

    def resolve_function(self, name: str) -> tuple[str, int] | None:
        if name in self.functions:
            return self.functions[name]
        return self.parent.resolve_function(name) if self.parent else None


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
        self._label_counter = 0
        # Pilas de etiquetas destino para 'break'/'continue'. 'switch' apila
        # en break_stack pero no en continue_stack (un continue dentro de un
        # switch se refiere al bucle que lo contiene, no al switch).
        self.break_stack: list[str] = []
        self.continue_stack: list[str] = []

    def new_label(self) -> str:
        self._label_counter += 1
        return f"L{self._label_counter}"

    def generate(self, program: ast.Program) -> TACProgram:
        self.symtab.register_classes(program.classes)
        for class_decl in program.classes:
            self._gen_class(class_decl)
        scope = Scope()
        self._gen_stmt_list(program.statements, self.program.main, scope, current_class=None, qualified_prefix="")
        return self.program

    # -- clases -----------------------------------------------------------
    def _gen_class(self, decl: ast.ClassDecl) -> None:
        info = self.symtab.classes[decl.name]
        for method in decl.methods:
            qualified_name = f"{decl.name}.{method.name}"
            func = self.program.new_function(qualified_name)
            scope = Scope()
            scope.declare("this", decl.name)
            for pname, ptype in method.params:
                scope.declare(pname, ptype)
            self._gen_stmt_list(
                method.body, func, scope, current_class=info, qualified_prefix=f"{qualified_name}."
            )

    # -- bloques de sentencias y funciones ------------------------------------
    def _gen_stmt_list(
        self,
        stmts: list[ast.Stmt],
        func: TACFunction,
        scope: Scope,
        current_class,
        qualified_prefix: str,
    ) -> None:
        # Pasada previa: registra en este ámbito las firmas de las funciones
        # declaradas directamente en este bloque (sin descender a bloques
        # anidados), igual que SymbolTable.register_classes pre-registra
        # clases. Esto habilita llamadas hacia adelante, recursión directa y
        # recursión mutua entre funciones hermanas del mismo bloque.
        for stmt in stmts:
            if isinstance(stmt, ast.FunctionDecl):
                if stmt.name in scope.functions:
                    raise SemanticError(
                        f"La función '{stmt.name}' ya está definida en este ámbito", stmt.line
                    )
                scope.declare_function(stmt.name, f"{qualified_prefix}{stmt.name}", len(stmt.params))

        for stmt in stmts:
            if isinstance(stmt, ast.FunctionDecl):
                self._gen_function_decl(stmt, scope, qualified_prefix)
            else:
                self._gen_stmt(stmt, func, scope, current_class, qualified_prefix)

    def _gen_function_decl(self, stmt: ast.FunctionDecl, parent_scope: Scope, qualified_prefix: str) -> None:
        qualified_name = f"{qualified_prefix}{stmt.name}"
        func = self.program.new_function(qualified_name)
        func_scope = Scope(parent=parent_scope)
        for pname, ptype in stmt.params:
            func_scope.declare(pname, ptype)
        self._gen_stmt_list(stmt.body, func, func_scope, current_class=None, qualified_prefix=f"{qualified_name}.")

    # -- sentencias ---------------------------------------------------------
    def _gen_stmt(
        self, stmt: ast.Stmt, func: TACFunction, scope: Scope, current_class, qualified_prefix: str = ""
    ) -> None:
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
        elif isinstance(stmt, ast.IfStmt):
            self._gen_if(stmt, func, scope, current_class, qualified_prefix)
        elif isinstance(stmt, ast.WhileStmt):
            self._gen_while(stmt, func, scope, current_class, qualified_prefix)
        elif isinstance(stmt, ast.DoWhileStmt):
            self._gen_do_while(stmt, func, scope, current_class, qualified_prefix)
        elif isinstance(stmt, ast.ForStmt):
            self._gen_for(stmt, func, scope, current_class, qualified_prefix)
        elif isinstance(stmt, ast.SwitchStmt):
            self._gen_switch(stmt, func, scope, current_class, qualified_prefix)
        elif isinstance(stmt, ast.BreakStmt):
            if not self.break_stack:
                raise SemanticError("'break' usado fuera de un bucle o switch", stmt.line)
            func.emit(f"goto {self.break_stack[-1]}")
        elif isinstance(stmt, ast.ContinueStmt):
            if not self.continue_stack:
                raise SemanticError("'continue' usado fuera de un bucle", stmt.line)
            func.emit(f"goto {self.continue_stack[-1]}")
        else:
            raise SemanticError(f"Sentencia no soportada: {type(stmt).__name__}", stmt.line)

    # -- control de flujo -----------------------------------------------------
    def _gen_if(self, stmt: ast.IfStmt, func: TACFunction, scope: Scope, current_class, qualified_prefix: str) -> None:
        cond_place, _ = self._gen_expr(stmt.cond, func, scope, current_class)
        end_label = self.new_label()
        if stmt.else_body is not None:
            else_label = self.new_label()
            func.emit(f"ifFalse {cond_place} goto {else_label}")
            self._gen_stmt_list(stmt.then_body, func, Scope(scope), current_class, qualified_prefix)
            func.emit(f"goto {end_label}")
            func.emit(f"{else_label}:")
            self._gen_stmt_list(stmt.else_body, func, Scope(scope), current_class, qualified_prefix)
        else:
            func.emit(f"ifFalse {cond_place} goto {end_label}")
            self._gen_stmt_list(stmt.then_body, func, Scope(scope), current_class, qualified_prefix)
        func.emit(f"{end_label}:")

    def _gen_while(
        self, stmt: ast.WhileStmt, func: TACFunction, scope: Scope, current_class, qualified_prefix: str
    ) -> None:
        start_label = self.new_label()
        end_label = self.new_label()
        func.emit(f"{start_label}:")
        cond_place, _ = self._gen_expr(stmt.cond, func, scope, current_class)
        func.emit(f"ifFalse {cond_place} goto {end_label}")
        self.break_stack.append(end_label)
        self.continue_stack.append(start_label)
        self._gen_stmt_list(stmt.body, func, Scope(scope), current_class, qualified_prefix)
        self.continue_stack.pop()
        self.break_stack.pop()
        func.emit(f"goto {start_label}")
        func.emit(f"{end_label}:")

    def _gen_do_while(
        self, stmt: ast.DoWhileStmt, func: TACFunction, scope: Scope, current_class, qualified_prefix: str
    ) -> None:
        start_label = self.new_label()
        cond_label = self.new_label()
        end_label = self.new_label()
        func.emit(f"{start_label}:")
        self.break_stack.append(end_label)
        self.continue_stack.append(cond_label)
        self._gen_stmt_list(stmt.body, func, Scope(scope), current_class, qualified_prefix)
        self.continue_stack.pop()
        self.break_stack.pop()
        func.emit(f"{cond_label}:")
        cond_place, _ = self._gen_expr(stmt.cond, func, scope, current_class)
        func.emit(f"if {cond_place} goto {start_label}")
        func.emit(f"{end_label}:")

    def _gen_for(
        self, stmt: ast.ForStmt, func: TACFunction, scope: Scope, current_class, qualified_prefix: str
    ) -> None:
        # El init vive en su propio ámbito (p. ej. 'let i = 0') visible para
        # la condición, el cuerpo y el update, pero no fuera del for.
        for_scope = Scope(scope)
        if stmt.init is not None:
            self._gen_stmt(stmt.init, func, for_scope, current_class, qualified_prefix)
        start_label = self.new_label()
        continue_label = self.new_label()
        end_label = self.new_label()
        func.emit(f"{start_label}:")
        if stmt.cond is not None:
            cond_place, _ = self._gen_expr(stmt.cond, func, for_scope, current_class)
            func.emit(f"ifFalse {cond_place} goto {end_label}")
        self.break_stack.append(end_label)
        self.continue_stack.append(continue_label)
        self._gen_stmt_list(stmt.body, func, Scope(for_scope), current_class, qualified_prefix)
        self.continue_stack.pop()
        self.break_stack.pop()
        func.emit(f"{continue_label}:")
        if stmt.update is not None:
            self._gen_stmt(stmt.update, func, for_scope, current_class, qualified_prefix)
        func.emit(f"goto {start_label}")
        func.emit(f"{end_label}:")

    def _gen_switch(
        self, stmt: ast.SwitchStmt, func: TACFunction, scope: Scope, current_class, qualified_prefix: str
    ) -> None:
        subject_place, _ = self._gen_expr(stmt.subject, func, scope, current_class)
        case_labels = [self.new_label() for _ in stmt.cases]
        default_label = self.new_label() if stmt.default_body is not None else None
        end_label = self.new_label()

        for (value_expr, _body), label in zip(stmt.cases, case_labels):
            value_place, _ = self._gen_expr(value_expr, func, scope, current_class)
            cmp_temp = self.temps.new_temp()
            func.emit(f"{cmp_temp} = {subject_place} == {value_place}")
            func.emit(f"if {cmp_temp} goto {label}")
        func.emit(f"goto {default_label if default_label else end_label}")

        # Los casos comparten un único ámbito hijo para que el "fallthrough"
        # (caer de un caso al siguiente sin 'break') vea las mismas variables.
        self.break_stack.append(end_label)
        switch_scope = Scope(scope)
        for (_value_expr, body), label in zip(stmt.cases, case_labels):
            func.emit(f"{label}:")
            self._gen_stmt_list(body, func, switch_scope, current_class, qualified_prefix)
        if default_label is not None:
            func.emit(f"{default_label}:")
            self._gen_stmt_list(stmt.default_body, func, switch_scope, current_class, qualified_prefix)
        self.break_stack.pop()
        func.emit(f"{end_label}:")

    def _gen_var_decl(self, stmt: ast.VarDecl, func: TACFunction, scope: Scope, current_class) -> None:
        if stmt.is_const and stmt.initializer is None:
            raise SemanticError(f"La constante '{stmt.name}' debe inicializarse", stmt.line)
        declared_type = stmt.type_name
        if stmt.initializer is not None:
            place, inferred_type = self._gen_expr(stmt.initializer, func, scope, current_class)
            declared_type = declared_type or inferred_type
            func.emit(f"{stmt.name} = {place}")
        scope.declare(stmt.name, declared_type)
        if stmt.is_const:
            scope.consts.add(stmt.name)

    def _gen_assign(self, stmt: ast.Assign, func: TACFunction, scope: Scope, current_class) -> None:
        target = stmt.target

        # Se evalúan primero las subexpresiones del target (objeto/índice) y
        # al final el valor, respetando el orden izquierda-a-derecha del
        # código fuente cuando ambos lados tienen efectos secundarios.
        if isinstance(target, ast.Identifier):
            if not scope.is_declared(target.name):
                raise SemanticError(f"Variable '{target.name}' no declarada", target.line)
            if scope.is_const(target.name):
                raise SemanticError(f"No se puede reasignar la constante '{target.name}'", target.line)
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

        if isinstance(expr, ast.UnaryOp):
            operand_place, _ = self._gen_expr(expr.operand, func, scope, current_class)
            temp = self.temps.new_temp()
            func.emit(f"{temp} = {expr.op} {operand_place}")
            return temp, None

        if isinstance(expr, ast.LogicalOp):
            return self._gen_logical(expr, func, scope, current_class)

        if isinstance(expr, ast.CallExpr):
            return self._gen_call(expr, func, scope, current_class)

        raise SemanticError(f"Expresión no soportada: {type(expr).__name__}", expr.line)

    def _gen_logical(self, expr: ast.LogicalOp, func: TACFunction, scope: Scope, current_class):
        # Evaluación de cortocircuito: el operando derecho de '&&' solo se
        # evalúa si el izquierdo es verdadero (y el de '||' solo si el
        # izquierdo es falso), como en la mayoría de lenguajes imperativos.
        left_place, _ = self._gen_expr(expr.left, func, scope, current_class)
        result = self.temps.new_temp()
        short_circuit_label = self.new_label()
        end_label = self.new_label()
        if expr.op == "&&":
            func.emit(f"ifFalse {left_place} goto {short_circuit_label}")
            right_place, _ = self._gen_expr(expr.right, func, scope, current_class)
            func.emit(f"{result} = {right_place}")
            func.emit(f"goto {end_label}")
            func.emit(f"{short_circuit_label}:")
            func.emit(f"{result} = false")
        else:  # "||"
            func.emit(f"if {left_place} goto {short_circuit_label}")
            right_place, _ = self._gen_expr(expr.right, func, scope, current_class)
            func.emit(f"{result} = {right_place}")
            func.emit(f"goto {end_label}")
            func.emit(f"{short_circuit_label}:")
            func.emit(f"{result} = true")
        func.emit(f"{end_label}:")
        return result, None

    def _gen_call(self, expr: ast.CallExpr, func: TACFunction, scope: Scope, current_class):
        resolved = scope.resolve_function(expr.name)
        if resolved is None:
            raise SemanticError(f"La función '{expr.name}' no está definida", expr.line)
        qualified_name, arity = resolved
        if arity != len(expr.args):
            raise SemanticError(
                f"La función '{expr.name}' espera {arity} argumento(s) pero se pasaron {len(expr.args)}",
                expr.line,
            )
        arg_places = [self._gen_expr(a, func, scope, current_class)[0] for a in expr.args]
        for place in arg_places:
            func.emit(f"param {place}")
        temp = self.temps.new_temp()
        func.emit(f"{temp} = call {qualified_name}, {len(arg_places)}")
        return temp, None

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
