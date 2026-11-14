"""Saneado de nombres de carpeta, de archivo y de dominio (RN-014 y RN-015; glosario 2.4 y 2.5).

Orden normativo (RN-008 g): RN-014 a, b, c y después RN-015. El paso RN-014 d (nombre vacío)
lo decide quien llama: en una carpeta, ``_`` (:func:`sanitize_folder`); en un nombre de archivo,
pasar al siguiente paso de RN-010 (:func:`sanitize_name` devuelve ``""``).

Las funciones son puras y totales: aceptan cualquier ``str``, incluidos sustitutos sueltos, y
nunca lanzan excepciones (PA-04). Las invariantes de salida son las de S-001-13 (3), (4) y (5).
"""

from typing import Final

from downloader.domain.text import windows_fold

_INVISIBLE_RANGES: Final = (
    (0x00AD, 0x00AD),  # guion suave
    (0x061C, 0x061C),  # marca de letra árabe
    (0x200B, 0x200F),  # espacios de ancho cero y marcas de dirección
    (0x202A, 0x202E),  # incrustaciones e inversiones de dirección
    (0x2060, 0x2064),  # unión de palabras y operadores invisibles
    (0x2066, 0x2069),  # aislamientos de dirección
    (0xFEFF, 0xFEFF),  # marca de orden de bytes
)
INVISIBLE_CHARS: Final = frozenset(
    chr(code) for low, high in _INVISIBLE_RANGES for code in range(low, high + 1)
)

_CONTROL_LIMIT: Final = 0x20  # U+0000..U+001F
INVALID_CHARS: Final = frozenset('<>:"/\\|?*')

# Glosario 2.5, ya en mayúsculas: la comparación usa ``windows_fold`` (S-001-03).
RESERVED_NAMES: Final = frozenset(
    (
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{suffix}" for suffix in "0123456789¹²³"),
        *(f"LPT{suffix}" for suffix in "0123456789¹²³"),
        "CONIN$",
        "CONOUT$",
        "CLOCK$",
    )
)

_TRAILING: Final = ". "
_SUBSTITUTE: Final = "_"


def remove_invisible(text: str) -> str:
    """RN-014 a: quita los caracteres invisibles y de control de dirección (glosario 2.4)."""
    return "".join(char for char in text if char not in INVISIBLE_CHARS)


def replace_invalid(text: str) -> str:
    """RN-014 b: cada carácter no válido en Windows y cada U+0000-U+001F pasa a ``_``."""
    return "".join(
        _SUBSTITUTE if char in INVALID_CHARS or ord(char) < _CONTROL_LIMIT else char
        for char in text
    )


def strip_trailing(text: str) -> str:
    """RN-014 c: quita los puntos y espacios del final (``a. .`` → ``a``)."""
    return text.rstrip(_TRAILING)


def protect_reserved(name: str) -> str:
    """RN-015: inserta ``_`` tras un nombre reservado de Windows.

    Se evalúa el texto anterior al primer punto, sin los espacios finales de ese tramo, sin
    distinguir mayúsculas. ``con.tar.gz`` → ``con_.tar.gz``; ``con .txt`` → ``con_ .txt``;
    ``CONIN$`` → ``CONIN$_``. ``CONSOLA.txt``, ``COM10.txt`` y ``.htaccess`` no cambian.
    """
    head, dot, tail = name.partition(".")
    core = head.rstrip(" ")
    if windows_fold(core) not in RESERVED_NAMES:
        return name
    return f"{core}{_SUBSTITUTE}{head[len(core) :]}{dot}{tail}"


def sanitize_name(text: str) -> str:
    """RN-014 a-c y RN-015 sobre un nombre ya decodificado; ``""`` si no queda nada (RN-014 d).

    Sirve para nombres de archivo (el llamador pasa al siguiente paso de RN-010 si es ``""``) y
    como base de :func:`sanitize_folder`.
    """
    return protect_reserved(strip_trailing(replace_invalid(remove_invisible(text))))


def sanitize_folder(text: str) -> str:
    """Saneado de una carpeta o del dominio: como :func:`sanitize_name`, y ``_`` si queda vacío."""
    return sanitize_name(text) or _SUBSTITUTE
