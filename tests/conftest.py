"""Configuracion comun de pruebas (nunca se empaqueta; ver ADR 0007).

* Gancho de auditoria (T-02, RNF-001-06): activo durante la fase de llamada de las pruebas de
  ``tests/unit/domain``, ``tests/regression`` y ``tests/property``.
* Perfiles de hypothesis ``dev`` (2 000 ejemplos, cada commit) y ``ci`` (100 000, marca
  ``fuzz``), sin base de datos de ejemplos: el dominio no escribe en disco ni siquiera en
  pruebas (plan 001, seccion 7).
"""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings

from tests.audit_guard import GUARD, is_guarded

TESTS_DIR = Path(__file__).resolve().parent

settings.register_profile(
    "dev",
    max_examples=2_000,
    database=None,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "ci",
    max_examples=100_000,
    database=None,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("dev")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, object, object]:
    """Activa el gancho solo durante la llamada de las pruebas de las suites protegidas.

    Mientras está activo no se escribe bytecode: hypothesis y pytest importan módulos propios de
    forma diferida dentro de la prueba y, al guardar su ``__pycache__``, el intérprete haría
    ``os.mkdir``/``os.rename``. Así el gancho se mantiene estricto, sin excepciones.
    """
    if is_guarded(Path(item.path).resolve(), TESTS_DIR):
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            with GUARD.active():
                return (yield)
        finally:
            sys.dont_write_bytecode = previous
    return (yield)
