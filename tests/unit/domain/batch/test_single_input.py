"""Campo de URL individual (RN-004 I-08; CA-001-12 y 16)."""

from __future__ import annotations

import pytest

from downloader.domain.batch.single_input import read_single_input
from downloader.domain.batch.source import SourceLine
from downloader.domain.catalog import InvalidReason
from downloader.domain.urls import InvalidUrl

CANARY = "CANARIO-5d1e"
NBSP = chr(0xA0)


@pytest.mark.parametrize(
    "text",
    ["", " ", "   ", "\t", " \t ", "\n", "\r\n", "\r", "\n\n\n", " \n\t\n  ", "\r\n \r \n"],
)
def test_ca_001_16_empty_or_blank_is_none(text: str) -> None:
    """Vacío o solo espacios: no se puede iniciar y no cuenta como inválida."""
    assert read_single_input(text) is None


def test_a_single_line_is_returned_trimmed() -> None:
    result = read_single_input("  https://sitio.com/a.pdf \t")
    assert result == SourceLine(1, "https://sitio.com/a.pdf")


@pytest.mark.parametrize(
    ("text", "number"),
    [
        ("\nhttps://a.com/x\n", 2),
        ("\n\n\nhttps://a.com/x", 4),
        ("https://a.com/x\n\n\n", 1),
        ("\r\n\r\n  https://a.com/x  \r\n\r\n", 3),
        ("\r\rhttps://a.com/x\r", 3),
        ("\n \t \nhttps://a.com/x\n \n", 3),
    ],
)
def test_ca_001_12_one_line_surrounded_by_blank_lines_is_accepted(text: str, number: int) -> None:
    assert read_single_input(text) == SourceLine(number, "https://a.com/x")


@pytest.mark.parametrize(
    "text",
    [
        "https://a.com/x\nhttps://b.com/y",
        "https://a.com/x\r\nhttps://b.com/y",
        "https://a.com/x\rhttps://b.com/y",
        "https://a.com/x\n\nhttps://b.com/y",  # una línea vacía en medio no cambia el resultado
        "\nhttps://a.com/x\nhttps://b.com/y\n",
        "a\nb",
        "https://a.com/x\n#comentario",  # en el campo individual no hay comentarios
        "https://a.com/x\n  y  ",
    ],
)
def test_ca_001_12_two_lines_with_content_is_i08(text: str) -> None:
    result = read_single_input(text)
    assert isinstance(result, InvalidUrl)
    assert result.reason is InvalidReason.I08


def test_i08_never_repeats_the_text() -> None:
    """S-001-08 c: ni el texto ni nada derivado de él."""
    result = read_single_input(f"https://a.com/x?t={CANARY}\nhttps://u:{CANARY}@b.com/y#{CANARY}")
    assert isinstance(result, InvalidUrl)
    assert result.masked_text == ""
    for shown in (result.masked_text, repr(result), str(result), result.reason.message):
        assert CANARY not in shown


def test_i08_message_is_the_catalog_text() -> None:
    result = read_single_input("a\nb")
    assert isinstance(result, InvalidUrl)
    assert result.reason.message == (
        "El campo admite una sola URL. Para varias, use un archivo masivo"
    )


def test_other_whitespace_is_content_not_blank() -> None:
    """Solo espacio y tabulación se recortan (RN-002): un espacio no separable es contenido."""
    assert read_single_input(NBSP) == SourceLine(1, NBSP)


@pytest.mark.parametrize("separator", [chr(0x85), chr(0x2028), chr(0x2029), chr(0x0B), chr(0x0C)])
def test_lines_are_never_split_at_other_separators(separator: str) -> None:
    """Solo CRLF, LF y CR son fin de línea (S-001-10): NEL, LS, PS, VT y FF no lo son."""
    text = f"https://a.com/x{separator}https://b.com/y"
    assert read_single_input(text) == SourceLine(1, text)


# --- RN-036: el texto crudo de una línea no se muestra --------------------------------------------


def test_source_line_repr_and_str_are_masked() -> None:
    """Regresión hallada por la propiedad P4: ``repr`` mostraba las credenciales de la línea."""
    line = SourceLine(3, f"https://u:{CANARY}@a.com/x?token={CANARY}#{CANARY}")
    for shown in (repr(line), str(line), f"{line}", f"{line!r}", repr([line]), repr((line,))):
        assert CANARY not in shown
    assert repr(line) == "SourceLine(number=3, text='https://***@a.com/x?***')"


def test_source_line_keeps_its_text_and_equality() -> None:
    line = SourceLine(1, "https://a.com/x?t=1")
    assert line.text == "https://a.com/x?t=1"
    assert line == SourceLine(1, "https://a.com/x?t=1")
    assert line != SourceLine(1, "https://a.com/x?t=2")
