"""Regresión: los 55 ejemplos del anexo 1, de la línea de texto a la ruta (T-21).

Cada caso recorre el flujo real del dominio: ``validate_batch`` (interpretación, clasificación,
duplicados, carpetas necesarias) y después ``compute_target_path`` para cada elemento válido, en
el orden del lote. La comparación es carácter a carácter.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path as FilePath

import pytest

from downloader.domain.addresses import AddressClass, classify_host
from downloader.domain.batch.source import SourceLine
from downloader.domain.batch.validator import validate_batch
from downloader.domain.paths.destination import SystemFolders, evaluate_destination
from tests.regression.annex1_data import (
    CASES,
    Case,
)
from tests.regression.runner import run

RULES = FilePath(__file__).resolve().parents[2] / "docs" / "01-requerimientos" / "reglas-negocio.md"
REGULAR_CASES = [case for case in CASES if case.lines]


@pytest.mark.parametrize("case", REGULAR_CASES, ids=[case.id for case in REGULAR_CASES])
def test_annex_1_example(case: Case) -> None:
    assert run(case) == list(case.expected)


@pytest.mark.parametrize(
    "case",
    [c for c in REGULAR_CASES if c.any_order],
    ids=[c.id for c in REGULAR_CASES if c.any_order],
)
def test_examples_stated_for_any_order_give_the_same_result_in_every_order(case: Case) -> None:
    """EJ-42: ``docs`` y ``docs\\x.pdf`` en cualquier orden (RN-012 b)."""
    for order in itertools.permutations(range(len(case.lines))):
        assert run(case, order) == list(case.expected), order


# --- Lo que el flujo debe además informar --------------------------------------------------------


@pytest.mark.parametrize("case", [c for c in REGULAR_CASES if c.internal], ids=lambda c: c.id)
def test_internal_examples_require_confirmation(case: Case) -> None:
    validation = validate_batch([SourceLine(1, case.lines[0])])
    assert [item.address_class for item in validation.items] == [AddressClass.INTERNAL]
    assert len(validation.internal_hosts) == 1


@pytest.mark.parametrize(
    "case", [c for c in REGULAR_CASES if not c.internal and c.id != "EJ-48"], ids=lambda c: c.id
)
def test_other_valid_examples_do_not_ask_for_confirmation(case: Case) -> None:
    validation = validate_batch([SourceLine(n, text) for n, text in enumerate(case.lines, 1)])
    assert validation.internal_hosts == ()


@pytest.mark.parametrize("case", REGULAR_CASES, ids=lambda c: c.id)
def test_corrected_counts(case: Case) -> None:
    validation = validate_batch([SourceLine(n, text) for n, text in enumerate(case.lines, 1)])
    assert validation.corrected_no_scheme == case.corrected_no_scheme
    assert validation.corrected_encoded == case.corrected_encoded


def test_ej_48_a_public_name_is_not_detectable_without_resolving_it() -> None:
    validation = validate_batch([SourceLine(1, "https://archivos.miempresa.com/a.pdf")])
    assert validation.items[0].address_class is AddressClass.PUBLIC
    assert validation.internal_hosts == ()


def test_ej_53_the_redirect_target_is_judged_by_its_own_name() -> None:
    """``x.corp`` es interno por su nombre; ``publico.com`` no. La 002 lo aplica en cada salto."""
    assert classify_host("x.corp") is AddressClass.INTERNAL
    assert classify_host("publico.com") is AddressClass.PUBLIC


def test_ej_54_a_link_to_a_system_folder_is_judged_by_its_real_path() -> None:
    """``D:\\Atajo`` apunta a ``C:\\Windows\\Temp``: la 002 entrega la ruta real."""
    system = SystemFolders(
        windows="C:\\Windows",
        program_files="C:\\Program Files",
        program_files_x86="C:\\Program Files (x86)",
        program_data="C:\\ProgramData",
        app_data="C:\\Users\\Ana\\AppData\\Local\\Descargador",
        system_drive_root="C:\\",
    )
    assert evaluate_destination("C:\\Windows\\Temp", system) is False
    assert evaluate_destination("D:\\Atajo", system) is True


# --- Completitud ---------------------------------------------------------------------------------


def annex_rows() -> list[int]:
    text = RULES.read_text(encoding="utf-8")
    annex = text[text.index("## Anexo 1") : text.index("## Anexo 2")]
    return [int(match) for match in re.findall(r"^\| (\d+) \|", annex, flags=re.MULTILINE)]


def test_the_annex_has_55_examples_numbered_without_gaps() -> None:
    assert annex_rows() == list(range(1, 56))


def test_every_example_of_the_annex_is_covered_exactly_once() -> None:
    expected_ids = [f"EJ-{number:02d}" for number in annex_rows()]
    assert [case.id for case in CASES] == expected_ids
    assert len(set(case.id for case in CASES)) == 55


def test_every_example_has_one_expectation_per_line() -> None:
    for case in CASES:
        assert len(case.expected) == len(case.lines), case.id
        assert not case.responses or len(case.responses) == len(case.lines), case.id


def test_the_urls_of_the_data_are_the_ones_written_in_the_annex() -> None:
    """Cada línea de cada caso aparece literalmente en la fila de su número (salvo EJ-43)."""
    text = RULES.read_text(encoding="utf-8")
    annex = text[text.index("## Anexo 1") : text.index("## Anexo 2")]
    rows = {
        int(match.group(1)): match.group(2)
        for match in re.finditer(r"^\| (\d+) \| (.+?) \| ", annex, flags=re.MULTILINE)
    }
    missing = [
        (case.id, line)
        for case in REGULAR_CASES
        if case.id != "EJ-43"  # el anexo escribe «<nombre de 300 caracteres>»
        for line in case.lines
        if f"`{line}`" not in rows[int(case.id[3:])]
    ]
    assert missing == []
