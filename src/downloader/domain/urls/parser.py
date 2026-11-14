"""Analizador de URL: RN-001 pasos 1 a 9 y RN-001a, en un único canal.

Dos tramos. :func:`split_raw_url` (pasos 1 a 6) trabaja sobre el texto **todavía sin
codificar** (RN-001 paso 6), de modo que se detecta lo ambiguo antes de que la codificación lo
enmascare (``https://a.com/x https://b.com/y`` es I-09, no una URL con ``%20``). Devuelve la
estructura mínima que necesitan los pasos siguientes (:class:`RawUrl`) o el motivo de
invalidez. Función pura y total (PA-04).

:func:`parse_url` completa los pasos 7 a 9 (barra invertida de la ruta, codificación, dominio,
puerto y largo) y produce la estructura única :class:`ParsedUrl`.

Orden de precedencia (S-001-07): I-02 → I-01 → I-09 → ambigüedad I-03 → credenciales I-05 →
dominio con espacio I-03 → resto del paso 9 (I-03) → I-04 → I-07. I-06 lo decide el validador
del lote con la clasificación de direcciones, siempre después de este canal.
"""

import re
from dataclasses import dataclass
from typing import Final, Literal

from downloader.domain.catalog import InvalidReason
from downloader.domain.result import Err, Ok, Result
from downloader.domain.urls.encoding import backslashes_to_slashes, encode_url_part
from downloader.domain.urls.host import parse_authority, resolve_port
from downloader.domain.urls.masking import mask_text
from downloader.domain.urls.model import Correction, InvalidUrl, ParsedUrl

type Scheme = Literal["http", "https"]

_SCHEME_SEPARATOR: Final = "://"
_SCHEME_PATTERN: Final = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*")
_DRIVE_PATH: Final = re.compile(r"[A-Za-z]:[\\/]")
_SUPPORTED_SCHEMES: Final = frozenset({"http", "https"})
_BLOCKED_PREFIXES: Final = (
    "javascript:",
    "vbscript:",
    "data:",
    "file:",
    "blob:",
    "about:",
    "mailto:",
)
_NEXT_URL: Final = re.compile(r"\s(?:https?)://", re.IGNORECASE)
_WHITESPACE: Final = re.compile(r"\s")
_AUTHORITY_END: Final = re.compile(r"[/?#]")
_DEFAULT_SCHEME: Final = "https"
_CONTROL_CHARS: Final = re.compile(r"[\x00-\x1f\x7f]")  # U+0000-U+001F y U+007F
MAX_URL_LENGTH: Final = 2048  # RN-003 h: sobre la URL ya corregida y codificada


@dataclass(frozen=True, slots=True, repr=False)
class RawUrl:
    """URL dividida pero sin codificar ni interpretar.

    ``authority`` va entre ``://`` y el primero de ``/``, ``?`` o ``#``: sin credenciales (I-05)
    y sin espacios. ``remainder`` es lo que sigue (ruta, parámetros, fragmento), o ``""``.
    """

    scheme: Scheme
    authority: str
    remainder: str
    scheme_added: bool

    def __repr__(self) -> str:
        """Enmascarado: ``remainder`` conserva los parámetros y el fragmento sin enmascarar."""
        shown = mask_text(f"{self.scheme}://{self.authority}{self.remainder}")
        return f"RawUrl({shown}, scheme_added={self.scheme_added})"


def split_raw_url(text: str) -> Result[RawUrl, InvalidReason]:
    """RN-001 pasos 1 a 6 sobre una línea ya recortada.

    ``Ok(RawUrl)`` si pasa todas las comprobaciones previas; ``Err(motivo)`` si no. No analiza
    el dominio ni el puerto ni codifica nada: eso es del tramo siguiente.
    """
    if _is_local_path(text):
        return Err(InvalidReason.I02)
    scheme = _explicit_scheme(text)
    if scheme is not None and scheme.lower() not in _SUPPORTED_SCHEMES:
        return Err(InvalidReason.I01)
    if text.lower().startswith(_BLOCKED_PREFIXES):
        return Err(InvalidReason.I01)
    if _NEXT_URL.search(text):
        return Err(InvalidReason.I09)

    scheme_added = scheme is None
    if scheme is None:
        text = f"{_DEFAULT_SCHEME}{_SCHEME_SEPARATOR}{text}"
        scheme = _DEFAULT_SCHEME
    after_scheme = text[len(scheme) + len(_SCHEME_SEPARATOR) :]
    return _check_authority(_normalized_scheme(scheme), after_scheme, scheme_added=scheme_added)


def _is_local_path(text: str) -> bool:
    """Paso 1: ``\\\\servidor\\x`` o una letra de unidad (``C:\\``, ``c:/``)."""
    return text.startswith("\\\\") or _DRIVE_PATH.match(text) is not None


def _explicit_scheme(text: str) -> str | None:
    """Paso 2: el texto anterior al primer ``://`` si cumple el patrón de esquema."""
    prefix, separator, _ = text.partition(_SCHEME_SEPARATOR)
    if separator and _SCHEME_PATTERN.fullmatch(prefix):
        return prefix
    return None


def _normalized_scheme(scheme: str) -> Scheme:
    return "http" if scheme.lower() == "http" else "https"


def _check_authority(
    scheme: Scheme, after_scheme: str, *, scheme_added: bool
) -> Result[RawUrl, InvalidReason]:
    """Paso 6 (RN-001a): ambigüedad en la autoridad cruda, credenciales y dominio con espacio."""
    raw_authority = after_scheme.partition("/")[0]
    if "\\" in raw_authority or _has_hash_then_at(raw_authority):
        return Err(InvalidReason.I03)

    end = _AUTHORITY_END.search(after_scheme)
    cut = end.start() if end else len(after_scheme)
    authority, remainder = after_scheme[:cut], after_scheme[cut:]
    if "@" in authority:
        return Err(InvalidReason.I05)
    if _WHITESPACE.search(authority):
        return Err(InvalidReason.I03)
    return Ok(RawUrl(scheme, authority, remainder, scheme_added))


def _has_hash_then_at(raw_authority: str) -> bool:
    """``#`` seguido más adelante de ``@``: distintos programas verían dominios distintos."""
    first_hash = raw_authority.find("#")
    return first_hash != -1 and "@" in raw_authority[first_hash + 1 :]


# I-05 e I-07 rechazan una URL de estructura legible: sus parámetros se muestran por nombre,
# como en una válida (S-001-08 b). En los demás, lo que sigue a ``?``/``#`` se oculta entero.
_READABLE_REASONS: Final = frozenset({InvalidReason.I05, InvalidReason.I07})


def interpret_url(text: str) -> ParsedUrl | InvalidUrl:
    """Contrato §2: interpreta una línea ya recortada o la rechaza con su texto enmascarado."""
    result = parse_url(text)
    if isinstance(result, Ok):
        return result.value
    reason = result.error
    return InvalidUrl(reason, mask_text(text, analyzable=reason in _READABLE_REASONS))


def parse_url(text: str) -> Result[ParsedUrl, InvalidReason]:
    """Interpreta una línea ya recortada: ``Ok(ParsedUrl)`` o ``Err(motivo de RN-004)``.

    Idempotente: ``parse_url(url.processed())`` da la misma estructura (CA-001-16).
    """
    split = split_raw_url(text)
    if isinstance(split, Err):
        return split
    raw = split.value

    authority = parse_authority(raw.authority)
    if isinstance(authority, Err):
        return authority
    host = authority.value

    problem = _remainder_problem(raw.remainder)
    if problem is not None:
        return Err(problem)
    path, query, fragment = _split_remainder(raw.remainder)
    straight_path = backslashes_to_slashes(path)  # paso 7: no cuenta como codificación
    encoded_path = encode_url_part(straight_path)
    encoded_query = None if query is None else encode_url_part(query)
    encoded_fragment = None if fragment is None else encode_url_part(fragment)

    corrections = Correction.SCHEME_ADDED if raw.scheme_added else Correction.NONE
    if (
        host.converted_to_ascii
        or encoded_path != straight_path
        or encoded_query != query
        or encoded_fragment != fragment
    ):
        corrections |= Correction.ENCODED

    port = resolve_port(host.port_text, raw.scheme)
    shown_port = host.port_text if isinstance(port, Err) else _port_text(port.value)
    length = (
        len(raw.scheme)
        + len(_SCHEME_SEPARATOR)
        + len(host.host)
        + len(shown_port)
        + len(encoded_path)
        + (0 if encoded_query is None else len(encoded_query) + 1)
        + (0 if encoded_fragment is None else len(encoded_fragment) + 1)
    )
    if length > MAX_URL_LENGTH:
        return Err(InvalidReason.I04)
    if isinstance(port, Err):
        return port

    return Ok(
        ParsedUrl(
            scheme=raw.scheme,
            host=host.host,
            host_kind=host.kind,
            ip=host.ip,
            port=port.value,
            path=encoded_path,
            query=encoded_query,
            fragment=encoded_fragment,
            corrections=corrections,
        )
    )


def _remainder_problem(remainder: str) -> InvalidReason | None:
    """Motivo por el que ruta, parámetros o fragmento ya no pueden dar una URL válida, si lo hay.

    * I-03 (paso 9, CA-001-33): un carácter de control no es una URL.
    * I-04: codificar nunca acorta el texto, así que si esto solo ya supera el máximo la URL es
      demasiado larga sin recorrerla carácter a carácter; una línea de 5 MB se rechaza en
      milisegundos (RNF-001-03 b). Los errores de dominio se descartaron antes y el de puerto
      (I-07) va después de I-04, de modo que el orden de S-001-07 se conserva.
    """
    if _CONTROL_CHARS.search(remainder):
        return InvalidReason.I03
    if len(remainder) > MAX_URL_LENGTH:
        return InvalidReason.I04
    return None


def _split_remainder(remainder: str) -> tuple[str, str | None, str | None]:
    """Ruta, parámetros y fragmento.

    El primer ``#`` abre el fragmento; el primer ``?`` anterior a él, los parámetros.
    """
    before_fragment, hash_mark, fragment = remainder.partition("#")
    path, question_mark, query = before_fragment.partition("?")
    return path, (query if question_mark else None), (fragment if hash_mark else None)


def _port_text(port: int | None) -> str:
    return "" if port is None else f":{port}"
