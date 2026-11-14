"""Resultado explícito en lugar de excepciones de negocio (PA-04).

Las validaciones con desenlace previsto devuelven ``Ok[T] | Err[E]`` (o un tipo resultado
específico del módulo). Las excepciones quedan para defectos de programación.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Ok[T]:
    """Desenlace correcto con su valor."""

    value: T


@dataclass(frozen=True, slots=True)
class Err[E]:
    """Desenlace previsto de error, con un código de catálogo cerrado."""

    error: E


type Result[T, E] = Ok[T] | Err[E]
