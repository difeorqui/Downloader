"""Clasificación de direcciones y nombres de host (RN-017 a, glosario 2.1 y 2.2).

Es léxica: nunca resuelve nombres ni usa la red. La spec 002 reutiliza :func:`classify_ip`
con las direcciones realmente resueltas. Las funciones son puras y no lanzan excepciones por
el texto recibido (PA-04).

Precedencia: una dirección bloqueada prevalece sobre la interna, salvo ``::1``, que tiene
entrada propia como interna aunque caiga dentro de ``::/96``.
"""

from enum import Enum
from ipaddress import IPv4Address, IPv6Address

from downloader.domain.addresses.ipv4 import parse_ipv4
from downloader.domain.addresses.lists import (
    BLOCKED_IPV4_NETWORKS,
    BLOCKED_IPV6_NETWORKS,
    EMBEDDED_IPV4_NETWORKS,
    INTERNAL_EXACT_NAMES,
    INTERNAL_IPV4_NETWORKS,
    INTERNAL_IPV6_NETWORKS,
    INTERNAL_NAME_SUFFIXES,
    IPV6_LOOPBACK,
)

_IPV4_MASK = 0xFFFFFFFF


class AddressClass(Enum):
    """``INTERNAL`` pide confirmación (RN-017); ``BLOCKED`` nunca se permite (RN-004 I-06)."""

    PUBLIC = "publica"
    INTERNAL = "interna"
    BLOCKED = "bloqueada"


def classify_ip(ip: IPv4Address | IPv6Address) -> AddressClass:
    """Clase de una dirección IP ya interpretada, en cualquier notación de origen."""
    if isinstance(ip, IPv6Address):
        return _classify_ipv6(ip)
    return _classify_ipv4(ip)


def classify_host(host: str, ip: IPv4Address | IPv6Address | None = None) -> AddressClass:
    """Clase de un host: por su IP si es un literal IP y, si no, por las reglas de nombre.

    ``ip`` es el valor interpretado del literal (IPv4 en cualquier notación o IPv6 entre
    corchetes). Si el llamador no lo da pero el host se lee como IPv4 en notación clásica
    (``0x7f.1``), se usa igualmente: así una notación alternativa no esquiva la comprobación.
    """
    if ip is not None:
        return classify_ip(ip)
    name = host.lower().removesuffix(".")
    written_ip = parse_ipv4(name)
    if written_ip is not None:
        return _classify_ipv4(written_ip)
    return _classify_name(name)


def _classify_ipv4(ip: IPv4Address) -> AddressClass:
    if any(ip in network for network in BLOCKED_IPV4_NETWORKS):
        return AddressClass.BLOCKED
    if any(ip in network for network in INTERNAL_IPV4_NETWORKS):
        return AddressClass.INTERNAL
    return AddressClass.PUBLIC


def _classify_ipv6(ip: IPv6Address) -> AddressClass:
    if any(ip in network for network in EMBEDDED_IPV4_NETWORKS):
        return _classify_ipv4(IPv4Address(int(ip) & _IPV4_MASK))
    if ip == IPV6_LOOPBACK:
        return AddressClass.INTERNAL
    if any(ip in network for network in BLOCKED_IPV6_NETWORKS):
        return AddressClass.BLOCKED
    if any(ip in network for network in INTERNAL_IPV6_NETWORKS):
        return AddressClass.INTERNAL
    return AddressClass.PUBLIC


def _classify_name(name: str) -> AddressClass:
    if name in INTERNAL_EXACT_NAMES or "." not in name:
        return AddressClass.INTERNAL
    if name.endswith(INTERNAL_NAME_SUFFIXES):
        return AddressClass.INTERNAL
    return AddressClass.PUBLIC
