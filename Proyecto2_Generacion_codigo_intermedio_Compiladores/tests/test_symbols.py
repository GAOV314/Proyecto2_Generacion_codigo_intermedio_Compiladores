"""Pruebas unitarias de la tabla de símbolos extendida: direcciones,
desplazamientos, tamaños, registros de activación y resolución de acceso a
variables libres de closures (parte de Wachuuu15)."""
from core.ast_nodes import ClassDecl, FieldDecl
from core.symbols import (
    ActivationRecord,
    Environment,
    SymbolTable,
    size_of,
)
from driver import compile_with_symbols


# -- tamaños de tipo ----------------------------------------------------


def test_size_of_tipos_conocidos():
    assert size_of("Int") == 4
    assert size_of("Bool") == 1
    assert size_of("Float") == 8


def test_size_of_tipo_desconocido_o_no_primitivo_es_tamano_de_puntero():
    assert size_of(None) == 8
    assert size_of("Point") == 8  # una clase: referencia, no el objeto inline


# -- layout de objetos (campos heredados + propios) ----------------------


def test_offsets_de_campos_de_una_clase_sin_herencia():
    symtab = SymbolTable()
    symtab.register_classes(
        [
            ClassDecl(
                line=1,
                name="Point",
                parent=None,
                fields=[FieldDecl(1, "x", "Int"), FieldDecl(1, "y", "Int")],
                methods=[],
            )
        ]
    )
    info = symtab.classes["Point"]
    assert info.field_offsets["x"] == 0
    assert info.field_offsets["y"] == 4
    assert info.instance_size == 8


def test_campos_heredados_se_colocan_antes_que_los_propios():
    symtab = SymbolTable()
    symtab.register_classes(
        [
            ClassDecl(1, "Animal", None, [FieldDecl(1, "name", "String")], []),
            ClassDecl(1, "Dog", "Animal", [FieldDecl(1, "breed", "String")], []),
        ]
    )
    dog = symtab.classes["Dog"]
    animal = symtab.classes["Animal"]
    assert dog.field_offset("name") == animal.field_offset("name") == 0
    assert dog.field_offset("breed") == animal.instance_size
    assert dog.instance_size == animal.instance_size + size_of("String")


# -- registros de activación ----------------------------------------------


def test_ar_reserva_enlaces_retorno_antes_de_params_y_locales():
    ar = ActivationRecord("f", parent=None, depth=0)
    kinds = [s.kind for s in ar.slots]
    assert kinds == ["control_link", "access_link", "return_address", "return_value"]
    base_size = ar.total_size
    ar.add_param("a", "Int")
    assert ar.lookup_local("a").offset == base_size
    ar.add_local("x", None)
    assert ar.lookup_local("x").offset == base_size + size_of("Int")


def test_declarar_el_mismo_nombre_dos_veces_reutiliza_la_ranura():
    ar = ActivationRecord("f", parent=None, depth=0)
    slot1 = ar.add_local("x", "Int")
    slot2 = ar.add_local("x", "Int")
    assert slot1 is slot2
    assert len(ar.slots) == 5  # 4 reservadas + una sola 'x'


def test_resolve_encuentra_variable_en_el_propio_ar_con_cero_saltos():
    ar = ActivationRecord("f", parent=None, depth=0)
    ar.add_local("x", "Int")
    hops, defining_ar, slot = ar.resolve("x")
    assert hops == 0
    assert defining_ar is ar
    assert slot.name == "x"


def test_resolve_sube_por_el_enlace_de_acceso_hacia_el_padre_lexico():
    outer_ar = ActivationRecord("outer", parent=None, depth=0)
    outer_ar.add_param("x", "Int")
    inner_ar = ActivationRecord("outer.inner", parent=outer_ar, depth=1)
    inner_ar.add_param("y", "Int")

    hops, defining_ar, slot = inner_ar.resolve("x")
    assert hops == 1
    assert defining_ar is outer_ar
    assert slot.name == "x"

    hops_local, defining_ar_local, _ = inner_ar.resolve("y")
    assert hops_local == 0
    assert defining_ar_local is inner_ar


def test_resolve_variable_inexistente_devuelve_none():
    ar = ActivationRecord("f", parent=None, depth=0)
    assert ar.resolve("no_existe") is None


# -- Environment (entornos léxicos) ----------------------------------------


def test_new_block_comparte_el_mismo_ar_que_su_padre():
    env = Environment(ActivationRecord("f", None, 0))
    block_env = env.new_block()
    assert block_env.ar is env.ar


def test_new_function_crea_un_ar_hijo_con_el_padre_como_enlace_de_acceso():
    env = Environment(ActivationRecord("outer", None, 0))
    nested_env = env.new_function("outer.inner")
    assert nested_env.ar is not env.ar
    assert nested_env.ar.parent is env.ar
    assert nested_env.ar.depth == env.ar.depth + 1


# -- integración end-to-end vía el compilador completo ---------------------


def test_closures_quedan_documentados_en_el_reporte_de_simbolos():
    source = """
    function outer(x) {
        function inner(y) {
            return x + y;
        }
        return inner(10);
    }
    """
    generator, _ = compile_with_symbols(source)
    accesses = generator.symtab.closure_accesses
    assert len(accesses) == 1
    access = accesses[0]
    assert access.variable == "x"
    assert access.used_in == "outer.inner"
    assert access.defined_in == "outer"
    assert access.access_link_hops == 1


def test_variable_local_no_genera_acceso_de_closure():
    source = "function f(a) { let b = a + 1; return b; }"
    generator, _ = compile_with_symbols(source)
    assert generator.symtab.closure_accesses == []


def test_metodo_no_tiene_padre_lexico_para_el_enlace_de_acceso():
    source = """
    class Point {
        let x: Int;
        function constructor(x) { this.x = x; }
        function sum() { return this.x; }
    }
    """
    generator, _ = compile_with_symbols(source)
    method_ars = [ar for ar in generator.symtab.activation_records if ar.name.startswith("Point.")]
    assert method_ars
    assert all(ar.parent is None for ar in method_ars)


def test_this_se_modela_como_parametro_del_metodo():
    source = """
    class Point {
        let x: Int;
        function constructor(x) { this.x = x; }
    }
    """
    generator, _ = compile_with_symbols(source)
    ctor_ar = next(ar for ar in generator.symtab.activation_records if ar.name == "Point.constructor")
    this_slot = ctor_ar.lookup_local("this")
    assert this_slot is not None
    assert this_slot.kind == "param"
    assert this_slot.type_name == "Point"


def test_render_report_incluye_las_tres_secciones():
    source = """
    class Point {
        let x: Int;
        function constructor(x) { this.x = x; }
    }
    function f(a) { return a; }
    """
    generator, _ = compile_with_symbols(source)
    report = generator.symtab.render_report()
    assert "Layout de objetos" in report
    assert "Registros de activación" in report
