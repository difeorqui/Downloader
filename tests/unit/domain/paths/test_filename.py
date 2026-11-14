"""Nombre del archivo (RN-010, D-06; ejemplos 12 a 16, 22, 29, 40, 46, 47, 49)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.paths.filename import DEFAULT_NAME, choose_file_name, has_extension
from downloader.domain.paths.response import ServerResponse
from downloader.domain.paths.sanitize import INVALID_CHARS, INVISIBLE_CHARS, RESERVED_NAMES
from downloader.domain.result import Ok
from downloader.domain.text import windows_fold
from downloader.domain.urls import ParsedUrl
from downloader.domain.urls.parser import parse_url


def url(text: str) -> ParsedUrl:
    result = parse_url(text)
    assert isinstance(result, Ok), text
    return result.value


def name(text: str, response: ServerResponse | None = None) -> str:
    return choose_file_name(url(text), response)


def pdf() -> ServerResponse:
    return ServerResponse(content_type="application/pdf")


# --- Ejemplos del anexo 1 ---------------------------------------------------------------------


def test_example_12_the_server_name_is_used() -> None:
    response = ServerResponse(filename="reporte final.pdf")
    assert name("https://sitio.com/docs/", response) == "reporte final.pdf"


def test_example_13_no_name_in_url_and_known_type_gives_index_with_extension() -> None:
    assert name("https://sitio.com/docs/", pdf()) == "index.pdf"


def test_example_14_no_name_and_unknown_type_gives_plain_index() -> None:
    assert name("https://sitio.com") == "index"
    assert name("https://sitio.com", ServerResponse(content_type="application/x-nada")) == "index"


def test_example_15_directories_in_the_server_name_are_dropped() -> None:
    response = ServerResponse(filename="..\\..\\malo.exe")
    assert name("https://sitio.com/descarga?id=7", response) == "malo.exe"


def test_example_16_reserved_server_name() -> None:
    response = ServerResponse(filename="CON.pdf")
    assert name("https://sitio.com/descarga?id=8", response) == "CON_.pdf"


def test_example_22_extension_added_to_the_last_segment_from_the_type() -> None:
    assert name("https://corto.com/x", pdf()) == "x.pdf"


def test_example_29_segment_without_extension_gets_the_type_extension() -> None:
    assert name("www.sitio.com/ir?u=http://x.com/a.pdf", pdf()) == "ir.pdf"


def test_example_40_a_trailing_dot_dot_means_no_name() -> None:
    response = ServerResponse(content_type="text/html")
    assert name("https://sitio.com/a/b/..", response) == "index.html"


def test_example_46_html_page_for_an_extensionless_segment() -> None:
    response = ServerResponse(content_type="text/html")
    assert name("https://sitio.com/descarga", response) == "descarga.html"


def test_example_47_a_name_with_extension_is_not_renamed_by_the_type() -> None:
    response = ServerResponse(content_type="text/html")
    assert name("https://sitio.com/informe.pdf", response) == "informe.pdf"


def test_example_49_url_without_path_and_unknown_type() -> None:
    assert name("https://sitio.com?email=a@b.com") == "index"


def test_example_10_trailing_space_and_dot_are_removed() -> None:
    assert name("https://sitio.com/carpeta./archivo%20.txt%20") == "archivo .txt"


def test_example_11_decoded_name() -> None:
    assert name("https://sitio.com/Informe%20A%C3%B1o/Bogot%C3%A1.pdf") == "Bogotá.pdf"


def test_example_17_invisible_direction_character_is_removed() -> None:
    assert name("https://sitio.com/factura%E2%80%AEfdp.exe") == "facturafdp.exe"


# --- Prioridad (RN-010) --------------------------------------------------------------------------


def test_international_form_prevails_over_the_simple_one() -> None:
    response = ServerResponse(filename="simple.txt", filename_ext="internacional ñ.txt")
    assert name("https://a.com/url.pdf", response) == "internacional ñ.txt"


def test_simple_form_prevails_over_the_url() -> None:
    assert name("https://a.com/url.pdf", ServerResponse(filename="simple.txt")) == "simple.txt"


def test_url_is_used_when_the_server_gives_nothing() -> None:
    assert name("https://a.com/url.pdf", ServerResponse()) == "url.pdf"
    assert name("https://a.com/url.pdf", None) == "url.pdf"


@pytest.mark.parametrize("suggested", ["", " ", "...", "../", "..\\", "a/", ". .", "\u200b"])
def test_a_server_name_that_ends_up_empty_falls_through_to_the_url(suggested: str) -> None:
    response = ServerResponse(filename=suggested)
    assert name("https://a.com/url.pdf", response) == "url.pdf"


def test_an_empty_international_form_falls_back_to_the_simple_form() -> None:
    response = ServerResponse(filename="simple.txt", filename_ext="...")
    assert name("https://a.com/url.pdf", response) == "simple.txt"


def test_an_empty_url_segment_falls_through_to_index() -> None:
    assert name("https://a.com/%20...", pdf()) == "index.pdf"  # decodifica a " ..." y queda vacío
    assert name("https://a.com/...") == "index"


def test_the_server_name_is_not_decoded_again() -> None:
    """El nombre del servidor ya llega decodificado: ``%41`` es texto, no una ``A``."""
    assert name("https://a.com/x", ServerResponse(filename="100%41.txt")) == "100%41.txt"


def test_the_url_segment_is_decoded_exactly_once() -> None:
    assert name("https://a.com/a%2541.txt") == "a%41.txt"


def test_server_name_gets_no_extension_from_the_type() -> None:
    response = ServerResponse(filename="sin_extension", content_type="application/pdf")
    assert name("https://a.com/x", response) == "sin_extension"


def test_the_server_can_only_name_the_file_not_the_folder() -> None:
    response = ServerResponse(filename="C:\\Windows\\System32\\evil.dll")
    assert name("https://a.com/x", response) == "evil.dll"


def test_final_url_does_not_matter() -> None:
    response = ServerResponse(
        final_url=url("https://cdn.com/f/real.pdf"), content_type="application/pdf"
    )
    assert name("https://corto.com/x", response) == "x.pdf"


# --- Extensión según D-06 -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a.pdf", True),
        ("a.tar.gz", True),
        (".htaccess", False),
        ("a.", False),
        ("a", False),
        (".", False),
        ("", False),
        ("a.b.", False),
        ("..x", True),
    ],
)
def test_has_extension(text: str, expected: bool) -> None:
    assert has_extension(text) is expected


def test_a_dotfile_has_no_extension_so_the_type_adds_one() -> None:
    assert (
        name("https://a.com/.htaccess", ServerResponse(content_type="text/plain"))
        == ".htaccess.txt"
    )


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("text/html; charset=utf-8", "x.html"),
        ("TEXT/PLAIN", "x.txt"),
        ("application/xml", "x.xml"),
        ("text/xml", "x.xml"),
        ("image/jpeg", "x.jpg"),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "x.xlsx"),
        ("video/mp4", "x.mp4"),
        ("application/octet-stream", "x"),
        (None, "x"),
    ],
)
def test_type_table_applies_to_an_extensionless_segment(
    content_type: str | None, expected: str
) -> None:
    assert name("https://a.com/x", ServerResponse(content_type=content_type)) == expected


def test_a_segment_with_a_different_extension_keeps_it() -> None:
    assert name("https://a.com/x.php", pdf()) == "x.php"


# --- Saneado del nombre ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://a.com/con.tar.gz", "con_.tar.gz"),
        ("https://a.com/CON", "CON_"),
        ("https://a.com/aux", "aux_"),
        ("https://a.com/a%3Ab.txt", "a_b.txt"),
        ("https://a.com/a%00b.pdf", "a_b.pdf"),
        ("https://a.com/a%2fb.pdf", "a_b.pdf"),
        ("https://a.com/%2e%2e%2f", ".._"),
        ("https://a.com/con%20.txt", "con_ .txt"),
    ],
)
def test_the_url_name_is_decoded_then_sanitized(text: str, expected: str) -> None:
    assert name(text) == expected


def test_a_reserved_name_after_the_type_extension_is_checked_before_it_is_added() -> None:
    """``con`` + tipo pdf: ``con_`` sin extensión (no reservado) y luego ``.pdf``."""
    assert name("https://a.com/con", pdf()) == "con_.pdf"


# --- Propiedades ----------------------------------------------------------------------------------

PIECES = st.sampled_from(
    ["a", "con", "nul", ".", "..", " ", "%2e", "%20", "%2f", "%5c", "%00", "%E2%80%AE", "ñ",
     "x.pdf", "\\", "/", ":", "*", "$"]
)  # fmt: skip
SERVER_NAMES = st.one_of(st.none(), st.lists(PIECES, max_size=6).map("".join))
PATHS = st.lists(PIECES, max_size=6).map(lambda pieces: "https://a.com/" + "".join(pieces))
TYPES = st.sampled_from([None, "text/html", "application/pdf", "image/png", "x/y", ""])


@given(PATHS, SERVER_NAMES, SERVER_NAMES, TYPES)
def test_the_name_is_never_empty_and_meets_the_path_invariants(
    text: str, simple: str | None, international: str | None, content_type: str | None
) -> None:
    result = parse_url(text)
    if not isinstance(result, Ok):
        return
    response = ServerResponse(
        filename=simple, filename_ext=international, content_type=content_type
    )
    file_name = choose_file_name(result.value, response)
    assert file_name
    assert file_name not in {".", ".."}
    assert not any(char in INVALID_CHARS for char in file_name)
    assert not any(ord(char) < 0x20 for char in file_name)
    assert not any(char in INVISIBLE_CHARS for char in file_name)
    assert not file_name.endswith((".", " "))
    assert windows_fold(file_name.partition(".")[0].rstrip(" ")) not in RESERVED_NAMES


@given(PATHS, SERVER_NAMES, TYPES)
def test_the_choice_is_deterministic(
    text: str, simple: str | None, content_type: str | None
) -> None:
    result = parse_url(text)
    if not isinstance(result, Ok):
        return
    response = ServerResponse(filename=simple, content_type=content_type)
    assert choose_file_name(result.value, response) == choose_file_name(result.value, response)


def test_default_name_constant() -> None:
    assert DEFAULT_NAME == "index"
