"""Determinismo (RNF-001-04): mismas entradas y mismo orden de llamadas dan el mismo resultado.

* Cada caso del anexo 1, 100 veces, con estado nuevo en cada una.
* EJ-42 (y CA-001-90) en orden directo, inverso y aleatorio: el resultado por URL no cambia.
* EJ-19 (y CA-001-89) **solo en orden directo**: depende del orden por diseño (RN-012 a). Se
  comprueba además que el inverso cambia, para que nadie «arregle» la prueba por error.
"""

from __future__ import annotations

import itertools

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.regression.annex1_data import CASES, Case, Fails, Path
from tests.regression.runner import run

REGULAR = [case for case in CASES if case.lines]
CASE_BY_ID = {case.id: case for case in CASES}
REPETITIONS = 100


@pytest.mark.parametrize("case", REGULAR, ids=[case.id for case in REGULAR])
def test_each_case_gives_the_same_result_one_hundred_times(case: Case) -> None:
    first = run(case)
    for _ in range(REPETITIONS - 1):
        assert run(case) == first


def test_ej_42_is_the_same_in_direct_and_inverse_order() -> None:
    case = CASE_BY_ID["EJ-42"]
    direct = tuple(range(len(case.lines)))
    for order in (direct, tuple(reversed(direct))):
        assert run(case, order) == list(case.expected), order


@given(st.permutations(range(2)))
def test_ej_42_is_the_same_in_a_random_order(order: list[int]) -> None:
    """Orden aleatorio generado por hypothesis (la semilla queda en el informe si falla)."""
    case = CASE_BY_ID["EJ-42"]
    assert run(case, tuple(order)) == list(case.expected)


def test_ej_42_every_permutation_and_many_repetitions() -> None:
    case = CASE_BY_ID["EJ-42"]
    for order in itertools.permutations(range(len(case.lines))):
        for _ in range(REPETITIONS):
            assert run(case, order) == list(case.expected)


def test_ej_19_in_direct_order_gives_the_documented_result() -> None:
    case = CASE_BY_ID["EJ-19"]
    for _ in range(REPETITIONS):
        assert run(case) == list(case.expected)


def test_ej_19_depends_on_the_order_by_design() -> None:
    """Quien pide primero conserva el nombre (RN-012 a): invertir las llamadas lo invierte."""
    case = CASE_BY_ID["EJ-19"]
    inverse = run(case, (1, 0))
    assert inverse != list(case.expected)
    first, second = inverse
    assert isinstance(first, Path)
    assert isinstance(second, Path)
    assert first.full_path.endswith("\\A (1).pdf") or first.full_path.endswith("\\a (1).pdf")
    assert second.full_path.endswith("\\a.pdf")


def test_failures_are_deterministic_too() -> None:
    for case_id in ("EJ-25", "EJ-26", "EJ-43"):
        case = CASE_BY_ID[case_id]
        results = {tuple(map(repr, run(case))) for _ in range(REPETITIONS)}
        assert len(results) == 1
        assert isinstance(case.expected[0], Fails)
