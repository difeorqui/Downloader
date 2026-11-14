"""RN-001 pasos 1 a 6 y RN-001a (CA-001-01 a 09; ejemplos 20, 29, 35, 36, 49, 50, 52, 55)."""

from __future__ import annotations

import pytest

from downloader.domain.catalog import InvalidReason
from downloader.domain.result import Err, Ok
from downloader.domain.urls.parser import RawUrl, split_raw_url


def ok(text: str) -> RawUrl:
    result = split_raw_url(text)
    assert isinstance(result, Ok), f"{text!r} -> {result!r}"
    return result.value


def reason(text: str) -> InvalidReason:
    result = split_raw_url(text)
    assert isinstance(result, Err), f"{text!r} -> {result!r}"
    return result.error


# --- Esquema y corrección (CA-001-01, 05; ejemplos 20, 29) --------------------------------------


def test_url_without_scheme_gets_https_and_is_marked() -> None:
    """CA-001-01 y ejemplo 20."""
    raw = ok("www.sitio.com/a.pdf")
    assert raw == RawUrl("https", "www.sitio.com", "/a.pdf", scheme_added=True)


def test_explicit_schemes_are_kept_and_not_marked() -> None:
    assert ok("https://sitio.com/a.pdf") == RawUrl("https", "sitio.com", "/a.pdf", False)
    assert ok("http://sitio.com/a.pdf") == RawUrl("http", "sitio.com", "/a.pdf", False)


def test_scheme_and_domain_case_do_not_count_as_a_correction() -> None:
    """CA-001-05: ``HTTPS://Sitio.COM/a.pdf`` no es corregida; el dominio se normaliza luego."""
    raw = ok("HTTPS://Sitio.COM/a.pdf")
    assert raw == RawUrl("https", "Sitio.COM", "/a.pdf", False)
    assert ok("HtTp://x.com").scheme == "http"


def test_text_before_separator_that_is_not_a_scheme_is_a_missing_scheme() -> None:
    """Ejemplo 29: ``www.sitio.com/ir?u=http://x.com/a.pdf`` no es I-01."""
    raw = ok("www.sitio.com/ir?u=http://x.com/a.pdf")
    assert raw == RawUrl("https", "www.sitio.com", "/ir?u=http://x.com/a.pdf", True)


@pytest.mark.parametrize(
    "text",
    [
        "sitio.com:8080/a.pdf",  # ejemplo 30: sin "://", no hay esquema
        "sitio.com",
        "localhost",
        "10.0.0.1/a",
        "//sitio.com/a",  # relativa al protocolo: queda sin autoridad
    ],
)
def test_other_texts_without_scheme_are_corrected(text: str) -> None:
    assert ok(text).scheme_added is True


def test_authority_ends_at_the_first_slash_question_mark_or_hash() -> None:
    assert ok("https://sitio.com") == RawUrl("https", "sitio.com", "", False)
    assert ok("https://sitio.com/") == RawUrl("https", "sitio.com", "/", False)
    assert ok("https://sitio.com?x=1") == RawUrl("https", "sitio.com", "?x=1", False)
    assert ok("https://sitio.com#frag") == RawUrl("https", "sitio.com", "#frag", False)
    assert ok("https://sitio.com:8443/a") == RawUrl("https", "sitio.com:8443", "/a", False)
    assert ok("https://[::1]:8443/a") == RawUrl("https", "[::1]:8443", "/a", False)


def test_the_remainder_is_kept_without_touching_it() -> None:
    """La codificación y el ``\\`` de la ruta son del tramo siguiente (pasos 7 y 8)."""
    raw = ok("https://sitio.com/a b\\c.pdf?r=c:\\temp#f g")
    assert raw.remainder == "/a b\\c.pdf?r=c:\\temp#f g"


# --- I-01: protocolo no soportado (CA-001-02, 03) -----------------------------------------------


@pytest.mark.parametrize("text", ["ftp://x.com/a", "FTP://x.com/a", "ws://x.com", "git+ssh://x/y"])
def test_unsupported_scheme_is_i01(text: str) -> None:
    """CA-001-02."""
    assert reason(text) is InvalidReason.I01


@pytest.mark.parametrize(
    "text",
    [
        "javascript:alert(1)",
        "vbscript:msgbox(1)",
        "data:text/html,<b>x</b>",
        "file:///C:/Windows/x.dll",
        "file:C:/x",
        "blob:https://x.com/uuid",  # el texto antes de "://" no es un esquema: lo decide el paso 3
        "about:blank",
        "mailto:alguien@x.com",
    ],
)
def test_dangerous_prefixes_are_i01_in_any_case(text: str) -> None:
    """CA-001-03."""
    assert reason(text) is InvalidReason.I01
    assert reason(text.upper()) is InvalidReason.I01
    assert reason(text.capitalize()) is InvalidReason.I01


def test_a_scheme_with_a_dot_or_plus_is_a_scheme_not_a_domain() -> None:
    assert reason("a.b://x") is InvalidReason.I01
    assert reason("a+b-c://x") is InvalidReason.I01


def test_prefix_with_invalid_scheme_characters_is_not_a_scheme() -> None:
    assert ok("1abc://x.com/a").scheme_added is True  # empieza por dígito
    assert ok("ab_c://x.com/a").scheme_added is True  # "_" no está en el patrón


# --- I-02: ruta local o de red (CA-001-04) ------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["\\\\servidor\\a", "C:\\a", "c:/a", "Z:\\", "d:/carpeta/x.txt", "\\\\?\\C:\\x", "\\\\"],
)
def test_local_and_network_paths_are_i02(text: str) -> None:
    assert reason(text) is InvalidReason.I02


@pytest.mark.parametrize("text", ["C:", "C:a", "cc:/a", "1:/a", "/a/b", "\\a"])
def test_texts_that_only_resemble_paths_are_not_i02(text: str) -> None:
    result = split_raw_url(text)
    assert not (isinstance(result, Err) and result.error is InvalidReason.I02)


# --- I-09: varias URLs en una línea (CA-001-06; ejemplo 50) -------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "https://a.com/x.pdf https://b.com/y.pdf",  # ejemplo 50
        "https://a.com/x.pdf http://b.com/y.pdf",
        "a.com/x.pdf https://b.com/y.pdf",
        "https://a.com/x.pdf\thttps://b.com/y.pdf",
        "https://a.com/x.pdf   HTTP://b.com",
        "https://a.com/x.pdf\u00a0https://b.com",  # espacio no separable
    ],
)
def test_space_followed_by_http_is_i09(text: str) -> None:
    assert reason(text) is InvalidReason.I09


@pytest.mark.parametrize(
    "text",
    [
        "https://a.com/x%20https://b.com",  # sin espacio real
        "https://a.com/x?u=https://b.com/y",  # una URL dentro de un parámetro
        "https://a.com/x httpx://b.com",  # no es http ni https
        "https://a.com/x http:/b.com",
    ],
)
def test_only_a_real_space_before_a_scheme_is_i09(text: str) -> None:
    result = split_raw_url(text)
    assert not (isinstance(result, Err) and result.error is InvalidReason.I09)


# --- I-03: autoridad cruda ambigua (CA-001-08; ejemplos 35, 36, 52) ------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "https://sitio.com\\@127.0.0.1/a.pdf",  # ejemplo 35
        "https://sitio.com#@127.0.0.1/a.pdf",  # ejemplo 36
        "https://sitio.com?q=a\\b",  # ejemplo 52: rechazo conservador aceptado
        "https://sitio.com\\a",
        "https://sitio.com\\",
        "https://sitio.com#x@y",
    ],
)
def test_ambiguous_raw_authority_is_i03(text: str) -> None:
    assert reason(text) is InvalidReason.I03


@pytest.mark.parametrize(
    "text",
    [
        "https://sitio.com/#@127.0.0.1",  # la "/" cierra la autoridad cruda
        "https://sitio.com/a\\b.pdf",  # "\" en la ruta: paso 7
        "https://sitio.com/a?x=1#@",
        "https://sitio.com#frag",  # "#" sin "@" después
        "https://sitio.com@",  # "@" sin "#": es I-05 y no I-03
    ],
)
def test_backslash_or_hash_at_after_the_first_slash_is_not_ambiguous(text: str) -> None:
    result = split_raw_url(text)
    assert not (isinstance(result, Err) and result.error is InvalidReason.I03)


# --- I-05: credenciales (CA-001-09; ejemplo 49) --------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "https://user:pass@sitio.com/a",
        "https://user@sitio.com/a",
        "https://@sitio.com",
        "https://a@b@sitio.com/a",
        "user:pass@sitio.com/a",  # sin esquema: se antepone https:// y se detecta igual
        "https://user@sitio.com?x=1",
    ],
)
def test_credentials_in_the_authority_are_i05(text: str) -> None:
    assert reason(text) is InvalidReason.I05


@pytest.mark.parametrize(
    "text",
    [
        "https://sitio.com?email=a@b.com",  # ejemplo 49: la autoridad termina en "?"
        "https://sitio.com/a@b.pdf",
        "https://sitio.com/user:pass@x",
        "https://sitio.com/a?u=x@y#f@g",
    ],
)
def test_at_sign_after_the_authority_is_not_a_credential(text: str) -> None:
    raw = ok(text)
    assert raw.authority == "sitio.com"


def test_credentials_cut_by_question_mark_are_not_in_the_authority() -> None:
    """``https://user:p?ss@sitio.com``: la autoridad es ``user:p``; el ``@`` queda en parámetros."""
    raw = ok("https://user:p?ss@sitio.com")
    assert raw.authority == "user:p"
    assert raw.remainder == "?ss@sitio.com"


# --- I-03: dominio con espacio (CA-001-07; ejemplo 55) --------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "https://sitio .com/a.pdf",  # ejemplo 55
        "https://sitio.com /a.pdf",
        "https://sitio.com :80/a",
        "https://sitio.com\t/a",
        "sitio .com/a.pdf",
        "https://sitio\u00a0.com/a.pdf",
        "https://si tio.com",
    ],
)
def test_space_in_the_domain_is_i03(text: str) -> None:
    assert reason(text) is InvalidReason.I03


def test_space_in_path_query_or_fragment_is_fine_here() -> None:
    """Se codifica después (paso 8): ejemplo 41."""
    assert ok("https://sitio.com/Informe Final/año 2024.pdf").authority == "sitio.com"
    assert ok("https://sitio.com?a=b c#d e").remainder == "?a=b c#d e"


# --- Entradas límite -----------------------------------------------------------------------------


def test_empty_and_degenerate_inputs_do_not_raise() -> None:
    for text in ["", " ", "://", "https://", "http:///", "https:///a", "?", "#", "@", "\\"]:
        result = split_raw_url(text)
        assert isinstance(result, Ok | Err)


def test_empty_authority_is_left_to_the_host_check() -> None:
    assert ok("https://").authority == ""
    assert ok("https:///a/b").authority == ""


# --- RN-036: el tipo intermedio tampoco muestra parámetros ni fragmento ---------------------------


def test_raw_url_repr_is_masked() -> None:
    raw = ok("https://sitio.com/a?token=SECRETO#frag")
    assert raw.remainder == "/a?token=SECRETO#frag"  # el dato sigue intacto para el siguiente paso
    for shown in (repr(raw), str(raw), f"{raw}"):
        assert "SECRETO" not in shown
        assert "frag" not in shown
    assert repr(raw) == "RawUrl(https://sitio.com/a?***, scheme_added=False)"
