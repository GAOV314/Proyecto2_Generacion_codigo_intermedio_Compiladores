"""IDE gráfico mínimo para escribir y compilar .cps (parte de Cindy).

Permite:
- Escribir/editar código .cps en un editor de texto.
- Compilarlo y ver el TAC generado (Ctrl+Enter o el botón "Compilar").
- Ver errores de compilación con su tipo (LexError/ParseError/
  SemanticError) y la línea donde ocurrieron.
- Ver el reporte de la tabla de símbolos extendida (direcciones, registros
  de activación, acceso a variables libres de closures).
- Ejecutar la batería de pruebas .cps (pruebas/runner.py) y ver el
  resultado, sin salir del IDE.

Ejecutar: python3 ide/app.py
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path
from tkinter import filedialog

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import customtkinter as ctk  # noqa: E402

import pruebas.runner as runner  # noqa: E402
from core.errors import CompilerError  # noqa: E402
from driver import compile_with_symbols  # noqa: E402

EJEMPLO = """class Animal {
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
"""


class CompilerIDE(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("IDE .cps — Proyecto 2: Generación de Código Intermedio (TAC)")
        self.geometry("1150x720")
        ctk.set_appearance_mode("system")

        self.mono_font = ctk.CTkFont(family="Menlo", size=13)

        self._build_toolbar()
        self._build_body()

        self.editor.insert("1.0", EJEMPLO)

    # -- construcción de la interfaz -------------------------------------
    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self)
        bar.pack(side="top", fill="x", padx=8, pady=8)

        ctk.CTkButton(bar, text="Abrir...", command=self.open_file, width=90).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Guardar...", command=self.save_file, width=90).pack(side="left", padx=4)
        ctk.CTkButton(
            bar, text="Compilar (Ctrl+Enter)", command=self.compile_current, width=160
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            bar, text="Correr batería de pruebas", command=self.run_battery, width=190
        ).pack(side="left", padx=4)

        self.status_label = ctk.CTkLabel(bar, text="Listo.")
        self.status_label.pack(side="right", padx=8)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self)
        body.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        editor_frame = ctk.CTkFrame(body)
        editor_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(editor_frame, text="Código .cps").pack(anchor="w", padx=6, pady=(6, 0))
        self.editor = ctk.CTkTextbox(editor_frame, font=self.mono_font, undo=True)
        self.editor.pack(fill="both", expand=True, padx=6, pady=6)
        self.editor.bind("<Control-Return>", lambda _event: self.compile_current())

        self.tabs = ctk.CTkTabview(body)
        self.tabs.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        for name in ("TAC", "Errores", "Tabla de símbolos", "Pruebas"):
            self.tabs.add(name)

        self.tac_box = self._make_output_box(self.tabs.tab("TAC"))
        self.errors_box = self._make_output_box(self.tabs.tab("Errores"))
        self.symbols_box = self._make_output_box(self.tabs.tab("Tabla de símbolos"))
        self.tests_box = self._make_output_box(self.tabs.tab("Pruebas"))

    def _make_output_box(self, parent: ctk.CTkFrame) -> ctk.CTkTextbox:
        box = ctk.CTkTextbox(parent, font=self.mono_font)
        box.pack(fill="both", expand=True, padx=4, pady=4)
        box.configure(state="disabled")
        return box

    # -- utilidades ------------------------------------------------------
    def _set_box_text(self, box: ctk.CTkTextbox, text: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    # -- acciones de archivo ----------------------------------------------
    def open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Archivos .cps", "*.cps"), ("Todos", "*.*")])
        if not path:
            return
        with open(path, encoding="utf-8") as f:
            source = f.read()
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", source)
        self.status_label.configure(text=f"Abierto: {path}")

    def save_file(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".cps", filetypes=[("Archivos .cps", "*.cps")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.editor.get("1.0", "end"))
        self.status_label.configure(text=f"Guardado: {path}")

    # -- compilación -------------------------------------------------------
    def compile_current(self) -> None:
        source = self.editor.get("1.0", "end")
        try:
            generator, tac = compile_with_symbols(source)
        except CompilerError as e:
            self._set_box_text(self.tac_box, "")
            self._set_box_text(self.symbols_box, "")
            tipo = type(e).__name__
            ubicacion = f"línea {e.line}" if e.line is not None else "ubicación desconocida"
            self._set_box_text(self.errors_box, f"[{tipo}] {e.message}\n({ubicacion})\n")
            self.tabs.set("Errores")
            self.status_label.configure(text=f"Error de compilación: {tipo}.")
            return

        self._set_box_text(self.tac_box, tac)
        report = generator.symtab.render_report()
        self._set_box_text(
            self.symbols_box, report or "(no hay clases, funciones ni closures que reportar)\n"
        )
        self._set_box_text(self.errors_box, "Sin errores.\n")
        self.tabs.set("TAC")
        self.status_label.configure(text="Compilación exitosa.")

    # -- batería de pruebas --------------------------------------------------
    def run_battery(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = runner.main()
        self._set_box_text(self.tests_box, buffer.getvalue())
        self.tabs.set("Pruebas")
        self.status_label.configure(
            text="Batería: todas las pruebas pasaron." if exit_code == 0 else "Batería: hay pruebas fallidas."
        )


def main() -> None:
    app = CompilerIDE()
    app.mainloop()


if __name__ == "__main__":
    main()
