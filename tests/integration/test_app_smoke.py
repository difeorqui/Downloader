"""Humo de la ventana real (tkinter): flujo completo con un servidor local y los tres temas."""

from __future__ import annotations

import http.server
import os
import threading
import time
import tkinter as tk
from collections.abc import Iterator
from pathlib import Path
from tkinter import filedialog, messagebox

import pytest

from downloader.ui import settings as settings_store
from downloader.ui.app import App, human_size
from downloader.ui.themes import PALETTES

BODY = b"contenido de prueba" * 5000


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path.startswith("/slow"):
            self.send_response(200)
            self.send_header("Content-Length", str(400 * 1024))
            self.end_headers()
            try:
                for _ in range(400):
                    self.wfile.write(b"z" * 1024)
                    self.wfile.flush()
                    time.sleep(0.02)
            except OSError:
                return
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(BODY)))
        self.end_headers()
        self.wfile.write(BODY)


@pytest.fixture(scope="module")
def base_url() -> Iterator[str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def tk_root() -> Iterator[tk.Tk]:
    """Una sola raíz Tk por módulo: recrear el intérprete Tcl varias veces falla a ratos."""
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"No hay pantalla disponible para tkinter: {error}")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def app(tk_root: tk.Tk, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[App]:
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(messagebox, "showwarning", lambda *a, **k: None)
    window = App(tk_root)
    yield window
    window.release()
    for child in tk_root.winfo_children():
        child.destroy()


def pump(app: App, until: object, seconds: float = 20.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app._root.update()
        if callable(until) and until():
            return
        time.sleep(0.01)
    pytest.fail("la ventana no llegó al estado esperado a tiempo")


def rows(app: App) -> list[tuple[str, ...]]:
    return [tuple(app._tree.item(iid, "values")) for iid in app._tree.get_children()]


def test_adding_urls_validates_and_shows_invalid_lines(app: App) -> None:
    app._url.set("https://sitio.com/a.pdf")
    app._add_url()
    app._url.set("ftp://x.com/a")
    app._add_url()
    states = [row[1] for row in rows(app)]
    assert states == ["Pendiente", "Inválida"]
    assert "1 válidas" in app._summary.get()
    assert "Protocolo no soportado" in rows(app)[1][3]


def test_start_stays_disabled_until_there_is_a_valid_url_and_a_folder(
    app: App, tmp_path: Path
) -> None:
    assert str(app._start_button.cget("state")) == "disabled"
    app._url.set("https://sitio.com/a.pdf")
    app._add_url()
    assert str(app._start_button.cget("state")) == "disabled"
    app._destination.set(str(tmp_path))
    app._update_buttons()
    assert str(app._start_button.cget("state")) == "normal"


def test_full_download_with_progress_and_folders(app: App, base_url: str, tmp_path: Path) -> None:
    destination = tmp_path / "descargas"
    destination.mkdir()
    app._destination.set(str(destination))
    app._url.set(f"{base_url}/informe.pdf")
    app._add_url()
    app._start()
    pump(app, lambda: not app._running)
    saved = [p for p in destination.rglob("*") if p.is_file()]
    assert [p.name for p in saved] == ["informe.pdf"]
    assert saved[0].read_bytes() == BODY
    assert saved[0].parent.name.startswith("127.0.0.1_")  # subcarpeta por la estructura de la URL
    assert rows(app)[0][1] == "Completada"
    assert rows(app)[0][2] == "100 %"
    assert float(app._overall["value"]) == 100.0
    assert "1 completadas" in app._summary.get()
    assert str(app._open_button.cget("state")) == "normal"


def test_cancel_stops_the_download_from_the_window(app: App, base_url: str, tmp_path: Path) -> None:
    destination = tmp_path / "descargas"
    destination.mkdir()
    app._destination.set(str(destination))
    app._url.set(f"{base_url}/slow")
    app._add_url()
    app._start()
    pump(app, lambda: rows(app)[0][1] == "Descargando" and rows(app)[0][2] != "")
    assert str(app._cancel_button.cget("state")) == "normal"
    app._cancel()
    pump(app, lambda: not app._running)
    assert rows(app)[0][1] == "Cancelada"
    assert [p for p in destination.rglob("*") if p.is_file()] == []
    assert "1 canceladas" in app._summary.get()


def test_a_system_folder_is_refused_as_destination(app: App, base_url: str) -> None:
    windows = os.environ.get("SYSTEMROOT", "C:\\Windows")
    app._destination.set(windows)
    app._url.set(f"{base_url}/a.pdf")
    app._add_url()
    app._start()
    assert not app._running


def test_loading_a_file_adds_its_lines(
    app: App, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    listing = tmp_path / "lista.txt"
    listing.write_text(
        "# comentario\nhttps://a.com/1.pdf\n\nhttps://b.com/2.pdf\nbasura!!\n", encoding="utf-8"
    )
    monkeypatch.setattr(filedialog, "askopenfilename", lambda *a, **k: str(listing))
    app._load_file()
    assert len(rows(app)) == 3


def test_a_rejected_file_shows_its_message(
    app: App, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[str] = []
    monkeypatch.setattr(messagebox, "showerror", lambda title, message: shown.append(message))
    listing = tmp_path / "lista.csv"
    listing.write_text("https://a.com/1.pdf", encoding="utf-8")
    monkeypatch.setattr(filedialog, "askopenfilename", lambda *a, **k: str(listing))
    app._load_file()
    assert shown == [
        "Los archivos .csv no se admiten. Guarde la lista como .txt, con una URL por línea."
    ]
    assert rows(app) == []


@pytest.mark.parametrize("theme", list(PALETTES))
def test_the_three_themes_apply_and_are_remembered(app: App, theme: str) -> None:
    app._theme.set(theme)
    app._apply_theme(theme)
    app._root.update()
    assert str(app._root.cget("background")).lower() == PALETTES[theme].background.lower()
    assert settings_store.load().theme == theme


def test_the_window_title_never_contains_a_url(app: App) -> None:
    app._url.set("https://u:clave@sitio.com/a.pdf?token=secreto")
    app._add_url()
    assert app._root.title() == "Descargador"
    assert all(
        "secreto" not in str(value) and "clave" not in str(value)
        for row in rows(app)
        for value in row
    )


def test_human_size() -> None:
    assert human_size(0) == "0 B"
    assert human_size(1023) == "1023 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"
    assert human_size(3 * 1024**3) == "3.0 GB"
    assert human_size(5000 * 1024**3).endswith("GB")


def test_the_finish_button_closes_the_window_and_stops_a_running_download(
    app: App, base_url: str, tmp_path: Path
) -> None:
    closed: list[bool] = []
    app._root.destroy = lambda: closed.append(True)  # type: ignore[method-assign]
    app._destination.set(str(tmp_path))
    app._url.set(f"{base_url}/slow")
    app._add_url()
    app._start()
    pump(app, lambda: rows(app)[0][1] == "Descargando")
    app._on_close()  # lo que ejecuta el botón «Finalizar»
    assert closed == [True]
    assert app._runner is None or app._runner._cancel.is_set()
