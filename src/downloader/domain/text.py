"""Utilidades de texto del dominio (S-001-02, S-001-03, RN-002).

Funciones puras, sin dependencias.
"""

_BASIC_PLANE_MAX = 0xFFFF


def windows_fold(text: str) -> str:
    """Clave de comparación "sin distinguir mayúsculas" como la hace Windows (S-001-03).

    Aplica la mayúscula simple carácter a carácter y solo si el resultado es un único carácter
    del plano básico (NTFS no tiene tabla de mayúsculas fuera de él). No se usa ``casefold()``:
    convierte ``ß`` en ``ss``, que Windows no iguala. Los caracteres cuya mayúscula en Python es
    de varios caracteres (``ß``, ``ŉ``, ``ﬁ``...) se dejan como están.
    """
    return "".join(_fold_char(char) for char in text)


def _fold_char(char: str) -> str:
    if ord(char) > _BASIC_PLANE_MAX:
        return char
    upper = char.upper()
    if len(upper) != 1 or ord(upper) > _BASIC_PLANE_MAX:
        return char
    return upper


def utf16_len(text: str) -> int:
    """Longitud como la cuenta Windows: unidades UTF-16 (un emoji cuenta 2) (S-001-02).

    Un sustituto suelto cuenta 1 y no provoca error, a diferencia de ``encode("utf-16")``.
    """
    return sum(2 if ord(char) > _BASIC_PLANE_MAX else 1 for char in text)


def trim_blanks(text: str) -> str:
    """Recorta espacios y tabulaciones al inicio y al final (RN-002); otros blancos se conservan."""
    return text.strip(" \t")
