"""Catalogos cerrados I-NN, F-NN y A-N (RN-004, RN-021, RN-026, anexo 2)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from downloader.domain.catalog import FailureClass, FailureCode, InvalidReason, WarningCode

RULES = Path(__file__).resolve().parents[3] / "docs" / "01-requerimientos" / "reglas-negocio.md"


def rules_text() -> str:
    return RULES.read_text(encoding="utf-8")


# --- I-NN (RN-004) -----------------------------------------------------------------------------

INVALID_MESSAGES = {
    "I-01": "Protocolo no soportado",
    "I-02": "Ruta local o de red no soportada",
    "I-03": "URL mal formada o ambigua",
    "I-04": "URL demasiado larga",
    "I-05": "Requiere autenticación (no soportado)",
    "I-06": "Dirección no permitida",
    "I-07": "Puerto no válido",
    "I-08": "El campo admite una sola URL. Para varias, use un archivo masivo",
    "I-09": "Parece haber varias URLs en una misma línea",
}


def test_invalid_reason_count_and_codes() -> None:
    assert len(InvalidReason) == 9
    assert [reason.value for reason in InvalidReason] == list(INVALID_MESSAGES)
    assert [reason.name for reason in InvalidReason] == [f"I0{n}" for n in range(1, 10)]


@pytest.mark.parametrize(("code", "message"), INVALID_MESSAGES.items())
def test_invalid_reason_messages_are_exact(code: str, message: str) -> None:
    assert InvalidReason(code).message == message


def test_invalid_reason_messages_match_rn004() -> None:
    block = next(line for line in rules_text().splitlines() if line.startswith("| RN-004 |"))
    found = dict(re.findall(r'\*\*(I-0\d)\*\* "([^"]+)"', block))
    assert found == INVALID_MESSAGES


def test_invalid_reason_is_a_string_enum() -> None:
    assert InvalidReason.I03 == "I-03"
    assert str(InvalidReason.I03) == "I-03"
    assert InvalidReason("I-03") is InvalidReason.I03


# --- F-NN (anexo 2) ----------------------------------------------------------------------------

EXPECTED_FAILURE_CODES = (
    [f"F-{n:02d}" for n in range(1, 9)]
    + [f"F-{n:02d}" for n in range(10, 29)]
    + [f"F-{n:02d}" for n in range(30, 34)]
    + ["F-99"]
)


def annex2_rows() -> list[tuple[str, str, str]]:
    text = rules_text()
    section = text.split("## Anexo 2.", 1)[1].split("## Anexo 3.", 1)[0]
    pattern = r"^\| (F-\d\d) \| ([^|]+) \| (Temporal|Permanente|Recuperable) \|"
    rows = re.findall(pattern, section, re.MULTILINE)
    return [(code, motive.strip(), failure_class) for code, motive, failure_class in rows]


def test_failure_code_count_and_codes() -> None:
    assert len(FailureCode) == 32
    assert [code.value for code in FailureCode] == EXPECTED_FAILURE_CODES
    assert [code.name for code in FailureCode] == [
        code.replace("-", "") for code in EXPECTED_FAILURE_CODES
    ]


def test_annex2_has_32_rows_in_the_same_order_as_the_enum() -> None:
    rows = annex2_rows()
    assert len(rows) == 32
    assert [code for code, _, _ in rows] == EXPECTED_FAILURE_CODES


CLASS_BY_NAME = {
    "Temporal": FailureClass.TEMPORARY,
    "Permanente": FailureClass.PERMANENT,
    "Recuperable": FailureClass.RECOVERABLE,
}


@pytest.mark.parametrize(("code", "motive", "klass"), annex2_rows())
def test_failure_messages_and_classes_match_annex2(code: str, motive: str, klass: str) -> None:
    failure = FailureCode(code)
    assert failure.message == motive
    assert failure.failure_class is CLASS_BY_NAME[klass]


def test_failure_classes_by_range() -> None:
    for failure in FailureCode:
        number = int(failure.value[2:])
        if number <= 9:
            expected = FailureClass.TEMPORARY
        elif number <= 29:
            expected = FailureClass.PERMANENT
        elif number <= 39:
            expected = FailureClass.RECOVERABLE
        else:
            expected = FailureClass.PERMANENT  # F-99
        assert failure.failure_class is expected, failure


def test_some_failure_texts_are_exact() -> None:
    assert FailureCode.F27.message == (
        "Conflicto de ruta: existe un archivo con el nombre de una carpeta necesaria"
    )
    assert FailureCode.F28.message == (
        "Nombre de carpeta o archivo demasiado largo (más de 255 caracteres)"
    )
    assert FailureCode.F24.message == "Ruta no permitida"
    assert FailureCode.F25.message == "Ruta demasiado larga"
    assert FailureCode.F99.message == "Error inesperado"
    assert FailureCode.F30.message == "Dirección interna no confirmada"


def test_failure_class_members() -> None:
    assert {c.name for c in FailureClass} == {"TEMPORARY", "PERMANENT", "RECOVERABLE"}


def test_failure_code_is_a_string_enum() -> None:
    assert FailureCode.F24 == "F-24"
    assert FailureCode("F-24") is FailureCode.F24


# --- A-N (RN-021) ------------------------------------------------------------------------------

WARNING_MESSAGES = {
    "A-1": "Archivo ejecutable o con macros: no lo abra si no confía en el origen",
    "A-2": "Se recibió una página web en lugar de un archivo",
    "A-3": "No se pudo marcar el origen",
}


def test_warning_codes_and_messages() -> None:
    assert len(WarningCode) == 3
    assert {w.value: w.message for w in WarningCode} == WARNING_MESSAGES
    assert [w.name for w in WarningCode] == ["A1", "A2", "A3"]


def test_warning_messages_match_rn021() -> None:
    block = next(line for line in rules_text().splitlines() if line.startswith("| RN-021 |"))
    found = dict(re.findall(r'\*\*(A-\d)\*\* "([^"]+)"', block))
    assert found == WARNING_MESSAGES


def test_unknown_codes_are_rejected() -> None:
    with pytest.raises(ValueError, match="I-10"):
        InvalidReason("I-10")
    with pytest.raises(ValueError, match="F-09"):
        FailureCode("F-09")
    with pytest.raises(ValueError, match="A-4"):
        WarningCode("A-4")
