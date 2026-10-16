"""Pruebas unitarias de generación de TAC para if/else, while, do-while,
for, switch, break y continue (parte de Gadiel)."""
import pytest

from driver import compile_source
from core.errors import SemanticError


def test_if_sin_else_salta_al_final_cuando_la_condicion_es_falsa():
    tac = compile_source("if (1 < 2) { print(1); }")
    lines = tac.splitlines()
    assert any(l.strip().startswith("ifFalse") for l in lines)
    assert any(l.strip() == "call print, 1" for l in lines)


def test_if_else_tiene_dos_ramas_y_un_salto_de_salida():
    tac = compile_source("if (1 < 2) { print(1); } else { print(2); }")
    lines = [l.strip() for l in tac.splitlines()]
    assert "param 1" in lines
    assert "param 2" in lines
    # debe haber un 'goto' que salte la rama else tras ejecutar el then
    assert any(l.startswith("goto") for l in lines)


def test_while_evalua_la_condicion_antes_de_cada_iteracion():
    tac = compile_source("let i = 0;\nwhile (i < 3) { i = i + 1; }")
    lines = [l.strip() for l in tac.splitlines()]
    # lines[0] es "func main:"; lines[1] es la inicialización 'i = 0' y
    # lines[2] debe ser la etiqueta de inicio del bucle, a la que el 'goto'
    # final regresa para volver a evaluar la condición en cada iteración.
    assert lines[1] == "i = 0"
    assert lines[2].endswith(":")
    start_label = lines[2].rstrip(":")
    assert f"goto {start_label}" in lines


def test_break_sale_del_while():
    tac = compile_source("while (true) { break; }")
    lines = [l.strip() for l in tac.splitlines()]
    goto_targets = [l.split()[1] for l in lines if l.startswith("goto")]
    labels = {l[:-1] for l in lines if l.endswith(":")}
    assert any(t in labels for t in goto_targets)


def test_continue_regresa_al_inicio_del_while():
    tac = compile_source("let i = 0;\nwhile (i < 3) {\n  i = i + 1;\n  continue;\n}")
    assert tac.count("goto L1") >= 2  # el continue y el cierre del bucle saltan a L1


def test_do_while_ejecuta_el_cuerpo_antes_de_revisar_la_condicion():
    tac = compile_source("let i = 0;\ndo { i = i + 1; } while (i < 3);")
    lines = tac.splitlines()
    # primera instrucción del cuerpo debe aparecer antes de la primera
    # evaluación de la condición 'i < 3'
    body_idx = next(i for i, l in enumerate(lines) if "i + 1" in l)
    cond_idx = next(i for i, l in enumerate(lines) if "i < 3" in l)
    assert body_idx < cond_idx


def test_for_ejecuta_init_una_sola_vez_y_update_antes_de_repetir():
    tac = compile_source("for (let j = 0; j < 3; j = j + 1) { print(j); }")
    assert tac.count("j = 0") == 1
    lines = [l.strip() for l in tac.splitlines()]
    print_idx = lines.index("call print, 1")
    update_idx = next(i for i, l in enumerate(lines) if l.startswith("j = ") and i > print_idx)
    assert update_idx > print_idx


def test_switch_con_fallthrough_cuando_no_hay_break():
    tac = compile_source(
        """
        let x = 2;
        switch (x) {
            case 2:
            case 3:
                print(23);
            default:
                print(0);
        }
        """
    )
    lines = [l.strip() for l in tac.splitlines()]
    param_indexes = [i for i, l in enumerate(lines) if l == "param 23"]
    assert len(param_indexes) == 1  # un solo cuerpo compartido por case 2 y case 3
    # Entre el 'call print' del caso 23 y el 'param 0' del default no debe
    # haber ningún 'goto': cae de un caso al siguiente (fallthrough real).
    call_idx = lines.index("call print, 1")
    default_param_idx = lines.index("param 0")
    assert default_param_idx > call_idx
    between = lines[call_idx + 1 : default_param_idx]
    assert not any(l.startswith("goto") for l in between)


def test_switch_con_break_no_cae_al_siguiente_caso():
    tac = compile_source(
        """
        let x = 1;
        switch (x) {
            case 1:
                print(1);
                break;
            case 2:
                print(2);
        }
        """
    )
    lines = [l.strip() for l in tac.splitlines()]
    call_idx = lines.index("param 1")
    assert lines[call_idx + 2].startswith("goto")


def test_break_fuera_de_bucle_o_switch_es_error_semantico():
    with pytest.raises(SemanticError, match="'break' usado fuera"):
        compile_source("break;")


def test_continue_fuera_de_bucle_es_error_semantico():
    with pytest.raises(SemanticError, match="'continue' usado fuera"):
        compile_source("continue;")
