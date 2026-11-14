"""Guardas de arquitectura del dominio (T-02, PA-01, AP-05, RNF-001-06).

Analiza con ``ast`` todo ``src/downloader/domain``: solo imports permitidos, sin E/S
(``open``, ``print``...) y sin estado global mutable. Los archivos de ``samples/`` demuestran
que cada infraccion se detecta; no son codigo de la aplicacion (extension ``.sample``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.layer_rules import (
    ALLOWED_IMPORT_ROOTS,
    FORBIDDEN_BUILTINS,
    Violation,
    check_source,
    check_tree,
)

ROOT = Path(__file__).resolve().parents[2]
DOMAIN = ROOT / "src" / "downloader" / "domain"
SAMPLES = Path(__file__).resolve().parent / "samples"
SAMPLE_MODULE = "downloader.domain.urls.sample"


def check_sample(name: str) -> list[Violation]:
    source = (SAMPLES / name).read_text(encoding="utf-8")
    return check_source(source, SAMPLE_MODULE, name)


def rules_of(violations: list[Violation]) -> set[str]:
    return {violation.rule for violation in violations}


def check_snippet(code: str) -> list[Violation]:
    return check_source(code, SAMPLE_MODULE, "snippet.py")


# --- el dominio real cumple las reglas ---------------------------------------------------------


def test_real_domain_has_no_violations() -> None:
    assert DOMAIN.is_dir()
    assert check_tree(DOMAIN) == []


def test_check_tree_reports_problems_in_a_tree(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "bad.py").write_text("import socket\n", encoding="utf-8")
    found = check_tree(package, base_module="downloader.domain")
    assert [(v.rule, Path(v.file).name) for v in found] == [("IMPORT", "bad.py")]


# --- muestras: cada infraccion se detecta ------------------------------------------------------


def test_sample_import_socket_is_detected() -> None:
    violations = check_sample("import_socket.py.sample")
    assert rules_of(violations) == {"IMPORT"}
    assert "socket" in violations[0].detail
    assert violations[0].line == 3


def test_sample_open_for_writing_inside_a_function_is_detected() -> None:
    violations = check_sample("open_write.py.sample")
    assert rules_of(violations) == {"BUILTIN"}
    assert "open" in violations[0].detail


def test_sample_from_os_import_is_detected() -> None:
    violations = check_sample("import_from_os.py.sample")
    assert rules_of(violations) == {"IMPORT"}
    assert "os" in violations[0].detail


def test_sample_import_of_upper_layer_is_detected() -> None:
    violations = check_sample("import_upper_layer.py.sample")
    assert rules_of(violations) == {"IMPORT"}
    assert "downloader.application" in violations[0].detail


def test_sample_relative_import_escaping_the_domain_is_detected() -> None:
    violations = check_sample("relative_escape.py.sample")
    assert rules_of(violations) == {"IMPORT"}
    assert "downloader.infrastructure" in violations[0].detail


def test_sample_global_mutable_state_is_detected() -> None:
    violations = check_sample("global_state.py.sample")
    assert rules_of(violations) == {"GLOBAL_STATE"}
    # _CACHE = {}, _SEEN: list = [] y la sentencia ``global``
    assert len(violations) == 3


def test_sample_clean_module_has_no_violations() -> None:
    assert check_sample("clean_module.py.sample") == []


# --- imports -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "import dataclasses",
        "from dataclasses import dataclass, field",
        "import enum",
        "from enum import Enum, Flag, StrEnum, auto",
        "import typing",
        "from typing import Final, Literal, Protocol",
        "import unicodedata",
        "import ipaddress",
        "from ipaddress import IPv4Address, IPv6Address",
        "import functools",
        "import itertools",
        "import collections",
        "from collections.abc import Sequence, Mapping",
        "import re",
        "import idna",
        "from __future__ import annotations",
        "from downloader.domain import catalog",
        "from downloader.domain.urls.model import ParsedUrl",
        "import downloader.domain.text",
        "from . import model",
        "from .model import ParsedUrl",
        "from .. import catalog",
        "from ..catalog import InvalidReason",
        "from ... import domain",
    ],
)
def test_allowed_imports_pass(code: str) -> None:
    assert check_snippet(code) == []


@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "import os.path",
        "import pathlib",
        "from pathlib import Path",
        "import io",
        "import shutil",
        "import socket",
        "import ssl",
        "import urllib",
        "import urllib.parse",
        "from urllib.parse import urlsplit",
        "import http.client",
        "import threading",
        "import asyncio",
        "import subprocess",
        "import time",
        "import datetime",
        "from datetime import datetime",
        "import random",
        "import json",
        "import importlib",
        "import builtins",
        "import ctypes",
        "import sys",
        "import downloader.application",
        "import downloader.infrastructure.fs",
        "import downloader.ui",
        "from downloader import application",
        "from downloader.application import ports",
        "from downloader.infrastructure import fs",
        "from downloader.ui import app",
        "from downloader.domainx import foo",
        "from .... import application",
        "import urllib3",
        "import truststore",
    ],
)
def test_forbidden_imports_are_detected(code: str) -> None:
    violations = check_snippet(code)
    assert rules_of(violations) == {"IMPORT"}, code


def test_import_inside_a_function_is_also_checked() -> None:
    code = "def f() -> None:\n    import socket\n"
    assert rules_of(check_snippet(code)) == {"IMPORT"}


def test_import_inside_type_checking_block_is_also_checked() -> None:
    code = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import pathlib\n"
    assert rules_of(check_snippet(code)) == {"IMPORT"}


def test_allowed_roots_match_pa01() -> None:
    assert (
        frozenset(
            {
                "dataclasses",
                "enum",
                "typing",
                "unicodedata",
                "ipaddress",
                "functools",
                "itertools",
                "collections",
                "re",
                "idna",
            }
        )
        <= ALLOWED_IMPORT_ROOTS
    )
    assert "os" not in ALLOWED_IMPORT_ROOTS
    assert "socket" not in ALLOWED_IMPORT_ROOTS


# --- funciones integradas prohibidas -----------------------------------------------------------


@pytest.mark.parametrize("name", sorted(FORBIDDEN_BUILTINS))
def test_forbidden_builtin_calls_are_detected(name: str) -> None:
    code = f"def f() -> None:\n    {name}('x')\n"
    violations = check_snippet(code)
    assert rules_of(violations) == {"BUILTIN"}
    assert name in violations[0].detail


def test_builtin_names_cover_plan_list() -> None:
    assert {"open", "print", "input", "eval", "exec"} <= FORBIDDEN_BUILTINS


def test_forbidden_builtin_used_as_value_is_detected() -> None:
    assert rules_of(check_snippet("opener = open\n")) == {"BUILTIN"}


def test_attribute_named_open_is_not_a_builtin_call() -> None:
    # p. ej. un metodo propio llamado ``open`` o ``print`` de un objeto de dominio
    assert check_snippet("def f(x: object) -> None:\n    x.open()\n") == []


def test_shadowed_name_in_function_parameter_is_not_flagged() -> None:
    assert check_snippet("def f(input: str) -> str:\n    return input\n") == []


# --- estado global mutable ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        "A = []",
        "A = {}",
        "A = {1, 2}",
        "A = [x for x in range(3)]",
        "A = {x: 1 for x in range(3)}",
        "A = {x for x in range(3)}",
        "A = list()",
        "A = dict()",
        "A = set()",
        "A = bytearray()",
        "A = collections.defaultdict(list)",
        "A = collections.deque()",
        "A = collections.Counter()",
        "A: list[int] = []",
        "A: dict[str, int] = {}",
        "A = B = []",
        "A += [1]",
        "class C:\n    A = []",
        "class C:\n    A: dict[str, int] = {}",
        "def f() -> None:\n    global A\n    A = 1\n",
    ],
)
def test_global_mutable_state_is_detected(code: str) -> None:
    assert rules_of(check_snippet(code)) == {"GLOBAL_STATE"}, code


@pytest.mark.parametrize(
    "code",
    [
        "A = ()",
        "A = (1, 2)",
        "A = frozenset()",
        "A = frozenset({1, 2})",
        "A = 'texto'",
        "A = 3",
        "A: tuple[str, ...] = ('a',)",
        "def f() -> list[int]:\n    return []\n",
        "def f() -> dict[str, int]:\n    local = {}\n    local['a'] = 1\n    return local\n",
        "class C:\n    A = ()",
        "class C:\n    def m(self) -> None:\n        self.x = []\n",
    ],
)
def test_immutable_or_local_state_passes(code: str) -> None:
    assert check_snippet(code) == [], code


def test_syntax_error_is_reported_not_raised() -> None:
    violations = check_snippet("def f(:\n")
    assert rules_of(violations) == {"SYNTAX"}
