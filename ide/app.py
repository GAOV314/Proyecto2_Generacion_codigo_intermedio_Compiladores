"""
IDE de Compiscript (CustomTkinter): escribir/abrir un .cps, compilarlo y ver
el codigo intermedio (TAC), los errores, la tabla de simbolos extendida
(direcciones, registros de activacion), el arbol sintactico y la bateria de
pruebas. Los paneles se alimentan de `driver.Resultado`; la compilacion NO
se reimplementa aqui.
"""

from __future__ import annotations

import io
import pathlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import Image, ImageTk

from arbol.ast_graphviz import dot_disponible, render_png, render_texto
from codegen.interpreter import ejecutar
from codegen.report import render_codegen_report
from driver import Resultado, analizar
from pruebas.runner import ejecutar_bateria

ctk.set_appearance_mode("system")

MAX_NODOS_ARBOL = 400
ZOOM_PASO = 1.25


class CompiscriptIDE(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Compiscript IDE")
        self.geometry("1100x750")

        self.ruta_actual: pathlib.Path | None = None
        self.resultado: Resultado | None = None
        self._imagen_arbol_pil: Image.Image | None = None
        self._imagen_arbol_tk: ImageTk.PhotoImage | None = None
        self._zoom_arbol: float = 1.0

        self._construir_editor()
        self._construir_pestanas()
        self._construir_barra_estado()
        self.bind("<F5>", lambda evento: self.compilar())

    # ------------------------------------------------------------------
    # Construccion de la UI
    # ------------------------------------------------------------------

    def _construir_editor(self) -> None:
        barra = ctk.CTkFrame(self)
        barra.pack(side="top", fill="x")
        ctk.CTkButton(barra, text="Abrir", command=self.abrir_archivo).pack(side="left", padx=2, pady=2)
        ctk.CTkButton(barra, text="Guardar", command=self.guardar_archivo).pack(side="left", padx=2, pady=2)
        ctk.CTkButton(barra, text="Guardar como", command=self.guardar_como).pack(side="left", padx=2, pady=2)
        ctk.CTkButton(barra, text="Compilar (F5)", command=self.compilar).pack(side="left", padx=2, pady=2)
        ctk.CTkButton(barra, text="Ejecutar TAC", command=self.ejecutar_tac).pack(side="left", padx=2, pady=2)
        ctk.CTkButton(barra, text="Correr bateria", command=self.correr_bateria).pack(side="left", padx=2, pady=2)

        contenedor = ctk.CTkFrame(self)
        contenedor.pack(side="top", fill="both", expand=True)

        self.numeros_linea = tk.Text(
            contenedor, width=4, padx=4, takefocus=0, border=0,
            background="#e8e8e8", state="disabled", wrap="none",
        )
        self.numeros_linea.pack(side="left", fill="y")

        self.editor = tk.Text(contenedor, wrap="none", undo=True)
        self.editor.pack(side="left", fill="both", expand=True)
        self.editor.bind("<KeyRelease>", lambda evento: self._actualizar_numeros_linea())
        self.editor.bind("<MouseWheel>", lambda evento: self._actualizar_numeros_linea())
        self.editor.bind("<Configure>", lambda evento: self._actualizar_numeros_linea())
        self._actualizar_numeros_linea()

    def _actualizar_numeros_linea(self) -> None:
        num_lineas = int(self.editor.index("end-1c").split(".")[0])
        texto = "\n".join(str(i) for i in range(1, num_lineas + 1))
        self.numeros_linea.configure(state="normal")
        self.numeros_linea.delete("1.0", "end")
        self.numeros_linea.insert("1.0", texto)
        self.numeros_linea.configure(state="disabled")

    def _construir_pestanas(self) -> None:
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(side="top", fill="both", expand=True)
        self.tab_tac = self.tabs.add("Codigo intermedio (TAC)")
        self.tab_errores = self.tabs.add("Errores")
        self.tab_tabla = self.tabs.add("Tabla de simbolos")
        self.tab_arbol = self.tabs.add("Arbol sintactico")
        self.tab_bateria = self.tabs.add("Bateria")

        self._construir_tab_tac()
        self._construir_tab_errores()
        self._construir_tab_tabla()
        self._construir_tab_arbol()
        self._construir_tab_bateria()

    def _construir_tab_tac(self) -> None:
        self.texto_tac = ctk.CTkTextbox(self.tab_tac, font=("Courier", 13))
        self.texto_tac.pack(fill="both", expand=True)

    def _construir_tab_errores(self) -> None:
        columnas = ("linea", "columna", "categoria", "mensaje")
        self.tabla_errores = ttk.Treeview(self.tab_errores, columns=columnas, show="headings")
        for col in columnas:
            self.tabla_errores.heading(col, text=col.capitalize())
        self.tabla_errores.column("linea", width=60, anchor="center")
        self.tabla_errores.column("columna", width=70, anchor="center")
        self.tabla_errores.column("categoria", width=110, anchor="center")
        self.tabla_errores.column("mensaje", width=500, anchor="w")
        self.tabla_errores.pack(fill="both", expand=True)
        self.tabla_errores.bind("<Double-1>", self._on_doble_clic_error)

    def _construir_tab_tabla(self) -> None:
        self.texto_tabla = ctk.CTkTextbox(self.tab_tabla)
        self.texto_tabla.pack(fill="both", expand=True)

    def _construir_tab_arbol(self) -> None:
        barra = ctk.CTkFrame(self.tab_arbol)
        barra.pack(side="top", fill="x")
        ctk.CTkButton(barra, text="Acercar (+)", command=lambda: self._zoom(ZOOM_PASO)).pack(side="left", padx=2)
        ctk.CTkButton(barra, text="Alejar (-)", command=lambda: self._zoom(1 / ZOOM_PASO)).pack(side="left", padx=2)

        marco_canvas = ctk.CTkFrame(self.tab_arbol)
        marco_canvas.pack(side="top", fill="both", expand=True)

        self.canvas_arbol = tk.Canvas(marco_canvas, bg="white")
        scroll_y = ttk.Scrollbar(marco_canvas, orient="vertical", command=self.canvas_arbol.yview)
        scroll_x = ttk.Scrollbar(marco_canvas, orient="horizontal", command=self.canvas_arbol.xview)
        self.canvas_arbol.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.canvas_arbol.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        marco_canvas.rowconfigure(0, weight=1)
        marco_canvas.columnconfigure(0, weight=1)

    def _construir_tab_bateria(self) -> None:
        self.texto_bateria = ctk.CTkTextbox(self.tab_bateria)
        self.texto_bateria.pack(fill="both", expand=True)

    def _construir_barra_estado(self) -> None:
        self.barra_estado = ctk.CTkLabel(self, text="Listo", anchor="w")
        self.barra_estado.pack(side="bottom", fill="x", padx=4, pady=2)

    # ------------------------------------------------------------------
    # abrir / guardar
    # ------------------------------------------------------------------

    def abrir_archivo(self) -> None:
        ruta = filedialog.askopenfilename(filetypes=[("Compiscript", "*.cps"), ("Todos", "*.*")])
        if ruta:
            self.cargar_archivo(ruta)

    def cargar_archivo(self, ruta: str | pathlib.Path) -> None:
        ruta = pathlib.Path(ruta)
        try:
            contenido = ruta.read_text(encoding="utf-8")
        except OSError as error:
            messagebox.showerror("No se pudo abrir", str(error))
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", contenido)
        self.ruta_actual = ruta
        self._actualizar_numeros_linea()

    def guardar_archivo(self) -> None:
        if self.ruta_actual is None:
            self.guardar_como()
            return
        self._escribir_a_disco(self.ruta_actual)

    def guardar_como(self) -> None:
        ruta = filedialog.asksaveasfilename(defaultextension=".cps", filetypes=[("Compiscript", "*.cps")])
        if ruta:
            self.ruta_actual = pathlib.Path(ruta)
            self._escribir_a_disco(self.ruta_actual)

    def _escribir_a_disco(self, ruta: str | pathlib.Path) -> None:
        contenido = self.editor.get("1.0", "end-1c")
        try:
            pathlib.Path(ruta).write_text(contenido, encoding="utf-8")
        except OSError as error:
            messagebox.showerror("No se pudo guardar", str(error))

    # ------------------------------------------------------------------
    # compilar
    # ------------------------------------------------------------------

    def compilar(self) -> None:
        fuente = self.editor.get("1.0", "end-1c")
        self.resultado = analizar(fuente, nombre=str(self.ruta_actual) if self.ruta_actual else "<memoria>")
        self._pintar_tac()
        self._pintar_errores()
        self._pintar_tabla()
        self._pintar_arbol()
        self._pintar_estado()
        self.tabs.set("Codigo intermedio (TAC)" if self.resultado.tac is not None else "Errores")

    # ------------------------------------------------------------------
    # Codigo intermedio
    # ------------------------------------------------------------------

    def _pintar_tac(self) -> None:
        self.texto_tac.delete("1.0", "end")
        r = self.resultado
        if r is None:
            return
        if r.tac is not None:
            self.texto_tac.insert("1.0", r.tac.render())
        elif r.error_interno:
            self.texto_tac.insert("1.0", f"Error interno del generador:\n{r.error_interno}")
        else:
            self.texto_tac.insert(
                "1.0",
                f"No se genero codigo intermedio: hay {len(r.errores)} error(es).\n"
                "El generador solo corre cuando el analisis no reporta errores (ver pestana Errores).",
            )

    def ejecutar_tac(self) -> None:
        """Corre el TAC con el simulador y muestra lo que imprime el programa."""
        self.compilar()
        r = self.resultado
        self.texto_bateria.delete("1.0", "end")
        if r is None or r.tac is None:
            self.texto_bateria.insert("1.0", "Nada que ejecutar: corrija los errores primero.")
        else:
            try:
                salida = ejecutar(r)
                texto = "\n".join(salida) if salida else "(el programa no imprimio nada)"
            except Exception as error:  # noqa: BLE001 - se muestra al usuario
                texto = f"Error en tiempo de ejecucion: {error!r}"
            self.texto_bateria.insert("1.0", "== Salida del programa ==\n" + texto)
        self.tabs.set("Bateria")

    # ------------------------------------------------------------------
    # pestana de errores
    # ------------------------------------------------------------------

    def _pintar_errores(self) -> None:
        self.tabla_errores.delete(*self.tabla_errores.get_children())
        if self.resultado is None:
            return
        for error in self.resultado.errores:
            self.tabla_errores.insert("", "end", values=(error.line, error.column, error.category, error.message))

    def _on_doble_clic_error(self, evento) -> None:
        seleccion = self.tabla_errores.selection()
        if not seleccion:
            return
        linea = self.tabla_errores.item(seleccion[0], "values")[0]
        self.editor.mark_set("insert", f"{linea}.0")
        self.editor.see(f"{linea}.0")
        self.editor.focus_set()

    # ------------------------------------------------------------------
    # pestana de tabla de simbolos
    # ------------------------------------------------------------------

    def _pintar_tabla(self) -> None:
        self.texto_tabla.delete("1.0", "end")
        if self.resultado is None or self.resultado.table is None:
            return
        texto = self.resultado.table.format_environments()
        if self.resultado.generador is not None:
            texto += "\n\n" + render_codegen_report(self.resultado.generador)
        self.texto_tabla.insert("1.0", texto)

    # ------------------------------------------------------------------
    # pestana de arbol sintactico
    # ------------------------------------------------------------------

    def _pintar_arbol(self) -> None:
        self.canvas_arbol.delete("all")
        self._imagen_arbol_pil = None
        self._imagen_arbol_tk = None
        self._zoom_arbol = 1.0

        if self.resultado is None or self.resultado.tree is None or self.resultado.parser is None:
            return

        if dot_disponible():
            try:
                png_bytes = render_png(self.resultado.tree, self.resultado.parser.ruleNames, MAX_NODOS_ARBOL)
                self._imagen_arbol_pil = Image.open(io.BytesIO(png_bytes))
                self._dibujar_imagen_arbol()
                return
            except Exception:
                pass  # cae al fallback de texto

        texto = render_texto(self.resultado.tree, self.resultado.parser)
        self.canvas_arbol.create_text(10, 10, anchor="nw", text=texto, font=("Courier", 10))
        self.canvas_arbol.configure(scrollregion=self.canvas_arbol.bbox("all"))

    def _dibujar_imagen_arbol(self) -> None:
        if self._imagen_arbol_pil is None:
            return
        ancho = int(self._imagen_arbol_pil.width * self._zoom_arbol)
        alto = int(self._imagen_arbol_pil.height * self._zoom_arbol)
        imagen_escalada = self._imagen_arbol_pil.resize((max(ancho, 1), max(alto, 1)))
        self._imagen_arbol_tk = ImageTk.PhotoImage(imagen_escalada)
        self.canvas_arbol.delete("all")
        self.canvas_arbol.create_image(0, 0, anchor="nw", image=self._imagen_arbol_tk)
        self.canvas_arbol.configure(scrollregion=(0, 0, ancho, alto))

    def _zoom(self, factor: float) -> None:
        if self._imagen_arbol_pil is None:
            return
        self._zoom_arbol *= factor
        self._dibujar_imagen_arbol()

    # ------------------------------------------------------------------
    # boton de bateria
    # ------------------------------------------------------------------

    def correr_bateria(self) -> None:
        resultados = ejecutar_bateria()
        pasaron = [r for r in resultados if r.paso]
        fallos = [r for r in resultados if not r.paso]

        lineas = [f"{len(pasaron)}/{len(resultados)} pasaron"]
        for r in fallos:
            lineas.append(f"FALLO {r.archivo}: {r.razon}")

        self.texto_bateria.delete("1.0", "end")
        self.texto_bateria.insert("1.0", "\n".join(lineas))
        self.tabs.set("Bateria")

    # ------------------------------------------------------------------
    # barra de estado
    # ------------------------------------------------------------------

    def _pintar_estado(self) -> None:
        if self.resultado is None:
            return
        if self.resultado.ok:
            self.barra_estado.configure(text="OK", text_color="green")
        else:
            n = len(self.resultado.errores)
            self.barra_estado.configure(text=f"{n} error{'es' if n != 1 else ''}", text_color="red")


def main() -> None:
    app = CompiscriptIDE()
    app.mainloop()


if __name__ == "__main__":
    main()
