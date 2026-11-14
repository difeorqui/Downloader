"""Línea de origen de una URL (archivo masivo o campo individual)."""

from dataclasses import dataclass

from downloader.domain.urls.masking import mask_text


@dataclass(frozen=True, slots=True, repr=False)
class SourceLine:
    """Línea con contenido, ya recortada de espacios y tabulaciones (RN-002).

    ``number`` cuenta desde 1 sobre todas las líneas del origen, incluidas vacías y comentarios
    (S-001-10). ``text`` es la URL **sin enmascarar** (hace falta para interpretarla): por eso
    ``repr`` y ``str`` muestran solo su forma enmascarada (RN-036).
    """

    number: int
    text: str

    def __repr__(self) -> str:
        return f"SourceLine(number={self.number}, text={mask_text(self.text)!r})"
