"""Clasificación léxica de direcciones (RN-017 a; CA-001-92 a 95; glosario 2.1 y 2.2).

Los rangos se escriben aquí a mano, sin leerlos de ``lists.py``, para que un error en la tabla
del dominio no se confirme a sí mismo.
"""

from __future__ import annotations

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

import pytest

from downloader.domain.addresses import AddressClass, classify_host, classify_ip

PUBLIC = AddressClass.PUBLIC
INTERNAL = AddressClass.INTERNAL
BLOCKED = AddressClass.BLOCKED

# --- CA-001-92 y 93: primera, intermedia y última dirección de cada rango -----------------------

INTERNAL_RANGES = [
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "100.64.0.0/10",
    "fc00::/7",
]
BLOCKED_RANGES = [
    "0.0.0.0/8",
    "169.254.0.0/16",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "224.0.0.0/4",
    "240.0.0.0/4",
    "::/96",
    "fe80::/10",
    "ff00::/8",
    "2001:db8::/32",
    "2001::/32",
    "2002::/16",
    "64:ff9b:1::/48",
]


def _three_points(cidr: str) -> list[IPv4Address | IPv6Address]:
    network = IPv4Network(cidr) if ":" not in cidr else IPv6Network(cidr)
    first = network.network_address
    last = network.broadcast_address
    middle = first + network.num_addresses // 2
    return [first, middle, last]


@pytest.mark.parametrize("cidr", INTERNAL_RANGES)
def test_each_internal_range_first_middle_last(cidr: str) -> None:
    for ip in _three_points(cidr):
        if ip == IPv6Address("fd00:ec2::254"):  # prevalece la bloqueada (CA-001-94)
            continue
        assert classify_ip(ip) is INTERNAL, ip


@pytest.mark.parametrize("cidr", BLOCKED_RANGES)
def test_each_blocked_range_first_middle_last(cidr: str) -> None:
    for ip in _three_points(cidr):
        if ip == IPv6Address("::1"):  # excepción propia: interna (glosario 2.2)
            continue
        assert classify_ip(ip) is BLOCKED, ip


@pytest.mark.parametrize(
    "text",
    [
        "255.255.255.255",  # entrada propia aunque caiga en 240.0.0.0/4
        "::",
        "fd00:ec2::254",  # CA-001-94: la bloqueada prevalece sobre fc00::/7
        "169.254.169.254",
    ],
)
def test_explicit_blocked_entries(text: str) -> None:
    ip = IPv6Address(text) if ":" in text else IPv4Address(text)
    assert classify_ip(ip) is BLOCKED


def test_blocked_prevails_over_internal_inside_fc00() -> None:
    assert classify_ip(IPv6Address("fd00:ec2::253")) is INTERNAL
    assert classify_ip(IPv6Address("fd00:ec2::254")) is BLOCKED
    assert classify_ip(IPv6Address("fd00:ec2::255")) is INTERNAL


def test_ipv6_loopback_is_internal_not_blocked() -> None:
    assert classify_ip(IPv6Address("::1")) is INTERNAL
    assert classify_ip(IPv6Address("::2")) is BLOCKED  # el resto de ::/96 sí es bloqueado


# --- Vecinos inmediatos: fuera del rango por un byte -------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "9.255.255.255",
        "11.0.0.0",
        "126.255.255.255",
        "128.0.0.0",
        "172.15.255.255",
        "172.32.0.0",
        "192.167.255.255",
        "192.169.0.0",
        "100.63.255.255",
        "100.128.0.0",
        "1.0.0.0",
        "169.253.255.255",
        "169.255.0.0",
        "191.255.255.255",
        "192.0.1.0",
        "192.0.3.0",
        "198.17.255.255",
        "198.20.0.0",
        "198.51.99.255",
        "198.51.101.0",
        "203.0.112.255",
        "203.0.114.0",
        "223.255.255.255",
        "8.8.8.8",
        "1.1.1.1",
        "010.0.0.1",  # octal: 8.0.0.1, pública
    ],
)
def test_ipv4_just_outside_every_range_is_public(text: str) -> None:
    assert classify_host(text) is PUBLIC


@pytest.mark.parametrize(
    "text",
    [
        "fbff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        "fe00::",
        "fe7f:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        "fec0::",
        "feff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        "2001:db7:ffff:ffff:ffff:ffff:ffff:ffff",
        "2001:db9::",
        "2000:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        "2001:1::",
        "2001:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        "2003::",
        "64:ff9b:0:ffff:ffff:ffff:ffff:ffff",
        "64:ff9b:2::",
        "::1:0:0",
        "2606:4700::1111",
        "2001:4860:4860::8888",
    ],
)
def test_ipv6_just_outside_every_range_is_public(text: str) -> None:
    assert classify_ip(IPv6Address(text)) is PUBLIC


def test_ipv4_adjacent_ranges_keep_their_own_class() -> None:
    assert classify_ip(IPv4Address("239.255.255.255")) is BLOCKED  # 224.0.0.0/4
    assert classify_ip(IPv4Address("240.0.0.0")) is BLOCKED  # 240.0.0.0/4, contigua a la anterior


# --- IPv6 con IPv4 incrustada (glosario 2.1) ----------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("::ffff:127.0.0.1", INTERNAL),
        ("::ffff:10.0.0.1", INTERNAL),
        ("::ffff:8.8.8.8", PUBLIC),
        ("::ffff:169.254.169.254", BLOCKED),
        ("::ffff:0:0", BLOCKED),  # incrusta 0.0.0.0
        ("::ffff:ffff:ffff", BLOCKED),  # incrusta 255.255.255.255
        ("64:ff9b::7f00:1", INTERNAL),  # 127.0.0.1
        ("64:ff9b::808:808", PUBLIC),  # 8.8.8.8
        ("64:ff9b::a9fe:a9fe", BLOCKED),  # 169.254.169.254
        ("64:ff9b::c0a8:1", INTERNAL),  # 192.168.0.1
    ],
)
def test_embedded_ipv4_is_judged_by_the_ipv4(text: str, expected: AddressClass) -> None:
    assert classify_ip(IPv6Address(text)) is expected


def test_6to4_with_loopback_inside_is_blocked() -> None:
    """AB-14: ``[2002:7f00:1::]`` es 6to4 y está bloqueada por su prefijo."""
    assert classify_ip(IPv6Address("2002:7f00:1::")) is BLOCKED


# --- Nombres (comprobación léxica) ---------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "localhost",
        "LOCALHOST",
        "localhost.",  # el punto final se ignora (RN-001a)
        "app.localhost",
        "a.b.localhost",
        "intranet",
        "servidor01",
        "x",
        "impresora.local",
        "wiki.internal",
        "wiki.intranet",
        "nas.lan",
        "erp.corp",
        "router.home.arpa",
        "Servidor.LOCAL.",
    ],
)
def test_internal_names(name: str) -> None:
    assert classify_host(name) is INTERNAL


@pytest.mark.parametrize(
    "name",
    [
        "example.com",
        "sitio.com.co",
        "localhost.com",  # solo cuenta como sufijo ".localhost" o el nombre exacto
        "notlocalhost.com",
        "mylocal.com",
        "a.local.com",
        "foo.localhost.evil.com",
        "xn--ao-zja.example",
        "home.arpa",  # el sufijo normativo es ".home.arpa": el apex literal no lo cumple
        "internal.example.org",
    ],
)
def test_public_names(name: str) -> None:
    assert classify_host(name) is PUBLIC


# --- AB-14: la notación alternativa no esquiva la comprobación ----------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2130706433", INTERNAL),
        ("0x7f.1", INTERNAL),
        ("127.1", INTERNAL),
        ("0177.0.0.1", INTERNAL),
        ("0xa9fea9fe", BLOCKED),
        ("0251.0376.0251.0376", BLOCKED),
        ("4294967295", BLOCKED),
        ("010.0.0.1", PUBLIC),
        ("0", BLOCKED),
    ],
)
def test_alternative_notation_without_parsed_ip(text: str, expected: AddressClass) -> None:
    assert classify_host(text) is expected


def test_given_ip_takes_precedence_over_the_name() -> None:
    assert classify_host("ejemplo.com", IPv4Address("127.0.0.1")) is INTERNAL
    assert classify_host("localhost", IPv4Address("8.8.8.8")) is PUBLIC
    assert classify_host("[::1]", IPv6Address("::1")) is INTERNAL


def test_classification_is_deterministic() -> None:
    results = {classify_host("localhost") for _ in range(100)}
    assert results == {INTERNAL}
