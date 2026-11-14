"""Validación previa del lote (RN-004 a RN-006, RN-012 b, RN-017 a; S-001-09).

Recibe las líneas con contenido (archivo masivo o campo individual) y devuelve, sin tocar la red
ni el disco, lo que se muestra antes de iniciar: elementos válidos y únicos, líneas inválidas ya
enmascaradas, conteos de corregidas y duplicadas, dominios internos y las carpetas que necesita
el lote (para que "prevalezcan las carpetas", RN-012 b, sin importar el orden de las descargas).

Invariante (S-001-09): ``len(items) + duplicates + len(invalid) == len(lines)``. Las duplicadas
se cuentan solo entre las válidas; una inválida repetida cuenta como inválida cada vez.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from downloader.domain.addresses import AddressClass, classify_host
from downloader.domain.batch.source import SourceLine
from downloader.domain.catalog import InvalidReason
from downloader.domain.paths.relative import relative_folders
from downloader.domain.text import windows_fold
from downloader.domain.urls import Correction, InvalidUrl, ParsedUrl, interpret_url
from downloader.domain.urls.dedup import dedup_key

_FOLDER_SEPARATOR = "\\"


@dataclass(frozen=True, slots=True)
class BatchItem:
    """URL válida y única del lote; ``address_class`` es ``PUBLIC`` o ``INTERNAL``."""

    index: int  # posición en el lote, desde 0, en el orden de las líneas
    line: int
    url: ParsedUrl
    address_class: AddressClass


@dataclass(frozen=True, slots=True)
class InvalidLine:
    """Línea rechazada: nunca contiene credenciales, parámetros ni fragmento (RN-036)."""

    line: int
    masked_text: str
    reason: InvalidReason


@dataclass(frozen=True, slots=True)
class InternalHost:
    """Dominio interno detectado por su nombre o por ser una IP escrita, con sus elementos."""

    host: str
    count: int


@dataclass(frozen=True, slots=True)
class BatchValidation:
    """Resumen de la validación previa (contrato §4)."""

    total_lines: int
    items: tuple[BatchItem, ...]
    corrected_no_scheme: int
    corrected_encoded: int
    duplicates: int
    invalid: tuple[InvalidLine, ...]
    internal_hosts: tuple[InternalHost, ...]  # sin repetir, en orden de primera aparición
    required_folders: frozenset[str]  # rutas relativas plegadas (RN-012 b), unidas por "\"

    @property
    def can_start(self) -> bool:
        """Se puede iniciar si hay al menos un elemento válido (RN-005)."""
        return bool(self.items)

    @property
    def corrected(self) -> int:
        """Elementos corregidos (una URL sin esquema y codificada cuenta una vez)."""
        return sum(1 for item in self.items if item.url.corrections is not Correction.NONE)


def validate_batch(lines: Sequence[SourceLine], total_lines: int | None = None) -> BatchValidation:
    """Interpreta, clasifica y deduplica las líneas; nunca consulta la red ni el disco.

    ``total_lines`` son todas las líneas del origen (vacías y comentarios incluidos); si no se da,
    se toma el número de líneas con contenido.
    """
    items: list[BatchItem] = []
    invalid: list[InvalidLine] = []
    seen: set[str] = set()
    duplicates = 0

    for line in lines:
        result = interpret_url(line.text)
        if isinstance(result, InvalidUrl):
            invalid.append(InvalidLine(line.number, result.masked_text, result.reason))
            continue
        address_class = classify_host(result.host, result.ip)
        if address_class is AddressClass.BLOCKED:
            invalid.append(InvalidLine(line.number, result.masked(), InvalidReason.I06))
            continue
        key = dedup_key(result)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        items.append(BatchItem(len(items), line.number, result, address_class))

    return BatchValidation(
        total_lines=len(lines) if total_lines is None else total_lines,
        items=tuple(items),
        corrected_no_scheme=sum(
            1 for item in items if Correction.SCHEME_ADDED in item.url.corrections
        ),
        corrected_encoded=sum(1 for item in items if Correction.ENCODED in item.url.corrections),
        duplicates=duplicates,
        invalid=tuple(invalid),
        internal_hosts=_internal_hosts(items),
        required_folders=_required_folders(items),
    )


def _internal_hosts(items: Sequence[BatchItem]) -> tuple[InternalHost, ...]:
    counts: dict[str, int] = {}
    for item in items:
        if item.address_class is AddressClass.INTERNAL:
            counts[item.url.host] = counts.get(item.url.host, 0) + 1
    return tuple(InternalHost(host, count) for host, count in counts.items())


def _required_folders(items: Sequence[BatchItem]) -> frozenset[str]:
    """Cada carpeta que necesita algún elemento, con todos sus ascendientes, plegada (RN-012 b)."""
    required: set[str] = set()
    for item in items:
        prefix: list[str] = []
        for folder in relative_folders(item.url):
            prefix.append(windows_fold(folder))
            required.add(_FOLDER_SEPARATOR.join(prefix))
    return frozenset(required)
