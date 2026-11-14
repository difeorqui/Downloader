"""Tabla cerrada de tipos de contenido y extensiones (RN-010, S-001-06; PA-06).

El tipo se compara sin sus parámetros (``; charset=utf-8``) y sin distinguir mayúsculas.
Cualquier tipo que no esté en la tabla se trata como "no está en la tabla" (``None``).
"""

from typing import Final

# Tipo informado por el servidor -> extensión. Son 16 tipos en 15 filas de la tabla de RN-010
# (``application/xml`` y ``text/xml`` comparten fila). Tupla de pares: dato inmutable.
CONTENT_TYPE_EXTENSIONS: Final = (
    ("text/html", ".html"),
    ("text/plain", ".txt"),
    ("text/csv", ".csv"),
    ("application/json", ".json"),
    ("application/xml", ".xml"),
    ("text/xml", ".xml"),
    ("application/pdf", ".pdf"),
    ("image/jpeg", ".jpg"),
    ("image/png", ".png"),
    ("image/gif", ".gif"),
    ("image/webp", ".webp"),
    ("application/zip", ".zip"),
    (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
    ("video/mp4", ".mp4"),
)

HTML_MEDIA_TYPE: Final = "text/html"


def normalize_media_type(content_type: str | None) -> str | None:
    """Tipo sin parámetros, sin espacios y en minúsculas; ``None`` si no hay o no es ASCII.

    Los tipos de medios son fichas ASCII: un texto con otros caracteres no puede coincidir con
    la tabla (así ``K`` KELVIN SIGN, que en minúsculas sería una ``k`` ASCII, no se cuela).
    """
    if content_type is None or not content_type.isascii():
        return None
    return content_type.partition(";")[0].strip().lower()


def extension_for_content_type(content_type: str | None) -> str | None:
    """Extensión con punto de la tabla para ese tipo (``.pdf``), o ``None`` si no está."""
    media_type = normalize_media_type(content_type)
    if media_type is None:
        return None
    for known, extension in CONTENT_TYPE_EXTENSIONS:
        if known == media_type:
            return extension
    return None


def is_html(content_type: str | None) -> bool:
    """``True`` si el tipo informado es ``text/html`` (con o sin parámetros)."""
    return normalize_media_type(content_type) == HTML_MEDIA_TYPE
