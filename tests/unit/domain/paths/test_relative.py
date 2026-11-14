"""Carpetas relativas (RN-008, RN-009, RN-011; CA-001-54 a 61; ejemplos del anexo 1)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.paths.relative import relative_folders, url_path_parts
from downloader.domain.paths.sanitize import INVALID_CHARS, RESERVED_NAMES
from downloader.domain.result import Ok
from downloader.domain.text import windows_fold
from downloader.domain.urls import ParsedUrl
from downloader.domain.urls.parser import parse_url


def url(text: str) -> ParsedUrl:
    result = parse_url(text)
    assert isinstance(result, Ok), text
    return result.value


def folders(text: str) -> tuple[str, ...]:
    return relative_folders(url(text))


def last(text: str) -> str | None:
    return url_path_parts(url(text)).last_segment


# --- Ejemplos del anexo 1 (solo las carpetas y el último segmento) --------------------------------


@pytest.mark.parametrize(
    ("text", "expected_folders", "expected_last"),
    [
        (
            "https://sitio.com/docs/2024/informe.pdf?v=2",
            ("sitio.com", "docs", "2024"),
            "informe.pdf",
        ),  # 1
        ("https://Sitio.COM:443/Docs/A.pdf", ("sitio.com", "Docs"), "A.pdf"),  # 2
        ("http://sitio.com:8080/a/b.zip", ("sitio.com_8080", "a"), "b.zip"),  # 3
        (
            "https://sitio.com/a/../../../Windows/System32/x.dll",
            ("sitio.com", "a", "Windows", "System32"),
            "x.dll",
        ),  # 4
        ("https://sitio.com/%2e%2e/%2e%2e/secreto.txt", ("sitio.com",), "secreto.txt"),  # 5
        ("https://sitio.com/a\\..\\..\\b.txt", ("sitio.com", "a"), "b.txt"),  # 6
        ("https://sitio.com/a%5c..%5c..%5cb.txt", ("sitio.com",), "a\\..\\..\\b.txt"),  # 7
        ("https://sitio.com/CON/aux.txt", ("sitio.com", "CON_"), "aux.txt"),  # 8
        ("https://sitio.com/a%3Ab/c%2Ad%22.pdf", ("sitio.com", "a_b"), 'c*d".pdf'),  # 9
        (
            "https://sitio.com/carpeta./archivo%20.txt%20",
            ("sitio.com", "carpeta"),
            "archivo .txt ",
        ),  # 10
        (
            "https://sitio.com/Informe%20A%C3%B1o/Bogot%C3%A1.pdf",
            ("sitio.com", "Informe Año"),
            "Bogotá.pdf",
        ),  # 11
        ("https://sitio.com//a///b.pdf", ("sitio.com", "a"), "b.pdf"),  # 21
        ("https://[::1]:8443/a.pdf", ("[__1]_8443",), "a.pdf"),  # 23
        ("https://nul.com/a.pdf", ("nul_.com",), "a.pdf"),  # 32
        ("https://sitio.com/CONIN$/x.txt", ("sitio.com", "CONIN$_"), "x.txt"),  # 34
        ("https://sitio.com/a%2fb/c.pdf", ("sitio.com", "a_b"), "c.pdf"),  # 37
        ("https://sitio.com/a%00b.pdf", ("sitio.com",), "a\x00b.pdf"),  # 38
        ("https://sitio.com/%252e%252e/x.pdf", ("sitio.com", "%2e%2e"), "x.pdf"),  # 39
    ],
)
def test_annex_1_examples(text: str, expected_folders: tuple[str, ...], expected_last: str) -> None:
    parts = url_path_parts(url(text))
    assert parts.folders == expected_folders
    assert parts.last_segment == expected_last


# --- Dominio y puerto (RN-008 b, c; CA-001-54, D-08) ----------------------------------------------


def test_ca_001_54_domain_port_segments_without_query_or_fragment() -> None:
    parts = url_path_parts(url("https://Sitio.COM:8443/a/b/c.pdf?t=1&u=2#frag"))
    assert parts.folders == ("sitio.com_8443", "a", "b")
    assert parts.last_segment == "c.pdf"


def test_idn_domain_uses_the_ascii_form() -> None:
    assert folders("https://bogotá.com/a.pdf") == ("xn--bogot-1qa.com",)


def test_standard_ports_are_not_in_the_folder_name() -> None:
    assert folders("https://a.com:443/x") == ("a.com",)
    assert folders("http://a.com:80/x") == ("a.com",)
    assert folders("http://a.com:443/x") == ("a.com_443",)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://2130706433/a", "2130706433"),  # D-08: tal como se escribió
        ("https://0x7f.1/a", "0x7f.1"),
        ("https://[::1]/a", "[__1]"),
        ("https://[2001:db8::1]:9000/a", "[2001_db8__1]_9000"),
        ("https://[::ffff:127.0.0.1]/a", "[__ffff_127.0.0.1]"),
    ],
)
def test_ip_literals_keep_their_written_form(text: str, expected: str) -> None:
    assert folders(text) == (expected,)


def test_reserved_domain_label_gets_an_underscore() -> None:
    assert folders("https://con/a.pdf") == ("con_",)
    assert folders("https://aux.example.com/a.pdf") == ("aux_.example.com",)
    assert folders("https://con.com:8443/a.pdf") == ("con_.com_8443",)


def test_a_reserved_name_with_a_port_is_judged_on_the_whole_folder_name() -> None:
    """``con_8443`` no es un nombre reservado de Windows: no se le añade nada."""
    assert folders("https://con:8443/a.pdf") == ("con_8443",)


# --- CA-001-55: las carpetas salen de la URL original ---------------------------------------------


def test_ca_001_55_only_the_original_url_counts() -> None:
    original = url("https://corto.com/x")
    assert relative_folders(original) == ("corto.com",)
    assert url_path_parts(original).last_segment == "x"


# --- CA-001-56: decodificar una vez, conservar lo que no es UTF-8 ---------------------------------


def test_ca_001_56_valid_and_invalid_utf8() -> None:
    assert folders("https://a.com/Informe%20A%C3%B1o/x") == ("a.com", "Informe Año")
    assert folders("https://a.com/ab%C3/x") == ("a.com", "ab%C3")
    assert folders("https://a.com/%FF%FE/x") == ("a.com", "%FF%FE")
    assert folders("https://a.com/a%C3%B1%FFb/x") == ("a.com", "añ%FFb")


# --- CA-001-57: segmentos . y .. en cualquier grafía ----------------------------------------------

DOT_SPELLINGS = [
    ".",
    "%2e",
    "%2E",
    "..",
    ".%2e",
    ".%2E",
    "%2e.",
    "%2E.",
    "%2e%2e",
    "%2E%2E",
    "%2e%2E",
    "%2E%2e",
]


@pytest.mark.parametrize("spelling", DOT_SPELLINGS)
def test_ca_001_57_dot_segments_in_the_middle_are_discarded(spelling: str) -> None:
    assert folders(f"https://a.com/x/{spelling}/y/z.pdf") == ("a.com", "x", "y")
    assert folders(f"https://a.com/{spelling}/{spelling}/z.pdf") == ("a.com",)


@pytest.mark.parametrize("spelling", DOT_SPELLINGS)
def test_ca_001_57_dot_segment_as_the_last_one_means_no_name(spelling: str) -> None:
    parts = url_path_parts(url(f"https://a.com/x/{spelling}"))
    assert parts.folders == ("a.com", "x")
    assert parts.last_segment is None


def test_a_path_ending_in_slash_has_no_name() -> None:
    assert url_path_parts(url("https://sitio.com/docs/")).last_segment is None
    assert folders("https://sitio.com/docs/") == ("sitio.com", "docs")
    assert url_path_parts(url("https://sitio.com")).last_segment is None
    assert url_path_parts(url("https://sitio.com/")).last_segment is None
    assert url_path_parts(url("https://sitio.com/a/b/..")).last_segment is None


# --- CA-001-58: casi-puntos -----------------------------------------------------------------------


@pytest.mark.parametrize("segment", ["...", "..%20", "%20..", "..%20%20", ".%20."])
def test_ca_001_58_near_dots_are_folders_named_underscore(segment: str) -> None:
    """No son ``.`` ni ``..``: al sanearlos quedan vacíos y como carpeta pasan a ``_``."""
    assert folders(f"https://a.com/{segment}/x.pdf") == ("a.com", "_")


@pytest.mark.parametrize(
    ("segment", "decoded"), [("...", "..."), ("..%20", ".. "), ("%20..", " ..")]
)
def test_ca_001_58_as_the_last_segment_the_name_is_left_for_the_next_step(
    segment: str, decoded: str
) -> None:
    """El último segmento va decodificado y sin sanear: RN-010 lo sanea y, si queda vacío, sigue."""
    assert last(f"https://a.com/{segment}") == decoded


# --- CA-001-59 a 61 -------------------------------------------------------------------------------


def test_ca_001_59_encoded_dot_dot_slash_is_one_name() -> None:
    assert folders("https://a.com/%2e%2e%2f/x.pdf") == ("a.com", ".._")
    assert last("https://a.com/%2e%2e%2f") == "../"


def test_ca_001_60_absolute_path_inside_the_url_stays_inside() -> None:
    assert folders("https://sitio.com/C:/Windows/x.dll") == ("sitio.com", "C_", "Windows")
    assert folders("https://sitio.com/%5C%5Cserver/share/x") == ("sitio.com", "__server", "share")


def test_ca_001_61_empty_segments_are_ignored() -> None:
    assert folders("https://sitio.com//servidor/recurso/a.pdf") == (
        "sitio.com",
        "servidor",
        "recurso",
    )


# --- Todo segmento pasa por RN-011, RN-014 y RN-015 -----------------------------------------------


@pytest.mark.parametrize(
    ("segment", "folder"),
    [
        ("con", "con_"),
        ("CON.tar", "CON_.tar"),
        ("nul%20.x", "nul_ .x"),
        ("a.", "a"),
        ("a%20", "a"),
        ("a%E2%80%AEb", "ab"),  # carácter de control de dirección
        ("a%3Cb%3E", "a_b_"),
        ("%7C", "_"),
        ("%3F%2A", "__"),
        (".htaccess", ".htaccess"),
        ("COM10", "COM10"),
        ("%C0%AF", "%C0%AF"),
    ],
)
def test_every_folder_segment_is_decoded_then_sanitized(segment: str, folder: str) -> None:
    assert folders(f"https://a.com/{segment}/x.pdf") == ("a.com", folder)


# --- Propiedades (S-001-13) -----------------------------------------------------------------------

SEGMENT_PIECES = st.sampled_from(
    ["a", "con", "CON", "nul", "aux", ".", "..", "%2e", "%2E", "%252e", "%2f", "%5c", "%00", "%20",
     "%3A", "%3a", "%E2%80%AE", "%C3%B1", "%FF", "%C3", "ñ", " ", "\\", "?", ":", "*", "$", "x.txt"]
)  # fmt: skip
HOSTILE_PATHS = st.lists(st.lists(SEGMENT_PIECES, max_size=4).map("".join), max_size=6).map(
    lambda segments: "https://a.com/" + "/".join(segments)
)


@given(HOSTILE_PATHS)
def test_folders_meet_the_path_invariants(text: str) -> None:
    result = parse_url(text)
    if not isinstance(result, Ok):
        return
    for component in relative_folders(result.value):
        assert component not in {"", ".", ".."}
        assert not any(char in INVALID_CHARS for char in component)
        assert not any(ord(char) < 0x20 for char in component)
        assert not component.endswith((".", " "))
        assert windows_fold(component.partition(".")[0].rstrip(" ")) not in RESERVED_NAMES


@given(HOSTILE_PATHS)
def test_the_domain_is_always_the_first_folder_and_is_deterministic(text: str) -> None:
    result = parse_url(text)
    if not isinstance(result, Ok):
        return
    first = relative_folders(result.value)
    assert first[0] == "a.com"
    assert relative_folders(result.value) == first
