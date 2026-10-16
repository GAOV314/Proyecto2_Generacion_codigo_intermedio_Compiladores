"""Pruebas unitarias de generación de TAC para funciones: definición,
parámetros, llamadas, retorno, recursión, funciones anidadas y closures
(parte de Gadiel)."""
import pytest

from driver import compile_source
from core.errors import SemanticError


def test_funcion_libre_se_emite_como_func_propia():
    tac = compile_source(
        "function suma(a, b) { return a + b; }\nlet r = suma(1, 2);"
    )
    assert "func suma:" in tac
    assert "param 1" in tac
    assert "param 2" in tac
    assert "call suma, 2" in tac


def test_funcion_recursiva_se_llama_a_si_misma():
    source = """
    function factorial(n) {
        if (n <= 1) {
            return 1;
        } else {
            return n * factorial(n - 1);
        }
    }
    let r = factorial(5);
    """
    tac = compile_source(source)
    assert "call factorial, 1" in tac


def test_recursion_mutua_entre_funciones_hermanas():
    source = """
    function esPar(n) {
        if (n == 0) { return true; }
        return esImpar(n - 1);
    }
    function esImpar(n) {
        if (n == 0) { return false; }
        return esPar(n - 1);
    }
    print(esPar(4));
    """
    tac = compile_source(source)
    assert "call esImpar, 1" in tac
    assert "call esPar, 1" in tac


def test_funcion_anidada_se_nombra_calificada_con_la_funcion_contenedora():
    source = """
    function outer(x) {
        function inner(y) {
            return x + y;
        }
        return inner(10);
    }
    """
    tac = compile_source(source)
    assert "func outer.inner:" in tac
    assert "call outer.inner, 1" in tac


def test_closure_referencia_directamente_la_variable_de_la_funcion_contenedora():
    source = """
    function outer(x) {
        function inner(y) {
            return x + y;
        }
        return inner(10);
    }
    """
    tac = compile_source(source)
    inner_body = tac.split("func outer.inner:")[1].split("func main:")[0]
    assert "x + y" in inner_body


def test_llamar_funcion_no_definida_es_error_semantico():
    with pytest.raises(SemanticError, match="no está definida"):
        compile_source("foo();")


def test_numero_incorrecto_de_argumentos_en_funcion_es_error_semantico():
    source = "function f(a, b) { return a + b; }\nf(1);"
    with pytest.raises(SemanticError, match=r"espera 2 argumento\(s\)"):
        compile_source(source)


def test_funcion_duplicada_en_el_mismo_ambito_es_error_semantico():
    source = """
    function f() { return 1; }
    function f() { return 2; }
    """
    with pytest.raises(SemanticError, match="ya está definida"):
        compile_source(source)
