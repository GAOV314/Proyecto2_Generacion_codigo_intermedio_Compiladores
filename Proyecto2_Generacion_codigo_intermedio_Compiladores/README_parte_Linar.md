# Parte de Linar (Proyecto 2): clases, objetos, listas y batería de pruebas

Implementación de la parte asignada a Linar en `Reparto_Proyecto2.md`. Como
el repositorio no tenía código del Proyecto 1 (lexer/parser/tabla de
símbolos de los demás integrantes), se construyó un subconjunto mínimo y
autocontenido de `.cps` suficiente para cubrir y probar estos puntos:

- Traducción de `new` e invocación del constructor.
- Acceso a atributos, invocación de métodos y uso de `this`, con herencia.
- Traducción de listas: creación y acceso indexado (`t = a[i]`, `a[i] = t`).
- Batería de pruebas de TAC (válidas e inválidas) y runner ampliado.
- Pruebas unitarias en `tests/`.

## Cómo ejecutar

```bash
python3 driver.py pruebas/casos/validos/clases_herencia.cps   # TAC de un archivo
python3 pruebas/runner.py                                     # batería completa
python3 -m pytest tests/ -q                                   # pruebas unitarias
```

## Estructura

- `core/lexer.py`, `core/parser.py`, `core/ast_nodes.py`: front-end mínimo
  (sin control de flujo `if/while/for`, que es la parte de Gadiel).
- `core/symbols.py`: tabla de clases/herencia (campos, métodos, padre).
  La tabla de símbolos completa con direcciones/registros de activación es
  responsabilidad de Wachuuu15.
- `core/tac.py`: formato textual de TAC y manejo de temporales (`t1`, `t2`, ...).
  El diseño final del lenguaje intermedio es responsabilidad de Cindy; este
  módulo define un subconjunto consistente para clases y listas.
- `core/codegen.py`: generador de TAC (foco de esta parte).
- `driver.py`: `fuente .cps -> TAC`.
- `pruebas/casos/{validos,invalidos}/*.cps` + `pruebas/runner.py`: batería
  de pruebas. Los casos inválidos llevan `// ERROR: <subcadena esperada>`
  en la primera línea.
- `tests/`: pruebas unitarias (pytest).

## Simplificaciones conscientes (a revisar con el equipo)

- **Despacho de métodos estático**: la invocación `obj.metodo()` se resuelve
  en tiempo de compilación siguiendo la cadena de herencia (no hay vtable
  dinámica). Suficiente para esta entrega; si el curso exige despacho
  dinámico real, hay que agregar una tabla de métodos virtuales.
- **Inferencia de tipos muy ligera**: el tipo estático de una variable se
  fija en su declaración/anotación (`new Clase(...)`, anotación `: Tipo`,
  o `this`) y no se refina después. Si el tipo es desconocido, no se valida
  el atributo/método/indexación (se asume válido).
- **Gramática reducida**: solo lo necesario para clases/objetos/listas
  (declaraciones, asignaciones, `return`, `print`, expresiones). No incluye
  `if/while/for/switch/break/continue` ni funciones libres (eso es la parte
  de Gadiel) ni el reciclaje de temporales (parte de Cindy).
- Falta integrar esto con el parser/tabla de símbolos reales del resto del
  equipo cuando estén disponibles; la interfaz clave a conservar es
  `core.codegen.CodeGenerator` recibiendo un AST y una `SymbolTable`.
