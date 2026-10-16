"""Tabla de símbolos (parte de Wachuuu15): información de clases/herencia
para el resto del front-end, más el modelo de direcciones/desplazamientos,
tamaños, registros de activación y entornos léxicos (necesarios para
resolver el acceso a variables de closures) que extiende esa tabla.

Esta ampliación es deliberadamente un artefacto *paralelo* al TAC que ya
generan las partes de Linar y Gadiel: ese TAC sigue siendo simbólico (usa
nombres de variable, no direcciones), tal como está documentado en
core/codegen.py. Aquí se construye, en paralelo a esa generación, el modelo
de memoria que un backend real necesitaría (desplazamientos dentro de cada
registro de activación, tamaños por tipo, enlaces de control/acceso) y se
expone como una salida adicional del compilador (ver
`SymbolTable.render_report` y `driver.py --symbols`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core import ast_nodes as ast
from core.errors import SemanticError

# Tamaños de tipo en bytes. Simplificación consciente: el proyecto no genera
# código de máquina para una arquitectura real, así que se usan tamaños de
# palabra fijos y razonables en vez de derivarlos de un target concreto.
POINTER_SIZE = 8
TYPE_SIZES: dict[str, int] = {
    "Int": 4,
    "Float": 8,
    "Bool": 1,
    "String": POINTER_SIZE,  # referencia, no el contenido inline
}


def size_of(type_name: str | None) -> int:
    """Tamaño en bytes de un valor de tipo `type_name`. Los tipos no
    primitivos (clases, listas) y los tipos desconocidos (type_name=None,
    cuando el front-end no pudo inferirlo) se modelan como una referencia de
    tamaño de puntero, igual que 'String'."""
    if type_name is None:
        return POINTER_SIZE
    return TYPE_SIZES.get(type_name, POINTER_SIZE)


@dataclass
class ClassInfo:
    name: str
    parent_name: str | None
    own_fields: list[str]
    field_types: dict[str, str | None]
    methods: dict[str, ast.MethodDecl]
    parent: "ClassInfo | None" = None
    # Desplazamiento (en bytes, dentro del objeto) de cada campo *propio* de
    # esta clase. Se calcula una sola vez en SymbolTable._compute_layout.
    field_offsets: dict[str, int] = field(default_factory=dict)
    # Tamaño total de una instancia: campos heredados + campos propios.
    instance_size: int = 0

    def has_field(self, name: str) -> bool:
        if name in self.own_fields:
            return True
        return self.parent.has_field(name) if self.parent else False

    def field_type(self, name: str) -> str | None:
        if name in self.field_types:
            return self.field_types[name]
        return self.parent.field_type(name) if self.parent else None

    def field_offset(self, name: str) -> int | None:
        """Desplazamiento de `name` dentro del objeto (propio o heredado)."""
        if name in self.field_offsets:
            return self.field_offsets[name]
        return self.parent.field_offset(name) if self.parent else None

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
        # Registros de activación de cada función/método, en el orden en que
        # el generador de código los crea. Es el estado que expone
        # `render_report` (ver más abajo).
        self.activation_records: list["ActivationRecord"] = []
        # Accesos a variables libres resueltos a través del enlace de acceso
        # (closures): cada entrada documenta, para una referencia dentro de
        # una función anidada, en qué función se define la variable y cuántos
        # saltos de enlace de acceso hacen falta para llegar a ella.
        self.closure_accesses: list["ClosureAccess"] = []

    def register_activation_record(self, ar: "ActivationRecord") -> None:
        self.activation_records.append(ar)

    def register_closure_access(self, access: "ClosureAccess") -> None:
        self.closure_accesses.append(access)

    def render_report(self) -> str:
        return render_symbol_report(self)

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

        # Pasada 3: calcular desplazamientos de campos (direcciones) y
        # tamaño de instancia, ahora que la herencia ya está enlazada y se
        # sabe que no hay ciclos (así el cálculo siempre termina).
        for info in self.classes.values():
            self._compute_layout(info)

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

    def _compute_layout(self, info: ClassInfo) -> None:
        """Asigna desplazamientos a los campos propios de `info`, colocados
        después de los campos heredados (que ya ocupan `parent.instance_size`
        bytes), en el orden en que fueron declarados."""
        if info.field_offsets:  # ya calculado (otra clase hija lo disparó antes)
            return
        if info.parent is not None:
            self._compute_layout(info.parent)
            offset = info.parent.instance_size
        else:
            offset = 0
        for fname in info.own_fields:
            info.field_offsets[fname] = offset
            offset += size_of(info.field_types.get(fname))
        info.instance_size = offset

    def get_class(self, name: str, line: int) -> ClassInfo:
        info = self.classes.get(name)
        if info is None:
            raise SemanticError(f"Clase '{name}' no definida", line)
        return info


# ---------------------------------------------------------------------------
# Registros de activación y entornos (direcciones/desplazamientos para
# variables, parámetros y temporales; enlaces de control y de acceso).
# ---------------------------------------------------------------------------

#: Tipos de ranura (slot) que puede tener un registro de activación.
SLOT_KINDS = (
    "control_link",   # enlace de control: AR de quien hizo la llamada
    "access_link",    # enlace de acceso: AR del entorno léxico que lo contiene
    "return_address",
    "return_value",
    "param",
    "local",
    "temp",
)


@dataclass
class Slot:
    """Una entrada del registro de activación: un parámetro, variable local,
    temporal, o una de las ranuras fijas (enlaces, retorno)."""
    name: str
    kind: str  # uno de SLOT_KINDS
    type_name: str | None
    size: int
    offset: int


class ActivationRecord:
    """Modelo del registro de activación de una función, método o del
    programa principal.

    Convención de layout usada (desplazamientos crecientes desde el inicio
    del registro; es una convención docente, no corresponde a ninguna ABI de
    una arquitectura real porque este proyecto no genera código de máquina):

        0: enlace de control  (control link)  -> AR de quien llama
        +: enlace de acceso   (access link)   -> AR del entorno léxico padre
        +: dirección de retorno
        +: espacio para el valor de retorno
        +: parámetros, en el orden declarado
        +: variables locales y temporales, en el orden en que se declaran

    `parent` es el registro de activación del entorno léxico que contiene a
    este (el de la función dentro de la cual está anidada/definida esta
    función), no el de quien la llama en tiempo de ejecución; es justo lo
    que necesita `resolve()` para modelar el enlace de acceso de closures.
    Para un método de una clase o una función de nivel de programa, no hay
    un entorno léxico que lo contenga, por lo que `parent` es `None`.
    """

    def __init__(self, name: str, parent: "ActivationRecord | None", depth: int) -> None:
        self.name = name
        self.parent = parent
        self.depth = depth
        self.slots: list[Slot] = []
        self._by_name: dict[str, Slot] = {}
        self._offset = 0
        self._reserve("<enlace_control>", "control_link", None, POINTER_SIZE)
        self._reserve("<enlace_acceso>", "access_link", None, POINTER_SIZE)
        self._reserve("<direccion_retorno>", "return_address", None, POINTER_SIZE)
        self._reserve("<valor_retorno>", "return_value", None, POINTER_SIZE)

    def _reserve(self, name: str, kind: str, type_name: str | None, size: int) -> Slot:
        slot = Slot(name, kind, type_name, size, self._offset)
        self.slots.append(slot)
        self._by_name[name] = slot
        self._offset += size
        return slot

    def add_param(self, name: str, type_name: str | None) -> Slot:
        return self._declare(name, "param", type_name)

    def add_local(self, name: str, type_name: str | None) -> Slot:
        return self._declare(name, "local", type_name)

    def add_temp(self, name: str, type_name: str | None = None) -> Slot:
        return self._declare(name, "temp", type_name)

    def _declare(self, name: str, kind: str, type_name: str | None) -> Slot:
        # Simplificación: si el mismo nombre ya tiene una ranura en este AR
        # (p. ej. porque dos bloques distintos de la misma función declaran
        # una variable con el mismo nombre, un caso de sombra léxica que el
        # `Scope` de codegen.py ya resuelve correctamente a nivel de TAC), se
        # reutiliza la ranura existente en vez de crear una duplicada. No se
        # modela aquí un sub-entorno por cada bloque (if/while/for) dentro de
        # una función: todas sus variables conviven en un único AR.
        existing = self._by_name.get(name)
        if existing is not None:
            return existing
        return self._reserve(name, kind, type_name, size_of(type_name))

    @property
    def total_size(self) -> int:
        return self._offset

    def lookup_local(self, name: str) -> Slot | None:
        return self._by_name.get(name)

    def resolve(self, name: str) -> tuple[int, "ActivationRecord", Slot] | None:
        """Busca `name` en este AR y, si no está, sube por el enlace de
        acceso hacia los entornos léxicos que lo contienen (no por el enlace
        de control). Devuelve (saltos_de_enlace_de_acceso, AR_que_lo_define,
        Slot) o None si no se encuentra en ningún entorno visible."""
        hops = 0
        current: "ActivationRecord | None" = self
        while current is not None:
            slot = current.lookup_local(name)
            if slot is not None:
                return hops, current, slot
            current = current.parent
            hops += 1
        return None


class Environment:
    """Entorno léxico (ámbito): une un alcance de nombres con el registro de
    activación al que pertenecen sus variables. Un entorno de *bloque*
    (if/while/for/switch) comparte el AR de la función que lo contiene; un
    entorno de *función* (función libre, anidada o método) tiene su propio
    AR nuevo."""

    def __init__(self, ar: ActivationRecord, lexical_parent: "Environment | None" = None) -> None:
        self.ar = ar
        self.lexical_parent = lexical_parent

    def declare(self, name: str, type_name: str | None, kind: str = "local") -> Slot:
        if kind == "param":
            return self.ar.add_param(name, type_name)
        if kind == "temp":
            return self.ar.add_temp(name, type_name)
        return self.ar.add_local(name, type_name)

    def resolve(self, name: str) -> tuple[int, ActivationRecord, Slot] | None:
        return self.ar.resolve(name)

    def new_block(self) -> "Environment":
        """Nuevo entorno de bloque: mismo AR (misma función), para if/while/
        for/switch."""
        return Environment(self.ar, lexical_parent=self)

    def new_function(self, name: str) -> "Environment":
        """Nuevo entorno de función anidada/libre: AR nuevo cuyo padre (para
        el enlace de acceso) es el AR de este entorno."""
        child_ar = ActivationRecord(name, parent=self.ar, depth=self.ar.depth + 1)
        return Environment(child_ar, lexical_parent=self)


@dataclass
class ClosureAccess:
    """Documenta la resolución de una variable libre referenciada desde una
    función anidada (closure): dónde se usa, dónde se define y cuántos
    saltos de enlace de acceso hacen falta para llegar a ella."""
    variable: str
    used_in: str  # nombre calificado de la función donde se referencia
    defined_in: str  # nombre calificado de la función donde vive la ranura
    access_link_hops: int
    offset: int
    line: int


def render_symbol_report(symtab: SymbolTable) -> str:
    """Texto legible con el estado de la tabla de símbolos extendida:
    tamaño/desplazamiento de cada campo de cada clase y el layout completo
    del registro de activación de cada función/método, incluyendo cómo se
    resuelven las variables libres de los closures. Esta es la "salida" que
    pide el reparto para la tabla de símbolos, separada del TAC."""
    lines: list[str] = []

    if symtab.classes:
        lines.append("== Layout de objetos ==")
        for info in symtab.classes.values():
            lines.append(f"clase {info.name} (tamaño={info.instance_size} bytes)")
            for fname in info.own_fields:
                ftype = info.field_types.get(fname)
                lines.append(
                    f"    +{info.field_offsets[fname]:<3} {fname}: "
                    f"{ftype or '?'} ({size_of(ftype)} bytes)"
                )
        lines.append("")

    if symtab.activation_records:
        lines.append("== Registros de activación ==")
        for ar in symtab.activation_records:
            parent_desc = f", padre léxico={ar.parent.name}" if ar.parent else ""
            lines.append(f"AR {ar.name} (profundidad={ar.depth}{parent_desc}, tamaño={ar.total_size} bytes)")
            for slot in ar.slots:
                type_desc = f": {slot.type_name}" if slot.type_name else ""
                lines.append(f"    +{slot.offset:<3} [{slot.kind}] {slot.name}{type_desc} ({slot.size} bytes)")
        lines.append("")

    if symtab.closure_accesses:
        lines.append("== Acceso a variables libres (closures) ==")
        for acc in symtab.closure_accesses:
            lines.append(
                f"    línea {acc.line}: '{acc.variable}' usada en {acc.used_in}, "
                f"definida en {acc.defined_in} a {acc.access_link_hops} salto(s) "
                f"de enlace de acceso, desplazamiento +{acc.offset}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n" if lines else ""
