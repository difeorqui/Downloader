"""Longitud de nombres y rutas (RN-016, S-001-02; D-07).

* (a) Ningún nombre de carpeta ni de archivo, ya saneado y con su sufijo de colisión, supera 255
  caracteres: si pasa, F-28 y los nombres **no se acortan** (nunca se pierde un archivo en
  silencio, RN-016 c).
* (b) Se mide la **mayor** de dos rutas: la final (carpeta + ``\\`` + nombre) y la del temporal
  (carpeta + ``\\`` + ``~descargador-<32>.parcial``, 53 caracteres). Límite: 32 000 con rutas
  largas habilitadas en Windows y 259 sin ellas. Si se supera, F-25.

Las longitudes se cuentan como las cuenta Windows: unidades UTF-16, un emoji cuenta 2.
Orden de fallos: F-28 antes que F-25 (S-001-07).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from downloader.domain.catalog import FailureCode
from downloader.domain.text import utf16_len

MAX_COMPONENT_LENGTH: Final = 255
TEMP_NAME_LENGTH: Final = 53  # "~descargador-" (13) + 32 + ".parcial" (8)
MAX_PATH_WITH_LONG_PATHS: Final = 32_000
MAX_PATH_WITHOUT_LONG_PATHS: Final = 259
_SEPARATOR_LENGTH: Final = 1


@dataclass(frozen=True, slots=True)
class PathLimits:
    """Capacidades del equipo que cambian el límite de la ruta completa."""

    long_paths_enabled: bool

    @property
    def max_path_length(self) -> int:
        return MAX_PATH_WITH_LONG_PATHS if self.long_paths_enabled else MAX_PATH_WITHOUT_LONG_PATHS


def check_component_lengths(folder_parts: Sequence[str], file_name: str) -> FailureCode | None:
    """``F-28`` si algún nombre de carpeta o de archivo supera 255 (RN-016 a)."""
    if any(utf16_len(part) > MAX_COMPONENT_LENGTH for part in (*folder_parts, file_name)):
        return FailureCode.F28
    return None


def check_total_length(folder_path: str, file_name: str, limits: PathLimits) -> FailureCode | None:
    """``F-25`` si la mayor de las rutas final y temporal supera el límite (RN-016 b)."""
    longest_name = max(utf16_len(file_name), TEMP_NAME_LENGTH)
    if utf16_len(folder_path) + _SEPARATOR_LENGTH + longest_name > limits.max_path_length:
        return FailureCode.F25
    return None


def check_path_lengths(
    folder_path: str,
    folder_parts: Sequence[str],
    file_name: str,
    limits: PathLimits,
) -> FailureCode | None:
    """``F-28`` si algún componente supera 255, ``F-25`` si la ruta mayor supera el límite.

    ``folder_path`` es la carpeta que contiene el archivo (destino + carpetas) y ``folder_parts``
    los componentes añadidos a la carpeta destino, todos ya saneados y con su sufijo. Es la
    composición de :func:`check_component_lengths` y :func:`check_total_length`; el orquestador
    las llama por separado porque entre ambas va la comprobación de carpetas (S-001-07).
    """
    return check_component_lengths(folder_parts, file_name) or check_total_length(
        folder_path, file_name, limits
    )
