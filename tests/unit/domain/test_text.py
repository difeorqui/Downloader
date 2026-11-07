"""Utilidades de texto: S-001-02 (longitudes UTF-16) y S-001-03 (mayusculas como Windows)."""

from __future__ import annotations

import pytest

from downloader.domain.text import trim_blanks, utf16_len, windows_fold

# --- windows_fold (S-001-03) -------------------------------------------------------------------


def test_sharp_s_is_not_equal_to_ss() -> None:
    assert windows_fold("ß") != windows_fold("ss")
    assert windows_fold("ß") == "ß"


def test_accented_letters_ignore_case() -> None:
    assert windows_fold("Á") == windows_fold("á")
    assert windows_fold("ñ") == windows_fold("Ñ")
    assert windows_fold("á") == "Á"


def test_ascii_ignores_case() -> None:
    assert windows_fold("CON") == windows_fold("con") == windows_fold("Con")
    assert windows_fold("A.pdf") == windows_fold("a.PDF")


def test_greek_and_cyrillic_ignore_case() -> None:
    assert windows_fold("\u03c3") == windows_fold("\u03a3")
    assert windows_fold("привет") == windows_fold("ПРИВЕТ")


@pytest.mark.parametrize("char", ["ŉ", "ǰ", "ΐ", "ᾳ", "ﬁ", "ﬃ"])
def test_characters_whose_uppercase_is_several_characters_stay_as_is(char: str) -> None:
    # Python da mas de un caracter; Windows aplica mayuscula simple y no los une con otros.
    assert windows_fold(char) == char


def test_characters_outside_the_basic_plane_are_not_folded() -> None:
    # NTFS solo tiene tabla de mayusculas para el plano basico.
    assert windows_fold("\U00010428") == "\U00010428"  # letra deseret minuscula
    assert windows_fold("\U0001f600") == "\U0001f600"


def test_fold_is_idempotent_and_keeps_length_in_code_points() -> None:
    text = "Informe Ñandú ß ŉ \U0001f600.TXT"
    folded = windows_fold(text)
    assert windows_fold(folded) == folded
    assert len(folded) == len(text)


def test_fold_of_empty_text() -> None:
    assert windows_fold("") == ""


def test_fold_keeps_lone_surrogates() -> None:
    assert windows_fold("a\ud800b") == "A\ud800B"


# --- utf16_len (S-001-02) ----------------------------------------------------------------------


def test_utf16_length_of_ascii_and_basic_plane() -> None:
    assert utf16_len("") == 0
    assert utf16_len("abc") == 3
    assert utf16_len("añ€") == 3


def test_emoji_counts_as_two() -> None:
    assert utf16_len("\U0001f600") == 2
    assert utf16_len("a\U0001f600b") == 4
    assert utf16_len("\U00010428") == 2


def test_lone_surrogate_counts_as_one_and_does_not_raise() -> None:
    assert utf16_len("\ud800") == 1


def test_utf16_length_matches_encoding_for_valid_text() -> None:
    text = "Bogotá \U0001f600 ｱ \U00020000"
    assert utf16_len(text) == len(text.encode("utf-16-le")) // 2


# --- trim_blanks (RN-002) ----------------------------------------------------------------------


def test_trim_blanks_removes_spaces_and_tabs_only_at_the_ends() -> None:
    assert trim_blanks("  \thttps://a.com/x \t ") == "https://a.com/x"
    assert trim_blanks("a b\tc") == "a b\tc"
    assert trim_blanks(" \t ") == ""
    assert trim_blanks("") == ""


def test_trim_blanks_keeps_other_whitespace() -> None:
    # RN-002 habla de espacios y tabulaciones; no se tocan otros blancos (NBSP, \x0b...)
    assert trim_blanks("\u00a0a\u00a0") == "\u00a0a\u00a0"
    assert trim_blanks("\x0ba\x0b") == "\x0ba\x0b"
