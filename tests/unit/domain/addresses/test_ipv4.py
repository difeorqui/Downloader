"""IPv4 escrita con semantica clasica (S-001-15, RN-017 a, AB-14, CA-001-95 y 96)."""

from __future__ import annotations

from ipaddress import IPv4Address

import pytest

from downloader.domain.addresses.ipv4 import ends_in_number, parse_ipv4

# Dato de prueba (resultado esperado), no un enlace de socket: el S104 de ruff es un falso positivo.
ZERO_ADDRESS = "0.0.0.0"  # noqa: S104 - dato de prueba, no un enlace de socket

# --- notaciones validas (CA-001-95) -------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2130706433", "127.0.0.1"),  # decimal entera
        ("0177.0.0.1", "127.0.0.1"),  # octal
        ("0x7f.1", "127.0.0.1"),  # hexadecimal + abreviada
        ("127.1", "127.0.0.1"),  # abreviada
        ("010.0.0.1", "8.0.0.1"),  # octal: es 8, no 10
        ("4294967295", "255.255.255.255"),
        ("0", ZERO_ADDRESS),
        ("0x0", ZERO_ADDRESS),
        ("0x", ZERO_ADDRESS),  # igual que los navegadores: prefijo sin digitos vale 0
        ("0x7f000001", "127.0.0.1"),
        ("0X7F.0.0.1", "127.0.0.1"),
        ("0x7F.0X00.0x0.0x1", "127.0.0.1"),
        ("127.0.1", "127.0.0.1"),
        ("127.0.0.1", "127.0.0.1"),
        ("1.2.3.4", "1.2.3.4"),
        ("255.255.255.255", "255.255.255.255"),
        (ZERO_ADDRESS, ZERO_ADDRESS),
        ("169.254.169.254", "169.254.169.254"),
        ("0251.0376.0251.0376", "169.254.169.254"),  # octal de 169.254.169.254
        ("0xa9fea9fe", "169.254.169.254"),
        ("2852039166", "169.254.169.254"),
        ("017700000001", "127.0.0.1"),  # octal de 32 bits en una sola parte
        ("1.2.65535", "1.2.255.255"),  # la ultima ocupa los 2 bytes que faltan
        ("1.16777215", "1.255.255.255"),  # la ultima ocupa los 3 bytes que faltan
        ("0000000000000000000000000000000000000000000000127.1", "87.0.0.1"),  # octal 0127 = 87
        ("0.0.0.00000000000000000000000000000000000000000000000000000000000001", "0.0.0.1"),
    ],
)
def test_valid_notations(text: str, expected: str) -> None:
    assert parse_ipv4(text) == IPv4Address(expected)


# --- invalidas: el ultimo segmento es numerico pero el conjunto no es IPv4 (CA-001-96) ----------


@pytest.mark.parametrize(
    "text",
    [
        "4294967296",  # desborde de 32 bits
        "0x100000000",
        "1.2.3.256",
        "1.2.3.999",
        "1.2.3.4.5",  # mas de 4 partes
        "0x1g",  # no es hexadecimal
        "0x1G",
        "08",  # octal con un 8
        "09.1",
        "1.2.65536",  # la ultima de 3 partes admite 16 bits
        "1.16777216",  # la ultima de 2 partes admite 24 bits
        "256.1",  # una parte que no es la ultima, fuera de 0..255
        "1.256.1",
        "0x100.1",
        "1..2",  # parte vacia
        "1.2.3.",
        ".1",
        "-1",
        "+1",
        " 1",
        "1 ",
        "1_0",
        "٣",  # digito arabe-indico: no es ASCII
        "1.٣",
        "9" * 5000,  # no debe fallar por el limite de digitos de int()
        "0x" + "f" * 5000,
        "1." * 100 + "1",
        "",
        ".",
    ],
)
def test_invalid_numeric_hosts_return_none(text: str) -> None:
    assert parse_ipv4(text) is None


@pytest.mark.parametrize("text", ["sitio.com", "a.b.c.d", "localhost", "1.2.3.a", "0b11", "1e3"])
def test_names_are_not_ipv4(text: str) -> None:
    assert parse_ipv4(text) is None


# --- regla "termina en numero" (WHATWG) ---------------------------------------------------------


@pytest.mark.parametrize(
    "host",
    [
        "127.1",
        "1",
        "0",
        "a.1",
        "sitio.123",
        "0x7f",
        "a.0x1g",  # empieza por 0x: se intenta como IPv4 y falla (D-03)
        "x.0xzz",
        "sitio.0x",
        "1.2.3.999",
        "4294967296",
        "010",
        "08",
        "0X1",
    ],
)
def test_ends_in_number_true(host: str) -> None:
    assert ends_in_number(host)


@pytest.mark.parametrize(
    "host",
    [
        "",
        "sitio.com",
        "1.a",
        "123abc",
        "a1",
        "0b1",
        "1.2.3.4a",
        "sitio.com1",
        "x0x1",
        ".",
        "a.",
        "1.2.3.",
        "[::1]",
        "a.٣",
        "٣",
        "-1",
        "1e3",
    ],
)
def test_ends_in_number_false(host: str) -> None:
    assert not ends_in_number(host)


def test_every_valid_ipv4_ends_in_number() -> None:
    for text in ("2130706433", "0177.0.0.1", "0x7f.1", "127.1", "1.2.3.4"):
        assert ends_in_number(text)
        assert parse_ipv4(text) is not None
