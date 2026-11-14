"""Datos de la respuesta del servidor que influyen en el nombre y los avisos (contrato §5).

El dominio no hace red: la spec 002 rellena este objeto con la respuesta real y ya decodificada.
"""

from dataclasses import dataclass

from downloader.domain.urls.model import ParsedUrl


@dataclass(frozen=True, slots=True)
class ServerResponse:
    """Respuesta exitosa del servidor, tal como la entrega la capa de infraestructura."""

    filename: str | None = None  # forma simple, ya decodificada
    filename_ext: str | None = None  # forma internacional (``filename*``), ya decodificada
    content_type: str | None = None  # valor crudo de la cabecera
    final_url: ParsedUrl | None = None  # solo informativo: las carpetas salen de la original
