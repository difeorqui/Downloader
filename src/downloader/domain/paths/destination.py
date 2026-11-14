"""Validez léxica de la carpeta destino sobre su ruta real (RN-007 c, D-11).

La spec 002 resuelve los enlaces y uniones y entrega la **ruta real** y las ubicaciones del
sistema; aquí solo se decide si esa ruta es aceptable. No es válida la carpeta de Windows, las de
Archivos de programa (64 y 32 bits), la de datos de programas de Windows ni la de datos de esta
aplicación, ni nada que esté dentro de ellas, ni la raíz de la unidad de Windows.

Se comparan **componentes** completos, sin distinguir mayúsculas y con ``/`` como ``\\``:
``C:\\WindowsBackup`` no está dentro de ``C:\\Windows``. Se quitan los prefijos ``\\\\?\\`` y
``\\\\?\\UNC\\`` y las barras finales (salvo en la raíz). Una ruta no absoluta no es aceptable.
"""

from dataclasses import dataclass
from typing import Final

from downloader.domain.text import windows_fold

_SEPARATOR: Final = "\\"
_EXTENDED_PREFIX: Final = "\\\\?\\"
_EXTENDED_UNC_PREFIX: Final = "\\\\?\\UNC\\"
_UNC_PREFIX: Final = "\\\\"
_DRIVE_LENGTH: Final = 2  # "C:"


@dataclass(frozen=True, slots=True)
class SystemFolders:
    """Ubicaciones del sistema, ya como rutas reales (las entrega la spec 002)."""

    windows: str
    program_files: str
    program_files_x86: str
    program_data: str
    app_data: str
    system_drive_root: str


type Components = tuple[str, ...]


def evaluate_destination(real_path: str, system: SystemFolders) -> bool:
    """``True`` si la ruta real es aceptable como carpeta destino (RN-007 c)."""
    candidate = _components(real_path)
    if candidate is None:
        return False
    forbidden_trees = (
        system.windows,
        system.program_files,
        system.program_files_x86,
        system.program_data,
        system.app_data,
    )
    for tree in forbidden_trees:
        tree_components = _components(tree)
        if tree_components and candidate[: len(tree_components)] == tree_components:
            return False
    root = _components(system.system_drive_root)
    return not (root and candidate == root)


def _components(path: str) -> Components | None:
    """Componentes plegados de una ruta absoluta de Windows, o ``None`` si no es absoluta."""
    text = path.replace("/", _SEPARATOR)
    if text.upper().startswith(_EXTENDED_UNC_PREFIX.upper()):
        text = _UNC_PREFIX + text[len(_EXTENDED_UNC_PREFIX) :]
    elif text.startswith(_EXTENDED_PREFIX):
        text = text[len(_EXTENDED_PREFIX) :]

    is_unc = text.startswith(_UNC_PREFIX)
    drive_root = (
        len(text) > _DRIVE_LENGTH
        and text[0].isascii()
        and text[0].isalpha()
        and text[1] == ":"
        and text[2] == _SEPARATOR
    )
    if not (is_unc or drive_root):
        return None

    floor = 2 if is_unc else 1  # servidor y recurso compartido / la unidad: nunca se sale de ahí
    resolved: list[str] = []
    for part in text.split(_SEPARATOR):
        if part in {"", "."}:
            continue
        if part == "..":
            if len(resolved) > floor:
                resolved.pop()
            continue
        resolved.append(windows_fold(part))
    if len(resolved) < floor:
        return None  # UNC sin servidor o sin recurso compartido
    if is_unc:
        resolved[:1] = [_UNC_PREFIX + resolved[0]]
    return tuple(resolved)
