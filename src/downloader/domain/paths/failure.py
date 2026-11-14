"""Fallo de cálculo de la ruta (contrato §5): solo los códigos que decide el dominio."""

from dataclasses import dataclass

from downloader.domain.catalog import FailureCode

#: F-24 enlace o unión, F-25 ruta larga, F-27 archivo donde va una carpeta, F-28 nombre largo.
PATH_FAILURE_CODES = frozenset({FailureCode.F24, FailureCode.F25, FailureCode.F27, FailureCode.F28})


@dataclass(frozen=True, slots=True)
class PathFailure:
    """El elemento no puede recibir una ruta; ``code`` es uno de ``PATH_FAILURE_CODES``."""

    code: FailureCode
