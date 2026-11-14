"""Enmascarado de URLs en toda salida visible (RN-036, S-001-08, D-10).

Mientras ``ParsedUrl.processed()`` es la única salida con secretos (para conectar y exportar),
todo lo que se muestra pasa por aquí: sin credenciales (``***@``), con el valor de cada parámetro
como ``***`` y con el fragmento como ``***``. El riesgo residual documentado son los tokens
dentro de la **ruta**, que no se distinguen de un nombre de carpeta.

Este módulo trabaja solo con texto (no importa el modelo) para que ``ParsedUrl`` pueda usarlo en
su ``repr``. Funciones puras y totales (PA-04).
"""

import re
from typing import Final

VISIBLE_LIMIT: Final = 200  # S-001-08 (d): 199 caracteres + "…"
ELLIPSIS: Final = "…"
MASK: Final = "***"

_NEXT_URL: Final = re.compile(r"\s+(?=https?://)", re.IGNORECASE)
_QUERY_OR_FRAGMENT: Final = re.compile(r"[?#]")
_SCHEME_SEPARATOR: Final = "://"


def truncate_visible(text: str) -> str:
    """S-001-08 (d): toda salida visible mide como máximo 200 caracteres (199 + ``…``)."""
    if len(text) <= VISIBLE_LIMIT:
        return text
    return text[: VISIBLE_LIMIT - 1] + ELLIPSIS


def mask_query(query: str) -> str:
    """Valor de cada parámetro como ``***``; un parámetro sin ``=`` cuenta como valor.

    ``a=1&b`` → ``a=***&***``; ``a=b=c`` → ``a=***``; un parámetro vacío (``&&``) se conserva.
    """
    return "&".join(_mask_parameter(parameter) for parameter in query.split("&"))


def _mask_parameter(parameter: str) -> str:
    if not parameter:
        return parameter
    name, equals, _ = parameter.partition("=")
    return f"{name}={MASK}" if equals else MASK


def mask_fragment(fragment: str) -> str:
    """El fragmento se oculta; un fragmento vacío (``#`` sin nada detrás) se conserva."""
    return MASK if fragment else fragment


def mask_text(text: str, *, analyzable: bool = False) -> str:
    """Enmascara el texto de una URL **no analizable** (S-001-08 b); nunca lanza excepciones.

    Cada URL detectada (en I-09, separada por el espacio que precede a ``http``) se trata por
    separado: se oculta todo lo que va hasta el último ``@`` del tramo de autoridad cruda y, en
    lo que queda, todo lo que sigue al primer ``?`` o ``#``. Con ``analyzable=True`` (I-05 e
    I-07, donde la estructura es legible) los parámetros se muestran como en una URL válida.
    """
    pieces = _NEXT_URL.split(text)
    masked = " ".join(_mask_piece(piece, analyzable=analyzable) for piece in pieces)
    return truncate_visible(masked)


def _mask_piece(piece: str, *, analyzable: bool) -> str:
    piece = _mask_credentials(piece)
    if analyzable:
        return _mask_tail_by_parts(piece)
    return _mask_tail_flat(piece)


def _mask_credentials(piece: str) -> str:
    """Reemplaza por ``***@`` lo que va del inicio de la autoridad cruda al último ``@``.

    Amplía S-001-08 (b) con las barras iniciales sobrantes: solo oculta más, nunca menos.
    """
    separator = piece.find(_SCHEME_SEPARATOR)
    start = 0 if separator == -1 else separator + len(_SCHEME_SEPARATOR)
    # Barras iniciales sobrantes (``//u:p@h``, ``https:///u:p@h``): sin saltarlas la «primera /»
    # sería la inicial, el tramo quedaría vacío y las credenciales se mostrarían.
    while piece.startswith("/", start):
        start += 1
    end = piece.find("/", start)
    if end == -1:
        end = len(piece)
    at = piece.rfind("@", start, end)
    if at == -1:
        return piece
    return f"{piece[:start]}{MASK}@{piece[at + 1 :]}"


def _mask_tail_flat(piece: str) -> str:
    """Lo que sigue al primer ``?`` o ``#`` pasa a ``***`` (si hay algo detrás)."""
    found = _QUERY_OR_FRAGMENT.search(piece)
    if found is None or found.end() == len(piece):
        return piece
    return f"{piece[: found.end()]}{MASK}"


def _mask_tail_by_parts(piece: str) -> str:
    """Parámetros y fragmento enmascarados como en una URL válida."""
    head, hash_mark, fragment = piece.partition("#")
    head, question_mark, query = head.partition("?")
    masked = head
    if question_mark:
        masked += f"?{mask_query(query)}"
    if hash_mark:
        masked += f"#{mask_fragment(fragment)}"
    return masked
