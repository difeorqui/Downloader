"""Clave de duplicado de una URL (RN-006).

Dos URLs del mismo lote son la misma si coinciden **después** de corregirlas y codificarlas, sin
fragmento, con esquema y dominio en minúsculas y sin el puerto estándar. Los parámetros cuentan
(``a.pdf?v=1`` y ``a.pdf?v=2`` son distintas) y la ruta distingue mayúsculas: ``A.pdf`` y
``a.pdf`` son dos elementos (S-001-03, CA-001-39).

Todo eso ya lo deja resuelto el analizador en ``ParsedUrl`` (esquema y dominio en minúsculas,
dominio en forma ASCII, puerto ``None`` si es el estándar), así que la clave solo omite el
fragmento.
"""

from downloader.domain.urls.model import ParsedUrl


def dedup_key(url: ParsedUrl) -> str:
    """Clave estable de comparación de duplicados; no se muestra (puede contener parámetros)."""
    port = "" if url.port is None else f":{url.port}"
    query = "" if url.query is None else f"?{url.query}"
    return f"{url.scheme}://{url.host}{port}{url.path}{query}"
