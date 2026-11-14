"""Ejecuta un caso del anexo 1 por el flujo real del dominio (compartido por las pruebas)."""

from __future__ import annotations

from downloader.domain.batch.source import SourceLine
from downloader.domain.batch.validator import validate_batch
from downloader.domain.paths.collisions import InMemoryDiskEntries, PathReservations
from downloader.domain.paths.failure import PathFailure
from downloader.domain.paths.length import PathLimits
from downloader.domain.paths.response import ServerResponse
from downloader.domain.paths.target import PathEnvironment, TargetPath, compute_target_path
from tests.regression.annex1_data import DESTINATION, Case, Expected, Fails, Invalid, Path


def run(case: Case, order: tuple[int, ...] | None = None) -> list[Expected]:
    """Resultado por línea, en el orden original de ``case.lines``."""
    indexes = order or tuple(range(len(case.lines)))
    lines = [SourceLine(position + 1, case.lines[index]) for position, index in enumerate(indexes)]
    validation = validate_batch(lines)
    invalid_by_line = {invalid.line: invalid for invalid in validation.invalid}
    env = PathEnvironment(
        InMemoryDiskEntries(dict(case.disk)),
        PathReservations(validation.required_folders),
        PathLimits(long_paths_enabled=False),
    )
    by_original: dict[int, Expected] = {}
    for position, index in enumerate(indexes):
        invalid = invalid_by_line.get(position + 1)
        if invalid is not None:
            by_original[index] = Invalid(invalid.reason)
    for item in validation.items:
        index = indexes[item.line - 1]
        response: ServerResponse | None = case.responses[index] if case.responses else None
        result = compute_target_path(DESTINATION, item.url, response, env)
        if isinstance(result, PathFailure):
            by_original[index] = Fails(result.code)
        else:
            assert isinstance(result, TargetPath)
            by_original[index] = Path(result.full_path, result.warnings)
    return [by_original[index] for index in range(len(case.lines))]
