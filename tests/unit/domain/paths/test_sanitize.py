"""Saneado de nombres (RN-014, RN-015; CA-001-58, 63 a 67; ejemplos 7 a 10, 16, 17, 23, 31 a 34)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.paths.sanitize import (
    INVALID_CHARS,
    INVISIBLE_CHARS,
    RESERVED_NAMES,
    protect_reserved,
    remove_invisible,
    replace_invalid,
    sanitize_folder,
    sanitize_name,
    strip_trailing,
)
from downloader.domain.text import windows_fold

# --- RN-014 a: caracteres invisibles (CA-001-63, AB-16) -----------------------------------------

# Glosario 2.4, escrito a mano: U+00AD, U+061C, U+200B-U+200F, U+202A-U+202E, U+2060-U+2064,
# U+2066-U+2069 y U+FEFF.
GLOSSARY_INVISIBLES = [
    0xAD,
    0x61C,
    0xFEFF,
    *range(0x200B, 0x2010),
    *range(0x202A, 0x202F),
    *range(0x2060, 0x2065),
    *range(0x2066, 0x206A),
]


def test_invisible_table_matches_the_glossary() -> None:
    assert {ord(char) for char in INVISIBLE_CHARS} == set(GLOSSARY_INVISIBLES)
    assert len(INVISIBLE_CHARS) == 3 + 5 + 5 + 5 + 4  # 22


@pytest.mark.parametrize("code", GLOSSARY_INVISIBLES)
def test_each_invisible_character_is_removed(code: int) -> None:
    assert remove_invisible(f"a{chr(code)}b") == "ab"
    assert sanitize_name(f"a{chr(code)}b.txt") == "ab.txt"


def test_right_to_left_override_cannot_fake_an_extension() -> None:
    """Ejemplo 17: ``factura\\u202efdp.exe`` queda ``facturafdp.exe``."""
    assert sanitize_name("factura\u202efdp.exe") == "facturafdp.exe"


def test_the_unassigned_neighbours_of_the_ranges_are_kept() -> None:
    for code in (0xAC, 0xAE, 0x61B, 0x61D, 0x2010, 0x2029, 0x202F, 0x205F, 0x2065, 0x206A, 0xFEFE):
        assert remove_invisible(chr(code)) == chr(code), hex(code)


# --- RN-014 b: caracteres no válidos (CA-001-64) -------------------------------------------------


@pytest.mark.parametrize("char", list('<>:"/\\|?*'))
def test_each_windows_invalid_character_becomes_underscore(char: str) -> None:
    assert replace_invalid(f"a{char}b") == "a_b"


@pytest.mark.parametrize("code", range(0x20))
def test_each_control_character_becomes_underscore(code: int) -> None:
    assert replace_invalid(f"a{chr(code)}b") == "a_b"


def test_invalid_table_has_exactly_the_nine_characters() -> None:
    assert set('<>:"/\\|?*')


def test_space_and_del_and_high_controls_are_not_replaced() -> None:
    """La spec solo lista U+0000-U+001F: el espacio (U+0020) y U+007F no se tocan."""
    assert replace_invalid("a b\x7fc\x85") == "a b\x7fc\x85"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a:b", "a_b"),  # ejemplo 9
        ('c*d"', "c_d_"),  # ejemplo 9
        ("a/b", "a_b"),  # ejemplo 37: la "/" decodificada es un carácter
        ("a\\..\\..\\b.txt", "a_.._.._b.txt"),  # ejemplo 7
        ("a\x00b.pdf", "a_b.pdf"),  # ejemplo 38
        ("[::1]", "[__1]"),  # ejemplo 23: se conservan los corchetes
        ("C:", "C_"),  # CA-001-60
        ("../", ".._"),  # CA-001-59
    ],
)
def test_invalid_characters_in_context(text: str, expected: str) -> None:
    assert sanitize_name(text) == expected


# --- RN-014 c y d: puntos y espacios finales, nombre vacío (CA-001-58, 65) -----------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("carpeta.", "carpeta"),  # ejemplo 10
        ("archivo .txt ", "archivo .txt"),  # ejemplo 10
        ("a. . .", "a"),
        ("a...", "a"),
        ("a  ", "a"),
        ("a .b", "a .b"),  # solo el final
        (" a", " a"),  # los espacios iniciales no se tocan
        (".htaccess", ".htaccess"),  # CA-001-67
    ],
)
def test_trailing_dots_and_spaces(text: str, expected: str) -> None:
    assert strip_trailing(text) == expected
    assert sanitize_name(text) == expected


@pytest.mark.parametrize("text", ["", ".", "..", "...", ".. ", " ..", " "])
def test_names_that_end_up_empty(text: str) -> None:
    """CA-001-58: ``.. ``, ``...``, `` ..`` y ``.. `` no son ``.`` ni ``..``: quedan vacíos."""
    assert sanitize_name(text) == ""


@pytest.mark.parametrize("text", ["", ".", "..", "...", ".. ", " ..", " ", "\u200b", "\u202e. "])
def test_empty_folder_becomes_underscore(text: str) -> None:
    assert sanitize_folder(text) == "_"


def test_a_name_with_content_is_not_replaced_by_underscore() -> None:
    assert sanitize_folder("docs") == "docs"


def test_invisibles_are_removed_before_trailing_dots() -> None:
    """RN-014 a precede a c: ``a`` + invisible + ``.`` queda ``a``."""
    assert sanitize_name("a\u200b.") == "a"


# --- RN-015: nombres reservados (CA-001-66, 67) --------------------------------------------------

# Glosario 2.5, escrito a mano.
GLOSSARY_RESERVED = [
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{n}" for n in "0123456789"),
    *(f"LPT{n}" for n in "0123456789"),
    "COM¹",
    "COM²",
    "COM³",
    "LPT¹",
    "LPT²",
    "LPT³",
    "CONIN$",
    "CONOUT$",
    "CLOCK$",
]


def test_reserved_table_matches_the_glossary() -> None:
    assert set(GLOSSARY_RESERVED) == RESERVED_NAMES
    assert len(RESERVED_NAMES) == 33


@pytest.mark.parametrize("name", GLOSSARY_RESERVED)
@pytest.mark.parametrize("case", [str.upper, str.lower, str.capitalize])
def test_every_reserved_name_gets_an_underscore(name: str, case: Callable[[str], str]) -> None:
    written = case(name)
    assert protect_reserved(written) == f"{written}_"  # solo
    assert protect_reserved(f"{written}.txt") == f"{written}_.txt"  # una extensión
    assert protect_reserved(f"{written}.tar.gz") == f"{written}_.tar.gz"  # varias
    assert protect_reserved(f"{written} .txt") == f"{written}_ .txt"  # espacios antes del punto
    assert protect_reserved(f"{written}   .a.b") == f"{written}_   .a.b"
    assert sanitize_name(f"{written}.txt") == f"{written}_.txt"
    assert sanitize_folder(written) == f"{written}_"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("CON", "CON_"),  # ejemplo 8
        ("aux.txt", "aux_.txt"),  # ejemplo 8
        ("CON.pdf", "CON_.pdf"),  # ejemplo 16
        ("con.tar.gz", "con_.tar.gz"),  # ejemplo 31
        ("nul.com", "nul_.com"),  # ejemplo 32 (primera etiqueta del dominio)
        ("con .txt", "con_ .txt"),  # ejemplo 33
        ("CONIN$", "CONIN$_"),  # ejemplo 34
    ],
)
def test_reserved_names_in_annex_examples(text: str, expected: str) -> None:
    assert sanitize_name(text) == expected


@pytest.mark.parametrize(
    "text", ["CONSOLA.txt", "micon.txt", "COM10.txt", ".htaccess", "LPT10", "COM"]
)
def test_names_that_only_look_reserved_are_kept(text: str) -> None:
    """CA-001-67."""
    assert protect_reserved(text) == text
    assert sanitize_name(text) == text


def test_reserved_name_hidden_behind_trailing_dots_and_invisibles() -> None:
    assert sanitize_name("con.") == "con_"
    assert sanitize_name("con. .") == "con_"
    assert sanitize_name("c\u200bon.txt") == "con_.txt"
    assert sanitize_name("NUL:") == "NUL_"  # ":" pasa a "_": el resultado ya no es reservado
    assert sanitize_name("con\x00.txt") == "con_.txt"


def test_reserved_comparison_ignores_case_like_windows() -> None:
    assert windows_fold("con") == windows_fold("CON")
    assert protect_reserved("Con") == "Con_"
    assert protect_reserved("cOnIn$") == "cOnIn$_"


def test_reserved_name_is_only_judged_before_the_first_dot() -> None:
    assert protect_reserved("a.con") == "a.con"
    assert protect_reserved("x.nul.txt") == "x.nul.txt"


# --- Propiedades: invariantes S-001-13 (3), (4) y (5) -------------------------------------------

# Cualquier carácter, incluidos los sustitutos sueltos (la función debe ser total).
ANY_CHARS = st.characters(blacklist_categories=())
HOSTILE_PIECES = st.sampled_from(
    ["con", "CON", "nul", "Aux", "COM1", "lpt²", "CONIN$", ".", "..", " ", "\u200b", "\u202e",
     "a", "x", "txt", ":", "\\", "/", "\x00", "$", "*"]
)  # fmt: skip
NAMES = st.one_of(
    st.text(alphabet=ANY_CHARS),
    st.lists(HOSTILE_PIECES, max_size=8).map("".join),
)


@given(NAMES)
def test_sanitized_name_meets_the_path_invariants(text: str) -> None:
    result = sanitize_name(text)
    assert not any(char in INVALID_CHARS for char in result)
    assert not any(ord(char) < 0x20 for char in result)
    assert not any(char in INVISIBLE_CHARS for char in result)
    assert not result.endswith((".", " "))
    head = result.partition(".")[0].rstrip(" ")
    assert windows_fold(head) not in RESERVED_NAMES


@given(NAMES)
def test_sanitized_folder_is_never_empty_dot_or_dotdot(text: str) -> None:
    result = sanitize_folder(text)
    assert result not in {"", ".", ".."}
    assert sanitize_name(result) == result


@given(NAMES)
def test_sanitizing_twice_changes_nothing(text: str) -> None:
    once = sanitize_name(text)
    assert sanitize_name(once) == once
    assert sanitize_folder(sanitize_folder(text)) == sanitize_folder(text)


@given(NAMES)
def test_sanitizing_never_grows_by_more_than_one_character(text: str) -> None:
    """Solo RN-015 añade, y añade un único carácter."""
    assert len(sanitize_name(text)) <= len(text) + 1
