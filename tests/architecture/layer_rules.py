"""Reglas de arquitectura del dominio como analisis de AST (T-02).

* PA-01: ``downloader.domain`` solo importa la biblioteca estandar pura permitida, ``idna`` y
  si mismo; nunca ``application``, ``infrastructure`` ni ``ui``.
* PA-01 / RNF-001-06: sin E/S por funciones integradas (``open``, ``print``, ``input``...).
* AP-05: sin estado global mutable (literales o constructores de colecciones mutables a nivel
  de modulo o de clase, y sentencias ``global``).

El analisis es estatico y no importa ni ejecuta el codigo analizado.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DOMAIN_PACKAGE: Final = "downloader.domain"

# PA-01 (patrones.md). ``__future__`` es una directiva del compilador, no una dependencia.
ALLOWED_IMPORT_ROOTS: Final = frozenset(
    {
        "__future__",
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

# Plan 001 §3 (PA-01) mas ``__import__``/``compile``/``breakpoint``: formas dinamicas de saltarse
# la lista de imports o de ejecutar codigo.
FORBIDDEN_BUILTINS: Final = frozenset(
    {"open", "print", "input", "eval", "exec", "__import__", "compile", "breakpoint"}
)

MUTABLE_CONSTRUCTORS: Final = frozenset(
    {"list", "dict", "set", "bytearray", "defaultdict", "deque", "Counter", "OrderedDict"}
)

_MUTABLE_LITERALS: Final = (
    ast.List,
    ast.Dict,
    ast.Set,
    ast.ListComp,
    ast.DictComp,
    ast.SetComp,
)


@dataclass(frozen=True, slots=True)
class Violation:
    """Una infraccion: archivo, linea, regla (IMPORT, BUILTIN, GLOBAL_STATE, SYNTAX) y detalle."""

    file: str
    line: int
    rule: str
    detail: str


def check_source(source: str, module_name: str, filename: str) -> list[Violation]:
    """Analiza el texto de un modulo del dominio cuyo nombre completo es ``module_name``."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as error:
        return [Violation(filename, error.lineno or 0, "SYNTAX", error.msg)]
    is_package = filename.endswith("__init__.py")
    package = module_name if is_package else module_name.rpartition(".")[0]
    violations: list[Violation] = []
    violations.extend(_check_imports(tree, package, filename))
    violations.extend(_check_builtins(tree, filename))
    violations.extend(_check_global_state(tree, filename))
    return sorted(violations, key=lambda v: (v.line, v.rule, v.detail))


def check_tree(root: Path, base_module: str = DOMAIN_PACKAGE) -> list[Violation]:
    """Analiza todos los ``.py`` bajo ``root``; ``root`` corresponde al paquete ``base_module``."""
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).with_suffix("")
        parts = [part for part in relative.parts if part != "__init__"]
        module_name = ".".join([base_module, *parts])
        violations.extend(check_source(path.read_text(encoding="utf-8"), module_name, str(path)))
    return violations


# --- imports ------------------------------------------------------------------------------------


def _check_imports(tree: ast.AST, package: str, filename: str) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                problem = _import_problem(alias.name)
                if problem:
                    yield Violation(filename, node.lineno, "IMPORT", problem)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from(package, node.level, node.module)
            if base is None:
                yield Violation(
                    filename, node.lineno, "IMPORT", "import relativo fuera del paquete raiz"
                )
                continue
            for alias in node.names:
                full = f"{base}.{alias.name}" if base else alias.name
                problem = _import_problem(full)
                if problem:
                    yield Violation(filename, node.lineno, "IMPORT", problem)


def _resolve_from(package: str, level: int, module: str | None) -> str | None:
    """Nombre absoluto del modulo de un ``from X import``; ``None`` si sale del paquete raiz."""
    if level == 0:
        return module or ""
    parts = package.split(".")
    if level - 1 >= len(parts):
        return None
    anchor = parts[: len(parts) - (level - 1)]
    if module:
        anchor.append(module)
    return ".".join(anchor)


def _import_problem(full_name: str) -> str | None:
    root = full_name.split(".", 1)[0]
    if root == "downloader":
        inside = full_name == DOMAIN_PACKAGE or full_name.startswith(f"{DOMAIN_PACKAGE}.")
        return None if inside else f"{full_name}: el dominio no puede depender de esa capa (PA-01)"
    if root in ALLOWED_IMPORT_ROOTS:
        return None
    return f"{full_name}: modulo fuera de la lista permitida de PA-01"


# --- funciones integradas prohibidas ------------------------------------------------------------


def _check_builtins(tree: ast.Module, filename: str) -> Iterator[Violation]:
    yield from _visit(tree, [_bound_names(tree)], filename)


def _visit(node: ast.AST, scopes: list[frozenset[str]], filename: str) -> Iterator[Violation]:
    if (
        isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id in FORBIDDEN_BUILTINS
        and not any(node.id in scope for scope in scopes)
    ):
        yield Violation(
            filename,
            node.lineno,
            "BUILTIN",
            f"{node.id}: funcion integrada prohibida en el dominio (PA-01)",
        )
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
        # decoradores y valores por defecto se evaluan en el ambito externo
        for outer in _outer_parts(node):
            yield from _visit(outer, scopes, filename)
        inner = [*scopes, _bound_names(node)]
        body = node.body if isinstance(node.body, list) else [node.body]
        for statement in body:
            yield from _visit(statement, inner, filename)
        return
    for child in ast.iter_child_nodes(node):
        yield from _visit(child, scopes, filename)


def _outer_parts(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> list[ast.AST]:
    parts: list[ast.AST] = list(node.args.defaults)
    parts.extend(default for default in node.args.kw_defaults if default is not None)
    if not isinstance(node, ast.Lambda):
        parts.extend(node.decorator_list)
    return parts


def _bound_names(scope: ast.AST) -> frozenset[str]:
    """Nombres ligados directamente en un ambito (argumentos, asignaciones, defs, imports)."""
    names: set[str] = set()
    if isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
        arguments = scope.args
        for arg in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]:
            names.add(arg.arg)
        for extra in (arguments.vararg, arguments.kwarg):
            if extra is not None:
                names.add(extra.arg)
        statements: list[ast.AST] = (
            list(scope.body) if isinstance(scope.body, list) else [scope.body]
        )
    else:
        statements = list(getattr(scope, "body", []))
    pending = statements
    while pending:
        node = pending.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
            continue  # su cuerpo es otro ambito
        if isinstance(node, ast.Lambda):
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
            names.add(node.id)
        if isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".", 1)[0])
        pending.extend(ast.iter_child_nodes(node))
    return frozenset(names)


# --- estado global mutable ----------------------------------------------------------------------


def _check_global_state(tree: ast.Module, filename: str) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            names = ", ".join(node.names)
            yield Violation(
                filename, node.lineno, "GLOBAL_STATE", f"global {names}: estado global (AP-05)"
            )
    yield from _mutable_bindings(tree.body, filename)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield from _mutable_bindings(node.body, filename)


def _mutable_bindings(body: list[ast.stmt], filename: str) -> Iterator[Violation]:
    for statement in body:
        value: ast.expr | None = None
        if isinstance(statement, ast.Assign | ast.AugAssign | ast.AnnAssign):
            value = statement.value
        if value is not None and _is_mutable_value(value) and not _only_dunder_all(statement):
            yield Violation(
                filename,
                statement.lineno,
                "GLOBAL_STATE",
                "coleccion mutable a nivel de modulo o de clase (AP-05)",
            )


def _is_mutable_value(value: ast.expr) -> bool:
    if isinstance(value, _MUTABLE_LITERALS):
        return True
    if isinstance(value, ast.Call):
        func = value.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        return name in MUTABLE_CONSTRUCTORS
    return False


def _only_dunder_all(statement: ast.stmt) -> bool:
    """``__all__ = [...]`` es una convencion de exportacion, no estado que se modifique."""
    if isinstance(statement, ast.Assign):
        targets = statement.targets
    elif isinstance(statement, ast.AugAssign | ast.AnnAssign):
        targets = [statement.target]
    else:
        return False
    return all(isinstance(t, ast.Name) and t.id == "__all__" for t in targets)
