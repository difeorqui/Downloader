"""Gancho de auditoria contra efectos externos en las pruebas del dominio (T-02, RNF-001-06).

``tests/audit_guard.py`` instala un ``sys.addaudithook`` que, mientras esta activo, hace fallar
cualquier acceso a red, escritura en disco, cambio del sistema de archivos o lanzamiento de
procesos. ``tests/conftest.py`` lo activa en ``tests/unit/domain``, ``tests/regression`` y
``tests/property``. Aqui se prueba el gancho y se demuestra con las muestras de ``samples/``.
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

import pytest

from tests.audit_guard import GUARD, SideEffectViolation, is_guarded, violation_for

SAMPLES = Path(__file__).resolve().parent / "samples"
TESTS_DIR = Path(__file__).resolve().parents[1]


def load_sample(name: str, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Importa una muestra (solo define funciones; no ejecuta nada peligroso al importarla)."""
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    loader = SourceFileLoader(f"sample_{name.split('.', maxsplit=1)[0]}", str(SAMPLES / name))
    module = ModuleType(loader.name)
    module.__file__ = str(SAMPLES / name)
    loader.exec_module(module)
    return module


# --- clasificacion de eventos (funcion pura) ----------------------------------------------------


@pytest.mark.parametrize(
    ("event", "args"),
    [
        ("socket.__new__", (object(), 2, 1, 0)),
        ("socket.connect", (object(), ("127.0.0.1", 80))),
        ("socket.bind", (object(), ("127.0.0.1", 0))),
        ("socket.getaddrinfo", ("localhost", 80, 0, 0, 0)),
        ("socket.gethostbyname", ("localhost",)),
        ("http.client.connect", (object(), "host", 80)),
        ("urllib.Request", ("http://x", None, {}, "GET")),
        ("subprocess.Popen", ("cmd", ["cmd"], None, None)),
        ("os.system", ("cmd",)),
        ("os.mkdir", ("d", 0o777, -1)),
        ("os.remove", ("f", -1)),
        ("os.rmdir", ("d", -1)),
        ("os.rename", ("a", "b", -1, -1)),
        ("os.replace", ("a", "b", -1, -1)),
        ("os.truncate", ("f", 0)),
        ("os.symlink", ("a", "b", 0, -1)),
        ("os.link", ("a", "b", -1, -1)),
        ("os.chmod", ("f", 0o600, -1)),
        ("os.startfile", ("f", "open")),
        ("shutil.rmtree", ("d", -1)),
        ("shutil.copyfile", ("a", "b")),
        ("shutil.move", ("a", "b")),
        ("open", ("f.txt", "w", 0)),
        ("open", ("f.txt", "wb", 0)),
        ("open", ("f.txt", "a", 0)),
        ("open", ("f.txt", "x", 0)),
        ("open", ("f.txt", "r+", 0)),
        ("open", ("f.txt", None, os.O_WRONLY | os.O_CREAT)),
        ("open", ("f.txt", "r", os.O_RDWR)),
        ("open", ("f.txt", None, os.O_APPEND)),
        ("open", ("f.txt", None, os.O_TRUNC)),
    ],
)
def test_forbidden_events_are_classified(event: str, args: tuple[object, ...]) -> None:
    assert violation_for(event, args) is not None


@pytest.mark.parametrize(
    ("event", "args"),
    [
        ("open", ("f.txt", "r", 0)),
        ("open", ("f.txt", "rb", 0)),
        ("open", ("f.txt", None, os.O_RDONLY)),
        ("open", (3, "r", 0)),
        ("os.listdir", ("d",)),
        ("os.scandir", ("d",)),
        ("compile", (b"x", "f")),
        ("exec", (object(),)),
        ("import", ("m", None, [], None, None)),
        ("sys.addaudithook", ()),
        ("object.__setattr__", (object(), "a")),
        # el interprete escribe su cache de bytecode al importar modulos por primera vez
        ("open", ("C:\\x\\__pycache__\\m.cpython-313.pyc.123", "wb", 0)),
        ("open", ("/x/__pycache__/m.cpython-313.pyc", None, os.O_WRONLY | os.O_CREAT)),
    ],
)
def test_harmless_events_are_not_classified(event: str, args: tuple[object, ...]) -> None:
    assert violation_for(event, args) is None


def test_violation_message_names_the_event() -> None:
    message = violation_for("os.mkdir", ("d", 0o777, -1))
    assert message is not None
    assert "os.mkdir" in message


# --- que suites quedan protegidas ---------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "unit/domain/test_x.py",
        "unit/domain/urls/test_parser.py",
        "regression/test_annex1.py",
        "regression/test_determinism.py",
        "property/test_properties.py",
    ],
)
def test_guarded_suites(relative: str) -> None:
    assert is_guarded(TESTS_DIR / relative, TESTS_DIR)


@pytest.mark.parametrize(
    "relative",
    [
        "architecture/test_layers.py",
        "unit/other/test_x.py",
        "unit/test_x.py",
        "integration/test_x.py",
        "performance/test_perf.py",
        "test_smoke.py",
        "regressionx/test_x.py",
    ],
)
def test_unguarded_suites(relative: str) -> None:
    assert not is_guarded(TESTS_DIR / relative, TESTS_DIR)


def test_path_outside_tests_is_not_guarded() -> None:
    assert not is_guarded(Path(TESTS_DIR.anchor) / "otro" / "test_x.py", TESTS_DIR)


# --- el gancho bloquea de verdad (con las muestras) ---------------------------------------------


def test_guard_is_inactive_in_architecture_suite() -> None:
    assert not GUARD.is_active()


def test_guard_context_activates_and_restores() -> None:
    with GUARD.active():
        assert GUARD.is_active()
        with GUARD.active():
            assert GUARD.is_active()
        assert GUARD.is_active()
    assert not GUARD.is_active()


def test_guard_restores_state_after_an_exception() -> None:
    with pytest.raises(KeyError), GUARD.active():
        raise KeyError("provocada a proposito")
    assert not GUARD.is_active()


def test_sample_open_for_writing_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample = load_sample("open_write.py.sample", monkeypatch)
    target = tmp_path / "salida.txt"
    with GUARD.active(), pytest.raises(SideEffectViolation):
        sample.save(str(target))
    assert not target.exists()


def test_sample_socket_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = load_sample("import_socket.py.sample", monkeypatch)
    with GUARD.active(), pytest.raises(SideEffectViolation, match=r"socket\."):
        sample.connect()


def test_reading_files_is_allowed(tmp_path: Path) -> None:
    existing = tmp_path / "datos.txt"
    existing.write_text("hola", encoding="utf-8")
    with GUARD.active():
        assert existing.read_text(encoding="utf-8") == "hola"


def test_filesystem_changes_are_blocked(tmp_path: Path) -> None:
    existing = tmp_path / "datos.txt"
    existing.write_text("hola", encoding="utf-8")
    with GUARD.active():
        with pytest.raises(SideEffectViolation):
            os.mkdir(tmp_path / "nueva")
        with pytest.raises(SideEffectViolation):
            existing.unlink()
        with pytest.raises(SideEffectViolation):
            os.rename(existing, tmp_path / "otra.txt")
        with pytest.raises(SideEffectViolation):
            shutil.copyfile(existing, tmp_path / "copia.txt")
        with pytest.raises(SideEffectViolation):
            (tmp_path / "creada.txt").write_text("x", encoding="utf-8")
    assert existing.exists()
    assert not (tmp_path / "nueva").exists()
    assert not (tmp_path / "otra.txt").exists()
    assert not (tmp_path / "copia.txt").exists()
    assert not (tmp_path / "creada.txt").exists()


def test_network_is_blocked() -> None:
    with GUARD.active():
        with pytest.raises(SideEffectViolation):
            socket.socket()
        with pytest.raises(SideEffectViolation):
            socket.getaddrinfo("localhost", 80)
