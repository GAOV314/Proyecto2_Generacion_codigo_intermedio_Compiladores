"""Tabla de símbolos mínima para clases/herencia/listas.

Nota de alcance: la tabla de símbolos completa (direcciones, desplazamientos
y registros de activación) es responsabilidad de Wachuuu15 en el reparto del
Proyecto 2. Aquí solo se modela lo necesario para resolver atributos,
métodos y herencia al generar TAC para la parte de Linar.
"""
from __future__ import annotations

from dataclasses import dataclass

from core import ast_nodes as ast
from core.errors import SemanticError


@dataclass
class ClassInfo:
    name: str
    parent_name: str | None
    own_fields: list[str]
    field_types: dict[str, str | None]
    methods: dict[str, ast.MethodDecl]
    parent: "ClassInfo | None" = None

    def has_field(self, name: str) -> bool:
        if name in self.own_fields:
            return True
        return self.parent.has_field(name) if self.parent else False

    def field_type(self, name: str) -> str | None:
        if name in self.field_types:
            return self.field_types[name]
        return self.parent.field_type(name) if self.parent else None

    def resolve_method(self, name: str) -> tuple[str, ast.MethodDecl] | None:
        """Busca el método en esta clase y, si no está, en los ancestros.

        Devuelve (nombre_de_la_clase_que_lo_define, MethodDecl) para
        resolución estática del destino de la llamada en TAC.
        """
        if name in self.methods:
            return self.name, self.methods[name]
        return self.parent.resolve_method(name) if self.parent else None


class SymbolTable:
    def __init__(self) -> None:
        self.classes: dict[str, ClassInfo] = {}

    def register_classes(self, class_decls: list[ast.ClassDecl]) -> None:
        # Pasada 1: registrar cada clase con sus campos y métodos propios.
        for decl in class_decls:
            if decl.name in self.classes:
                raise SemanticError(f"Clase '{decl.name}' ya está definida", decl.line)
            field_names = [f.name for f in decl.fields]
            field_types = {f.name: f.type_name for f in decl.fields}
            methods = {m.name: m for m in decl.methods}
            self.classes[decl.name] = ClassInfo(
                name=decl.name,
                parent_name=decl.parent,
                own_fields=field_names,
                field_types=field_types,
                methods=methods,
            )

        # Pasada 2: enlazar padres y detectar herencia inválida/cíclica.
        for decl in class_decls:
            info = self.classes[decl.name]
            if info.parent_name is None:
                continue
            parent = self.classes.get(info.parent_name)
            if parent is None:
                raise SemanticError(
                    f"La clase '{info.name}' extiende a '{info.parent_name}', que no está definida",
                    decl.line,
                )
            info.parent = parent

        for decl in class_decls:
            self._check_no_cycle(self.classes[decl.name], decl.line)

    def _check_no_cycle(self, info: ClassInfo, line: int) -> None:
        seen = {info.name}
        current = info.parent
        while current is not None:
            if current.name in seen:
                raise SemanticError(
                    f"Herencia cíclica detectada en la clase '{info.name}'", line
                )
            seen.add(current.name)
            current = current.parent

    def get_class(self, name: str, line: int) -> ClassInfo:
        info = self.classes.get(name)
        if info is None:
            raise SemanticError(f"Clase '{name}' no definida", line)
        return info
