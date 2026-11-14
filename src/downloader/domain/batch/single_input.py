"""Campo de URL individual (RN-004 I-08, CA-001-12, CA-001-16).

* Vacío o solo espacios y tabulaciones: ``None`` (no se puede iniciar y no cuenta como inválida).
* Una sola línea con contenido, aunque haya líneas vacías antes o después: esa línea, recortada.
* Más de una línea con contenido: I-08. El texto **no se repite** en la salida (S-001-08 c).
"""

import re
from typing import Final

from downloader.domain.batch.source import SourceLine
from downloader.domain.catalog import InvalidReason
from downloader.domain.text import trim_blanks
from downloader.domain.urls.model import InvalidUrl

# CRLF, LF y CR suelto, incluso mezclados; cada uno es un fin de línea (S-001-10).
_LINE_BREAK: Final = re.compile(r"\r\n|\n|\r")


def read_single_input(text: str) -> SourceLine | InvalidUrl | None:
    """Interpreta el texto del campo individual; no lanza excepciones (PA-04)."""
    content = [
        SourceLine(number, trimmed)
        for number, line in enumerate(_LINE_BREAK.split(text), start=1)
        if (trimmed := trim_blanks(line))
    ]
    if not content:
        return None
    if len(content) > 1:
        return InvalidUrl(InvalidReason.I08, "")
    return content[0]
