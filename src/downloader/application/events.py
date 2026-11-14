"""Eventos que el ejecutor del lote entrega a la interfaz (sin depender de ella)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Started:
    index: int


@dataclass(frozen=True, slots=True)
class Progress:
    index: int
    downloaded: int
    total: int | None  # None si el servidor no informó el tamaño


@dataclass(frozen=True, slots=True)
class Finished:
    index: int
    path: str
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Failed:
    index: int
    message: str


@dataclass(frozen=True, slots=True)
class Cancelled:
    index: int


@dataclass(frozen=True, slots=True)
class AllDone:
    completed: int
    failed: int
    cancelled: int


type Event = Started | Progress | Finished | Failed | Cancelled | AllDone
