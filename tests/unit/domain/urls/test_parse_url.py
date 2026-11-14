"""``parse_url``: RN-001 pasos 7 a 9 y estructura única (CA-001-10 a 16 y 44, anexo 1)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from ipaddress import IPv4Address, IPv6Address

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.catalog import InvalidReason
from downloader.domain.result import Err, Ok
from downloader.domain.urls.model import Correction, HostKind, ParsedUrl
from downloader.domain.urls.parser import MAX_URL_LENGTH, parse_url

NONE = Correction.NONE
ADDED = Correction.SCHEME_ADDED
ENCODED = Correction.ENCODED


def parsed(text: str) -> ParsedUrl:
    result = parse_url(text)
    assert isinstance(result, Ok), f"{text!r} -> {result!r}"
    return result.value


def rejected(text: str) -> InvalidReason:
    result = parse_url(text)
    assert isinstance(result, Err), f"{text!r} -> {result!r}"
    return result.error


# --- Ejemplos del anexo 1 ----------------------------------------------------------------------


def test_example_2_case_and_standard_port() -> None:
    url = parsed("https://Sitio.COM:443/Docs/A.pdf")
    assert (url.scheme, url.host, url.port, url.path) == ("https", "sitio.com", None, "/Docs/A.pdf")
    assert url.corrections is NONE


def test_example_3_non_standard_port() -> None:
    url = parsed("http://sitio.com:8080/a/b.zip")
    assert (url.scheme, url.host, url.port, url.path) == ("http", "sitio.com", 8080, "/a/b.zip")


def test_example_6_backslashes_in_the_path_are_slashes_and_not_a_correction() -> None:
    url = parsed("https://sitio.com/a\\..\\..\\b.txt")
    assert url.path == "/a/../../b.txt"
    assert url.corrections is NONE


def test_example_23_ipv6_literal() -> None:
    url = parsed("https://[::1]:8443/a.pdf")
    assert (url.host, url.host_kind, url.ip, url.port) == (
        "[::1]",
        HostKind.IPV6,
        IPv6Address("::1"),
        8443,
    )


def test_example_24_idn_is_converted_and_marked() -> None:
    url = parsed("https://bogotá.com/a.pdf")
    assert url.host == "xn--bogot-1qa.com"
    assert url.corrections is ENCODED


def test_example_27_decimal_ipv4() -> None:
    url = parsed("https://2130706433/a.pdf")
    assert (url.host, url.host_kind, url.ip) == (
        "2130706433",
        HostKind.IPV4,
        IPv4Address("127.0.0.1"),
    )


def test_example_30_scheme_added_with_port() -> None:
    url = parsed("sitio.com:8080/a.pdf")
    assert (url.scheme, url.host, url.port, url.path) == ("https", "sitio.com", 8080, "/a.pdf")
    assert url.corrections is ADDED


def test_example_20_scheme_added() -> None:
    url = parsed("www.sitio.com/a.pdf")
    assert url.processed() == "https://www.sitio.com/a.pdf"
    assert url.corrections is ADDED


def test_example_41_spaces_and_non_ascii_are_encoded() -> None:
    url = parsed("https://sitio.com/Informe Final/año 2024.pdf")
    assert url.path == "/Informe%20Final/a%C3%B1o%202024.pdf"
    assert url.corrections is ENCODED


def test_example_49_question_mark_ends_the_authority() -> None:
    url = parsed("https://sitio.com?email=a@b.com")
    assert (url.host, url.path, url.query) == ("sitio.com", "", "email=a@b.com")


def test_example_51_backslash_in_the_query_is_percent_5c() -> None:
    url = parsed("https://sitio.com/a.pdf?ruta=c:\\temp")
    assert (url.path, url.query) == ("/a.pdf", "ruta=c:%5Ctemp")
    assert url.corrections is ENCODED


def test_example_29_url_inside_the_query() -> None:
    url = parsed("www.sitio.com/ir?u=http://x.com/a.pdf")
    assert url.processed() == "https://www.sitio.com/ir?u=http://x.com/a.pdf"
    assert url.corrections is ADDED


# --- Correcciones (CA-001-05, 14; S-001-14) ------------------------------------------------------


def test_both_corrections_can_apply() -> None:
    url = parsed("sitio.com/a b.pdf")
    assert url.corrections == ADDED | ENCODED


@pytest.mark.parametrize(
    "text",
    [
        "HTTPS://Sitio.COM/a.pdf",
        "https://SITIO.com/A.PDF",
        "Http://a.com",
        "https://sitio.com/a%20b",
    ],
)
def test_case_and_existing_encoding_are_not_corrections(text: str) -> None:
    assert parsed(text).corrections is NONE


@pytest.mark.parametrize("text", ["BOGOTÁ.com", "bogotá.com", "bogota" + chr(0x301) + ".com"])
def test_ca_001_14_three_spellings_give_the_same_host(text: str) -> None:
    url = parsed(f"https://{text}")
    assert url.host == "xn--bogot-1qa.com"
    assert url.corrections is ENCODED


@pytest.mark.parametrize(
    ("text", "expected_path"),
    [
        ("https://a.com/a b", "/a%20b"),
        ('https://a.com/a"b', "/a%22b"),
        ("https://a.com/a<b>c", "/a%3Cb%3Ec"),
        ("https://a.com/a`b", "/a%60b"),
        ("https://a.com/a{b}c", "/a%7Bb%7Dc"),
        ("https://a.com/a|b^c", "/a%7Cb%5Ec"),
        ("https://a.com/ñ", "/%C3%B1"),
    ],
)
def test_ca_001_17_18_path_encoding(text: str, expected_path: str) -> None:
    url = parsed(text)
    assert url.path == expected_path
    assert url.corrections is ENCODED


@pytest.mark.parametrize("code", [*range(0x20), 0x7F])
def test_ca_001_33_a_control_character_makes_the_url_malformed(code: int) -> None:
    """Un solo carácter de control en cualquier tramo: I-03 (también un byte nulo)."""
    control = chr(code)
    for text in (
        f"https://a.com/a{control}b",
        f"https://a.com/a?x={control}",
        f"https://a.com/a#{control}",
        f"https://a{control}b.com/a",
        f"https://a.com/{control}",
    ):
        assert rejected(text) is InvalidReason.I03, text


@pytest.mark.parametrize("sequence", ["%20", "%2F", "%25", "%C3%B1"])
def test_ca_001_20_existing_escapes_are_not_encoded_and_not_a_correction(sequence: str) -> None:
    url = parsed(f"https://a.com/x{sequence}y?q={sequence}#{sequence}")
    assert url.path == f"/x{sequence}y"
    assert url.corrections is NONE


@pytest.mark.parametrize(
    ("text", "path"),
    [
        ("https://a.com/a%zz", "/a%25zz"),
        ("https://a.com/a%", "/a%25"),
        ("https://a.com/a%2", "/a%252"),
    ],
)
def test_ca_001_21_lone_percent_is_encoded_and_marked(text: str, path: str) -> None:
    url = parsed(text)
    assert url.path == path
    assert url.corrections is ENCODED
    assert parsed(url.processed()).corrections is NONE


def test_ca_001_21_in_query_and_fragment() -> None:
    url = parsed("https://a.com/p?x=100%&y=%zz#50%")
    assert (url.query, url.fragment) == ("x=100%25&y=%25zz", "50%25")
    assert url.corrections is ENCODED


def test_ca_001_22_only_allowed_characters_is_untouched() -> None:
    url = parsed("https://a.com/a-b_c.d~e/f?g=h&i=j#k")
    assert url.processed() == "https://a.com/a-b_c.d~e/f?g=h&i=j#k"
    assert url.corrections is NONE


# --- Ruta, parámetros y fragmento -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "path", "query", "fragment"),
    [
        ("https://a.com", "", None, None),
        ("https://a.com/", "/", None, None),
        ("https://a.com/p?x=1#f", "/p", "x=1", "f"),
        ("https://a.com/p#f?x=1", "/p", None, "f?x=1"),
        ("https://a.com/p?x=1?y=2", "/p", "x=1?y=2", None),
        ("https://a.com/p#a#b", "/p", None, "a#b"),
        ("https://a.com?", "", "", None),
        ("https://a.com#", "", None, ""),
        ("https://a.com/p?#", "/p", "", ""),
        ("https://a.com?x#f", "", "x", "f"),
    ],
)
def test_split_of_path_query_and_fragment(
    text: str, path: str, query: str | None, fragment: str | None
) -> None:
    url = parsed(text)
    assert (url.path, url.query, url.fragment) == (path, query, fragment)
    assert url.processed() == text  # un "?" o "#" sin nada detrás se conserva


# --- Puerto (CA-001-10, 44) ----------------------------------------------------------------------


@pytest.mark.parametrize("port", ["0", "65536", "99999", "100000", "9" * 100])
def test_ca_001_10_invalid_ports_are_i07(port: str) -> None:
    assert rejected(f"https://sitio.com:{port}/a") is InvalidReason.I07


@pytest.mark.parametrize("port", [1, 65535])
def test_ca_001_10_valid_ports(port: int) -> None:
    assert parsed(f"https://sitio.com:{port}/a").port == port


def test_empty_port_is_the_standard_port() -> None:
    assert parsed("https://sitio.com:/a").port is None


@pytest.mark.parametrize("port", ["80x", "pass", "-1", "8o", "0x50"])
def test_non_numeric_port_is_i07(port: str) -> None:
    """Ejemplo 18c de S-001-08: un puerto que no son dígitos es I-07."""
    assert rejected(f"https://sitio.com:{port}/a") is InvalidReason.I07


def test_example_18c_user_pass_before_question_mark() -> None:
    assert rejected("https://user:pass?@evil.com/") is InvalidReason.I07


def test_text_after_an_ipv6_literal_is_i03_but_a_bad_port_is_i07() -> None:
    assert rejected("https://[::1]x/a") is InvalidReason.I03
    assert rejected("https://[::1]:80x/a") is InvalidReason.I07


def test_ca_001_44_port_error_wins_over_the_address() -> None:
    assert rejected("https://169.254.169.254:99999/") is InvalidReason.I07


def test_standard_port_of_the_other_scheme_is_kept() -> None:
    assert parsed("http://a.com:443/").port == 443
    assert parsed("https://a.com:80/").port == 80
    assert parsed("http://a.com:80/").port is None


# --- Largo (CA-001-11, RN-003 h) ---------------------------------------------------------------


def test_ca_001_11_boundary_at_2048() -> None:
    prefix = "https://a.com/"
    ok = prefix + "x" * (MAX_URL_LENGTH - len(prefix))
    assert len(ok) == 2048
    assert parsed(ok).processed() == ok
    assert rejected(ok + "x") is InvalidReason.I04


def test_length_counts_the_added_scheme() -> None:
    ok = "a.com/" + "x" * (MAX_URL_LENGTH - len("https://a.com/"))
    assert len(parsed(ok).processed()) == 2048
    assert rejected(ok + "x") is InvalidReason.I04


def test_length_is_measured_after_encoding() -> None:
    prefix = "https://a.com/"
    exactly = prefix + " " * 678  # 678 * 3 = 2034
    assert len(parsed(exactly).processed()) == 2048
    assert rejected(exactly + " ") is InvalidReason.I04
    assert len(prefix + " " * 700) < 2048  # el texto escrito cabe, pero codificado no
    assert rejected(prefix + " " * 700) is InvalidReason.I04


def test_length_does_not_count_a_standard_port_that_is_dropped() -> None:
    text = "https://a.com:443/" + "x" * (2048 - len("https://a.com/") + 0)
    assert len(text) > 2048
    assert len(parsed(text).processed()) == 2048
    assert rejected(text + "x") is InvalidReason.I04


def test_i04_wins_over_i07() -> None:
    assert rejected("https://a.com:99999/" + "x" * 3000) is InvalidReason.I04


# --- Dominio y puerto: errores del paso 9 ---------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "https://",
        "https:///a",
        "https://:80/a",
        "https://a..com",
        "https://[::1",
        "https://1.2.3.256",
    ],
)
def test_malformed_authority_is_i03(text: str) -> None:
    assert rejected(text) is InvalidReason.I03


def test_errors_of_the_first_stage_are_passed_through() -> None:
    assert rejected("ftp://a.com") is InvalidReason.I01
    assert rejected("C:\\a") is InvalidReason.I02
    assert rejected("https://u@a.com") is InvalidReason.I05
    assert rejected("https://a.com/x https://b.com") is InvalidReason.I09


# --- Inmutabilidad y confidencialidad básica -----------------------------------------------------


def test_parsed_url_is_immutable() -> None:
    url = parsed("https://a.com/x")
    with pytest.raises(FrozenInstanceError):
        url.host = "otro.com"  # type: ignore[misc]


def test_default_repr_does_not_leak_query_or_fragment() -> None:
    url = parsed("https://a.com/x?token=CANARIO-123#CANARIO-456")
    for text in (repr(url), str(url), f"{url}", f"{url!r}"):
        assert "CANARIO" not in text


# --- Idempotencia (CA-001-15) y totalidad --------------------------------------------------------

SAMPLES = [
    "https://Sitio.COM:443/Docs/A.pdf",
    "sitio.com:8080/a b.pdf?x=1 2#f g",
    "https://bogotá.com/año?ñ=ü#ç",
    "https://[2001:DB8::1]:8443/a",
    "https://2130706433/a",
    "https://0x7f.1/a\\b\\c",
    "localhost.",
    "https://a.com?",
    "https://a.com#",
    "https://a.com/%252e%252e/%2e%2e/x?%41=%zz",
    "HTTP://A.COM:80",
]


@pytest.mark.parametrize("text", SAMPLES)
def test_ca_001_15_interpreting_the_processed_url_gives_the_same_structure(text: str) -> None:
    first = parsed(text)
    second = parsed(first.processed())
    assert replace(second, corrections=first.corrections) == first
    assert second.corrections is NONE  # ya está corregida y codificada
    assert second.processed() == first.processed()


PIECES = st.sampled_from(
    ["https://", "http://", "ftp://", "a.com", "Sitio.COM", "[::1]", "127.1", "0x7f.1", "@", ":",
     "80", "443", "/", "\\", "?", "#", "%2e", "%", "%zz", "ñ", " ", "\n", "..", ".", "bogotá",
     "xn--", "x=1", "=", "&", "\x00", "\u202e", "CANARIO"]
)  # fmt: skip
HOSTILE_URLS = st.one_of(
    st.lists(PIECES, max_size=12).map("".join),
    st.text(alphabet=st.characters(blacklist_categories=()), max_size=80),
)


@given(HOSTILE_URLS)
def test_parse_url_is_total_and_its_output_is_clean(text: str) -> None:
    result = parse_url(text)
    assert isinstance(result, Ok | Err)
    if isinstance(result, Ok):
        processed = result.value.processed()
        assert processed.isascii()
        assert not any(
            char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F for char in processed
        )
        assert len(processed) <= MAX_URL_LENGTH
        assert result.value.path == "" or result.value.path.startswith("/")
        assert "\\" not in processed


@given(HOSTILE_URLS)
def test_parse_url_is_idempotent_on_anything_it_accepts(text: str) -> None:
    result = parse_url(text)
    if isinstance(result, Err):
        return
    again = parse_url(result.value.processed())
    assert isinstance(again, Ok)
    assert replace(again.value, corrections=result.value.corrections) == result.value
