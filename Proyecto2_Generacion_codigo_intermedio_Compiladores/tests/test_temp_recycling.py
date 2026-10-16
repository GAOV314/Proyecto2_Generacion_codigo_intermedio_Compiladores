"""Pruebas unitarias del algoritmo de asignación y reciclaje de temporales
(parte de Cindy): core/tac.py::TempManager y
core/codegen.py::CodeGenerator._gen_stmt."""
from core.tac import TempManager
from driver import compile_source


# -- TempManager (unidad) --------------------------------------------------


def test_new_temp_acuña_nombres_consecutivos():
    temps = TempManager()
    assert temps.new_temp() == "t1"
    assert temps.new_temp() == "t2"
    assert temps.new_temp() == "t3"


def test_free_temp_permite_reutilizar_el_mismo_nombre():
    temps = TempManager()
    t1 = temps.new_temp()
    temps.free_temp(t1)
    assert temps.new_temp() == "t1"  # reciclado, no "t2"


def test_liberar_el_mas_reciente_se_reutiliza_primero():
    temps = TempManager()
    t1 = temps.new_temp()
    t2 = temps.new_temp()
    temps.free_temp(t1)
    temps.free_temp(t2)
    assert temps.new_temp() == "t2"
    assert temps.new_temp() == "t1"
    assert temps.new_temp() == "t3"  # el pool ya está vacío


# -- integración: sentencias independientes reciclan entre sí --------------


def test_sentencias_independientes_reciclan_el_mismo_temporal():
    tac = compile_source("let a = 1 + 2;\nlet b = 3 + 4;")
    # Sin reciclaje habría 't1' y 't2'; con reciclaje ambas sentencias usan
    # 't1', porque se libera tras 'a = t1' antes de generar la siguiente.
    assert "t1 = 1 + 2" in tac
    assert "a = t1" in tac
    assert "t1 = 3 + 4" in tac
    assert "b = t1" in tac
    assert "t2" not in tac


def test_el_temporal_de_la_condicion_vive_durante_todo_el_cuerpo():
    source = "let i = 0;\nwhile (i < 3) {\n  let x = i + 1;\n}"
    tac = compile_source(source)
    # La condición ('i < 3') usa t1 y sigue viva durante el cuerpo; el
    # cuerpo ('i + 1') no puede reciclar t1 todavía, así que usa t2.
    assert "t1 = i < 3" in tac
    assert "t2 = i + 1" in tac


def test_temporales_no_cruzan_la_frontera_de_una_funcion_a_otra_sin_control():
    source = """
    function f() { return 1 + 2; }
    function g() { return 3 + 4; }
    f();
    g();
    """
    tac = compile_source(source)
    # Cada función recicla independientemente: ambas usan 't1' para su
    # propio cuerpo porque cada 'return' libera el temporal antes de que la
    # otra función (o 'main') lo necesite.
    assert tac.count("t1 = 1 + 2") == 1
    assert tac.count("t1 = 3 + 4") == 1
