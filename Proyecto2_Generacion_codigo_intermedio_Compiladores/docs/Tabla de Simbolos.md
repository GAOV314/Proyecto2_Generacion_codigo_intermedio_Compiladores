# Tabla de símbolos extendida y registros de activación (parte de Wachuuu15)

Implementación de la parte asignada a Wachuuu15 en `Reparto_Proyecto2.md`:
ampliar `core/symbols.py` con direcciones/desplazamientos, tamaños y
etiquetas; diseñar los registros de activación (parámetros, locales,
temporales, valor y dirección de retorno, enlace de control y enlace de
acceso); calcular los desplazamientos por entorno y el acceso a variables
del entorno de definición que necesitan los closures; y exponer todo como
salida del compilador.

## Por qué es una salida separada del TAC

El TAC que generan las partes de Linar y Gadiel es **simbólico**: usa
nombres de variable (`x`, `t1`, `p.attr`), no direcciones. Esa es una
simplificación consciente que ambas partes documentan explícitamente,
dejando el modelo de memoria real para esta parte. Por eso lo que se agrega
aquí **no cambia ni una línea del TAC emitido**: es un artefacto paralelo
que el generador de código construye *en paralelo* a la generación del TAC
(reutilizando exactamente el mismo recorrido del AST, para no duplicar
lógica ni arriesgar que ambos se desincronicen) y que se expone como una
salida adicional, activable con `--symbols`:

```bash
python3 driver.py archivo.cps --symbols
```

## Cómo interactúa con cada fase de la compilación

Este proyecto no tiene una fase de "análisis semántico" separada: el
chequeo semántico y la generación de TAC ocurren juntos, recorriendo el AST
una sola vez (`core/codegen.py`). La tabla de símbolos extendida se conecta
exactamente en ese recorrido:

- Al **registrar clases** (`SymbolTable.register_classes`), calcula el
  layout de cada objeto (desplazamiento y tamaño de cada campo, propio o
  heredado).
- Al **declarar** una variable, parámetro o `this` (`Scope.declare` en
  `core/codegen.py`), reserva una ranura (`Slot`) en el registro de
  activación de la función/método que se está generando.
- Al **crear un temporal** (`CodeGenerator._new_temp`), también le reserva
  una ranura en ese mismo registro de activación.
- Al **resolver un identificador** (`CodeGenerator._track_closure_access`),
  si la variable se encuentra en un registro de activación distinto al
  actual (una función anidada leyendo una variable de la función que la
  contiene), registra ese acceso con la cantidad de saltos de enlace de
  acceso necesarios para llegar a ella.

## Tamaños de tipo

Simplificación consciente: el proyecto no genera código de máquina para una
arquitectura real, así que se usan tamaños de palabra fijos en vez de
derivarlos de un *target* concreto (`core/symbols.py::TYPE_SIZES`):

| Tipo | Tamaño |
|---|---|
| `Int` | 4 bytes |
| `Bool` | 1 byte |
| `Float` | 8 bytes |
| `String`, clases, tipos desconocidos | 8 bytes (una referencia/puntero) |

## Layout de objetos

Los campos de una clase se colocan en memoria con los campos **heredados
primero** (en el mismo desplazamiento que ya tenían en la clase padre, para
que un `Dog` sea compatible en memoria con un `Animal`), seguidos de los
campos propios en el orden en que se declaran:

```
class Animal { let name: String; }
class Dog extends Animal { let breed: String; }
```

```
clase Animal (tamaño=8 bytes)
    +0   name: String (8 bytes)
clase Dog (tamaño=16 bytes)
    +8   breed: String (8 bytes)
```

## Registros de activación

Convención de layout usada (desplazamientos crecientes desde el inicio del
registro). Es una convención docente razonable, **no corresponde a ninguna
ABI de una arquitectura real**, porque el proyecto no genera código de
máquina:

```
+0   enlace de control   (control link)   -> AR de quien llama
+8   enlace de acceso    (access link)    -> AR del entorno léxico padre
+16  dirección de retorno
+24  valor de retorno
+32  parámetros, en el orden declarado
+..  variables locales y temporales, en el orden en que se declaran
```

- **Enlace de control**: apunta al registro de activación de quien *llamó*
  a la función (la cadena dinámica de llamadas).
- **Enlace de acceso**: apunta al registro de activación del *entorno
  léxico que contiene* a esta función — el que necesitan los closures para
  resolver variables libres. Para una función de nivel de programa o una
  función anidada, es el AR de la función dentro de la cual está definida.
  Para un método de una clase, no hay un entorno léxico que lo contenga
  (un método no está anidado dentro de otra función), así que su enlace de
  acceso no tiene padre; el acceso al objeto se modela en cambio como un
  parámetro más (`this`), que es como ya lo generan el TAC y el AR.

### Ejemplo: función anidada / closure

```
function outer(x) {
    function inner(y) {
        return x + y;
    }
    return inner(10);
}
```

```
AR outer (profundidad=1, padre léxico=main)
    +32  [param] x
AR outer.inner (profundidad=2, padre léxico=outer)
    +32  [param] y

Acceso a variables libres (closures):
    'x' usada en outer.inner, definida en outer a 1 salto(s)
    de enlace de acceso, desplazamiento +32
```

`inner` referencia `x`, que no está en su propio registro de activación;
`Environment.resolve` sube un salto por el enlace de acceso (de
`outer.inner` a `outer`) y la encuentra en el desplazamiento +32. Esto es
justo la información que un backend real necesitaría para generar el
código de acceso a `x` desde dentro de `inner` (cargar el enlace de acceso
de `inner`, y leer el desplazamiento +32 de ese registro).

## Simplificaciones conscientes (a revisar con el equipo)

- **Sin sub-entorno por bloque**: `if`/`while`/`for`/`switch` no reciben su
  propio registro de activación; todas las variables declaradas dentro de
  una misma función (sin importar en qué bloque) conviven en un único AR.
  Esto es consistente con cómo la mayoría de compiladores reales tampoco
  dan su propio *stack frame* a cada bloque, solo a cada función. Si el
  mismo nombre se declara en dos bloques distintos de la misma función
  (sombra léxica), aquí se reutiliza la primera ranura con ese nombre; el
  `Scope` de `core/codegen.py` ya resuelve esa sombra correctamente a nivel
  de TAC de forma independiente, por lo que no hay pérdida de corrección en
  el TAC generado, solo una simplificación en el modelo de direcciones.
- **Tamaños de tipo fijos**, no derivados de una arquitectura real (ver
  arriba).
- **Esta salida es informativa, no se usa para generar direcciones reales
  en el TAC**: como ya está documentado en `core/codegen.py` (partes de
  Linar y Gadiel), el TAC sigue siendo simbólico. Integrar ambas cosas (que
  el TAC emita direcciones reales en vez de nombres) sería un cambio de
  diseño del lenguaje intermedio que le corresponde a Cindy, no a esta
  parte.

## Cómo ejecutar

```bash
python3 driver.py archivo.cps --symbols   # TAC + reporte de símbolos
python3 -m pytest tests/test_symbols.py -q
python3 -m pytest tests/ -q               # batería completa del proyecto
python3 pruebas/runner.py                 # batería de casos .cps
```
