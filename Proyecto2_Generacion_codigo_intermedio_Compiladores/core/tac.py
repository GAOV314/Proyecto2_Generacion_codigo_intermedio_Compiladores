"""Representación textual del código de tres direcciones (TAC) y manejo de
temporales, para las partes de clases/objetos/listas (Linar) y de
expresiones/control de flujo/funciones (Gadiel).

Formato de instrucciones usado (consistente con lo que describe el reparto):
  t1 = new ClaseX                 -> asignación de memoria para un objeto
  param t1                        -> paso de parámetro (this o argumento)
  call Clase.metodo, n            -> invocación resuelta estáticamente
  call funcion, n                 -> invocación de función libre/anidada
  x = t1                          -> copia
  t2 = obj.attr                   -> lectura de atributo
  obj.attr = t3                   -> escritura de atributo
  t4 = newlist n                  -> creación de una lista de tamaño n
  t4[0] = t5                      -> asignación indexada
  t6 = a[i]                       -> acceso indexado
  t7 = a + b                      -> operación binaria (aritmética/comparación)
  t8 = - a  /  t8 = ! a           -> operación unaria
  L1:                             -> etiqueta
  goto L1                         -> salto incondicional
  if t goto L1                    -> salto si t es verdadero
  ifFalse t goto L1                -> salto si t es falso
  return [t]                      -> retorno (con o sin valor)

Diseño del lenguaje intermedio y reciclaje de temporales: parte de Cindy.
Ver docs/Lenguaje_Intermedio_TAC.md para la especificación completa de cada
instrucción, con ejemplos de traducción y los supuestos considerados.
"""
from __future__ import annotations


class TempManager:
    """Asigna y recicla nombres de temporales (`t1`, `t2`, ...).

    Algoritmo de reciclaje: el que llama a `new_temp()` eventualmente
    devuelve el nombre con `free_temp()` cuando ya no lo necesita (ver
    `CodeGenerator._gen_stmt` en core/codegen.py, que libera automáticamente
    cada temporal que no sobrevive al final de la sentencia que lo creó).
    Los nombres liberados se guardan en una pila (`_free`) y `new_temp()`
    reutiliza el más recientemente liberado antes de acuñar uno nuevo; así
    el compilador usa la menor cantidad de nombres distintos de temporales
    posible, en vez de uno nuevo por cada subexpresión del programa.
    """

    def __init__(self) -> None:
        self._counter = 0
        self._free: list[int] = []

    def new_temp(self) -> str:
        if self._free:
            index = self._free.pop()
        else:
            self._counter += 1
            index = self._counter
        return f"t{index}"

    def free_temp(self, name: str) -> None:
        """Devuelve `name` (debe haber salido de `new_temp()`) al pool para
        que una llamada posterior a `new_temp()` lo reutilice."""
        self._free.append(int(name[1:]))


class TACFunction:
    def __init__(self, name: str) -> None:
        self.name = name
        self.instructions: list[str] = []

    def emit(self, instruction: str) -> None:
        self.instructions.append(instruction)

    def render(self) -> str:
        header = f"func {self.name}:"
        body = "\n".join(f"    {instr}" for instr in self.instructions)
        return f"{header}\n{body}\n" if body else f"{header}\n"


class TACProgram:
    def __init__(self) -> None:
        self.functions: list[TACFunction] = []
        self.main = TACFunction("main")

    def new_function(self, name: str) -> TACFunction:
        func = TACFunction(name)
        self.functions.append(func)
        return func

    def render(self) -> str:
        parts = [func.render() for func in self.functions]
        parts.append(self.main.render())
        return "\n".join(parts).rstrip() + "\n"
