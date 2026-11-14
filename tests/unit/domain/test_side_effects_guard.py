"""El gancho de auditoria esta activo en las pruebas del dominio (T-02, RNF-001-06)."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from tests.audit_guard import GUARD, SideEffectViolation


def test_guard_is_active_while_domain_tests_run() -> None:
    assert GUARD.is_active()


def test_domain_tests_cannot_write_files(tmp_path: Path) -> None:
    target = tmp_path / "no-debe-existir.txt"
    with pytest.raises(SideEffectViolation):
        target.write_text("x", encoding="utf-8")
    assert not target.exists()


def test_domain_tests_cannot_open_sockets() -> None:
    with pytest.raises(SideEffectViolation):
        socket.socket()


def test_domain_tests_can_read_files(tmp_path: Path) -> None:
    # tmp_path ya existe (se crea antes de la fase de llamada); leer esta permitido.
    assert list(tmp_path.iterdir()) == []
