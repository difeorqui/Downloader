"""Codificación (RN-001 paso 8; CA-001-17 a 19) y decodificación única (RN-011, D-04)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.urls.encoding import (
    backslashes_to_slashes,
    decode_segment,
    encode_url_part,
)

# --- Codificación (CA-001-17, 18, 19) -----------------------------------------------------------


@pytest.mark.parametrize(
    ("char", "expected"),
    [
        (" ", "%20"),
        ('"', "%22"),
        ("<", "%3C"),
        (">", "%3E"),
        ("`", "%60"),
        ("{", "%7B"),
        ("}", "%7D"),
        ("|", "%7C"),
        ("^", "%5E"),
    ],
)
def test_each_listed_character_is_encoded(char: str, expected: str) -> None:
    """CA-001-17."""
    assert encode_url_part(f"a{char}b") == f"a{expected}b"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ñ", "%C3%B1"),
        ("á", "%C3%A1"),
        ("\U0001f600", "%F0%9F%98%80"),  # emoji
        ("año 2024.pdf", "a%C3%B1o%202024.pdf"),  # ejemplo de RN-001 paso 8 y ejemplo 41
        ("Informe Final/año 2024.pdf", "Informe%20Final/a%C3%B1o%202024.pdf"),
    ],
)
def test_non_ascii_is_encoded_as_utf8(text: str, expected: str) -> None:
    """CA-001-18."""
    assert encode_url_part(text) == expected


def test_backslash_in_query_and_fragment_becomes_percent_5c() -> None:
    """CA-001-19: en parámetros y fragmento."""
    assert encode_url_part("a\\b") == "a%5Cb"


def test_backslash_in_path_becomes_slash_before_encoding() -> None:
    """CA-001-19 y ejemplo 6: en la ruta, cada ``\\`` es ``/`` (RN-001 paso 7)."""
    assert backslashes_to_slashes("/a\\..\\..\\b.txt") == "/a/../../b.txt"
    assert backslashes_to_slashes("/sin/barras") == "/sin/barras"


@pytest.mark.parametrize(
    "text",
    [
        "/docs/2024/informe.pdf",
        "a%20b",
        "a%2e%2e",
        "%252e",
        "x=1&y=2",
        "A-Z_a-z.0~9!$&'()*+,;=:@/?[]",
    ],
)
def test_characters_not_listed_are_left_alone(text: str) -> None:
    assert encode_url_part(text) == text


def test_existing_valid_escapes_are_never_encoded_again() -> None:
    """CA-001-20: ``%20``, ``%2F`` y ``%25`` ya codificados no se tocan."""
    assert encode_url_part("a%C3%B1o") == "a%C3%B1o"
    for sequence in ("%20", "%2F", "%2f", "%25", "%00", "%aF"):
        assert encode_url_part(f"a{sequence}b") == f"a{sequence}b"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a%zz", "a%25zz"),  # CA-001-21 y S-001-11
        ("a%", "a%25"),
        ("a%2", "a%252"),
        ("100% seguro", "100%25%20seguro"),
        ("%", "%25"),
        ("%%", "%25%25"),
        ("%%41", "%25%41"),  # el primero es suelto; el segundo ya es una secuencia
        ("%4%41", "%254%41"),
        ("%g1", "%25g1"),
        ("%1g", "%251g"),
        ("%é", "%25%C3%A9"),  # lo que sigue es una letra no ASCII: no son cifras
    ],
)
def test_percent_without_two_hex_digits_is_encoded_as_25(text: str, expected: str) -> None:
    assert encode_url_part(text) == expected


def test_hex_digits_are_written_in_uppercase() -> None:
    assert encode_url_part("é") == "%C3%A9"
    assert encode_url_part("{") == "%7B"


@pytest.mark.parametrize("code", [*range(0x20), 0x7F])
def test_control_characters_are_encoded_so_they_never_reach_the_request(code: int) -> None:
    """Defensa en profundidad: ni CR ni LF ni NUL crudos en la URL procesada."""
    assert encode_url_part(f"a{chr(code)}b") == f"a%{code:02X}b"


def test_lone_surrogate_is_encoded_as_replacement_character() -> None:
    assert encode_url_part("a\ud800b") == "a%EF%BF%BDb"


def test_encoding_is_idempotent_on_its_own_output() -> None:
    text = 'año "2024" <x> {y} |z| ^w^ `v` \\ \U0001f600'
    once = encode_url_part(text)
    assert encode_url_part(once) == once
    assert once.isascii()


# --- Decodificación única (RN-011, D-04) --------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Informe%20A%C3%B1o", "Informe Año"),  # RN-011
        ("Bogot%C3%A1.pdf", "Bogotá.pdf"),  # ejemplo 11
        ("a%2Fb", "a/b"),  # ejemplo 37: "/" decodificada es un carácter
        ("a%2fb", "a/b"),
        ("a%5Cb", "a\\b"),  # ejemplo 7
        ("a%3Ab", "a:b"),  # ejemplo 9
        ("c%2Ad%22", 'c*d"'),  # ejemplo 9
        ("a%00b.pdf", "a\x00b.pdf"),  # ejemplo 38: el saneado lo vuelve "_" después
        ("%2e%2e", ".."),
        ("%2e%2e%2f", "../"),  # CA-001-59
        ("%F0%9F%98%80", "\U0001f600"),
        ("sin porcentaje.txt", "sin porcentaje.txt"),
        ("", ""),
    ],
)
def test_valid_sequences_are_decoded_once(text: str, expected: str) -> None:
    assert decode_segment(text) == expected


def test_double_encoding_is_decoded_a_single_time() -> None:
    """Ejemplo 39: ``%252e%252e`` queda ``%2e%2e`` y no ``..``."""
    assert decode_segment("%252e%252e") == "%2e%2e"
    assert decode_segment(decode_segment("%252e")) == "."  # solo la segunda pasada lo decodificaría


@pytest.mark.parametrize(
    "text",
    [
        "%C3",  # byte de inicio suelto
        "a%C3",
        "%C3A",  # inicio seguido de un carácter normal
        "%80",  # continuación suelta
        "%E2%82",  # secuencia truncada
        "%C0%AF",  # sobrelarga de "/"
        "%ED%A0%80",  # sustituto codificado
        "%FF",
        "%c3",  # se conserva la grafía original
    ],
)
def test_invalid_utf8_keeps_its_percent_sequences(text: str) -> None:
    assert decode_segment(text) == text


def test_only_the_undecodable_bytes_keep_their_percent() -> None:
    """D-04: por secuencia, no por segmento entero."""
    assert decode_segment("a%C3%B1%FFb%20c") == "añ%FFb c"
    assert decode_segment("%C3%FF%C3%B1") == "%C3%FFñ"
    assert decode_segment("%e2%82%ac%c3") == "€%c3"  # minúsculas: se conservan en el trozo inválido


@pytest.mark.parametrize("text", ["100%", "%", "%z1", "%1", "%%20", "a%2", "%g0"])
def test_a_percent_without_two_hex_digits_is_a_plain_character(text: str) -> None:
    assert decode_segment(text) == text.replace("%20", " ")


def test_percent_followed_by_valid_escape() -> None:
    assert decode_segment("%%41") == "%A"


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="%")))
def test_encode_then_decode_returns_the_original(text: str) -> None:
    assert decode_segment(encode_url_part(text)) == text


@given(st.text(alphabet=st.characters(blacklist_categories=()), max_size=60))
def test_both_functions_are_total_and_encoding_yields_ascii(text: str) -> None:
    assert encode_url_part(text).isascii()
    decode_segment(text)  # no lanza


@given(st.text(alphabet="%0123456789abcdefABCDEFxz ", max_size=40))
def test_decoding_never_lengthens_the_text(text: str) -> None:
    """Cada ``%XX`` ocupa 3 caracteres y produce como máximo 1."""
    assert len(decode_segment(text)) <= len(text)
