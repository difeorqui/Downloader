"""Rendimiento del dominio (RNF-001-01 a 03). Marca ``perf``: se ejecuta antes de integrar.

Los datos son deterministas (patrones por índice, sin aleatoriedad) para que dos ejecuciones midan
lo mismo. p95 de 20 ejecuciones con ``statistics.quantiles``. La memoria pico se mide con
``tracemalloc`` en una ejecución aparte: mide asignaciones de Python, aproximación aceptada de la
memoria privada adicional (plan §7). Resultados de referencia en ``--durations`` y en el informe
del cierre (T-25).
"""

from __future__ import annotations

import statistics
import time
import tracemalloc
from collections.abc import Callable

import pytest

from downloader.domain.batch.file_decoder import DecodedBatch, decode_batch_file
from downloader.domain.batch.source import SourceLine
from downloader.domain.batch.validator import BatchValidation, validate_batch
from downloader.domain.catalog import InvalidReason
from downloader.domain.paths.collisions import EntryKind, InMemoryDiskEntries, PathReservations
from downloader.domain.paths.length import PathLimits
from downloader.domain.paths.target import PathEnvironment, TargetPath, compute_target_path

pytestmark = pytest.mark.perf

RUNS = 20
BATCH = 10_000
DESTINATION = "D:\\Descargas"
LIMIT_BATCH_SECONDS = 1.0  # RNF-001-01 y 02
LIMIT_WORST_CASE_SECONDS = 2.0  # RNF-001-03 (a)
LIMIT_SINGLE_LINE_SECONDS = 0.5  # RNF-001-03 (b)
LIMIT_MEMORY_BYTES = 100 * 1024 * 1024  # RNF-001-03 (a)

INVALID_SAMPLES = [
    "ftp://x.com/a",  # I-01
    "C:\\temp\\a.pdf",  # I-02
    "https://sitio.com\\@127.0.0.1/a",  # I-03
    "https://u:p@sitio.com/a",  # I-05
    "https://169.254.169.254/a",  # I-06
    "https://sitio.com:99999/a",  # I-07
    "https://a.com/x https://b.com/y",  # I-09
]


def p95(samples: list[float]) -> float:
    return statistics.quantiles(samples, n=20)[-1]


def measure(operation: Callable[[], object]) -> list[float]:
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        operation()
        times.append(time.perf_counter() - start)
    return times


def token_url(index: int) -> str:
    return (
        f"https://archivos{index // 20}.sitio.com/carpeta/{index}/informe-{index}.pdf?v=1"
        f"&token={'x' * 40}"
    )


def mixed_batch() -> list[SourceLine]:
    """10 000 líneas (~1 MB), un 5 % de cada categoría (20 cubos de 500 líneas)."""
    lines = []
    for index in range(BATCH):
        bucket = index % 20
        if bucket == 0 and index >= 20:
            text = token_url(index - 15)  # repite una línea válida anterior (cubo 5)
        elif bucket == 1:
            text = f"archivos{index // 20}.sitio.com/carpeta/{index}/sin esquema.pdf"
        elif bucket == 2:
            text = f"https://archivos{index // 20}.sitio.com/año/{index}/informe final.pdf"
        elif bucket == 3:
            text = f"http://intranet{index % 7}/docs/{index}/informe.pdf"
        elif bucket == 4:
            text = INVALID_SAMPLES[(index // 20) % len(INVALID_SAMPLES)]
        else:
            text = token_url(index)
        lines.append(SourceLine(index + 1, text))
    return lines


def valid_batch() -> BatchValidation:
    lines = [
        SourceLine(i + 1, f"https://s{i % 400}.sitio.com/a/b{i % 50}/informe-{i}.pdf?v={i}")
        for i in range(BATCH)
    ]
    validation = validate_batch(lines)
    assert len(validation.items) == BATCH
    return validation


# --- RNF-001-01: validar un lote máximo ----------------------------------------------------------


def test_rnf_001_01_validating_a_maximum_batch_p95_under_one_second() -> None:
    lines = mixed_batch()
    assert len(lines) == BATCH
    assert sum(len(line.text) for line in lines) > 700_000  # ~1 MB de texto
    sample = validate_batch(lines)
    assert sample.duplicates > 0
    assert sample.internal_hosts
    assert {invalid.reason for invalid in sample.invalid} >= {InvalidReason.I01, InvalidReason.I06}
    assert p95(measure(lambda: validate_batch(lines))) <= LIMIT_BATCH_SECONDS


# --- RNF-001-02: calcular las rutas de un lote máximo --------------------------------------------


def test_rnf_001_02_computing_paths_for_a_maximum_batch_p95_under_one_second() -> None:
    validation = valid_batch()
    # Estado del disco simulado: 10 000 entradas; un 10 % coincide con nombres del lote.
    entries = {
        ("otro.com", f"existente-{i}.bin"): EntryKind.FILE for i in range(BATCH - BATCH // 10)
    }
    for item in validation.items[: BATCH // 10]:
        host, folder = f"s{item.index % 400}.sitio.com", f"b{item.index % 50}"
        entries[(host, "a", folder, f"informe-{item.index}.pdf")] = EntryKind.FILE
    assert len(entries) == BATCH
    disk = InMemoryDiskEntries(entries)

    def compute_all() -> list[object]:
        env = PathEnvironment(
            disk, PathReservations(validation.required_folders), PathLimits(False)
        )
        return [compute_target_path(DESTINATION, item.url, None, env) for item in validation.items]

    results = compute_all()
    assert all(isinstance(result, TargetPath) for result in results)
    suffixed = sum(
        1 for result in results if isinstance(result, TargetPath) and "(1)" in result.file_name
    )
    assert suffixed >= BATCH // 10 - 1  # el 10 % de colisiones se resolvió con sufijo
    assert p95(measure(compute_all)) <= LIMIT_BATCH_SECONDS


# --- RNF-001-03: peor caso de tamaño -------------------------------------------------------------


def worst_case_file() -> bytes:
    """5 MB con 2 500 URLs de 2 048 caracteres (ya codificadas: no crecen al interpretarlas)."""
    lines = []
    for index in range(2_500):
        head = f"https://sitio.com/{index:05d}-"
        lines.append(head + ("ab%20" * 500)[: 2_048 - len(head)])
    content = "\n".join(lines).encode("ascii")
    assert all(len(line) == 2_048 for line in lines)
    return content


def process_file(content: bytes) -> BatchValidation:
    decoded = decode_batch_file("lista.txt", content)
    assert isinstance(decoded, DecodedBatch)
    return validate_batch(decoded.lines, decoded.total_lines)


def test_rnf_001_03_a_five_megabytes_of_maximum_length_urls_in_two_seconds() -> None:
    content = worst_case_file()
    assert 4_900_000 < len(content) <= 5_242_880
    result = process_file(content)
    assert len(result.items) + len(result.invalid) + result.duplicates == 2_500
    assert max(measure(lambda: process_file(content))) <= LIMIT_WORST_CASE_SECONDS


def test_rnf_001_03_a_peak_memory_under_one_hundred_megabytes() -> None:
    content = worst_case_file()
    tracemalloc.start()
    try:
        baseline = tracemalloc.get_traced_memory()[0]
        process_file(content)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert peak - baseline <= LIMIT_MEMORY_BYTES


def test_rnf_001_03_b_a_single_five_megabyte_line_is_i04_in_half_a_second() -> None:
    content = ("https://sitio.com/" + "a" * (5_242_880 - 18)).encode("ascii")
    assert len(content) == 5_242_880
    result = process_file(content)
    assert [invalid.reason for invalid in result.invalid] == [InvalidReason.I04]
    assert max(measure(lambda: process_file(content))) <= LIMIT_SINGLE_LINE_SECONDS


def test_rnf_001_03_b_a_single_line_full_of_characters_to_encode_is_also_fast() -> None:
    content = ("https://sitio.com/" + "ñ " * 2_621_430).encode("utf-8")[:5_242_880]
    result = decode_batch_file("lista.txt", content)
    if isinstance(result, DecodedBatch):
        validation = validate_batch(result.lines, result.total_lines)
        assert validation.invalid[0].reason in {InvalidReason.I04, InvalidReason.I03}
        assert max(measure(lambda: validate_batch(result.lines))) <= LIMIT_SINGLE_LINE_SECONDS


def test_rnf_001_05_each_hostile_input_is_processed_in_under_100_ms() -> None:
    """Cada entrada se procesa en <= 100 ms, incluidas las más largas y las más hostiles."""
    hostile = [
        "https://sitio.com/" + "%2e/" * 500_000,
        "https://sitio.com/" + "a/" * 500_000 + "x.pdf",
        "https://" + "a." * 100_000 + "com/",
        "https://sitio.com/?" + "&".join(f"k{i}=v{i}" for i in range(100_000)),
        "https://sitio.com/" + "%" * 1_000_000,
        "https://sitio.com/" + "\\" * 1_000_000,
        "https://[" + ":" * 500_000 + "]/",
        "a" * 1_000_000,
        "@" * 1_000_000,
        "https://" + "@" * 1_000_000,
    ]
    slowest = 0.0
    for text in hostile:
        start = time.perf_counter()
        validate_batch([SourceLine(1, text)])
        slowest = max(slowest, time.perf_counter() - start)
    assert slowest <= 0.1
