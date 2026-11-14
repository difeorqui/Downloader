"""Enmascarado (RN-036, S-001-08, D-10; CA-001-107 a 109): tabla de pares exactos y canario."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.catalog import InvalidReason
from downloader.domain.result import Ok
from downloader.domain.urls import InvalidUrl, ParsedUrl, interpret_url, mask_text
from downloader.domain.urls.masking import (
    VISIBLE_LIMIT,
    mask_fragment,
    mask_query,
    truncate_visible,
)
from downloader.domain.urls.parser import parse_url

CANARY = "CANARIO-7f3a9c"


def visible(text: str) -> str:
    """Salida visible de interpretar ``text``: ``masked()`` si es válida o ``masked_text`` si no."""
    result = interpret_url(text)
    return result.masked() if isinstance(result, ParsedUrl) else result.masked_text


def invalid(text: str) -> InvalidUrl:
    result = interpret_url(text)
    assert isinstance(result, InvalidUrl), text
    return result


# --- S-001-08: tabla de pares exactos -------------------------------------------------------------

VALID_PAIRS = [
    ("https://sitio.com/a.pdf?token=abc&v=2#frag", "https://sitio.com/a.pdf?token=***&v=***#***"),
    ("https://sitio.com/a.pdf?a", "https://sitio.com/a.pdf?***"),
    ("https://sitio.com/a.pdf?a=", "https://sitio.com/a.pdf?a=***"),
    ("https://sitio.com/a.pdf?a=1&a=2", "https://sitio.com/a.pdf?a=***&a=***"),
    ("https://sitio.com/a.pdf?", "https://sitio.com/a.pdf?"),
    ("https://sitio.com/a.pdf#", "https://sitio.com/a.pdf#"),
    ("https://sitio.com/a.pdf?a=1&&b=2", "https://sitio.com/a.pdf?a=***&&b=***"),
    ("https://sitio.com/a.pdf?a=b=c", "https://sitio.com/a.pdf?a=***"),
]


@pytest.mark.parametrize(("text", "expected"), VALID_PAIRS)
def test_valid_urls_rows_1_to_8(text: str, expected: str) -> None:
    assert visible(text) == expected


INVALID_PAIRS = [
    ("https://u:p@sitio.com/a", InvalidReason.I05, "https://***@sitio.com/a"),  # 9
    ("https://sitio.com:99999/a?t=1", InvalidReason.I07, "https://sitio.com:99999/a?t=***"),  # 11
    ("ftp://u:p@x.com/a?t=1", InvalidReason.I01, "ftp://***@x.com/a?***"),  # 12
    ("mailto:juan@correo.com", InvalidReason.I01, "***@correo.com"),  # 13
    ("javascript:alert(1)#x", InvalidReason.I01, "javascript:alert(1)#***"),  # 14
    (
        "\\\\servidor\\recurso\\a.pdf?t=1",
        InvalidReason.I02,
        "\\\\servidor\\recurso\\a.pdf?***",
    ),  # 15
    ("C:\\temp\\a.pdf", InvalidReason.I02, "C:\\temp\\a.pdf"),  # 16
    ("https://sitio.com\\@127.0.0.1/?t=1", InvalidReason.I03, "https://***@127.0.0.1/?***"),  # 17
    ("https://sitio.com#@127.0.0.1/a", InvalidReason.I03, "https://***@127.0.0.1/a"),  # 18
    ("https://user:pa#ss@host/", InvalidReason.I03, "https://***@host/"),  # 18b
    ("https://user:pass?@evil.com/", InvalidReason.I07, "https://***@evil.com/"),  # 18c
    (
        f"https://a.com/x.pdf?t={CANARY} https://u:p@b.com/y#k",
        InvalidReason.I09,
        "https://a.com/x.pdf?*** https://***@b.com/y#***",
    ),  # 19
]


@pytest.mark.parametrize(("text", "reason", "expected"), INVALID_PAIRS)
def test_invalid_urls_rows_9_to_19(text: str, reason: InvalidReason, expected: str) -> None:
    result = invalid(text)
    assert result.reason is reason
    assert result.masked_text == expected


def test_row_10_blocked_address_shows_its_parameters_masked() -> None:
    """I-06 lo decide el validador del lote sobre una URL ya analizada: ``masked()``."""
    result = parse_url("https://169.254.169.254/x?k=1")
    assert isinstance(result, Ok)
    assert result.value.masked() == "https://169.254.169.254/x?k=***"


def test_row_20_too_long_is_cut_to_199_plus_ellipsis() -> None:
    text = "https://sitio.com/" + "a" * 2100 + "?t=1"
    result = invalid(text)
    assert result.reason is InvalidReason.I04
    assert result.masked_text == "https://sitio.com/" + "a" * 181 + "…"
    assert len(result.masked_text) == 200


# --- Funciones auxiliares -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", ""),
        ("a", "***"),
        ("a=", "a=***"),
        ("a=1", "a=***"),
        ("a=1&b=2", "a=***&b=***"),
        ("a=1&&b", "a=***&&***"),
        ("&", "&"),
        ("=x", "=***"),
        ("a=b=c&d", "a=***&***"),
        ("a=1&", "a=***&"),
    ],
)
def test_mask_query(query: str, expected: str) -> None:
    assert mask_query(query) == expected


def test_mask_fragment() -> None:
    assert mask_fragment("") == ""
    assert mask_fragment("x") == "***"
    assert mask_fragment("a#b") == "***"


def test_truncate_visible_boundaries() -> None:
    assert truncate_visible("a" * 200) == "a" * 200
    assert truncate_visible("a" * 201) == "a" * 199 + "…"
    assert len(truncate_visible("a" * 10_000)) == VISIBLE_LIMIT
    assert truncate_visible("") == ""


def test_ca_001_109_a_visible_output_over_200_characters_is_cut() -> None:
    long_path = "https://sitio.com/" + "x" * 500
    shown = visible(long_path)
    assert len(shown) == 200
    assert shown.endswith("…")


# --- CA-001-107: el canario no aparece en ninguna salida visible ----------------------------------

CANARY_URLS = [
    (f"ftp://u:{CANARY}@x.com/a?t={CANARY}#{CANARY}", InvalidReason.I01),
    (f"javascript:alert(1)?k={CANARY}", InvalidReason.I01),
    (f"\\\\srv\\a?t={CANARY}#{CANARY}", InvalidReason.I02),
    (f"C:\\a?token={CANARY}", InvalidReason.I02),
    (f"https://sitio.com\\@127.0.0.1/?t={CANARY}", InvalidReason.I03),
    (f"https://{CANARY}#@127.0.0.1/a", InvalidReason.I03),
    (f"https://user:{CANARY}#x@host/", InvalidReason.I03),
    (f"https://sitio .com/a?t={CANARY}", InvalidReason.I03),
    (f"https://a..com/a?t={CANARY}#{CANARY}", InvalidReason.I03),
    ("https://sitio.com/" + "a" * 2100 + f"?t={CANARY}", InvalidReason.I04),
    (f"https://{CANARY}:{CANARY}@sitio.com/a?t={CANARY}#{CANARY}", InvalidReason.I05),
    (f"https://sitio.com:99999/a?t={CANARY}#{CANARY}", InvalidReason.I07),
    (f"https://user:{CANARY}?@evil.com/", InvalidReason.I07),
    (f"https://a.com/x?t={CANARY} https://u:{CANARY}@b.com/y#{CANARY}", InvalidReason.I09),
]


@pytest.mark.parametrize(("text", "reason"), CANARY_URLS)
def test_ca_001_107_canary_is_not_in_the_visible_output(text: str, reason: InvalidReason) -> None:
    result = invalid(text)
    assert result.reason is reason
    for shown in (result.masked_text, repr(result), str(result), f"{result}"):
        assert CANARY not in shown, (reason, shown)


# --- CA-001-108: en una URL válida el canario solo está en processed() --------------------------


def test_ca_001_108_canary_only_in_processed() -> None:
    text = f"https://sitio.com/a.pdf?t={CANARY}&u=2#{CANARY}"
    url = interpret_url(text)
    assert isinstance(url, ParsedUrl)
    assert CANARY in url.processed()
    outputs = [
        url.masked(),
        repr(url),
        str(url),
        f"{url}",
        f"{url!r}",
        f"{url!s}",
        format(url),
        "%s" % url,  # noqa: UP031 - se prueba precisamente el formato con %
        "%r" % url,  # noqa: UP031
        "{}".format(url),  # noqa: UP032
        str([url]),
        str({"u": url}),
        str((url,)),
    ]
    for shown in outputs:
        assert CANARY not in shown, shown


def test_canary_in_userinfo_never_reaches_a_parsed_url_at_all() -> None:
    url = interpret_url(f"https://u:{CANARY}@sitio.com/a")
    assert isinstance(url, InvalidUrl)
    assert url.reason is InvalidReason.I05
    assert CANARY not in url.masked_text


def test_canary_in_the_path_is_a_documented_residual_risk() -> None:
    """RN-036: los tokens dentro de la ruta no se distinguen de un nombre de carpeta."""
    url = interpret_url(f"https://sitio.com/descarga/{CANARY}/archivo.pdf")
    assert isinstance(url, ParsedUrl)
    assert CANARY in url.masked()


def test_masked_and_repr_forms() -> None:
    url = interpret_url("https://sitio.com:8443/a.pdf?t=1#f")
    assert isinstance(url, ParsedUrl)
    assert str(url) == url.masked() == "https://sitio.com:8443/a.pdf?t=***#***"
    assert repr(url) == "ParsedUrl(https://sitio.com:8443/a.pdf?t=***#***)"


def test_ipv6_and_ipv4_hosts_are_shown_as_written() -> None:
    assert visible("https://[::1]:8443/a.pdf") == "https://[::1]:8443/a.pdf"
    assert visible("https://0x7f.1/a?k=v") == "https://0x7f.1/a?k=***"


# --- mask_text directo --------------------------------------------------------------------------


def test_mask_text_never_fails_on_degenerate_inputs() -> None:
    for text in ["", "@", "?", "#", "://", "@@@", "?#", "#?", "https://", "https://@", "a b c"]:
        assert isinstance(mask_text(text), str)


def test_mask_text_keeps_an_empty_question_mark_or_hash() -> None:
    assert mask_text("javascript:x?") == "javascript:x?"
    assert mask_text("javascript:x#") == "javascript:x#"


def test_mask_text_credentials_use_the_last_at_of_the_authority() -> None:
    assert mask_text("ftp://a@b@c.com/x") == "ftp://***@c.com/x"
    assert mask_text("ftp://u:p@h/p@q") == "ftp://***@h/p@q"  # el "@" de la ruta no es credencial


def test_mask_text_splits_several_urls_by_the_space_before_http() -> None:
    masked = mask_text(f"ftp://u:{CANARY}@a.com/x?k={CANARY}   HTTP://b.com/y#{CANARY}")
    assert masked == "ftp://***@a.com/x?*** HTTP://b.com/y#***"


def test_mask_text_analyzable_flag_masks_by_part() -> None:
    assert mask_text("https://u:p@h/a?x=1&y#f", analyzable=True) == "https://***@h/a?x=***&***#***"
    assert mask_text("https://u:p@h/a?x=1&y#f") == "https://***@h/a?***"


# --- Propiedades --------------------------------------------------------------------------------

PREFIX = st.text(alphabet="abcdefghij:/.-_", max_size=30)
TAILS = st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=30)


@given(PREFIX, st.sampled_from(["?", "#"]), TAILS)
def test_nothing_after_the_first_question_mark_or_hash_survives(
    prefix: str, mark: str, tail: str
) -> None:
    text = f"{prefix}{mark}k={CANARY}{tail}"  # el valor de un parámetro, no su nombre
    for analyzable in (False, True):
        masked = mask_text(text, analyzable=analyzable)
        assert CANARY not in masked


@given(PREFIX, TAILS)
def test_credentials_before_the_last_at_never_survive(prefix: str, tail: str) -> None:
    text = f"https://{CANARY}:{CANARY}@{prefix.replace('/', '')}/{tail}"
    assert CANARY not in mask_text(text)


@given(st.text(alphabet=st.characters(blacklist_categories=()), max_size=300))
def test_mask_text_is_total_and_bounded(text: str) -> None:
    masked = mask_text(text)
    assert len(masked) <= VISIBLE_LIMIT


@given(st.text(max_size=200))
def test_interpret_url_is_total_and_never_leaks_outside_the_path(text: str) -> None:
    result = interpret_url(f"{text}?token={CANARY}")
    shown = result.masked() if isinstance(result, ParsedUrl) else result.masked_text
    assert CANARY not in shown


# --- Hueco de S-001-08 (b): barras iniciales antes de la autoridad -------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("//u:p@h.com/x", "//***@h.com/x"),
        ("///u:p@h.com/x", "///***@h.com/x"),
        ("https:///u:p@h.com/x", "https:///***@h.com/x"),
        ("https://////u:p@h.com/x?t=1", "https://////***@h.com/x?***"),
        ("ftp:////u:p@h.com", "ftp:////***@h.com"),
        ("//h.com/p@q", "//h.com/p@q"),  # el "@" de la ruta no es una credencial
    ],
)
def test_leading_slashes_do_not_hide_the_credentials_from_the_mask(
    text: str, expected: str
) -> None:
    assert mask_text(text) == expected


@pytest.mark.parametrize("text", [f"//{CANARY}@a.com/x", f"https:///{CANARY}:{CANARY}@a.com/"])
def test_leading_slashes_in_interpreted_urls_do_not_leak(text: str) -> None:
    result = invalid(text)
    assert result.reason is InvalidReason.I03
    assert CANARY not in result.masked_text
    assert CANARY not in repr(result)
