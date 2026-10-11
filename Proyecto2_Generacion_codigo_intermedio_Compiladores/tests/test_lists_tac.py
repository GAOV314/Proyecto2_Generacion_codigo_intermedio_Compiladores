"""Pruebas unitarias de generación de TAC para listas: creación y acceso
indexado (parte de Linar)."""
import pytest

from driver import compile_source
from core.errors import SemanticError


def test_creacion_de_lista_emite_newlist_y_asignaciones_indexadas():
    tac = compile_source("let nums = [1, 2, 3];")
    assert "t1 = newlist 3" in tac
    assert "t1[0] = 1" in tac
    assert "t1[1] = 2" in tac
    assert "t1[2] = 3" in tac
    assert "nums = t1" in tac


def test_lectura_indexada_produce_t_igual_a_a_corchete_i():
    tac = compile_source("let nums = [1, 2, 3];\nlet first = nums[0];")
    assert "t2 = nums[0]" in tac
    assert "first = t2" in tac


def test_escritura_indexada_produce_a_corchete_i_igual_a_t():
    tac = compile_source("let nums = [1, 2, 3];\nnums[1] = 99;")
    assert "nums[1] = 99" in tac


def test_patron_leer_y_reescribir_mismo_indice():
    tac = compile_source("let a = [10, 20, 30];\nlet t = a[0];\na[0] = t;")
    lines = [l.strip() for l in tac.splitlines()]
    assert "t2 = a[0]" in lines
    assert "t = t2" in lines
    assert "a[0] = t" in lines


def test_lista_vacia_no_falla():
    tac = compile_source("let xs = [];")
    assert "t1 = newlist 0" in tac


def test_no_se_puede_indexar_un_objeto():
    source = """
    class Point {
        let x: Int;
        function constructor(x) { this.x = x; }
    }
    let p = new Point(1);
    let z = p[0];
    """
    with pytest.raises(SemanticError, match="(?i)no se puede indexar"):
        compile_source(source)


def test_no_se_puede_acceder_a_atributos_de_una_lista():
    source = "let xs = [1, 2];\nlet z = xs.foo;"
    with pytest.raises(SemanticError, match="atributos de una lista"):
        compile_source(source)


def test_no_se_puede_indexar_un_entero():
    source = "let x: Int = 5;\nlet z = x[0];"
    with pytest.raises(SemanticError, match="(?i)no se puede indexar"):
        compile_source(source)
