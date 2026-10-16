# Proyecto 2: Generación de Código Intermedio (TAC)

Compilador de un subconjunto de `.cps` a código de tres direcciones (TAC):
clases, objetos, herencia y listas; expresiones, control de flujo y
funciones (incluyendo recursión, funciones anidadas y closures); tabla de
símbolos con direcciones/registros de activación; y un IDE gráfico para
escribir, compilar e inspeccionar todo lo anterior.

Ver `Reparto_Proyecto2.md` para el reparto de trabajo entre el equipo.

## Arquitectura

```
driver.py              CLI: fuente .cps -> TAC (+ reporte de símbolos con --symbols)
ide/app.py              IDE gráfico (editor, TAC, errores, tabla de símbolos, batería de pruebas)

core/
  lexer.py              Tokenización (.cps -> tokens)
  parser.py              Parser recursivo-descendente (tokens -> AST)
  ast_nodes.py           Nodos del AST
  symbols.py             Tabla de símbolos: clases/herencia, layout de objetos,
                          registros de activación, entornos léxicos (closures)
  codegen.py             AST -> TAC (y, en paralelo, alimenta la tabla de símbolos)
  tac.py                 Representación textual del TAC + reciclaje de temporales
  errors.py              Jerarquía de errores del compilador (Lex/Parse/Semantic)

pruebas/
  casos/{validos,invalidos}/*.cps    Batería de programas de prueba
  runner.py                           Corre la batería y compara contra lo esperado

tests/                   Pruebas unitarias (pytest) de cada módulo/parte

docs/
  "Lenguaje_Intermedio_TAC.md"   Especificación del TAC, ejemplos, reciclaje de temporales
  "Tabla de Simbolos.md"         Diseño de direcciones/registros de activación/closures
```

### Fases de compilación

El compilador no tiene una fase de "análisis semántico" separada: el
chequeo semántico, la generación de TAC y la construcción de la tabla de
símbolos extendida ocurren **juntos**, en un solo recorrido del AST
(`core/codegen.py`):

```
fuente .cps
   │  core/lexer.py
   ▼
tokens
   │  core/parser.py
   ▼
AST (core/ast_nodes.py)
   │  core/codegen.py  (usa core/symbols.py para clases/herencia/entornos)
   ▼
TAC (core/tac.py)  +  reporte de tabla de símbolos (opcional, --symbols)
```

## Reparto de responsabilidades por archivo

Cada integrante extendió el mismo front-end compartido en vez de duplicarlo
(ver cada README de parte para el detalle y las simplificaciones
conscientes de cada una):

| Parte | Integrante | README | Commit |
|---|---|---|---|
| Clases, objetos, listas | Linar | `README_parte_Linar.md` | 1/4 |
| Expresiones, control de flujo, funciones | Gadiel | `README_parte_Gadiel.md` | 2/4 |
| Tabla de símbolos, registros de activación | Wachuuu15 | `docs/Tabla de Simbolos.md` | 3/4 |
| Diseño del TAC, temporales, IDE | Cindy | `docs/Lenguaje_Intermedio_TAC.md` (este README) | 4/4 |

## Cómo ejecutar

```bash
# TAC de un archivo .cps
python3 driver.py pruebas/casos/validos/funciones_recursion.cps

# TAC + reporte de la tabla de símbolos (direcciones, registros de
# activación, acceso a variables libres de closures)
python3 driver.py pruebas/casos/validos/funciones_anidadas_closures.cps --symbols

# Batería completa de casos .cps (válidos e inválidos)
python3 pruebas/runner.py

# Pruebas unitarias de todo el proyecto
python3 -m pytest tests/ -q

# IDE gráfico
python3 ide/app.py
```

El IDE (`ide/app.py`, requiere `customtkinter`) permite escribir o abrir un
`.cps`, compilarlo (`Ctrl+Enter` o el botón "Compilar") y ver en pestañas
separadas el TAC generado, los errores de compilación (con su tipo —
`LexError`/`ParseError`/`SemanticError` — y la línea exacta), el reporte de
la tabla de símbolos, y el resultado de correr toda la batería de pruebas
`.cps` sin salir de la aplicación.

## Lenguaje `.cps`: resumen

```cps
class Animal {
    let name: String;
    function constructor(name) { this.name = name; }
    function speak() { print(this.name); }
}

class Dog extends Animal {
    function speak() { print("Woof"); }
}

function saludar(a: Animal) {
    a.speak();
}

const MAX = 3;
let animales = [new Animal("Rex"), new Dog("Fido")];
for (let i = 0; i < MAX && i < 2; i = i + 1) {
    saludar(animales[i]);
}
```

Cobertura: `class`/`extends`/`this`/`new`, listas (creación e indexación),
`let`/`const`, expresiones aritméticas/lógicas/de comparación con
precedencia y cortocircuito, `if/else`, `while`, `do-while`, `for`,
`switch` (con fallthrough), `break`/`continue`, funciones (libres,
anidadas, recursivas, closures). El detalle y las simplificaciones de cada
construcción están documentados en el README de la parte correspondiente.
