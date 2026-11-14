"""Archivo masivo (RN-002, RN-003 a-g; CA-001-23 a 34; S-001-07, S-001-09, S-001-10)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.batch.file_decoder import (
    MAX_FILE_BYTES,
    MAX_URLS,
    BatchFileRejection,
    DecodedBatch,
    RejectionKind,
    decode_batch_file,
)
from downloader.domain.batch.source import SourceLine

BOM = b"\xef\xbb\xbf"


def decoded(content: bytes, name: str = "lista.txt") -> DecodedBatch:
    result = decode_batch_file(name, content)
    assert isinstance(result, DecodedBatch), result
    return result


def rejected(content: bytes, name: str = "lista.txt") -> BatchFileRejection:
    result = decode_batch_file(name, content)
    assert isinstance(result, BatchFileRejection), result
    return result


def texts(batch: DecodedBatch) -> list[str]:
    return [line.text for line in batch.lines]


# --- Extensión (CA-001-28) ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", ["a.txt", "a.TXT", "a.Txt", "a.csv.txt", "dir/a.txt", "C:\\x\\a.TXT"]
)
def test_ca_001_28_txt_names_are_accepted(name: str) -> None:
    assert texts(decoded(b"https://a.com/x", name)) == ["https://a.com/x"]


@pytest.mark.parametrize("name", ["a.csv", "a.CSV", "a.txt.csv", "C:\\datos\\lista.Csv"])
def test_ca_001_28_csv_has_its_own_message(name: str) -> None:
    result = rejected(b"https://a.com/x", name)
    assert result.kind is RejectionKind.CSV
    assert result.message == (
        "Los archivos .csv no se admiten. Guarde la lista como .txt, con una URL por línea."
    )


@pytest.mark.parametrize("name", ["a", "a.txt.exe", "a.docx", "", ".txt", "a.", ".", "a.tx", "txt"])
def test_ca_001_28_other_extensions(name: str) -> None:
    """``.txt`` sin nombre no tiene extensión (S-001-12) y ``txt`` sin punto tampoco."""
    result = rejected(b"https://a.com/x", name)
    assert result.kind is RejectionKind.NOT_TXT
    assert result.message == "Solo se admiten archivos .txt"


# --- BOM, fines de línea, comentarios (CA-001-23 a 25) -------------------------------------------


def test_ca_001_23_bom_makes_no_difference() -> None:
    body = b"https://a.com/x\nhttps://b.com/y\n"
    assert decoded(BOM + body) == decoded(body)
    assert decoded(BOM + body).lines[0] == SourceLine(1, "https://a.com/x")


def test_ca_001_24_mixed_line_endings_count_one_each() -> None:
    batch = decoded(b"uno\r\ndos\ntres\rcuatro\r\n\r\ncinco")
    assert [(line.number, line.text) for line in batch.lines] == [
        (1, "uno"),
        (2, "dos"),
        (3, "tres"),
        (4, "cuatro"),
        (6, "cinco"),
    ]
    assert batch.total_lines == 6


def test_a_lone_cr_and_a_crlf_are_not_double_counted() -> None:
    assert decoded(b"a\r\nb").total_lines == 2
    assert decoded(b"a\r\rb").total_lines == 3
    assert decoded(b"a\n\nb").total_lines == 3


def test_ca_001_25_blank_lines_and_comments_are_ignored() -> None:
    content = b"\n   \n\t\n# comentario\n  # otro\n\thttps://a.com/x  \n#\n"
    batch = decoded(content)
    assert batch.lines == (SourceLine(6, "https://a.com/x"),)
    assert batch.total_lines == 7


def test_lines_are_trimmed_of_spaces_and_tabs_only() -> None:
    batch = decoded(" \t https://a.com/x \t \n\xc2\xa0https://b.com/y".encode("latin-1"))
    assert batch.lines[0].text == "https://a.com/x"
    assert batch.lines[1].text.startswith(chr(0xA0))  # el espacio no separable es contenido


def test_a_trailing_line_break_does_not_add_a_line() -> None:
    """S-001-09."""
    assert decoded(b"a\nb\n").total_lines == 2
    assert decoded(b"a\nb").total_lines == 2
    assert decoded(b"a\n\n").total_lines == 2
    assert decoded(b"a\r\n").total_lines == 1


def test_a_hash_inside_a_line_is_not_a_comment() -> None:
    assert texts(decoded(b"https://a.com/x#frag\nhttps://b.com/#")) == [
        "https://a.com/x#frag",
        "https://b.com/#",
    ]


# --- Conteo (CA-001-26) --------------------------------------------------------------------------


def test_ca_001_26_ten_thousand_lines_are_accepted() -> None:
    content = b"\n".join(b"https://a.com/%d" % n for n in range(MAX_URLS))
    batch = decoded(content)
    assert len(batch.lines) == 10_000
    assert batch.total_lines == 10_000


def test_ca_001_26_ten_thousand_and_one_lines_are_rejected_with_the_exact_message() -> None:
    content = b"\n".join(b"https://a.com/%d" % n for n in range(MAX_URLS + 1))
    result = rejected(content)
    assert result.kind is RejectionKind.TOO_MANY_URLS
    assert result.message == "El archivo tiene 10.001 URLs; el máximo es 10.000."


def test_the_count_includes_duplicates_and_invalid_lines_but_not_comments_or_blanks() -> None:
    lines = [b"https://a.com/x"] * 6_000 + [b"basura!"] * 4_000 + [b"# c", b"", b"  "] * 100
    assert len(decoded(b"\n".join(lines)).lines) == 10_000
    assert rejected(b"\n".join([*lines, b"otra"])).kind is RejectionKind.TOO_MANY_URLS


def test_count_message_uses_thousands_dots() -> None:
    content = b"\n".join(b"u%d" % n for n in range(12_345))
    assert rejected(content).message == "El archivo tiene 12.345 URLs; el máximo es 10.000."


# --- Tamaño (CA-001-27) --------------------------------------------------------------------------


def test_ca_001_27_exactly_5_mb_is_accepted() -> None:
    line = b"https://a.com/" + b"x" * 985 + b"\n"  # 1 000 bytes
    content = line * 5242 + b"y" * 880
    assert len(content) == 5_242_880
    assert len(decoded(content).lines) == 5243


def test_ca_001_27_one_byte_over_is_rejected_with_the_exact_message() -> None:
    result = rejected(b"a" * (MAX_FILE_BYTES + 1))
    assert result.kind is RejectionKind.TOO_LARGE
    assert result.message == (
        "El archivo pesa 5,01 MB (5.242.881 bytes); el máximo es 5 MB (5.242.880 bytes)."
    )


def test_size_message_example_of_the_spec() -> None:
    result = rejected(b"a" * 5_252_345)
    assert result.message == (
        "El archivo pesa 5,01 MB (5.252.345 bytes); el máximo es 5 MB (5.242.880 bytes)."
    )


def test_size_message_for_a_much_larger_file() -> None:
    result = rejected(b"a" * (12 * 1024 * 1024))
    assert result.message == (
        "El archivo pesa 12,00 MB (12.582.912 bytes); el máximo es 5 MB (5.242.880 bytes)."
    )


# --- Codificación (CA-001-29 a 31, 33) ------------------------------------------------------------

UTF16_TEXT = "https://a.com/x\nhttps://b.com/y\n"
UTF16_MESSAGE = "El archivo está guardado en UTF-16. Guárdelo como UTF-8 e inténtelo de nuevo"


@pytest.mark.parametrize(
    "content",
    [
        UTF16_TEXT.encode("utf-16"),  # con marca, endianidad nativa (LE)
        UTF16_TEXT.encode("utf-16-le"),  # sin marca, con muchos nulos
        UTF16_TEXT.encode("utf-16-be"),
        b"\xfe\xff" + UTF16_TEXT.encode("utf-16-be"),
        b"\xff\xfe" + b"a\x00",
        b"\xff\xfe",  # solo la marca
        b"\xfe\xff",
        b"a" * 90 + b"\x00" * 10,  # exactamente el 10 % de nulos
        b"\x00" * 4096,
    ],
)
def test_ca_001_29_utf16_is_rejected_with_its_message(content: bytes) -> None:
    result = rejected(content)
    assert result.kind is RejectionKind.UTF16
    assert result.message == UTF16_MESSAGE


def test_ca_001_29_ratio_just_below_ten_percent_is_not_utf16() -> None:
    content = b"https://a.com/x" + b"\x00" * 1 + b"a" * 150
    assert decode_batch_file("a.txt", content).__class__ is DecodedBatch


def test_ca_001_29_null_ratio_is_measured_on_the_first_4_kb_only() -> None:
    head = b"a" * 4096
    assert isinstance(decode_batch_file("a.txt", head + b"\x00" * 4000), DecodedBatch)
    assert rejected(b"a" * 3000 + b"\x00" * 1096 + b"a" * 1000).kind is RejectionKind.UTF16


@pytest.mark.parametrize(
    "content",
    [
        b"\x00\x00\xfe\xff" + "a".encode("utf-32-be"),
        b"\xff\xfe\x00\x00" + "a".encode("utf-32-le"),
        "https://a.com/x\n".encode("utf-32"),
        b"\x00\x00\xfe\xff",
        b"\xff\xfe\x00\x00",
    ],
)
def test_ca_001_30_utf32_reports_line_1_and_not_utf16(content: bytes) -> None:
    result = rejected(content)
    assert result.kind is RejectionKind.INVALID_UTF8
    assert result.message == "El archivo no es texto UTF-8 válido (línea 1)"


@pytest.mark.parametrize(
    "bad",
    [
        b"\xc0\xaf",  # sobrelarga de "/"
        b"\xe0\x80\xaf",
        b"\xed\xa0\x80",  # sustituto U+D800
        b"\xed\xbf\xbf",  # sustituto U+DFFF
        b"\xf4\x90\x80\x80",  # mayor que U+10FFFF
        b"\xf8\x88\x80\x80\x80",
        b"\xe2\x82",  # secuencia truncada
        b"\xc3",  # byte de inicio suelto al final
        b"\x80",  # continuación suelta
        b"\xff",
        b"\xfe",
    ],
)
def test_ca_001_31_invalid_utf8_reports_the_line_even_in_a_comment(bad: bytes) -> None:
    lines = [
        b"https://a.com/1",
        b"",
        b"https://a.com/3",
        b"# c",
        b"https://a.com/5",
        b"x",
        b"# " + bad + b" fin",
    ]
    result = rejected(b"\n".join(lines))
    assert result.kind is RejectionKind.INVALID_UTF8
    assert result.message == "El archivo no es texto UTF-8 válido (línea 7)"


def test_ca_001_31_line_numbers_count_every_kind_of_line_break() -> None:
    result = rejected(b"a\r\nb\rc\n\xff")
    assert result.message.endswith("(línea 4)")
    assert rejected(b"\r\r\r\xff").message.endswith("(línea 4)")
    assert rejected(b"\xffx").message.endswith("(línea 1)")


def test_ca_001_31_the_bom_does_not_shift_the_line() -> None:
    assert rejected(BOM + b"a\n\xff").message.endswith("(línea 2)")


def test_ca_001_33_a_single_null_byte_does_not_reject_the_file() -> None:
    batch = decoded(b"https://a.com/x\nhttps://a.com/a\x00b\nhttps://b.com/y")
    assert len(batch.lines) == 3
    assert batch.lines[1].text == "https://a.com/a\x00b"  # esa línea será I-03 al interpretarla


# --- Sin URLs (CA-001-32) ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [b"", b"\n", b"\r\n\r\n", b"   \n\t\n", b"# solo\n# comentarios\n", BOM, BOM + b"\n#", b" # x"],
)
def test_ca_001_32_nothing_to_download(content: bytes) -> None:
    result = rejected(content)
    assert result.kind is RejectionKind.NO_URLS
    assert result.message == "El archivo no contiene URLs"


# --- Orden de rechazos (CA-001-34, S-001-07) ---------------------------------------------------


def test_ca_001_34_csv_beats_every_other_problem() -> None:
    content = (b"a\n" * 12_000).ljust(MAX_FILE_BYTES + 100, b"\x00")
    assert rejected(content, "datos.csv").kind is RejectionKind.CSV


def test_extension_beats_size_beats_encoding() -> None:
    big_utf16 = b"\xff\xfe" + b"a\x00" * (MAX_FILE_BYTES // 2 + 10)
    assert rejected(big_utf16, "a.docx").kind is RejectionKind.NOT_TXT
    assert rejected(big_utf16, "a.txt").kind is RejectionKind.TOO_LARGE


def test_utf32_beats_utf16_beats_utf8() -> None:
    assert rejected(b"\xff\xfe\x00\x00\xff").kind is RejectionKind.INVALID_UTF8
    assert rejected(b"\xff\xfe\xff\xff").kind is RejectionKind.UTF16
    assert rejected(b"\xc3\x28" + b"\x00" * 5).kind is RejectionKind.UTF16  # >= 10 % de nulos


def test_utf8_problem_beats_the_empty_and_count_checks() -> None:
    assert rejected(b"# solo\n\xff").kind is RejectionKind.INVALID_UTF8
    content = b"\n".join([b"u"] * 10_001) + b"\n\xff"
    assert rejected(content).kind is RejectionKind.INVALID_UTF8


# --- Propiedades -------------------------------------------------------------------------------


@given(st.binary(max_size=300), st.sampled_from(["a.txt", "a.csv", "a.docx", "", "x.TXT"]))
def test_decoding_is_total_and_every_outcome_is_well_formed(content: bytes, name: str) -> None:
    result = decode_batch_file(name, content)
    if isinstance(result, BatchFileRejection):
        assert result.message
    else:
        assert result.lines
        assert result.total_lines >= result.lines[-1].number
        numbers = [line.number for line in result.lines]
        assert numbers == sorted(set(numbers))
        assert all(line.text == line.text.strip(" \t") and line.text for line in result.lines)
        assert not any(line.text.startswith("#") for line in result.lines)


@given(
    st.lists(st.text(alphabet="abc# \t", max_size=8), max_size=20),
    st.sampled_from(["\n", "\r\n", "\r"]),
)
def test_line_endings_do_not_change_what_is_read(rows: list[str], ending: str) -> None:
    unix = decode_batch_file("a.txt", "\n".join(rows).encode())
    other = decode_batch_file("a.txt", ending.join(rows).encode())
    assert unix == other
