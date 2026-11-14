"""Dominio y puerto de una URL (RN-001 pasos 6, 8 y 9; RN-001a; D-02, D-03, D-08).

Recibe la **autoridad** ya sin credenciales ni espacios (:mod:`downloader.domain.urls.parser`) y
devuelve el host listo para usar: sin punto final, en minúsculas, normalizado a NFC y, si tenía
caracteres no ASCII, en su forma ``xn--`` (``idna`` solo en ese caso, ADR 0003). Las funciones
son puras y totales (PA-04).
"""

import unicodedata
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address
from typing import Final, Literal

import idna

from downloader.domain.addresses.ipv4 import ends_in_number, parse_ipv4
from downloader.domain.catalog import InvalidReason
from downloader.domain.result import Err, Ok, Result
from downloader.domain.urls.model import HostKind

MAX_HOST_LENGTH: Final = 253
MAX_PORT: Final = 65535
_MAX_PORT_DIGITS: Final = 5
_HTTP_PORT: Final = 80
_HTTPS_PORT: Final = 443

# D-03: caracteres prohibidos de WHATWG en un dominio (fuera del literal IPv6), más los de control.
_FORBIDDEN_HOST_CHARS: Final = frozenset(" #%/:<>?@[\\]^|")
_CONTROL_LIMIT: Final = 0x20
_DEL: Final = 0x7F
_IPV6_CHARS: Final = frozenset("0123456789abcdefABCDEF:.")
_ASCII_DIGITS: Final = frozenset("0123456789")


@dataclass(frozen=True, slots=True)
class Authority:
    """Autoridad interpretada. ``port_text`` va tal cual (``""`` si no hay): lo valida otro."""

    host: str
    kind: HostKind
    ip: IPv4Address | IPv6Address | None
    port_text: str
    converted_to_ascii: bool  # el dominio tenía caracteres no ASCII (cuenta como "codificada")


def parse_authority(authority: str) -> Result[Authority, InvalidReason]:
    """Extrae y valida el dominio (D-03); el puerto se valida aparte con :func:`resolve_port`."""
    if authority.startswith("["):
        return _parse_ipv6_authority(authority)
    host_text, _, port_text = authority.partition(":")
    return _parse_name_or_ipv4(host_text, port_text)


def resolve_port(
    port_text: str, scheme: Literal["http", "https"]
) -> Result[int | None, InvalidReason]:
    """D-02: ``""`` y el puerto estándar del esquema dan ``None``; lo demás inválido es I-07.

    Es ``I-07`` tanto un número fuera de 1-65535 como un texto que no son solo dígitos ASCII
    (``user:pass?@evil.com``, ejemplo 18c de S-001-08).
    """
    if not port_text:
        return Ok(None)
    if not _is_port_text(port_text):
        return Err(InvalidReason.I07)
    digits = port_text.lstrip("0")  # evita convertir cadenas enormes de ceros o dígitos
    if not digits or len(digits) > _MAX_PORT_DIGITS or int(digits) > MAX_PORT:
        return Err(InvalidReason.I07)
    port = int(digits)
    return Ok(None if port == _standard_port(scheme) else port)


def _standard_port(scheme: Literal["http", "https"]) -> int:
    return _HTTP_PORT if scheme == "http" else _HTTPS_PORT


def _is_port_text(port_text: str) -> bool:
    return all(char in _ASCII_DIGITS for char in port_text)


def _parse_ipv6_authority(authority: str) -> Result[Authority, InvalidReason]:
    close = authority.find("]")
    if close == -1:
        return Err(InvalidReason.I03)
    literal, after = authority[1:close], authority[close + 1 :]
    port_text = ""
    if after:
        if not after.startswith(":"):
            return Err(InvalidReason.I03)
        port_text = after[1:]
    ip = _parse_ipv6(literal)
    if ip is None:
        return Err(InvalidReason.I03)
    return Ok(Authority(f"[{literal.lower()}]", HostKind.IPV6, ip, port_text, False))


def _parse_ipv6(literal: str) -> IPv6Address | None:
    """IPv6 sin zona (``%`` → inválida, D-03) ni caracteres ajenos al literal."""
    if not literal or any(char not in _IPV6_CHARS for char in literal):
        return None
    try:
        return IPv6Address(literal)
    except ValueError:
        return None


def _parse_name_or_ipv4(host_text: str, port_text: str) -> Result[Authority, InvalidReason]:
    host = unicodedata.normalize("NFC", host_text.removesuffix(".").lower())
    if not _has_valid_shape(host):
        return Err(InvalidReason.I03)
    converted = not host.isascii()
    if converted:
        converted_host = _to_ascii(host)
        if converted_host is None or not _has_valid_shape(converted_host):
            return Err(InvalidReason.I03)
        host = converted_host
    if len(host) > MAX_HOST_LENGTH:
        return Err(InvalidReason.I03)
    if ends_in_number(host):
        ip = parse_ipv4(host)
        if ip is None:
            return Err(InvalidReason.I03)
        return Ok(Authority(host, HostKind.IPV4, ip, port_text, converted))
    return Ok(Authority(host, HostKind.NAME, None, port_text, converted))


def _has_valid_shape(host: str) -> bool:
    """D-03: no vacío, sin etiquetas vacías y sin caracteres prohibidos ni de control."""
    if not host or any(not label for label in host.split(".")):
        return False
    return not any(
        char in _FORBIDDEN_HOST_CHARS or ord(char) < _CONTROL_LIMIT or ord(char) == _DEL
        for char in host
    )


def _to_ascii(host: str) -> str | None:
    """Forma ASCII (``xn--``) con IDNA 2008 estricto; ``None`` si el nombre no es válido."""
    try:
        return idna.encode(host).decode("ascii")
    except UnicodeError:  # ``idna.IDNAError`` hereda de ``UnicodeError``
        return None
