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

Nota de alcance: el diseño final y unificado del lenguaje intermedio (todas
las instrucciones, convenciones de nombres, reciclaje de temporales) es
responsabilidad de Cindy. Este módulo implementa un subconjunto consistente
y documentado, suficiente para generar y probar TAC de clases, listas,
expresiones, control de flujo y funciones.
"""
from __future__ import annotations


class TempManager:
    def __init__(self) -> None:
        self._counter = 0

    def new_temp(self) -> str:
        self._counter += 1
        return f"t{self._counter}"


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
