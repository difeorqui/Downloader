"""Propiedades y fuzz del dominio (RNF-001-05, CA-001-50, 62 y 111; plan §7).

Perfil ``dev`` (2 000 ejemplos) en la batería normal y perfil ``ci`` (100 000) con
``pytest -m fuzz --hypothesis-profile=ci``. La semilla es fija y queda registrada
(``strategies.SEED``): cualquier fallo se reproduce con ``--hypothesis-seed``.

Propiedades: (1) 0 excepciones; (2) toda salida es una ruta dentro del destino con componentes
seguros (oráculo S-001-13) o un código del catálogo, y en un lote ninguna ruta coincide con otra;
(3) idempotencia del analizador; (4) el canario no aparece en ninguna salida salvo ``processed()``;
(5) determinismo.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import HealthCheck, given, seed, settings
from hypothesis import strategies as st

from downloader.domain.batch.file_decoder import decode_batch_file
from downloader.domain.batch.single_input import read_single_input
from downloader.domain.batch.source import SourceLine
from downloader.domain.batch.validator import BatchValidation, validate_batch
from downloader.domain.catalog import FailureCode
from downloader.domain.paths.collisions import EntryKind, InMemoryDiskEntries, PathReservations
from downloader.domain.paths.failure import PathFailure
from downloader.domain.paths.length import TEMP_NAME_LENGTH, PathLimits
from downloader.domain.paths.response import ServerResponse
from downloader.domain.paths.sanitize import INVALID_CHARS, INVISIBLE_CHARS, RESERVED_NAMES
from downloader.domain.paths.target import PathEnvironment, TargetPath, compute_target_path
from downloader.domain.result import Ok
from downloader.domain.text import utf16_len, windows_fold
from downloader.domain.urls import InvalidUrl, ParsedUrl, interpret_url, mask_text
from downloader.domain.urls.parser import parse_url
from tests.property.strategies import (
    CANARY,
    CANARY_URLS,
    COLLIDING_URLS,
    DISK_STATES,
    HOSTILE_URLS,
    RESPONSES,
    SEED,
)

pytestmark = pytest.mark.fuzz

DESTINATION = "D:\\Descargas"
CATALOG_CODES = {FailureCode.F24, FailureCode.F25, FailureCode.F27, FailureCode.F28}
COMMON = settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
LIMITS = st.booleans().map(PathLimits)


def assert_safe_target(result: TargetPath, limits: PathLimits) -> None:
    """Oráculo independiente: los invariantes de S-001-13, sin usar el código bajo prueba."""
    full = result.full_path
    assert full.startswith(DESTINATION + "\\")  # (1)
    tail = full[len(DESTINATION) + 1 :]
    components = tail.split("\\")
    assert components == [*result.folder_parts, result.file_name]
    for component in components:
        assert component not in {"", ".", ".."}  # (2)
        assert not set(component) & (INVALID_CHARS | INVISIBLE_CHARS)  # (3)
        assert not any(ord(char) < 0x20 for char in component)
        assert not component.endswith((".", " "))  # (4)
        assert windows_fold(component.partition(".")[0].rstrip(" ")) not in RESERVED_NAMES  # (5)
        assert utf16_len(component) <= 255  # (6)
    assert ":" not in tail and not tail.startswith("\\")  # (7) sin otra unidad ni prefijo de red
    folder = full[: -(len(result.file_name) + 1)]
    longest = max(utf16_len(full), utf16_len(folder) + 1 + TEMP_NAME_LENGTH)
    assert longest <= limits.max_path_length  # (8)


def run_pipeline(
    texts: list[str],
    responses: list[ServerResponse | None],
    entries: dict[tuple[str, ...], EntryKind],
    limits: PathLimits,
) -> tuple[BatchValidation, list[TargetPath | PathFailure]]:
    lines = [SourceLine(number, text) for number, text in enumerate(texts, start=1)]
    validation = validate_batch(lines)
    env = PathEnvironment(
        InMemoryDiskEntries(entries),
        PathReservations(validation.required_folders),
        limits,
    )
    results = [
        compute_target_path(DESTINATION, item.url, responses[(item.line - 1) % len(responses)], env)
        for item in validation.items
    ]
    return validation, results


# --- (1) y (2): ninguna excepción y rutas seguras ------------------------------------------------


@seed(SEED)
@COMMON
@given(HOSTILE_URLS)
def test_p1_no_input_raises_anywhere_in_the_pipeline(text: str) -> None:
    interpret_url(text)
    mask_text(text)
    read_single_input(text)
    validation = validate_batch([SourceLine(1, text)])
    assert len(validation.items) + len(validation.invalid) + validation.duplicates == 1


@seed(SEED)
@COMMON
@given(st.binary(max_size=200), st.sampled_from(["a.txt", "a.csv", "x", "A.TXT"]))
def test_p1_no_file_content_raises(content: bytes, name: str) -> None:
    decode_batch_file(name, content)


@seed(SEED)
@COMMON
@given(HOSTILE_URLS, RESPONSES, DISK_STATES, LIMITS)
def test_p2_every_result_is_a_safe_path_or_a_catalog_code(
    text: str,
    response: ServerResponse,
    entries: dict[tuple[str, ...], EntryKind],
    limits: PathLimits,
) -> None:
    _, results = run_pipeline([text], [response], entries, limits)
    for result in results:
        if isinstance(result, PathFailure):
            assert result.code in CATALOG_CODES
        else:
            assert_safe_target(result, limits)


@seed(SEED)
@COMMON
@given(
    st.lists(COLLIDING_URLS, min_size=1, max_size=12),
    st.lists(RESPONSES, min_size=1, max_size=3),
    DISK_STATES,
    LIMITS,
)
def test_p2_in_a_batch_no_two_paths_coincide_and_none_hits_the_disk(
    texts: list[str],
    responses: list[ServerResponse | None],
    entries: dict[tuple[str, ...], EntryKind],
    limits: PathLimits,
) -> None:
    """Nunca se sobrescribe nada: ni a otro elemento del lote ni a lo que ya existe en disco."""
    _, results = run_pipeline(texts, responses, entries, limits)
    taken = {windows_fold("\\".join(key)) for key in entries}
    seen: set[str] = set()
    for result in results:
        if isinstance(result, PathFailure):
            continue
        assert_safe_target(result, limits)
        key = windows_fold("\\".join((*result.folder_parts, result.file_name)))
        assert key not in seen
        assert key not in taken
        seen.add(key)


@seed(SEED)
@COMMON
@given(st.lists(COLLIDING_URLS, min_size=1, max_size=12), DISK_STATES)
def test_p2_a_needed_folder_is_never_taken_by_a_file(
    texts: list[str], entries: dict[tuple[str, ...], EntryKind]
) -> None:
    """RN-012 b: ningún archivo recibe el nombre de una carpeta que necesita el lote."""
    validation, results = run_pipeline(texts, [None], entries, PathLimits(False))
    for result in results:
        if isinstance(result, TargetPath):
            key = windows_fold("\\".join((*result.folder_parts, result.file_name)))
            assert key not in validation.required_folders


# --- (3): idempotencia del analizador ------------------------------------------------------------


@seed(SEED)
@COMMON
@given(HOSTILE_URLS)
def test_p3_the_parser_is_idempotent(text: str) -> None:
    first = parse_url(text)
    if not isinstance(first, Ok):
        return
    second = parse_url(first.value.processed())
    assert isinstance(second, Ok)
    assert replace(second.value, corrections=first.value.corrections) == first.value
    assert second.value.processed() == first.value.processed()


# --- (4): el canario no se muestra ---------------------------------------------------------------


def visible_outputs(text: str) -> list[str]:
    outputs = [mask_text(text)]
    result = interpret_url(text)
    if isinstance(result, ParsedUrl):
        outputs += [result.masked(), repr(result), str(result), f"{result}"]
    else:
        assert isinstance(result, InvalidUrl)
        outputs += [result.masked_text, repr(result)]
    validation = validate_batch([SourceLine(1, text)])
    outputs += [repr(validation), repr(validation.items), repr(validation.invalid)]
    outputs += [invalid.masked_text for invalid in validation.invalid]
    single = read_single_input(text)
    outputs.append(repr(single))
    return outputs


@seed(SEED)
@COMMON
@given(CANARY_URLS)
def test_p4_the_canary_never_appears_in_a_visible_output(text: str) -> None:
    assert CANARY in text
    for shown in visible_outputs(text):
        assert CANARY not in shown, shown


@seed(SEED)
@COMMON
@given(CANARY_URLS)
def test_p4_the_canary_only_shows_up_in_processed(text: str) -> None:
    result = interpret_url(text)
    if isinstance(result, ParsedUrl):
        assert CANARY in result.processed() or CANARY not in text.partition(" ")[0]


# --- (5): determinismo ---------------------------------------------------------------------------


@seed(SEED)
@COMMON
@given(
    st.lists(COLLIDING_URLS, min_size=1, max_size=8),
    st.lists(RESPONSES, min_size=1, max_size=3),
    DISK_STATES,
    LIMITS,
)
def test_p5_same_inputs_same_outputs(
    texts: list[str],
    responses: list[ServerResponse | None],
    entries: dict[tuple[str, ...], EntryKind],
    limits: PathLimits,
) -> None:
    assert run_pipeline(texts, responses, entries, limits) == run_pipeline(
        texts, responses, entries, limits
    )


@seed(SEED)
@COMMON
@given(HOSTILE_URLS)
def test_p5_interpretation_is_deterministic(text: str) -> None:
    assert interpret_url(text) == interpret_url(text)
    assert mask_text(text) == mask_text(text)
