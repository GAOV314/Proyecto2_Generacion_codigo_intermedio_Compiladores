# Parte de Gadiel (Proyecto 2): expresiones, control de flujo y funciones

Implementación de la parte asignada a Gadiel en `Reparto_Proyecto2.md`, sobre
el mismo front-end mínimo y autocontenido de `.cps` que construyó Linar para
su parte (clases, objetos, listas). El lexer, el parser, los nodos de AST y
el generador de TAC son compartidos por ambas partes:

- Traducción de expresiones aritméticas, lógicas y de comparación, con
  precedencia y asociatividad correctas.
- Traducción de declaraciones y asignaciones de variables (`let`) y
  constantes (`const`).
- Traducción de `if/else`, `while`, `do-while`, `for` y `switch`, y de
  `break`/`continue` hacia las etiquetas del bucle (o `switch`, para
  `break`) que los contiene.
- Traducción de funciones: definición, paso de parámetros, llamadas, valor
  de retorno, recursión (directa y mutua), funciones anidadas y closures.
- Integración en `driver.py`/CLI (ya existente; no se creó un `main.py`
  aparte para no duplicar esa responsabilidad).

## Cómo ejecutar

```bash
python3 driver.py pruebas/casos/validos/funciones_recursion.cps   # TAC de un archivo
python3 pruebas/runner.py                                         # batería completa
python3 -m pytest tests/ -q                                       # pruebas unitarias
```

## Gramática añadida

- Precedencia de expresiones (de menor a mayor): `||` > `&&` > comparación
  (`== != < > <= >=`) > aditiva (`+ -`) > multiplicativa (`* /`) > unaria
  (`-`, `!`) > postfijo (`.attr`, `[i]`, llamada).
- `const nombre [: Tipo] = valor;` — igual que `let`, pero no puede
  reasignarse y debe inicializarse.
- `if (cond) { ... } [else { ... } | else if (...) { ... }]`
- `while (cond) { ... }`, `do { ... } while (cond);`
- `for ([init]; [cond]; [update]) { ... }` — `init`/`update` son una
  declaración o una asignación/expresión, sin punto y coma final propio.
- `switch (expr) { case valor: ...; [break;] ... default: ... }` — sin
  `break` cae al siguiente caso (fallthrough real, como en C/Java/JS).
- `break;` / `continue;`
- `function nombre(params) [: Tipo] { ... }` como *sentencia*: puede
  aparecer a nivel de programa, dentro de otra función (función anidada)
  o incluso dentro de un bloque `if`/`while` (con alcance de bloque). El
  tipo de retorno anotado se parsea pero no se valida (fuera de alcance).
- `nombre(args)` como expresión: llamada a una función libre o anidada
  (distinta de `obj.metodo(args)`, que es la parte de Linar).

## Estructura (archivos compartidos con la parte de Linar)

- `core/lexer.py`: se agregaron las palabras reservadas de control de
  flujo/funciones (`if else while do for switch case default break
  continue const`) y los operadores `&&`, `||`, `!`.
- `core/ast_nodes.py`: nodos nuevos `IfStmt`, `WhileStmt`, `DoWhileStmt`,
  `ForStmt`, `SwitchStmt`, `BreakStmt`, `ContinueStmt`, `FunctionDecl`,
  `UnaryOp`, `LogicalOp`, `CallExpr`; `VarDecl` ganó el campo `is_const`.
- `core/parser.py`: nueva cadena de precedencia de expresiones y los
  parsers de cada sentencia de control de flujo/funciones.
- `core/codegen.py`: `_gen_stmt_list` reemplaza el bucle plano sobre
  sentencias (tanto para el cuerpo de `main` como el de cada método/
  función), con una pasada previa que registra las funciones declaradas en
  cada bloque — igual que `register_classes` pre-registra clases — para
  permitir llamadas hacia adelante y recursión mutua entre funciones
  hermanas. `Scope` ahora también resuelve funciones (alcance léxico) y
  marca constantes.
- `tests/test_expressions_tac.py`, `tests/test_control_flow_tac.py`,
  `tests/test_functions_tac.py`: pruebas unitarias de esta parte.
- `pruebas/casos/{validos,invalidos}/*.cps`: casos nuevos de expresiones,
  control de flujo y funciones, corridos por el mismo
  `pruebas/runner.py` que ya usaba Linar.

## Simplificaciones conscientes (a revisar con el equipo)

- **Closures sin registro de activación real**: el TAC que genera este
  módulo es simbólico (usa nombres de variable, no direcciones ni
  desplazamientos). Por eso una función anidada puede referirse
  directamente por nombre a una variable de la función que la contiene
  (`x + y` dentro de `inner`, donde `x` es un parámetro de `outer`); el
  "enlace de acceso" real entre registros de activación para que esa
  captura funcione en una máquina real es responsabilidad de Wachuuu15
  (tabla de símbolos y registros de activación). Esto es consistente con
  cómo Linar ya maneja `this`/atributos sin direcciones reales.
- **`this` no es visible dentro de una función anidada en un método**:
  como esa anidación no pasa por `_gen_class` (que sí liga `current_class`
  al método), una función anidada dentro de un método no puede usar
  `this`. No se ejercitó este caso porque el reparto no lo pide
  explícitamente; si el curso lo requiere, hay que propagar
  `current_class` también a las funciones anidadas dentro de métodos.
- **`switch` se traduce con comparaciones encadenadas** (`if subject ==
  valor goto Lcaso`), no con una tabla de salto. Es la forma más simple de
  obtener fallthrough correcto sin introducir una instrucción TAC nueva de
  salto indexado.
- **Las etiquetas de `case` deben ser expresiones evaluables**, no
  literales constantes como exige la mayoría de lenguajes con tabla de
  salto; aquí cualquier expresión es válida porque la comparación es una
  instrucción TAC normal (`==`), no una tabla de salto. Más permisivo que
  lo usual, documentado por si el curso espera lo contrario.
- **Tipos de retorno de función solo se parsean, no se validan**: igual
  que las anotaciones de tipo del resto del front-end, el chequeo de tipos
  completo queda fuera de alcance de esta entrega.
