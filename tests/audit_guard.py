"""Gancho de auditoria (``sys.addaudithook``) contra efectos externos (T-02, RNF-001-06).

Mientras esta activo, hace fallar con ``SideEffectViolation`` cualquier intento de abrir
sockets o resolver nombres, escribir o cambiar el sistema de archivos, lanzar procesos o
abrir archivos en modo escritura. Solo lo activa ``tests/conftest.py`` durante la fase de
llamada de las pruebas de ``tests/unit/domain``, ``tests/regression`` y ``tests/property``:
el dominio es puro (PA-01) y sus pruebas no necesitan ninguna de esas operaciones.

Es infraestructura de pruebas (no llega a produccion). El estado del gancho es un contador
porque ``sys.addaudithook`` no permite desinstalar ganchos: se instala una vez y se activa o
desactiva consultando el contador.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final


class SideEffectViolation(RuntimeError):
    """Una prueba del dominio intento un efecto externo."""


# Eventos de auditoria exactos prohibidos.
_FORBIDDEN_EVENTS: Final = frozenset(
    {
        "os.system",
        "os.mkdir",
        "os.remove",
        "os.rmdir",
        "os.rename",
        "os.replace",
        "os.truncate",
        "os.symlink",
        "os.link",
        "os.chmod",
        "os.chown",
        "os.utime",
        "os.startfile",
        "os.posix_spawn",
        "subprocess.Popen",
        "urllib.Request",
    }
)

# Prefijos de eventos prohibidos: toda la familia.
_FORBIDDEN_PREFIXES: Final = (
    "socket.",
    "http.client.",
    "shutil.",
    "os.exec",
    "os.spawn",
)

_WRITE_MODE_CHARS: Final = frozenset("wax+")
_WRITE_FLAGS: Final = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

# Carpetas de pruebas (relativas a ``tests/``) cuyo codigo corre con el gancho activo.
_GUARDED_PREFIXES: Final = (("unit", "domain"), ("regression",), ("property",))


def violation_for(event: str, args: tuple[object, ...]) -> str | None:
    """Mensaje de infraccion si el evento de auditoria es un efecto externo; si no, ``None``."""
    if event in _FORBIDDEN_EVENTS or event.startswith(_FORBIDDEN_PREFIXES):
        return f"Efecto externo prohibido en pruebas del dominio: {event}"
    if event == "open" and _opens_for_writing(args):
        return "Efecto externo prohibido en pruebas del dominio: open (escritura)"
    return None


def _opens_for_writing(args: tuple[object, ...]) -> bool:
    if len(args) < 3:
        return False
    path, mode, flags = args[0], args[1], args[2]
    if _is_bytecode_cache(path):
        return False
    writes_by_mode = isinstance(mode, str) and not _WRITE_MODE_CHARS.isdisjoint(mode)
    writes_by_flags = isinstance(flags, int) and bool(flags & _WRITE_FLAGS)
    return writes_by_mode or writes_by_flags


def _is_bytecode_cache(path: object) -> bool:
    """El interprete escribe ``__pycache__/*.pyc`` al importar un modulo por primera vez."""
    try:
        text = os.fsdecode(path) if isinstance(path, str | bytes | os.PathLike) else ""
    except (TypeError, ValueError):
        return False
    return "__pycache__" in text.replace("\\", "/").split("/")


def is_guarded(path: Path, tests_dir: Path) -> bool:
    """``True`` si el archivo de pruebas pertenece a una suite que corre con el gancho activo."""
    try:
        parts = path.relative_to(tests_dir).parts
    except ValueError:
        return False
    return any(
        parts[: len(prefix)] == prefix and len(parts) > len(prefix) for prefix in _GUARDED_PREFIXES
    )


class SideEffectGuard:
    """Interruptor del gancho de auditoria (instalado una sola vez por proceso)."""

    def __init__(self) -> None:
        self._depth = 0
        self._installed = False

    def is_active(self) -> bool:
        return self._depth > 0

    def _hook(self, event: str, args: tuple[object, ...]) -> None:
        if self._depth > 0:
            message = violation_for(event, args)
            if message is not None:
                raise SideEffectViolation(message)

    def _install(self) -> None:
        if not self._installed:
            self._installed = True
            sys.addaudithook(self._hook)

    @contextmanager
    def active(self) -> Iterator[None]:
        self._install()
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1


GUARD: Final = SideEffectGuard()
