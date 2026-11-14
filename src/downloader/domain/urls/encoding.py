"""Codificación y decodificación en porcentaje (RN-001 paso 8, RN-011, D-04).

* Codificar (:func:`encode_url_part`): sobre texto de la ruta, los parámetros o el fragmento.
  Solo se codifican los caracteres que la regla lista y el ``%`` que no va seguido de dos
  cifras hexadecimales (``%25``, S-001-11); una secuencia ``%XX`` ya válida nunca se vuelve a
  codificar. El llamador compara el resultado con la entrada para saber si la URL quedó
  "corregida (codificada)".
* Decodificar (:func:`decode_segment`): **una sola vez**, desde UTF-8. ``%252e`` queda ``%2e``.
  Un byte que no forma UTF-8 válido conserva su ``%XX`` original (por secuencia, D-04).

Funciones puras y totales: aceptan cualquier ``str`` y no lanzan excepciones (PA-04).
"""

import re
from typing import Final

# RN-001 paso 8: espacio, comillas dobles, <, >, acento grave, {, }, | y ^. Se añade la barra
# invertida: en parámetros y fragmento se codifica ``%5C`` (CA-001-19) y en la ruta ya no queda
# ninguna (:func:`backslashes_to_slashes` va antes), así que codificarla aquí es siempre correcto.
_ENCODED_ASCII: Final = frozenset(' "<>`{}|^\\')

_C0_LIMIT: Final = 0x20
_DEL: Final = 0x7F
_ASCII_LIMIT: Final = 0x80
_SURROGATES: Final = range(0xD800, 0xE000)
_REPLACEMENT_ESCAPED: Final = "%EF%BF%BD"  # U+FFFD: un sustituto suelto no tiene forma UTF-8

_ESCAPE_RUN: Final = re.compile(r"(?:%[0-9A-Fa-f]{2})+")
_LONE_PERCENT: Final = re.compile(r"%(?![0-9A-Fa-f]{2})")
_ESCAPE_LENGTH: Final = 3  # "%" + dos cifras hexadecimales
_ESCAPED_BYTE_FIRST: Final = 0xDC80  # ``surrogateescape`` representa el byte b como U+DC00 + b
_ESCAPED_BYTE_LAST: Final = 0xDCFF


def backslashes_to_slashes(path: str) -> str:
    """RN-001 paso 7: cada ``\\`` literal de la ruta pasa a ``/`` antes de codificar."""
    return path.replace("\\", "/")


def encode_url_part(text: str) -> str:
    """RN-001 paso 8: codifica en porcentaje (UTF-8, hexadecimal en mayúsculas) lo necesario.

    Se codifican los caracteres no ASCII, los listados por la regla (espacio, comillas dobles,
    ``<``, ``>``, acento grave, ``{``, ``}``, ``|``, ``^`` y ``\\``) y, por defensa en
    profundidad, los de control U+0000-U+001F y U+007F: un CR o LF crudo nunca llega a la URL
    procesada. Un ``%`` sin dos cifras hexadecimales detrás pasa a ``%25`` (S-001-11).
    """
    return "".join(_encode_char(char) for char in _LONE_PERCENT.sub("%25", text))


def _encode_char(char: str) -> str:
    code = ord(char)
    if code < _C0_LIMIT or code == _DEL or char in _ENCODED_ASCII:
        return f"%{code:02X}"
    if code < _ASCII_LIMIT:
        return char
    if code in _SURROGATES:
        return _REPLACEMENT_ESCAPED
    return "".join(f"%{byte:02X}" for byte in char.encode("utf-8"))


def decode_segment(text: str) -> str:
    """RN-011: decodifica una sola vez las secuencias ``%XX`` que forman UTF-8 válido.

    Las que no lo forman se conservan con su ``%XX`` y su grafía original, byte a byte
    (``%C3`` suelto sigue siendo ``%C3``). Un ``%`` que no va seguido de dos cifras
    hexadecimales es un carácter normal. El resultado puede contener ``/``, ``\\``, ``.`` o
    controles (``%2f``, ``%5c``, ``%00``): el saneado de RN-014 los trata después.
    """
    return _ESCAPE_RUN.sub(lambda match: _decode_run(match.group()), text)


def _decode_run(run: str) -> str:
    spellings = [
        run[start : start + _ESCAPE_LENGTH] for start in range(0, len(run), _ESCAPE_LENGTH)
    ]
    data = bytes(int(spelling[1:], 16) for spelling in spellings)
    decoded = data.decode("utf-8", errors="surrogateescape")
    pieces: list[str] = []
    consumed = 0
    for char in decoded:
        if _ESCAPED_BYTE_FIRST <= ord(char) <= _ESCAPED_BYTE_LAST:
            pieces.append(spellings[consumed])
            consumed += 1
        else:
            pieces.append(char)
            consumed += len(char.encode("utf-8"))
    return "".join(pieces)
