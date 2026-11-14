"""Ventana principal (tkinter): minimalista, con avance en todo momento y cancelación."""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from downloader.application.events import (
    AllDone,
    Cancelled,
    Event,
    Failed,
    Finished,
    Progress,
    Started,
)
from downloader.application.runner import BatchRunner, RunConfig
from downloader.domain.addresses import AddressClass
from downloader.domain.batch.file_decoder import BatchFileRejection, decode_batch_file
from downloader.domain.batch.single_input import read_single_input
from downloader.domain.batch.source import SourceLine
from downloader.domain.batch.validator import BatchValidation, validate_batch
from downloader.domain.paths.destination import evaluate_destination
from downloader.domain.urls import InvalidUrl
from downloader.infrastructure.disk import is_writable_folder, system_folders
from downloader.ui import settings as settings_store
from downloader.ui.themes import PALETTES, Palette

POLL_MILLISECONDS = 100
MAX_EVENTS_PER_TICK = 200
PERCENT = 100
KILOBYTE = 1024
COLUMNS = ("url", "state", "progress", "detail")
HEADINGS = {"url": "Dirección", "state": "Estado", "progress": "Avance", "detail": "Detalle"}
WIDTHS = {"url": 380, "state": 110, "progress": 90, "detail": 300}


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < KILOBYTE or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= KILOBYTE
    return f"{value:.1f} GB"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._settings = settings_store.load()
        self._lines: list[SourceLine] = []
        self._validation: BatchValidation | None = None
        self._runner: BatchRunner | None = None
        self._events: queue.Queue[Event] = queue.Queue()
        self._running = False
        self._fractions: dict[int, float] = {}
        self._finished: set[int] = set()
        self._destination = tk.StringVar(value=self._settings.destination)
        self._url = tk.StringVar()
        self._summary = tk.StringVar(value="Agregue una dirección o cargue un archivo .txt.")
        self._overall_text = tk.StringVar(value="")
        self._theme = tk.StringVar(value=self._settings.theme)

        root.title("Descargador")
        root.minsize(860, 520)
        self._style = ttk.Style(root)
        self._style.theme_use("clam")
        self._build()
        self._apply_theme(self._settings.theme)
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_job = root.after(POLL_MILLISECONDS, self._poll)

    # --- construcción --------------------------------------------------------------------------

    def _build(self) -> None:
        outer = ttk.Frame(self._root, padding=16)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)
        self._build_header(outer)
        self._build_inputs(outer)
        ttk.Label(outer, textvariable=self._summary, style="Muted.TLabel").grid(
            row=2, column=0, sticky="w", pady=(12, 6)
        )
        self._build_table(outer)
        self._build_footer(outer)

    def _build_header(self, outer: ttk.Frame) -> None:
        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Descargador", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, text="Tema", style="Muted.TLabel").grid(row=0, column=1, padx=(0, 6))
        theme = ttk.Combobox(
            header,
            textvariable=self._theme,
            values=list(PALETTES),
            state="readonly",
            width=9,
        )
        theme.grid(row=0, column=2)
        theme.bind("<<ComboboxSelected>>", lambda _: self._apply_theme(self._theme.get()))

    def _build_inputs(self, outer: ttk.Frame) -> None:
        inputs = ttk.Frame(outer)
        inputs.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        inputs.columnconfigure(1, weight=1)
        ttk.Label(inputs, text="Dirección").grid(row=0, column=0, sticky="w", padx=(0, 10))
        entry = ttk.Entry(inputs, textvariable=self._url)
        entry.grid(row=0, column=1, sticky="ew")
        entry.bind("<Return>", lambda _: self._add_url())
        entry.focus_set()
        self._add_button = ttk.Button(inputs, text="Agregar", command=self._add_url)
        self._add_button.grid(row=0, column=2, padx=(8, 0))
        self._file_button = ttk.Button(inputs, text="Cargar archivo…", command=self._load_file)
        self._file_button.grid(row=0, column=3, padx=(8, 0))

        ttk.Label(inputs, text="Guardar en").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=(8, 0)
        )
        ttk.Entry(inputs, textvariable=self._destination, state="readonly").grid(
            row=1, column=1, sticky="ew", pady=(8, 0)
        )
        self._folder_button = ttk.Button(
            inputs, text="Elegir carpeta…", command=self._choose_folder
        )
        self._folder_button.grid(
            row=1, column=2, columnspan=2, sticky="ew", padx=(8, 0), pady=(8, 0)
        )

    def _build_table(self, outer: ttk.Frame) -> None:
        table = ttk.Frame(outer)
        table.grid(row=3, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self._tree = ttk.Treeview(table, columns=COLUMNS, show="headings", selectmode="browse")
        for column in COLUMNS:
            self._tree.heading(column, text=HEADINGS[column], anchor="w")
            self._tree.column(
                column, width=WIDTHS[column], anchor="w", stretch=column in {"url", "detail"}
            )
        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self._tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=scroll.set)

    def _build_footer(self, outer: ttk.Frame) -> None:
        footer = ttk.Frame(outer)
        footer.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        self._overall = ttk.Progressbar(footer, mode="determinate", maximum=PERCENT)
        self._overall.grid(row=0, column=0, sticky="ew")
        ttk.Label(footer, textvariable=self._overall_text, style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        buttons = ttk.Frame(footer)
        buttons.grid(row=0, column=1, rowspan=2, padx=(12, 0))
        self._clear_button = ttk.Button(buttons, text="Limpiar", command=self._clear)
        self._clear_button.grid(row=0, column=0, padx=(0, 8))
        self._open_button = ttk.Button(
            buttons, text="Abrir carpeta", command=self._open_folder, state="disabled"
        )
        self._open_button.grid(row=0, column=1, padx=(0, 8))
        self._cancel_button = ttk.Button(
            buttons, text="Cancelar", command=self._cancel, state="disabled"
        )
        self._cancel_button.grid(row=0, column=2, padx=(0, 8))
        self._start_button = ttk.Button(
            buttons,
            text="Iniciar descarga",
            command=self._start,
            style="Accent.TButton",
            state="disabled",
        )
        self._start_button.grid(row=0, column=3, padx=(0, 8))
        ttk.Button(buttons, text="Finalizar", command=self._on_close).grid(row=0, column=4)

    # --- temas ---------------------------------------------------------------------------------

    def _apply_theme(self, name: str) -> None:
        palette = PALETTES.get(name, PALETTES["Claro"])
        self._theme.set(palette.name)
        style, root = self._style, self._root
        root.configure(background=palette.background)
        font = ("Segoe UI", 10)
        style.configure(
            ".", background=palette.background, foreground=palette.foreground, font=font
        )
        style.configure("TFrame", background=palette.background)
        style.configure("TLabel", background=palette.background, foreground=palette.foreground)
        style.configure("Muted.TLabel", foreground=palette.muted)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 16))
        style.configure(
            "TButton",
            background=palette.surface,
            foreground=palette.foreground,
            bordercolor=palette.border,
            lightcolor=palette.surface,
            darkcolor=palette.surface,
            focuscolor=palette.accent,
            padding=(12, 6),
        )
        style.map(
            "TButton",
            background=[("disabled", palette.background), ("active", palette.selection)],
            foreground=[("disabled", palette.muted)],
        )
        style.configure(
            "Accent.TButton",
            background=palette.accent,
            foreground=palette.accent_text,
            bordercolor=palette.accent,
            lightcolor=palette.accent,
            darkcolor=palette.accent,
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", palette.border), ("active", palette.accent)],
            foreground=[("disabled", palette.muted)],
        )
        style.configure(
            "TEntry",
            fieldbackground=palette.surface,
            foreground=palette.foreground,
            bordercolor=palette.border,
            lightcolor=palette.border,
            darkcolor=palette.border,
            insertcolor=palette.foreground,
        )
        style.map("TEntry", fieldbackground=[("readonly", palette.surface)])
        style.configure(
            "TCombobox",
            fieldbackground=palette.surface,
            background=palette.surface,
            foreground=palette.foreground,
            arrowcolor=palette.foreground,
            bordercolor=palette.border,
        )
        style.map("TCombobox", fieldbackground=[("readonly", palette.surface)])
        root.option_add("*TCombobox*Listbox.background", palette.surface)
        root.option_add("*TCombobox*Listbox.foreground", palette.foreground)
        root.option_add("*TCombobox*Listbox.selectBackground", palette.selection)
        root.option_add("*TCombobox*Listbox.selectForeground", palette.foreground)
        style.configure(
            "Treeview",
            background=palette.surface,
            fieldbackground=palette.surface,
            foreground=palette.foreground,
            bordercolor=palette.border,
            rowheight=26,
        )
        style.map(
            "Treeview",
            background=[("selected", palette.selection)],
            foreground=[("selected", palette.foreground)],
        )
        style.configure(
            "Treeview.Heading",
            background=palette.background,
            foreground=palette.muted,
            relief="flat",
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=palette.accent,
            troughcolor=palette.border,
            bordercolor=palette.border,
            lightcolor=palette.accent,
            darkcolor=palette.accent,
        )
        style.configure(
            "Vertical.TScrollbar",
            background=palette.border,
            troughcolor=palette.background,
            bordercolor=palette.background,
            arrowcolor=palette.muted,
        )
        self._tag_colors(palette)
        self._settings = self._settings.with_theme(palette.name)
        settings_store.save(self._settings)

    def _tag_colors(self, palette: Palette) -> None:
        self._tree.tag_configure("done", foreground=palette.success)
        self._tree.tag_configure("failed", foreground=palette.error)
        self._tree.tag_configure("invalid", foreground=palette.error)
        self._tree.tag_configure("muted", foreground=palette.muted)

    # --- entrada -------------------------------------------------------------------------------

    def _add_url(self) -> None:
        if self._running:
            return
        result = read_single_input(self._url.get())
        if result is None:
            return
        if isinstance(result, InvalidUrl):
            messagebox.showwarning("Descargador", result.reason.message)
            return
        self._append([result.text])
        self._url.set("")

    def _load_file(self) -> None:
        if self._running:
            return
        path = filedialog.askopenfilename(
            title="Archivo con las direcciones", filetypes=[("Archivo de texto", "*.txt")]
        )
        if not path:
            return
        try:
            with open(path, "rb") as file:
                content = file.read(6 * 1024 * 1024)
        except OSError:
            messagebox.showerror("Descargador", "No se pudo leer el archivo.")
            return
        decoded = decode_batch_file(os.path.basename(path), content)
        if isinstance(decoded, BatchFileRejection):
            messagebox.showerror("Descargador", decoded.message)
            return
        self._append([line.text for line in decoded.lines])

    def _append(self, texts: list[str]) -> None:
        start = len(self._lines)
        self._lines.extend(SourceLine(start + n, text) for n, text in enumerate(texts, 1))
        self._revalidate()

    def _clear(self) -> None:
        if self._running:
            return
        self._lines.clear()
        self._validation = None
        self._fractions.clear()
        self._finished.clear()
        self._overall["value"] = 0
        self._overall_text.set("")
        self._open_button.configure(state="disabled")
        self._render()

    def _choose_folder(self) -> None:
        if self._running:
            return
        initial = self._destination.get() or os.path.expanduser("~")
        folder = filedialog.askdirectory(title="Carpeta donde guardar", initialdir=initial)
        if folder:
            self._destination.set(os.path.normpath(folder))
            self._settings = self._settings.with_destination(self._destination.get())
            settings_store.save(self._settings)
            self._update_buttons()

    # --- validación y tabla --------------------------------------------------------------------

    def _revalidate(self) -> None:
        self._validation = validate_batch(self._lines, len(self._lines)) if self._lines else None
        self._render()

    def _render(self) -> None:
        self._tree.delete(*self._tree.get_children())
        validation = self._validation
        if validation is None:
            self._summary.set("Agregue una dirección o cargue un archivo .txt.")
            self._update_buttons()
            return
        for item in validation.items:
            notes = []
            if item.address_class is AddressClass.INTERNAL:
                notes.append("Dirección interna: se pedirá confirmación")
            if item.url.corrections.value:
                notes.append("Corregida")
            self._tree.insert(
                "",
                "end",
                iid=f"i{item.index}",
                values=(item.url.masked(), "Pendiente", "", " · ".join(notes)),
            )
        for position, invalid in enumerate(validation.invalid):
            self._tree.insert(
                "",
                "end",
                iid=f"x{position}",
                values=(
                    invalid.masked_text,
                    "Inválida",
                    "",
                    f"{invalid.reason.message} (línea {invalid.line})",
                ),
                tags=("invalid",),
            )
        parts = [f"{len(validation.items)} válidas"]
        if validation.duplicates:
            parts.append(f"{validation.duplicates} duplicadas")
        if validation.invalid:
            parts.append(f"{len(validation.invalid)} inválidas")
        if validation.corrected:
            parts.append(f"{validation.corrected} corregidas")
        self._summary.set(" · ".join(parts))
        self._update_buttons()

    def _update_buttons(self) -> None:
        ready = bool(self._validation and self._validation.can_start and self._destination.get())
        self._start_button.configure(state="normal" if ready and not self._running else "disabled")
        state = "disabled" if self._running else "normal"
        for button in (
            self._add_button,
            self._file_button,
            self._folder_button,
            self._clear_button,
        ):
            button.configure(state=state)
        self._cancel_button.configure(state="normal" if self._running else "disabled")

    # --- ejecución -----------------------------------------------------------------------------

    def _start(self) -> None:
        validation = self._validation
        destination = self._destination.get()
        if validation is None or not validation.can_start:
            return
        problem = self._destination_problem(destination)
        if problem:
            messagebox.showerror("Carpeta destino", problem)
            return
        authorized = frozenset[str]()
        if validation.internal_hosts:
            names = "\n".join(
                f"  • {host.host} ({host.count})" for host in validation.internal_hosts
            )
            allowed = messagebox.askyesno(
                "Direcciones internas",
                "Estas direcciones apuntan a la red interna o a este equipo:\n\n"
                f"{names}\n\n¿Permite descargar de ellas?",
                icon="warning",
            )
            if not allowed:
                return
            authorized = frozenset(host.host for host in validation.internal_hosts)
        for item in validation.items:
            self._set_row(item.index, state="Pendiente", progress="", detail="", tag="")
        self._fractions.clear()
        self._finished.clear()
        self._overall["value"] = 0
        self._overall_text.set(f"0 de {len(validation.items)}")
        self._open_button.configure(state="disabled")
        config = RunConfig(destination, validation.required_folders, authorized)
        self._runner = BatchRunner(config, validation.items, self._events.put)
        self._running = True
        self._update_buttons()
        threading.Thread(target=self._runner.run, daemon=True).start()

    @staticmethod
    def _destination_problem(destination: str) -> str:
        if not os.path.isdir(destination):
            return "La carpeta elegida no existe."
        if not is_writable_folder(destination):
            return "No se puede escribir en la carpeta elegida."
        real = os.path.realpath(destination)
        if not evaluate_destination(real, system_folders(settings_store.settings_dir())):
            return "Esa carpeta pertenece al sistema. Elija otra, por ejemplo dentro de Documentos."
        return ""

    def _cancel(self) -> None:
        if self._runner is not None and self._running:
            self._runner.cancel()
            self._cancel_button.configure(state="disabled")
            self._summary.set("Cancelando…")

    def _poll(self) -> None:
        for _ in range(MAX_EVENTS_PER_TICK):
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            self._handle(event)
        self._poll_job = self._root.after(POLL_MILLISECONDS, self._poll)

    def _handle(self, event: Event) -> None:
        match event:
            case Started(index):
                self._set_row(index, state="Descargando")
            case Progress(index, downloaded, total):
                if total:
                    self._fractions[index] = min(downloaded / total, 1.0)
                    shown = f"{int(self._fractions[index] * PERCENT)} %"
                else:
                    shown = human_size(downloaded)
                self._set_row(index, progress=shown)
                self._update_overall()
            case Finished(index, path, warnings):
                self._finished.add(index)
                detail = os.path.relpath(path, self._destination.get())
                if warnings:
                    detail += " · " + " · ".join(warnings)
                self._set_row(
                    index, state="Completada", progress="100 %", detail=detail, tag="done"
                )
                self._update_overall()
            case Failed(index, message):
                self._finished.add(index)
                self._set_row(index, state="Fallida", detail=message, tag="failed")
                self._update_overall()
            case Cancelled(index):
                self._finished.add(index)
                self._set_row(index, state="Cancelada", progress="", tag="muted")
                self._update_overall()
            case AllDone(completed, failed, cancelled):
                self._running = False
                self._runner = None
                parts = [f"{completed} completadas"]
                if failed:
                    parts.append(f"{failed} fallidas")
                if cancelled:
                    parts.append(f"{cancelled} canceladas")
                self._summary.set("Terminado: " + " · ".join(parts))
                self._open_button.configure(state="normal")
                self._update_buttons()

    def _set_row(
        self,
        index: int,
        *,
        state: str | None = None,
        progress: str | None = None,
        detail: str | None = None,
        tag: str | None = None,
    ) -> None:
        iid = f"i{index}"
        if not self._tree.exists(iid):
            return
        for column, value in (("state", state), ("progress", progress), ("detail", detail)):
            if value is not None:
                self._tree.set(iid, column, value)
        if tag is not None:
            self._tree.item(iid, tags=(tag,) if tag else ())

    def _update_overall(self) -> None:
        validation = self._validation
        if validation is None or not validation.items:
            return
        total = len(validation.items)
        partial = sum(
            fraction for index, fraction in self._fractions.items() if index not in self._finished
        )
        value = (len(self._finished) + partial) / total
        self._overall["value"] = value * PERCENT
        self._overall_text.set(f"{len(self._finished)} de {total} · {int(value * PERCENT)} %")

    def _open_folder(self) -> None:
        folder = self._destination.get()
        if os.path.isdir(folder):
            os.startfile(folder)  # noqa: S606  # seguridad-ok: abre la carpeta elegida (RN-021)

    def _on_close(self) -> None:
        if self._running and not messagebox.askyesno(
            "Descargador", "Hay descargas en curso. ¿Cancelar y salir?"
        ):
            return
        self.release()
        self._root.destroy()

    def release(self) -> None:
        """Para el sondeo y cancela lo que esté en curso (al cerrar la ventana y en las pruebas)."""
        self._root.after_cancel(self._poll_job)
        if self._runner is not None:
            self._runner.cancel()
