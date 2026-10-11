"""Pruebas unitarias de generación de TAC para new/constructor, atributos,
métodos, this y herencia (parte de Linar)."""
import pytest

from driver import compile_source
from core.errors import SemanticError


def test_new_e_invocacion_de_constructor():
    source = """
    class Point {
        let x: Int;
        function constructor(x) {
            this.x = x;
        }
    }
    let p = new Point(5);
    """
    tac = compile_source(source)
    assert "t1 = new Point" in tac
    assert "param t1" in tac
    assert "param 5" in tac
    assert "call Point.constructor, 2" in tac
    assert "p = t1" in tac


def test_atributo_lectura_y_escritura():
    source = """
    class Box {
        let value: Int;
        function constructor(value) {
            this.value = value;
        }
    }
    let b = new Box(1);
    b.value = 9;
    let v = b.value;
    """
    tac = compile_source(source)
    assert "b.value = 9" in tac
    assert any(line.strip().startswith("t") and ".value" in line for line in tac.splitlines())


def test_this_dentro_de_metodo_referencia_la_clase_actual():
    source = """
    class Counter {
        let total: Int;
        function constructor(total) {
            this.total = total;
        }
        function get() {
            return this.total;
        }
    }
    """
    tac = compile_source(source)
    assert "func Counter.get:" in tac
    assert "this.total" in tac


def test_this_fuera_de_metodo_es_error_semantico():
    source = "print(this);"
    with pytest.raises(SemanticError, match="'this' usado fuera de un método"):
        compile_source(source)


def test_metodo_heredado_se_resuelve_a_la_clase_que_lo_define():
    source = """
    class Animal {
        let name: String;
        function constructor(name) { this.name = name; }
        function speak() { print(this.name); }
    }
    class Dog extends Animal {
        function constructor(name) { this.name = name; }
    }
    let d = new Dog("Rex");
    d.speak();
    """
    tac = compile_source(source)
    # Dog no redefine speak(): la llamada debe resolverse estáticamente a Animal.speak
    assert "call Animal.speak, 1" in tac
    assert "func Dog.speak:" not in tac


def test_metodo_sobrescrito_usa_la_version_de_la_subclase():
    source = """
    class Animal {
        function constructor() {}
        function speak() { print(1); }
    }
    class Dog extends Animal {
        function constructor() {}
        function speak() { print(2); }
    }
    let d = new Dog();
    d.speak();
    """
    tac = compile_source(source)
    assert "call Dog.speak, 1" in tac


def test_atributo_heredado_accesible_desde_subclase():
    source = """
    class Animal {
        let name: String;
        function constructor(name) { this.name = name; }
    }
    class Dog extends Animal {
        function constructor(name) { this.name = name; }
    }
    let d = new Dog("Rex");
    print(d.name);
    """
    tac = compile_source(source)
    assert "d.name" in tac


def test_clase_no_definida_es_error_semantico():
    with pytest.raises(SemanticError, match="Clase 'Foo' no definida"):
        compile_source("let x = new Foo();")


def test_clase_padre_no_definida_es_error_semantico():
    with pytest.raises(SemanticError, match="no está definida"):
        compile_source("class Dog extends Animal {}")


def test_herencia_ciclica_es_error_semantico():
    source = """
    class A extends B {}
    class B extends A {}
    """
    with pytest.raises(SemanticError, match="[Hh]erencia cíclica"):
        compile_source(source)


def test_atributo_no_definido_es_error_semantico():
    source = """
    class Point {
        let x: Int;
        function constructor(x) { this.x = x; }
    }
    let p = new Point(1);
    print(p.z);
    """
    with pytest.raises(SemanticError, match="no tiene el atributo 'z'"):
        compile_source(source)


def test_metodo_no_definido_es_error_semantico():
    source = """
    class Point {
        let x: Int;
        function constructor(x) { this.x = x; }
    }
    let p = new Point(1);
    p.fly();
    """
    with pytest.raises(SemanticError, match="no tiene el método 'fly'"):
        compile_source(source)


def test_orden_evaluacion_target_antes_que_valor_en_asignacion_a_atributo():
    source = """
    class Box {
        let v: Int;
        function constructor(v) { this.v = v; }
        function left() { return this; }
        function right() { return this; }
    }
    let a = new Box(1);
    let b = new Box(2);
    a.left().v = b.right().v;
    """
    tac = compile_source(source)
    lines = tac.splitlines()
    left_idx = next(i for i, l in enumerate(lines) if "call Box.left" in l)
    right_idx = next(i for i, l in enumerate(lines) if "call Box.right" in l)
    # El objeto del target (a.left()) debe evaluarse antes que el valor
    # (b.right()), como ocurriría de izquierda a derecha en el código fuente.
    assert left_idx < right_idx


def test_clase_llamada_list_no_choca_con_el_tipo_lista():
    source = """
    class list {
        let x: Int;
        function constructor(x) { this.x = x; }
    }
    let obj = new list(5);
    print(obj.x);
    """
    tac = compile_source(source)
    assert "call list.constructor, 2" in tac
    assert ".x" in tac


def test_no_se_puede_acceder_a_atributos_de_un_entero():
    source = "let x: Int = 5;\nlet z = x.foo;"
    with pytest.raises(SemanticError, match="(?i)no se puede acceder a atributos"):
        compile_source(source)


def test_numero_incorrecto_de_argumentos_en_constructor():
    source = """
    class Point {
        let x: Int;
        let y: Int;
        function constructor(x, y) {
            this.x = x;
            this.y = y;
        }
    }
    let p = new Point(1);
    """
    with pytest.raises(SemanticError, match="espera 2 argumento"):
        compile_source(source)
