"""Pruebas unitarias de generación de TAC para expresiones aritméticas,
lógicas, de comparación, unarias y declaraciones de variables/constantes
(parte de Gadiel)."""
import pytest

from driver import compile_source
from core.errors import SemanticError


def test_precedencia_multiplicacion_sobre_suma():
    tac = compile_source("let a = 2 + 3 * 4;")
    assert "t1 = 3 * 4" in tac
    assert "t2 = 2 + t1" in tac
    assert "a = t2" in tac


def test_parentesis_alteran_la_precedencia():
    tac = compile_source("let b = (2 + 3) * 4;")
    assert "t1 = 2 + 3" in tac
    assert "t2 = t1 * 4" in tac


def test_comparacion_emite_binaryop():
    tac = compile_source("let c = 1 < 2;")
    assert "t1 = 1 < 2" in tac


def test_unario_negacion_logica_y_aritmetica():
    tac = compile_source("let d = !false;\nlet e = -5;")
    assert "t1 = ! false" in tac
    # t1 se libera tras 'd = t1' y se recicla para la siguiente sentencia.
    assert "t1 = - 5" in tac


def test_and_logico_con_cortocircuito():
    tac = compile_source("let c = true && false;")
    lines = tac.splitlines()
    # El operando derecho solo se evalúa en la rama que sigue del salto
    # 'ifFalse', nunca incondicionalmente antes de él.
    assert any("ifFalse true goto" in l for l in lines)


def test_or_logico_con_cortocircuito():
    tac = compile_source("let c = false || true;")
    lines = tac.splitlines()
    assert any("if false goto" in l for l in lines)


def test_declaracion_const_con_inicializador():
    tac = compile_source("const pi = 3;")
    assert "pi = 3" in tac


def test_const_sin_inicializador_es_error_semantico():
    with pytest.raises(SemanticError, match="debe inicializarse"):
        compile_source("const x;")


def test_reasignar_constante_es_error_semantico():
    source = "const x = 1;\nx = 2;"
    with pytest.raises(SemanticError, match="reasignar la constante"):
        compile_source(source)


def test_constante_se_puede_leer_normalmente():
    tac = compile_source("const x = 1;\nlet y = x + 1;")
    assert "t1 = x + 1" in tac
