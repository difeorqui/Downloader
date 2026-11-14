"""Modelo de una URL ya interpretada (RN-001a: se analiza una sola vez).

``ParsedUrl`` es inmutable. Contiene valores de parámetros y fragmento, que pueden ser secretos
(RN-036): por eso ``repr`` y ``str`` devuelven la forma enmascarada (``masked()``) y
``processed()`` es la única salida sin enmascarar (solo para conectar y exportar).
"""

from dataclasses import dataclass
from enum import Enum, Flag, auto
from ipaddress import IPv4Address, IPv6Address
from typing import Literal

from downloader.domain.catalog import InvalidReason
from downloader.domain.urls.masking import mask_fragment, mask_query, truncate_visible


class Correction(Flag):
    """Qué se corrigió al interpretar (RN-001): cuentan en la validación previa (RN-005)."""

    NONE = 0
    SCHEME_ADDED = auto()
    ENCODED = auto()


class HostKind(Enum):
    NAME = "nombre"
    IPV4 = "ipv4"
    IPV6 = "ipv6"


@dataclass(frozen=True, slots=True, repr=False)
class ParsedUrl:
    """Estructura única de una URL válida (contrato §2).

    ``host`` es ASCII, en minúsculas y sin punto final; un literal IPv6 va entre corchetes. Un
    literal IP se guarda como se escribió (D-08) y ``ip`` trae su valor interpretado, en
    cualquier notación. ``port`` es ``None`` si es el estándar del esquema. ``path`` es ``""`` o
    empieza por ``/``; ``path``, ``query`` y ``fragment`` ya están codificados y sin ``?``/``#``.
    """

    scheme: Literal["http", "https"]
    host: str
    host_kind: HostKind
    ip: IPv4Address | IPv6Address | None
    port: int | None
    path: str
    query: str | None
    fragment: str | None
    corrections: Correction

    def processed(self) -> str:
        """URL completa **sin enmascarar**: solo para conectar y exportar (RN-035 b)."""
        port = "" if self.port is None else f":{self.port}"
        query = "" if self.query is None else f"?{self.query}"
        fragment = "" if self.fragment is None else f"#{self.fragment}"
        return f"{self.scheme}://{self.host}{port}{self.path}{query}{fragment}"

    def masked(self) -> str:
        """Forma visible (RN-036, S-001-08 a): sin credenciales, parámetros y fragmento en ``***``.

        Se recorta a 200 caracteres (199 + ``…``). Los tokens dentro de la ruta no se ocultan
        (riesgo residual documentado).
        """
        port = "" if self.port is None else f":{self.port}"
        visible = f"{self.scheme}://{self.host}{port}{self.path}"
        if self.query is not None:
            visible += f"?{mask_query(self.query)}"
        if self.fragment is not None:
            visible += f"#{mask_fragment(self.fragment)}"
        return truncate_visible(visible)

    def __repr__(self) -> str:
        return f"ParsedUrl({self.masked()})"

    def __str__(self) -> str:
        return self.masked()


@dataclass(frozen=True, slots=True)
class InvalidUrl:
    """URL rechazada: el motivo (RN-004) y el texto original ya enmascarado (S-001-08 b)."""

    reason: InvalidReason
    masked_text: str
