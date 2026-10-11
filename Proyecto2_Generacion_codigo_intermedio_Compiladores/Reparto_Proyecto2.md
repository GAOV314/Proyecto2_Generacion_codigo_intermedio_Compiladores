# Reparto de trabajo: Proyecto 2 (Generación de Código Intermedio TAC)

El reparto sigue lo que cada integrante hizo en el Proyecto 1, según el historial de git. Así cada quien extiende el módulo que ya conoce. Le asigné a cada persona commits propios, porque el PDF prohíbe compartir commits.

## Resumen de aportes previos (base del reparto)

| Integrante | Usuario git | Trabajo en el Proyecto 1 |
|---|---|---|
| Linar | `lin231135` | Estructura inicial y contrato de `core`, manejo de clases/herencia/`this`/`new`, prepass de dos pasadas, orden de mixins, batería de pruebas `.cps` y runner |
| Gadiel Ocaña | `GAOV314` | Sistema de tipos, funciones, ámbito y control de flujo, driver de análisis y CLI, informe del proyecto |
| Wachuuu15 | `Wachuuu15` | Tabla de símbolos (`core/symbols.py`), generador de parser (ANTLR), `core/errors.py`, entornos y ámbitos |
| Cindy Gualim | `Cindy Gualim` | IDE con CustomTkinter, árbol sintáctico visual (Graphviz), correcciones del sistema de tipos, README y matriz de cobertura |

## Reparto del Proyecto 2

### 1. Linar (`lin231135`): Clases, objetos, listas y batería de pruebas (parte de 65 pts)
- Traducción de `new` e invocación del constructor.
- Acceso a atributos, invocación de métodos y uso de `this`, incluyendo herencia.
- Traducción de listas: creación y acceso indexado (`t = a[i]`, `a[i] = t`).
- Batería de pruebas de TAC para casos válidos e inválidos de clases y listas, y ampliación del runner `pruebas/runner.py`.
- Pruebas unitarias en `tests/`.

**Por qué:** ya implementó `class_mixin` y el runner de pruebas.

### 2. Gadiel Ocaña (`GAOV314`): Expresiones, control de flujo y funciones (parte de 65 pts)
- Traducción de expresiones aritméticas, lógicas y de comparación, con precedencia y asociatividad.
- Traducción de declaraciones y asignaciones de variables y constantes.
- Traducción de `if/else`, `while`, `do-while`, `for` y `switch`, y de `break`/`continue` hacia las etiquetas del bucle que los contiene.
- Traducción de funciones: definición, paso de parámetros, llamadas, valor de retorno, recursión, funciones anidadas y closures.
- Integración del generador de TAC en `driver.py` y en la CLI (`main.py`).

**Por qué:** ya hizo el sistema de tipos, las funciones, el control de flujo y el driver.

### 3. Wachuuu15: Tabla de símbolos extendida y registros de activación (100 pts del componente de tabla de símbolos)
- Ampliar `core/symbols.py` con direcciones/desplazamientos, tamaños y etiquetas.
- Diseñar los registros de activación: parámetros, variables locales, temporales, valor y dirección de retorno, enlace de control y enlace de acceso.
- Calcular los desplazamientos por entorno y el acceso a variables del entorno de definición, que los closures necesitan.
- Exponer el estado de la tabla de símbolos como salida (direcciones, desplazamientos y registros de activación).
- Hacer que la tabla de símbolos interactúe con cada fase de la compilación.
- Pruebas en `tests/test_symbols.py` y actualización de `docs/Tabla de Simbolos.md`.

**Por qué:** es dueño de `core/symbols.py` y de los entornos.

### 4. Cindy Gualim: Diseño del lenguaje intermedio, temporales e IDE (25 pts de diseño y parte de la generación)
- Definir y documentar el conjunto de instrucciones TAC: asignación, operaciones binarias y unarias, copia, saltos, etiquetas, llamadas, acceso indexado. La sintaxis debe ser consistente.
- Escribir la documentación del lenguaje intermedio, con ejemplos de traducción y los supuestos considerados.
- Implementar el algoritmo de asignación y reciclaje de temporales.
- Actualizar el IDE (`ide/app.py`) para escribir y compilar `.cps`, mostrar el TAC generado, los errores con tipo y ubicación, la tabla de símbolos y la ejecución de la batería de pruebas.
- Actualizar el README y la documentación de arquitectura y de cómo ejecutar el compilador.

**Por qué:** ya hizo el IDE, el árbol visual y la documentación.

## Resumen por componente de evaluación

| Componente | Puntos | Responsable principal | Apoyo |
|---|---|---|---|
| Diseño de CI | 25 | Cindy | Gadiel (revisión de ejemplos) |
| Generación de TAC, temporales y batería de pruebas | 65 | Gadiel (expresiones, control de flujo, funciones), Linar (clases, listas, pruebas), Cindy (temporales) | Todos |
| Tabla de símbolos y registros de activación | 10 | Wachuuu15 | Gadiel (closures) |

> Nota: en el texto extraído del PDF las columnas de puntos salieron desordenadas. Los valores 25/65/10 suman 100, pero conviene confirmar contra el PDF a qué componente corresponde cada uno.

## Entregables compartidos
- Cada integrante hace **commits propios** de su parte, sin commits conjuntos.
- Documentación de arquitectura y de ejecución: Cindy la redacta y todos la revisan.
- Antes de la presentación, todos verifican que el programa funcione y que la batería de pruebas pase.
