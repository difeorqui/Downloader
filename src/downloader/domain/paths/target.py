"""Ruta resultante de una descarga (RN-008 a RN-016, D-07, D-11; contrato §5).

``compute_target_path`` es el único punto que junta todas las piezas del dominio de rutas. Orden de
fallos (S-001-07), el primero que se cumple:

1. nombre libre con su sufijo de colisión (RN-012);
2. **F-28** componente de más de 255 caracteres (RN-016 a);
3. carpetas, de la raíz hacia dentro: **F-24** enlace o unión, **F-27** archivo donde va una
   carpeta (RN-013 b, RN-012 c);
4. **F-25** ruta final o temporal por encima del límite (RN-016 b);
5. guarda de contención: la ruta debe quedar dentro de la carpeta destino, si no **F-24**.

El nombre solo se **reserva** si el resultado es correcto: un elemento que falla no deja un nombre
ocupado. Mismas entradas y mismo orden de llamadas dan el mismo resultado (RNF-001-04).
"""

from dataclasses import dataclass
from typing import Final

from downloader.domain.catalog import FailureCode, WarningCode
from downloader.domain.paths.collisions import (
    KnownDiskEntries,
    PathReservations,
    first_folder_problem,
)
from downloader.domain.paths.failure import PathFailure
from downloader.domain.paths.filename import choose_file_name
from downloader.domain.paths.length import (
    MAX_COMPONENT_LENGTH,
    PathLimits,
    check_component_lengths,
    check_total_length,
)
from downloader.domain.paths.relative import url_path_parts
from downloader.domain.paths.response import ServerResponse
from downloader.domain.paths.sanitize import (
    INVALID_CHARS,
    INVISIBLE_CHARS,
    RESERVED_NAMES,
)
from downloader.domain.text import utf16_len, windows_fold
from downloader.domain.urls.model import ParsedUrl
from downloader.domain.warnings import classify_warnings

_SEPARATOR: Final = "\\"
_CONTROL_LIMIT: Final = 0x20
_DRIVE_LENGTH: Final = 2  # "D:"


@dataclass(frozen=True, slots=True)
class TargetPath:
    """Ruta calculada. ``full_path`` p. ej. ``D:\\Descargas\\sitio.com\\a (1).pdf``."""

    full_path: str
    folder_parts: tuple[str, ...]  # componentes de carpeta relativos a la carpeta destino
    file_name: str
    warnings: frozenset[WarningCode]  # A-1 / A-2 (RN-021)


@dataclass(frozen=True, slots=True)
class PathEnvironment:
    """Lo que la spec 002 construye una vez por lote: disco conocido, reservas y límites.

    ``reservations`` es mutable (uno por lote) y no es seguro entre hilos: la 002 lo protege.
    """

    disk: KnownDiskEntries
    reservations: PathReservations
    limits: PathLimits


def compute_target_path(
    destination: str,
    url: ParsedUrl,
    response: ServerResponse | None,
    environment: PathEnvironment,
) -> TargetPath | PathFailure:
    """Calcula la ruta del archivo o el fallo (F-24, F-25, F-27 o F-28); nunca lanza excepciones."""
    disk, reservations, limits = environment.disk, environment.reservations, environment.limits
    root = normalize_destination(destination)
    folder_parts = url_path_parts(url).folders
    base_name = choose_file_name(url, response)
    candidate = reservations.find_name(folder_parts, base_name, disk)
    file_name = candidate.file_name

    code = (
        check_component_lengths(folder_parts, file_name)
        or first_folder_problem(folder_parts, disk)
        or check_total_length(join_path(root, folder_parts), file_name, limits)
    )
    if code is not None:
        return PathFailure(code)
    if not is_contained(folder_parts, file_name):
        return PathFailure(FailureCode.F24)

    reservations.commit(candidate)
    content_type = None if response is None else response.content_type
    return TargetPath(
        full_path=join_path(root, (*folder_parts, file_name)),
        folder_parts=folder_parts,
        file_name=file_name,
        warnings=classify_warnings(file_name, content_type),
    )


def normalize_destination(destination: str) -> str:
    """D-11: separador ``\\`` y sin barra final, salvo en la raíz (``D:\\``)."""
    text = destination.replace("/", _SEPARATOR)
    trimmed = text.rstrip(_SEPARATOR)
    if len(trimmed) == _DRIVE_LENGTH and trimmed[1] == ":":
        return trimmed + _SEPARATOR  # raíz de unidad
    return trimmed or text


def join_path(root: str, parts: tuple[str, ...]) -> str:
    """Une la carpeta destino normalizada con los componentes (sin duplicar la barra de la raíz)."""
    if not parts:
        return root
    return root + ("" if root.endswith(_SEPARATOR) else _SEPARATOR) + _SEPARATOR.join(parts)


def is_contained(folder_parts: tuple[str, ...], file_name: str) -> bool:
    """Guarda de contención (RN-013 a, S-001-13 2 a 6): ningún componente puede salir del destino.

    Es defensa en profundidad: con el saneado correcto no se incumple nunca; si ocurriera, el
    elemento falla en lugar de escribir fuera de la carpeta destino.
    """
    return all(_is_safe_component(part) for part in (*folder_parts, file_name))


def _is_safe_component(part: str) -> bool:
    return (
        bool(part)
        and part not in {".", ".."}
        and not part.endswith((".", " "))
        and utf16_len(part) <= MAX_COMPONENT_LENGTH
        and not any(
            char in INVALID_CHARS or char in INVISIBLE_CHARS or ord(char) < _CONTROL_LIMIT
            for char in part
        )
        and windows_fold(part.partition(".")[0].rstrip(" ")) not in RESERVED_NAMES
    )
