# Diseño del lenguaje intermedio (TAC)

Parte de Cindy en `Reparto_Proyecto2.md`: define y documenta el conjunto de
instrucciones TAC que ya generan las demás partes del compilador (Linar:
clases/objetos/listas; Gadiel: expresiones/control de flujo/funciones;
Wachuuu15: direcciones y registros de activación, como salida paralela),
consolidándolas en una sintaxis única y consistente, con el algoritmo de
reciclaje de temporales (`core/tac.py::TempManager`) y la documentación de
cómo ejecutar el compilador completo.

## Formato general

Un programa TAC es una secuencia de funciones (`func nombre:` ... cuerpo),
terminando siempre con `func main:` (el punto de entrada: las sentencias de
nivel de programa). Cada instrucción del cuerpo ocupa una línea, indentada
con 4 espacios; las etiquetas no llevan indentación de instrucción (se
escriben como `L1:`).

```
func suma:
    t1 = a + b
    return t1

func main:
    param 3
    param 4
    t1 = call suma, 2
    print t1    # (ver tabla: en realidad 'print' se traduce con param+call)
```

## Tabla de instrucciones

| Instrucción | Significado | Quién la genera |
|---|---|---|
| `x = y` | Copia: asigna el valor de `y` a `x` | todas |
| `x = a op b` | Operación binaria (`+ - * /` aritméticas; `== != < > <= >=` comparación) | Gadiel |
| `x = op a` | Operación unaria (`-` negación aritmética, `!` negación lógica) | Gadiel |
| `x = new Clase` | Reserva memoria para una instancia de `Clase`; `x` identifica el objeto | Linar |
| `x = newlist n` | Reserva memoria para una lista de `n` elementos | Linar |
| `x.attr = y` | Escribe el campo `attr` del objeto `x` | Linar |
| `x = y.attr` | Lee el campo `attr` del objeto `y` | Linar |
| `x[i] = y` | Escritura indexada (lista) | Linar |
| `x = y[i]` | Lectura indexada (lista) | Linar |
| `param x` | Empuja `x` como argumento de la próxima llamada | Linar (objetos/this) y Gadiel (funciones) |
| `x = call nombre, n` | Invoca `nombre` (ya resuelto: `Clase.metodo` o una función) con los `n` `param` anteriores; `x` recibe el valor de retorno | Linar y Gadiel |
| `call nombre, n` | Igual, pero se descarta el valor de retorno (p. ej. `call print, 1`) | todas |
| `L1:` | Etiqueta: destino de un salto | Gadiel |
| `goto L1` | Salto incondicional a `L1` | Gadiel |
| `if x goto L1` | Salta a `L1` si `x` es verdadero | Gadiel |
| `ifFalse x goto L1` | Salta a `L1` si `x` es falso | Gadiel |
| `return x` / `return` | Retorna de la función actual, con o sin valor | Gadiel |

`x`, `y`, `a`, `b`, `i` son "lugares" (*places*): un nombre de variable, un
temporal (`t1`, `t2`, ...), o un literal (`5`, `"hola"`, `true`, `false`,
`null`).

## Temporales: asignación y reciclaje

Cada vez que se necesita un lugar para guardar el resultado intermedio de
una subexpresión, se acuña un temporal nuevo (`TempManager.new_temp()`,
`t1`, `t2`, ...). Sin reciclaje, un programa con muchas sentencias
acuñaría un temporal nuevo por cada una, sin límite.

**Algoritmo de reciclaje** (`core/codegen.py::CodeGenerator._gen_stmt`,
`core/tac.py::TempManager.free_temp`): ningún temporal creado al evaluar
una sentencia (`let`, asignación, `print`, `return`, la condición de un
`if`/`while`/`for`/`switch`, etc.) se referencia jamás desde una sentencia
*hermana* posterior — cada sentencia nueva empieza evaluando su propia
expresión desde cero. Por eso, al terminar de generar una sentencia, todo
temporal que acuñó y que sigue vivo se libera y vuelve a un *pool*; la
siguiente sentencia que necesite un temporal reutiliza el nombre liberado
antes de acuñar uno nuevo. El resultado: el compilador usa la menor
cantidad de nombres de temporales distintos posible, en vez de uno nuevo
por cada subexpresión de todo el programa.

```cps
let d = !false;
let e = -5;
```
```
t1 = ! false
d = t1
t1 = - 5      ← t1 se recicló: el 't1' anterior ya murió en 'd = t1'
e = t1
```

**Simplificación consciente**: el reciclaje es a nivel de sentencia, no un
análisis de vivacidad (*liveness*) instrucción por instrucción sobre el
grafo de flujo. Por ejemplo, el temporal de la condición de un `if` sigue
"vivo" (no se recicla) durante toda la generación de sus ramas `then`/
`else`, aunque en rigor ya no se necesite después del `ifFalse`. Es una
aproximación más gruesa pero correcta y mucho más simple que una pasada de
vivacidad completa, suficiente para el alcance de este proyecto.

## Ejemplo de traducción completo

Esta es la salida real y completa del compilador para este programa
(`python3 driver.py archivo.cps`), sin editar:

```cps
class Animal {
    let name: String;
    function constructor(name) { this.name = name; }
    function speak() { print(this.name); }
}

function saludar(a: Animal) {
    a.speak();
}

let perro = new Animal("Rex");
let i = 0;
while (i < 2) {
    saludar(perro);
    i = i + 1;
}
```

```
func Animal.constructor:
    this.name = name

func Animal.speak:
    t1 = this.name
    param t1
    call print, 1

func saludar:
    param a
    t1 = call Animal.speak, 1

func main:
    t1 = new Animal
    param t1
    param "Rex"
    call Animal.constructor, 2
    perro = t1
    i = 0
    L1:
    t1 = i < 2
    ifFalse t1 goto L2
    param perro
    t2 = call saludar, 1
    t2 = i + 1
    i = t2
    goto L1
    L2:
```

Dos detalles a notar en esta salida real:
- `param this.name` **no existe**: `param` solo acepta un *lugar* simple,
  nunca una expresión compuesta, así que el valor siempre se materializa
  primero en un temporal (`t1 = this.name`) antes del `param t1`.
- Dentro de `main`, el `while` usa `t2` (no `t1`) para el resultado de
  `saludar(perro)`: el `t1` de la condición (`i < 2`) sigue vivo durante
  toda la generación del cuerpo del bucle (ver la simplificación de
  reciclaje descrita arriba), así que no está disponible todavía para
  reciclarse en ese punto.

## Supuestos y simplificaciones de diseño

- **No hay tipos en el TAC**: las anotaciones de tipo (`: Int`, `: String`,
  etc.) se usan solo durante la generación (para las validaciones
  semánticas de Linar/Gadiel y los tamaños de Wachuuu15); no aparecen en el
  TAC emitido, que es puro texto simbólico.
- **No hay direcciones en el TAC**: los operandos son nombres simbólicos
  (`x`, `t3`, `obj.attr`), no desplazamientos de memoria. El modelo de
  direcciones/registros de activación (Wachuuu15, `core/symbols.py`) es una
  salida *paralela* y opcional (`driver.py --symbols`), no reemplaza este
  formato textual.
- **Resolución estática**: tanto los métodos (vía la cadena de herencia)
  como las funciones libres/anidadas se resuelven a un nombre calificado
  fijo en tiempo de compilación (`Clase.metodo`, `funcion.anidada`); no hay
  despacho dinámico ni valores de función de primera clase.
- **`print` es la única función con tratamiento especial**: se traduce
  siempre como `param x` seguido de `call print, 1`, como si fuera una
  función predefinida de un solo parámetro.
- **Cortocircuito explícito para `&&`/`||`**: estos operadores se traducen
  con saltos (no con una instrucción binaria), para no evaluar el operando
  derecho cuando sea innecesario (ver `README_parte_Gadiel.md` para más
  detalle de control de flujo).
- **`switch` se traduce con comparaciones encadenadas** (`if subject == v
  goto Lcaso`), con *fallthrough* real entre casos que no terminan en
  `break` — no hay una instrucción de salto indexado/tabla de saltos.

## Cómo ejecutar el compilador

```bash
# TAC de un archivo .cps
python3 driver.py archivo.cps

# TAC + reporte de la tabla de símbolos (direcciones, AR, closures)
python3 driver.py archivo.cps --symbols

# Batería completa de casos .cps (válidos/inválidos)
python3 pruebas/runner.py

# Pruebas unitarias de todas las partes
python3 -m pytest tests/ -q

# IDE gráfico (editar, compilar, ver TAC/errores/tabla de símbolos/pruebas)
python3 ide/app.py
```

Ver también: `README.md` (arquitectura general), `README_parte_Linar.md`,
`README_parte_Gadiel.md` y `docs/Tabla de Simbolos.md`.
