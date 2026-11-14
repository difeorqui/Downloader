"""Nombre del archivo (RN-010, D-06).

Prioridad, y en cada paso, si tras sanear el nombre queda vacío se pasa al siguiente:

1. El nombre que sugiere el servidor: ``filename*`` (forma internacional) y, si no, ``filename``.
   Se toma lo que va después de la última ``/`` o ``\\`` y se sanea con RN-014 y RN-015. Ya viene
   decodificado: **no** se vuelve a decodificar con RN-011.
2. El último segmento de la ruta de la URL original (decodificado una vez, RN-011, y saneado). Si
   no tiene extensión y el tipo de contenido está en la tabla, se le añade (``x`` → ``x.pdf``).
3. Si la URL no trae nombre: ``index`` más la extensión de la tabla.
4. Si el tipo no está en la tabla o no se informa: ``index``.

El resultado nunca está vacío. El sufijo por colisión y los límites de longitud son de otros
módulos.
"""

from typing import Final

from downloader.domain.paths.content_types import extension_for_content_type
from downloader.domain.paths.relative import url_path_parts
from downloader.domain.paths.response import ServerResponse
from downloader.domain.paths.sanitize import sanitize_name
from downloader.domain.urls.model import ParsedUrl

DEFAULT_NAME: Final = "index"


def has_extension(name: str) -> bool:
    """D-06: hay un ``.`` que no es el primer carácter y le sigue al menos un carácter."""
    head, dot, tail = name.rpartition(".")
    return bool(dot and head and tail)


def choose_file_name(url: ParsedUrl, response: ServerResponse | None = None) -> str:
    """Nombre del archivo según RN-010; ``response`` es ``None`` antes de conectar."""
    suggested = _server_name(response)
    if suggested:
        return suggested

    content_type = None if response is None else response.content_type
    extension = extension_for_content_type(content_type)

    last_segment = url_path_parts(url).last_segment
    from_url = "" if last_segment is None else sanitize_name(last_segment)
    if from_url:
        if extension is not None and not has_extension(from_url):
            return f"{from_url}{extension}"
        return from_url

    return f"{DEFAULT_NAME}{extension or ''}"


def _server_name(response: ServerResponse | None) -> str:
    """RN-010 (1): ``filename*`` prevalece sobre ``filename``; cada uno se sanea por separado.

    Si el internacional queda vacío al sanear se prueba con el simple antes de pasar al paso 2.
    """
    if response is None:
        return ""
    for candidate in (response.filename_ext, response.filename):
        if candidate is None:
            continue
        name = sanitize_name(_after_last_separator(candidate))
        if name:
            return name
    return ""


def _after_last_separator(name: str) -> str:
    return name.replace("\\", "/").rpartition("/")[2]
