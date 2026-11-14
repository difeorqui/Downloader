"""Lectura y rechazo del archivo masivo (RN-002, RN-003 a-g, D-01, S-001-07, S-001-10).

Entrada: el nombre y los **bytes** del archivo (el dominio no abre archivos, PA-01). Salida: las
líneas con contenido o el rechazo del archivo completo, con el mensaje exacto de la spec.

Orden de rechazos (S-001-07), siempre el primero que se cumple: extensión → tamaño → UTF-32 →
UTF-16 → UTF-8 estricto → sin contenido → conteo.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from downloader.domain.batch.source import SourceLine
from downloader.domain.text import trim_blanks, windows_fold

MAX_FILE_BYTES: Final = 5_242_880  # 5 MB (S-001-01): se acepta hasta ese valor, inclusive
MAX_URLS: Final = 10_000
_BYTES_PER_MB: Final = 1_048_576
_NULL_SAMPLE_BYTES: Final = 4096
_NULL_RATIO_DENOMINATOR: Final = 10  # >= 10 % de bytes nulos
_COMMENT_PREFIX: Final = "#"

_UTF8_BOM: Final = b"\xef\xbb\xbf"
_UTF32_BOMS: Final = (b"\x00\x00\xfe\xff", b"\xff\xfe\x00\x00")
_UTF16_BOMS: Final = (b"\xff\xfe", b"\xfe\xff")

# CRLF, LF y CR suelto, incluso mezclados; cada uno es un fin de línea (S-001-10).
_LINE_BREAK: Final = re.compile(r"\r\n|\n|\r")

_MESSAGE_CSV: Final = (
    "Los archivos .csv no se admiten. Guarde la lista como .txt, con una URL por línea."
)
_MESSAGE_NOT_TXT: Final = "Solo se admiten archivos .txt"
_MESSAGE_UTF16: Final = (
    "El archivo está guardado en UTF-16. Guárdelo como UTF-8 e inténtelo de nuevo"
)
_MESSAGE_NO_URLS: Final = "El archivo no contiene URLs"


class RejectionKind(Enum):
    CSV = "csv"
    NOT_TXT = "no_txt"
    TOO_LARGE = "tamano"
    UTF16 = "utf16"
    INVALID_UTF8 = "utf8"
    NO_URLS = "vacio"
    TOO_MANY_URLS = "conteo"


@dataclass(frozen=True, slots=True)
class BatchFileRejection:
    """El archivo se rechaza completo; ``message`` es el texto exacto que ve el usuario."""

    kind: RejectionKind
    message: str


@dataclass(frozen=True, slots=True)
class DecodedBatch:
    """Líneas con contenido y el total de líneas del archivo (S-001-09)."""

    total_lines: int
    lines: tuple[SourceLine, ...]


def decode_batch_file(file_name: str, content: bytes) -> DecodedBatch | BatchFileRejection:
    """Aplica RN-002 y RN-003 a-g; nunca lanza excepciones por el contenido (PA-04)."""
    early_rejection = _check_name_size_and_encoding(file_name, content)
    if early_rejection is not None:
        return early_rejection

    text_or_rejection = _decode_utf8(content)
    if isinstance(text_or_rejection, BatchFileRejection):
        return text_or_rejection

    all_lines = _split_lines(text_or_rejection)
    lines = tuple(
        SourceLine(number, trimmed)
        for number, line in enumerate(all_lines, start=1)
        if (trimmed := trim_blanks(line)) and not trimmed.startswith(_COMMENT_PREFIX)
    )
    if not lines:
        return BatchFileRejection(RejectionKind.NO_URLS, _MESSAGE_NO_URLS)
    if len(lines) > MAX_URLS:
        return BatchFileRejection(RejectionKind.TOO_MANY_URLS, _count_message(len(lines)))
    return DecodedBatch(len(all_lines), lines)


def _check_name_size_and_encoding(file_name: str, content: bytes) -> BatchFileRejection | None:
    """Extensión → tamaño → UTF-32 → UTF-16 (S-001-07); ``None`` si ninguna se cumple."""
    extension_problem = _check_extension(file_name)
    if extension_problem is not None:
        return extension_problem
    if len(content) > MAX_FILE_BYTES:
        return BatchFileRejection(RejectionKind.TOO_LARGE, _size_message(len(content)))
    if content.startswith(_UTF32_BOMS):
        return _invalid_utf8(1)  # la marca de UTF-32 se comprueba antes y no se trata como UTF-16
    if _looks_like_utf16(content):
        return BatchFileRejection(RejectionKind.UTF16, _MESSAGE_UTF16)
    return None


def _check_extension(file_name: str) -> BatchFileRejection | None:
    """RN-003 d: ``.txt`` sin distinguir mayúsculas; ``.csv`` tiene su propio mensaje."""
    base = file_name.replace("\\", "/").rpartition("/")[2]
    extension = windows_fold(_file_extension(base))
    if extension == windows_fold("txt"):
        return None
    if extension == windows_fold("csv"):
        return BatchFileRejection(RejectionKind.CSV, _MESSAGE_CSV)
    return BatchFileRejection(RejectionKind.NOT_TXT, _MESSAGE_NOT_TXT)


def _file_extension(name: str) -> str:
    """S-001-12: lo que sigue al último punto, si no es ni el primer ni el último carácter."""
    head, dot, tail = name.rpartition(".")
    return tail if dot and head and tail else ""


def _looks_like_utf16(content: bytes) -> bool:
    """RN-003 e: marca inicial de UTF-16 o >= 10 % de bytes nulos en los primeros 4 KB."""
    if content.startswith(_UTF16_BOMS):
        return True
    sample = content[:_NULL_SAMPLE_BYTES]
    return bool(sample) and sample.count(0) * _NULL_RATIO_DENOMINATOR >= len(sample)


def _decode_utf8(content: bytes) -> str | BatchFileRejection:
    """UTF-8 estricto sobre todo el archivo, comentarios incluidos; quita la marca BOM."""
    body = content.removeprefix(_UTF8_BOM)
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as error:
        before = body[: error.start].decode("utf-8", errors="replace")
        return _invalid_utf8(len(_LINE_BREAK.findall(before)) + 1)


def _split_lines(text: str) -> list[str]:
    """Líneas del archivo: un fin de línea al final no añade otra línea (S-001-09)."""
    if not text:
        return []
    lines = _LINE_BREAK.split(text)
    if lines[-1] == "":
        lines.pop()
    return lines


def _invalid_utf8(line: int) -> BatchFileRejection:
    return BatchFileRejection(
        RejectionKind.INVALID_UTF8, f"El archivo no es texto UTF-8 válido (línea {line})"
    )


def _thousands(number: int) -> str:
    return f"{number:,}".replace(",", ".")


def _size_message(size: int) -> str:
    """S-001-10: miles con punto y decimales con coma; los MB se redondean hacia arriba.

    Hacia arriba para que nunca diga "5,00 MB" de un archivo que supera el máximo.
    """
    hundredths = (size * 100 + _BYTES_PER_MB - 1) // _BYTES_PER_MB
    megabytes = f"{hundredths // 100},{hundredths % 100:02d}"
    return (
        f"El archivo pesa {megabytes} MB ({_thousands(size)} bytes); "
        f"el máximo es 5 MB ({_thousands(MAX_FILE_BYTES)} bytes)."
    )


def _count_message(count: int) -> str:
    return f"El archivo tiene {_thousands(count)} URLs; el máximo es {_thousands(MAX_URLS)}."
