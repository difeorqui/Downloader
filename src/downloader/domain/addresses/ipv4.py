"""Interpretación de IPv4 escrita con la semántica clásica (S-001-15, RN-017 a, AB-14).

De 1 a 4 partes separadas por puntos; cada parte en decimal, en octal (con 0 inicial) o en
hexadecimal (con ``0x``); la última parte ocupa los bytes que faltan. Así ``2130706433``,
``0177.0.0.1``, ``0x7f.1`` y ``127.1`` son todas 127.0.0.1.

Regla "termina en número" (WHATWG): si la última etiqueta del dominio parece un número, el
dominio entero debe ser una IPv4 válida; si no lo es, el llamador lo rechaza como I-03 (D-03).
Ambas funciones son puras y nunca lanzan excepciones por el texto recibido (PA-04).
"""

from ipaddress import IPv4Address
from typing import Final

_DECIMAL_DIGITS: Final = frozenset("0123456789")
_OCTAL_DIGITS: Final = frozenset("01234567")
_HEX_DIGITS: Final = frozenset("0123456789abcdefABCDEF")

_HEX_PREFIXES: Final = frozenset({"0x", "0X"})

_MAX_PARTS: Final = 4
_MAX_PART_VALUE: Final = 255
# Una parte con más cifras significativas que esto (11 en octal) ya desborda los 32 bits.
_MAX_SIGNIFICANT_DIGITS: Final = 11


def ends_in_number(host: str) -> bool:
    """``True`` si la última etiqueta es decimal pura o empieza por ``0x``/``0X``.

    ``host`` ya viene sin punto final (RN-001a): una etiqueta final vacía no es un número.
    Que empiece por ``0x`` basta aunque lo que sigue no sea hexadecimal (``0x1g``): se
    intenta como IPv4 y, al fallar, el llamador lo rechaza (D-03).
    """
    label = host.rpartition(".")[2]
    if not label:
        return False
    if all(char in _DECIMAL_DIGITS for char in label):
        return True
    return label[:2] in _HEX_PREFIXES


def parse_ipv4(host: str) -> IPv4Address | None:
    """Valor de una IPv4 escrita en cualquier notación clásica, o ``None`` si no lo es.

    ``None`` cubre tanto los nombres de dominio como los textos numéricos que no forman una
    IPv4 válida (desborde, más de 4 partes, parte vacía, cifra fuera de la base...). Para
    distinguirlos, el llamador usa antes :func:`ends_in_number`.
    """
    parts = host.split(".")
    if len(parts) > _MAX_PARTS:
        return None
    values: list[int] = []
    for part in parts:
        value = _parse_part(part)
        if value is None:
            return None
        values.append(value)
    *head, last = values
    if any(value > _MAX_PART_VALUE for value in head):
        return None
    if last >= 256 ** (_MAX_PARTS + 1 - len(values)):
        return None
    address = last
    for index, value in enumerate(head):
        address += value << (8 * (_MAX_PARTS - 1 - index))
    return IPv4Address(address)


def _parse_part(part: str) -> int | None:
    if part[:2] in _HEX_PREFIXES:
        digits, allowed, radix = part[2:], _HEX_DIGITS, 16
    elif part[:1] == "0" and len(part) > 1:
        digits, allowed, radix = part[1:], _OCTAL_DIGITS, 8
    else:
        digits, allowed, radix = part, _DECIMAL_DIGITS, 10
    if not part or not all(char in allowed for char in digits):
        return None
    significant = digits.lstrip("0")
    if not significant:
        return 0
    if len(significant) > _MAX_SIGNIFICANT_DIGITS:
        return None
    return int(significant, radix)
