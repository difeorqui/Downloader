"""Dominio y puerto (RN-001 pasos 6, 8 y 9; RN-001a; D-02, D-03, D-08; CA-001-10, 13, 14)."""

from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address

import pytest

from downloader.domain.catalog import InvalidReason
from downloader.domain.result import Err, Ok
from downloader.domain.urls.host import Authority, parse_authority, resolve_port
from downloader.domain.urls.model import HostKind

I03 = InvalidReason.I03
I07 = InvalidReason.I07


def authority(text: str) -> Authority:
    result = parse_authority(text)
    assert isinstance(result, Ok), f"{text!r} -> {result!r}"
    return result.value


def rejected(text: str) -> InvalidReason:
    result = parse_authority(text)
    assert isinstance(result, Err), f"{text!r} -> {result!r}"
    return result.error


# --- Nombres -------------------------------------------------------------------------------------


def test_plain_name() -> None:
    result = authority("sitio.com")
    assert result == Authority("sitio.com", HostKind.NAME, None, "", False)


def test_case_does_not_count_as_a_conversion() -> None:
    """S-001-14: ``Sitio.COM`` en minúsculas no es una corrección."""
    result = authority("Sitio.COM")
    assert result.host == "sitio.com"
    assert result.converted_to_ascii is False


@pytest.mark.parametrize(
    ("text", "host"),
    [("localhost.", "localhost"), ("intranet.", "intranet"), ("sitio.com.", "sitio.com")],
)
def test_one_trailing_dot_is_removed(text: str, host: str) -> None:
    """CA-001-13 y RN-001a."""
    assert authority(text).host == host
    assert authority(f"{text}:8080").port_text == "8080"


@pytest.mark.parametrize("text", ["a.com..", "..", ".", "", ".com", "a..com", ":80"])
def test_empty_labels_and_empty_host_are_i03(text: str) -> None:
    assert rejected(text) is I03


def test_single_label_names_are_valid_names() -> None:
    for name in (
        "intranet",
        "servidor01",
        "x",
        "a_b",
        "a-b",
        "xn--bogot-1qa",
        "_dmarc.example.com",
    ):
        assert authority(name).kind is HostKind.NAME


@pytest.mark.parametrize("char", [*" #%/<>?@[\\]^|", "\x00", "\x1f", "\x7f", "\t", "\n"])
def test_forbidden_host_characters_are_i03(char: str) -> None:
    """D-03."""
    assert rejected(f"a{char}b.com") is I03
    assert rejected(f"a.com{char}") is I03


def test_host_length_limit_is_253() -> None:
    longest = ".".join(["a" * 63, "a" * 63, "a" * 63, "a" * 61])
    assert len(longest) == 253
    assert authority(longest).host == longest
    assert rejected(longest + "a") is I03


# --- Dominios internacionales (CA-001-14) ---------------------------------------------------------

COMBINED = "bogota" + chr(0x301) + ".com"  # "a" + tilde combinada


@pytest.mark.parametrize("text", ["BOGOTÁ.com", "bogotá.com", "Bogotá.COM", COMBINED])
def test_idn_becomes_ascii_form_and_is_marked(text: str) -> None:
    result = authority(text)
    assert result.host == "xn--bogot-1qa.com"
    assert result.converted_to_ascii is True
    assert result.kind is HostKind.NAME


def test_idn_in_a_later_label() -> None:
    assert authority("www.año.es").host == "www.xn--ao-zja.es"


@pytest.mark.parametrize(
    "text",
    [
        "a" + chr(0x200D) + "b.com",  # unión de ancho cero fuera de contexto
        "-á.com",  # guion inicial
        "á-.com",  # guion final
        "\U0001f600.com",  # emoji: no permitido en IDNA 2008
        "á" * 64 + ".com",  # etiqueta de más de 63
        chr(0xFF41) + ".com",  # letra de ancho completo: no es PVALID
        "bogotá.com" + chr(0x3002),  # punto ideográfico final => etiqueta vacía
    ],
)
def test_invalid_idn_is_i03(text: str) -> None:
    assert rejected(text) is I03


# --- IPv4 en cualquier notación (D-03, AB-14) -----------------------------------------------------


@pytest.mark.parametrize(
    ("text", "ip"),
    [
        ("127.0.0.1", "127.0.0.1"),
        ("2130706433", "127.0.0.1"),
        ("0x7f.1", "127.0.0.1"),
        ("127.1", "127.0.0.1"),
        ("0177.0.0.1", "127.0.0.1"),
        ("010.0.0.1", "8.0.0.1"),
        ("4294967295", "255.255.255.255"),
        ("1.2.3.4.", "1.2.3.4"),  # el punto final se quita antes
    ],
)
def test_ipv4_literal_keeps_its_written_form_and_its_value(text: str, ip: str) -> None:
    """D-08: el host queda como se escribió; ``ip`` trae el valor interpretado."""
    result = authority(text)
    assert result.kind is HostKind.IPV4
    assert result.ip == IPv4Address(ip)
    assert result.host == text.removesuffix(".")


@pytest.mark.parametrize(
    "text",
    ["4294967296", "0x100000000", "1.2.3.256", "1.2.3.4.5", "a.1", "x.0x", "0x1g", "1..2"],
)
def test_numeric_last_label_that_is_not_an_ipv4_is_i03(text: str) -> None:
    """CA-001-96."""
    assert rejected(text) is I03


@pytest.mark.parametrize("text", ["1.com", "1a.com", "a1", "x.1a", "0x.com", "123abc", "1.2.3.-1"])
def test_names_whose_last_label_is_not_a_number_are_names(text: str) -> None:
    assert authority(text).kind is HostKind.NAME


# --- IPv6 entre corchetes -------------------------------------------------------------------------


def test_ipv6_literal() -> None:
    result = authority("[::1]:8443")
    assert result == Authority("[::1]", HostKind.IPV6, IPv6Address("::1"), "8443", False)


@pytest.mark.parametrize(
    ("text", "host", "ip"),
    [
        ("[::1]", "[::1]", "::1"),
        ("[2001:DB8::1]", "[2001:db8::1]", "2001:db8::1"),
        ("[::ffff:127.0.0.1]", "[::ffff:127.0.0.1]", "::ffff:127.0.0.1"),
        ("[2002:7f00:1::]", "[2002:7f00:1::]", "2002:7f00:1::"),
        ("[0:0:0:0:0:0:0:1]", "[0:0:0:0:0:0:0:1]", "::1"),
    ],
)
def test_ipv6_keeps_lowercase_written_form(text: str, host: str, ip: str) -> None:
    result = authority(text)
    assert result.host == host
    assert result.ip == IPv6Address(ip)


@pytest.mark.parametrize(
    "text",
    [
        "[::1",
        "[::1]x",
        "[]",
        "[::g]",
        "[1.2.3.4]",
        "[fe80::1%eth0]",
        "[fe80::1%25eth0]",
        "[::1]80",
        "[ ::1]",
        "[::1 ]",
        "[:::1]",
        "[1:2:3:4:5:6:7:8:9]",
        "::1",
    ],
)
def test_malformed_ipv6_is_i03(text: str) -> None:
    assert rejected(text) is I03


def test_ipv6_with_empty_port_is_valid_and_has_no_port() -> None:
    assert authority("[::1]:").port_text == ""


# --- Puerto (D-02, CA-001-10) ---------------------------------------------------------------------


def test_port_text_is_kept_for_the_caller() -> None:
    assert authority("sitio.com:8080").port_text == "8080"
    assert authority("sitio.com:").port_text == ""
    assert authority("sitio.com").port_text == ""


@pytest.mark.parametrize(
    "port",
    [
        "80x",
        "x",
        "-1",
        " 80",
        "+80",
        "8 0",
        "b:c",
        "pass",
        chr(0x668) + chr(0x660),
        chr(0xB2),
        "8.0",
    ],
)
def test_non_numeric_port_is_kept_and_rejected_as_i07(port: str) -> None:
    """Ejemplo 18c de S-001-08: un puerto que no son dígitos ASCII es I-07, no I-03."""
    assert authority(f"sitio.com:{port}").port_text == port
    assert resolve_port(port, "https") == Err(I07)
    assert resolve_port(port, "http") == Err(I07)


def test_ipv6_with_port_text_keeps_it_for_resolve_port() -> None:
    assert authority("[::1]:80x").port_text == "80x"
    assert authority("[::1]:80:80").port_text == "80:80"


@pytest.mark.parametrize("port", ["1", "80", "443", "8443", "65535", "00080", "0000443", "00001"])
def test_valid_ports(port: str) -> None:
    assert isinstance(resolve_port(port, "https"), Ok)


@pytest.mark.parametrize(
    "port", ["0", "00", "65536", "99999", "100000", "123456", "9" * 5000, "0" * 5000]
)
def test_out_of_range_ports_are_i07(port: str) -> None:
    assert resolve_port(port, "http") == Err(I07)
    assert resolve_port(port, "https") == Err(I07)


def test_standard_ports_resolve_to_none() -> None:
    assert resolve_port("", "http") == Ok(None)
    assert resolve_port("80", "http") == Ok(None)
    assert resolve_port("0080", "http") == Ok(None)
    assert resolve_port("443", "https") == Ok(None)
    assert resolve_port("443", "http") == Ok(443)
    assert resolve_port("80", "https") == Ok(80)
    assert resolve_port("8080", "http") == Ok(8080)
