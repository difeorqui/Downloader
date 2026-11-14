"""Carpetas relativas de una URL (RN-008, RN-009, RN-011 y RN-014/RN-015; D-05, D-08).

Ruta = carpeta destino / dominio / segmentos de carpeta / nombre de archivo. Este módulo calcula
las dos primeras partes a partir de la URL **original** (RN-008 a): nunca de la URL a la que se
llega por una redirección, y sin los parámetros ni el fragmento (RN-009).

A cada segmento y al dominio se le aplican, en este orden, RN-011 (decodificar una vez),
RN-014 (caracteres) y RN-015 (nombres reservados). Los segmentos vacíos y los ``.``/``..``, también
codificados (``%2e``), se **descartan sin resolverse** (RN-008 f): ``a/../b`` da las carpetas
``a`` y ``b``.
"""

from dataclasses import dataclass

from downloader.domain.paths.sanitize import sanitize_folder
from downloader.domain.urls.encoding import decode_segment
from downloader.domain.urls.model import ParsedUrl


@dataclass(frozen=True, slots=True)
class UrlPathParts:
    """Partes de la ruta de una URL listas para construir la ruta en disco.

    ``folders`` empieza por la carpeta del dominio y ya está saneada. ``last_segment`` es el
    último segmento decodificado (RN-011) pero **sin sanear** (el nombre del archivo lo sanea
    RN-010, que puede pasar al paso siguiente si queda vacío); es ``None`` si la URL no trae
    nombre: la ruta termina en ``/`` o el último segmento era vacío, ``.`` o ``..`` (RN-008 f).
    """

    folders: tuple[str, ...]
    last_segment: str | None


def url_path_parts(url: ParsedUrl) -> UrlPathParts:
    """Carpetas (con la del dominio) y último segmento de la ruta de la URL."""
    segments = url.path.split("/")[1:]  # el primero es el vacío anterior a la "/" inicial
    folder_segments, last = segments[:-1], (segments[-1] if segments else "")
    folders = [_domain_folder(url)]
    for segment in folder_segments:
        decoded = decode_segment(segment)
        if not _is_discardable(decoded):
            folders.append(sanitize_folder(decoded))
    decoded_last = decode_segment(last)
    last_segment = None if _is_discardable(decoded_last) else decoded_last
    return UrlPathParts(tuple(folders), last_segment)


def relative_folders(url: ParsedUrl) -> tuple[str, ...]:
    """Contrato §5: dominio (+``_puerto``) y segmentos de carpeta, ya saneados (RN-008)."""
    return url_path_parts(url).folders


def _domain_folder(url: ParsedUrl) -> str:
    """Dominio en minúsculas y forma ASCII; el puerto no estándar va unido con ``_`` (RN-008 b, c).

    Un literal IP queda como se escribió (D-08): ``[::1]`` y el puerto 8443 dan ``[__1]_8443``.
    El saneado se aplica al nombre completo de la carpeta, que es el que existe en disco.
    """
    name = url.host if url.port is None else f"{url.host}_{url.port}"
    return sanitize_folder(name)


def _is_discardable(decoded_segment: str) -> bool:
    """Vacío, ``.`` o ``..`` tras decodificar **una** vez: ``%252e`` no es un punto (D-05)."""
    return decoded_segment in {"", ".", ".."}
