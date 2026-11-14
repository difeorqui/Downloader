"""Nombres ya ocupados, reservas del lote y carpetas conflictivas (RN-012 a-c, RN-013 b; D-12).

El dominio no lee el disco: la spec 002 entrega un :class:`KnownDiskEntries` de solo lectura con lo
que existe. Aquí se decide qué nombre queda libre y qué carpeta es un problema.

* **Sufijo** (RN-012 a): si la ruta existe en disco (archivo o carpeta) o la reservó otro
  elemento del lote, se añade `` (1)``, `` (2)``... antes de la **última** extensión (S-001-12),
  o al final si no hay. La comparación no distingue mayúsculas, como Windows (S-001-03).
* **Prevalecen las carpetas** (RN-012 b): un archivo nunca toma el nombre de una carpeta que
  necesita el lote, sin importar el orden de las descargas.
* **F-27** (RN-012 c): existe en disco un archivo con el nombre de una carpeta que hay que crear.
* **F-24** (RN-013 b): una carpeta intermedia que ya existe es un enlace o una unión, apunte a donde
  apunte.

Orden de uso, que decide :mod:`downloader.domain.paths.target` (S-001-07): nombre libre → F-28 →
carpetas (F-24, F-27) → F-25 → confirmar la reserva. Reservar solo al final garantiza que un
elemento que falla no deja un nombre ocupado.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from downloader.domain.catalog import FailureCode
from downloader.domain.text import windows_fold

_KEY_SEPARATOR = "\\"


class EntryKind(Enum):
    FILE = "archivo"
    DIRECTORY = "carpeta"
    REPARSE_POINT = "enlace_o_union"


class KnownDiskEntries(Protocol):
    """Puerto de **solo lectura** sobre el disco; lo implementa la spec 002."""

    def kind_of(self, relative_parts: tuple[str, ...]) -> EntryKind | None:
        """Tipo de lo que existe en esa ruta relativa a la carpeta destino, o ``None``."""
        ...


class InMemoryDiskEntries:
    """Implementación de datos para pruebas y para el cálculo sin disco; sin mayúsculas."""

    __slots__ = ("_entries",)

    def __init__(self, entries: Mapping[tuple[str, ...], EntryKind] | None = None) -> None:
        self._entries = {_key(parts): kind for parts, kind in (entries or {}).items()}

    def kind_of(self, relative_parts: tuple[str, ...]) -> EntryKind | None:
        return self._entries.get(_key(relative_parts))


@dataclass(frozen=True, slots=True)
class NameCandidate:
    """Nombre libre encontrado, aún **sin reservar**."""

    folder_parts: tuple[str, ...]
    file_name: str
    key: str  # ruta plegada del nombre (con sufijo)
    base_key: str  # ruta plegada del nombre pedido (sin sufijo)
    suffix: int  # 0 si no hizo falta sufijo


def has_extension_for_suffix(name: str) -> bool:
    """S-001-12: hay un punto que no es ni el primer ni el último carácter."""
    head, dot, tail = name.rpartition(".")
    return bool(dot and head and tail)


def add_suffix(name: str, number: int) -> str:
    """``informe.final.pdf`` → ``informe.final (1).pdf``; ``docs`` → ``docs (1)``."""
    if has_extension_for_suffix(name):
        head, _, tail = name.rpartition(".")
        return f"{head} ({number}).{tail}"
    return f"{name} ({number})"


def first_folder_problem(
    folder_parts: tuple[str, ...], disk: KnownDiskEntries
) -> FailureCode | None:
    """Recorre las carpetas de la raíz hacia dentro; la primera con problema decide.

    ``F-27`` si ya existe un archivo donde va una carpeta y ``F-24`` si es un enlace o una unión.
    La propia carpeta destino no se evalúa: puede ser un enlace (RN-013 b).
    """
    for depth in range(1, len(folder_parts) + 1):
        kind = disk.kind_of(folder_parts[:depth])
        if kind is EntryKind.FILE:
            return FailureCode.F27
        if kind is EntryKind.REPARSE_POINT:
            return FailureCode.F24
    return None


class PathReservations:
    """Reservas de un lote. Mutable; **uno por lote**; no es seguro entre hilos (lo protege la 002).

    ``required_folders`` son las carpetas que necesitan todas las URLs válidas (rutas relativas
    plegadas y unidas por ``\\``), calculadas al validar el lote.
    """

    def __init__(self, required_folders: frozenset[str]) -> None:
        self._required = required_folders
        self._reserved: set[str] = set()
        # D-12: último sufijo confirmado por nombre pedido; 10 000 nombres iguales no son O(n²)
        self._last_suffix: dict[str, int] = {}

    def find_name(
        self, folder_parts: tuple[str, ...], file_name: str, disk: KnownDiskEntries
    ) -> NameCandidate:
        """Primer nombre libre: el pedido o el pedido con sufijo. No cambia ninguna reserva."""
        base_key = _key((*folder_parts, file_name))
        number = self._last_suffix.get(base_key, 0)
        while True:
            name = file_name if number == 0 else add_suffix(file_name, number)
            key = _key((*folder_parts, name))
            if not self._is_taken(key, (*folder_parts, name), disk):
                return NameCandidate(folder_parts, name, key, base_key, number)
            number += 1

    def commit(self, candidate: NameCandidate) -> None:
        """Reserva el nombre: ningún otro elemento del lote podrá tomarlo."""
        self._reserved.add(candidate.key)
        self._last_suffix[candidate.base_key] = candidate.suffix

    def is_reserved(self, folder_parts: tuple[str, ...], file_name: str) -> bool:
        return _key((*folder_parts, file_name)) in self._reserved

    def _is_taken(self, key: str, parts: tuple[str, ...], disk: KnownDiskEntries) -> bool:
        return key in self._reserved or key in self._required or disk.kind_of(parts) is not None


def _key(parts: tuple[str, ...]) -> str:
    return _KEY_SEPARATOR.join(windows_fold(part) for part in parts)
