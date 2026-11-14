"""Longitud de nombres y rutas (RN-016, S-001-02; CA-001-70 a 79, con límites exactos +/-1)."""

from __future__ import annotations

import pytest

from downloader.domain.catalog import FailureCode
from downloader.domain.paths.length import (
    MAX_COMPONENT_LENGTH,
    TEMP_NAME_LENGTH,
    PathLimits,
    check_path_lengths,
)

SHORT = PathLimits(long_paths_enabled=False)
LONG = PathLimits(long_paths_enabled=True)
DESTINATION = "D:\\Descargas"  # 12 caracteres
EMOJI = chr(0x1F600)  # cuenta 2 unidades UTF-16


def check(segment_length: int, file_name: str, limits: PathLimits) -> FailureCode | None:
    """Carpeta ``D:\\Descargas\\sitio.com\\<s>``, que mide ``12 + 1 + 9 + 1 + s = 23 + s``."""
    folder_parts = ("sitio.com", "s" * segment_length)
    folder_path = "\\".join((DESTINATION, *folder_parts))
    return check_path_lengths(folder_path, folder_parts, file_name, limits)


def name_of(length: int) -> str:
    return "n" * length


def folder_of_length(total: int) -> tuple[str, list[str]]:
    """Carpeta ``D:\\...`` de exactamente ``total`` caracteres con componentes de <= 255."""
    segment = 100
    remaining = total - len("D:")
    parts = ["p" * segment for _ in range(remaining // (segment + 1))]
    rest = remaining % (segment + 1)
    if rest == 1:  # no existe un segmento de longitud 0: se alarga el primero
        parts[0] += "p"
    elif rest > 1:
        parts.append("p" * (rest - 1))
    folder = "\\".join(("D:", *parts))
    assert len(folder) == total
    assert all(len(part) <= MAX_COMPONENT_LENGTH for part in parts)
    return folder, parts


def test_the_reference_folder_measures_23_plus_s() -> None:
    assert len("\\".join((DESTINATION, "sitio.com", "s" * 175))) == 23 + 175


def test_temp_name_is_53_characters() -> None:
    assert TEMP_NAME_LENGTH == len("~descargador-") + 32 + len(".parcial") == 53


# --- Sin rutas largas: 259 (CA-001-70 a 75) ------------------------------------------------------


def test_ca_001_70_final_259_is_accepted() -> None:
    assert check(175, name_of(60), SHORT) is None  # carpeta 198 + 1 + 60 = 259


def test_ca_001_71_final_260_is_f25() -> None:
    assert check(176, name_of(60), SHORT) is FailureCode.F25


def test_ca_001_72_temp_259_is_accepted_although_the_final_is_shorter() -> None:
    assert check(182, "a.pdf", SHORT) is None  # temporal 205 + 1 + 53 = 259; final 211


def test_ca_001_73_temp_260_is_f25_although_the_final_fits() -> None:
    assert check(183, "a.pdf", SHORT) is FailureCode.F25  # el final mide 212


def test_ca_001_74_collision_suffix_is_part_of_the_measure() -> None:
    assert check(175, name_of(60), SHORT) is None
    assert check(175, name_of(64), SHORT) is FailureCode.F25  # " (1)" lo lleva a 64: 263


def test_ca_001_75_name_of_exactly_53_both_paths_are_equal() -> None:
    assert check(182, name_of(53), SHORT) is None  # 259
    assert check(183, name_of(53), SHORT) is FailureCode.F25  # 260


def test_a_folder_of_205_always_admits_its_temp_and_206_never_does() -> None:
    """RN-016: sin rutas largas la carpeta que contiene el archivo no puede superar 205."""
    assert check(182, "a", SHORT) is None
    assert check(183, "a", SHORT) is FailureCode.F25


@pytest.mark.parametrize("name_length", [1, 10, 52, 53, 54, 60])
def test_the_longest_of_the_two_paths_decides(name_length: int) -> None:
    longest = max(name_length, 53)
    fits_segment = 259 - 23 - 1 - longest
    assert check(fits_segment, name_of(name_length), SHORT) is None
    assert check(fits_segment + 1, name_of(name_length), SHORT) is FailureCode.F25


# --- Con rutas largas: componentes de 255 y ruta de 32 000 (CA-001-76 a 79) ----------------------


def test_ca_001_76_file_name_of_255_and_256() -> None:
    assert check(5, name_of(255), LONG) is None
    assert check(5, name_of(256), LONG) is FailureCode.F28


def test_ca_001_77_folder_segment_of_255_and_256() -> None:
    assert check(255, "a.pdf", LONG) is None
    assert check(256, "a.pdf", LONG) is FailureCode.F28


def test_ca_001_78_final_path_of_32000_and_32001() -> None:
    name = name_of(60)
    folder, parts = folder_of_length(32_000 - 1 - len(name))
    assert check_path_lengths(folder, parts, name, LONG) is None  # 32 000
    folder, parts = folder_of_length(32_000 - len(name))
    assert check_path_lengths(folder, parts, name, LONG) is FailureCode.F25  # 32 001


def test_ca_001_79_temp_path_of_32001_is_f25_and_32000_is_accepted() -> None:
    folder, parts = folder_of_length(31_947)  # + 1 + 53 = 32 001
    assert check_path_lengths(folder, parts, "a.pdf", LONG) is FailureCode.F25
    folder, parts = folder_of_length(31_946)  # + 1 + 53 = 32 000
    assert check_path_lengths(folder, parts, "a.pdf", LONG) is None


def test_long_paths_still_cap_every_component_at_255() -> None:
    assert check(255, name_of(255), LONG) is None
    assert check(256, name_of(255), LONG) is FailureCode.F28
    assert check(255, name_of(256), LONG) is FailureCode.F28


def test_without_long_paths_a_component_over_255_is_f28_not_f25() -> None:
    """F-28 antes que F-25 (S-001-07): estos nombres también harían pasar los 259."""
    assert check(1, name_of(256), SHORT) is FailureCode.F28
    assert check(256, "a.pdf", SHORT) is FailureCode.F28


# --- Se miden unidades UTF-16 (S-001-02) ---------------------------------------------------------


def test_an_emoji_counts_as_two_characters_in_a_component() -> None:
    assert check(5, EMOJI * 127 + "a", LONG) is None  # 127 * 2 + 1 = 255
    assert check(5, EMOJI * 128, LONG) is FailureCode.F28  # 256
    assert check(5, EMOJI * 127 + "ab", LONG) is FailureCode.F28  # 256


def test_an_emoji_counts_as_two_characters_in_the_path() -> None:
    """Con ``len()`` de Python este caso se aceptaría; con UTF-16 la carpeta mide 206."""
    k, rest = 50, 83
    folder_parts = ("sitio.com", EMOJI * k + "x" * rest)
    folder = "\\".join((DESTINATION, *folder_parts))
    assert len(folder) == 23 + k + rest == 156  # lo que contaría Python
    assert check_path_lengths(folder, folder_parts, "a.pdf", SHORT) is FailureCode.F25
    folder_parts = ("sitio.com", EMOJI * k + "x" * (rest - 1))  # UTF-16: 205
    folder = "\\".join((DESTINATION, *folder_parts))
    assert check_path_lengths(folder, folder_parts, "a.pdf", SHORT) is None


def test_limits_object() -> None:
    assert SHORT.max_path_length == 259
    assert LONG.max_path_length == 32_000


def test_a_normal_download_is_fine() -> None:
    folder_parts = ("sitio.com", "docs")
    folder = "D:\\Descargas\\sitio.com\\docs"
    assert check_path_lengths(folder, folder_parts, "informe.pdf", SHORT) is None
