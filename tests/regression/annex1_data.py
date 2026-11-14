"""Los 55 ejemplos del anexo 1 de las reglas de negocio, como datos (T-21).

Fuente: ``docs/01-requerimientos/reglas-negocio.md`` (Anexo 1). Carpeta destino ``D:\\Descargas``.
Cada caso describe las líneas del lote, la respuesta del servidor (si la hay), lo que ya existe
en disco y el resultado esperado de **cada línea**. Los ejemplos que dependen de la red (22, 48 y
53) o del disco real (18, 25, 26, 54) se prueban aquí en su parte de dominio; la 002 los repite en
el equipo real.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from downloader.domain.catalog import FailureCode, InvalidReason, WarningCode
from downloader.domain.paths.collisions import EntryKind
from downloader.domain.paths.response import ServerResponse
from downloader.domain.result import Ok
from downloader.domain.urls.parser import parse_url

DESTINATION = "D:\\Descargas"
A1 = frozenset({WarningCode.A1})
A2 = frozenset({WarningCode.A2})
NO_WARNINGS: frozenset[WarningCode] = frozenset()
FILE = EntryKind.FILE
LINK = EntryKind.REPARSE_POINT


@dataclass(frozen=True, slots=True)
class Path:
    """La línea es válida y recibe esta ruta (y estos avisos)."""

    full_path: str
    warnings: frozenset[WarningCode] = NO_WARNINGS


@dataclass(frozen=True, slots=True)
class Fails:
    """La línea es válida pero el cálculo de la ruta falla con este código."""

    code: FailureCode


@dataclass(frozen=True, slots=True)
class Invalid:
    """La línea se rechaza en la validación previa con este motivo."""

    reason: InvalidReason


type Expected = Path | Fails | Invalid


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    lines: tuple[str, ...]
    expected: tuple[Expected, ...]  # uno por línea, en el orden de ``lines``
    responses: tuple[ServerResponse | None, ...] = ()  # uno por línea; vacío = ninguna
    disk: tuple[tuple[tuple[str, ...], EntryKind], ...] = ()
    internal: bool = False  # la primera línea es una dirección interna (requiere confirmación)
    corrected_no_scheme: int = 0
    corrected_encoded: int = 0
    any_order: bool = False  # "en cualquier orden": el resultado por URL no cambia
    note: str = field(default="", compare=False)


def p(path: str, warnings: frozenset[WarningCode] = NO_WARNINGS) -> Path:
    return Path(f"{DESTINATION}\\{path}", warnings)


def resp(filename: str | None = None, content_type: str | None = None) -> ServerResponse:
    return ServerResponse(filename=filename, content_type=content_type)


def _final(url: str) -> ServerResponse:
    parsed = parse_url(url)
    assert isinstance(parsed, Ok)
    return ServerResponse(content_type="application/pdf", final_url=parsed.value)


LONG_300 = "a" * 296 + ".pdf"

CASES: tuple[Case, ...] = (
    Case(
        "EJ-01",
        ("https://sitio.com/docs/2024/informe.pdf?v=2",),
        (p("sitio.com\\docs\\2024\\informe.pdf"),),
    ),
    Case("EJ-02", ("https://Sitio.COM:443/Docs/A.pdf",), (p("sitio.com\\Docs\\A.pdf"),)),
    Case("EJ-03", ("http://sitio.com:8080/a/b.zip",), (p("sitio.com_8080\\a\\b.zip"),)),
    Case(
        "EJ-04",
        ("https://sitio.com/a/../../../Windows/System32/x.dll",),
        (p("sitio.com\\a\\Windows\\System32\\x.dll", A1),),
    ),
    Case(
        "EJ-05",
        ("https://sitio.com/%2e%2e/%2e%2e/secreto.txt",),
        (p("sitio.com\\secreto.txt"),),
    ),
    Case("EJ-06", ("https://sitio.com/a\\..\\..\\b.txt",), (p("sitio.com\\a\\b.txt"),)),
    Case(
        "EJ-07",
        ("https://sitio.com/a%5c..%5c..%5cb.txt",),
        (p("sitio.com\\a_.._.._b.txt"),),
    ),
    Case("EJ-08", ("https://sitio.com/CON/aux.txt",), (p("sitio.com\\CON_\\aux_.txt"),)),
    Case(
        "EJ-09",
        ("https://sitio.com/a%3Ab/c%2Ad%22.pdf",),
        (p("sitio.com\\a_b\\c_d_.pdf"),),
    ),
    Case(
        "EJ-10",
        ("https://sitio.com/carpeta./archivo%20.txt%20",),
        (p("sitio.com\\carpeta\\archivo .txt"),),
    ),
    Case(
        "EJ-11",
        ("https://sitio.com/Informe%20A%C3%B1o/Bogot%C3%A1.pdf",),
        (p("sitio.com\\Informe Año\\Bogotá.pdf"),),
    ),
    Case(
        "EJ-12",
        ("https://sitio.com/docs/",),
        (p("sitio.com\\docs\\reporte final.pdf"),),
        responses=(resp(filename="reporte final.pdf"),),
    ),
    Case(
        "EJ-13",
        ("https://sitio.com/docs/",),
        (p("sitio.com\\docs\\index.pdf"),),
        responses=(resp(content_type="application/pdf"),),
    ),
    Case(
        "EJ-14",
        ("https://sitio.com",),
        (p("sitio.com\\index"),),
        responses=(resp(content_type="application/x-desconocido"),),
    ),
    Case(
        "EJ-15",
        ("https://sitio.com/descarga?id=7",),
        (p("sitio.com\\malo.exe", A1),),
        responses=(resp(filename="..\\..\\malo.exe"),),
    ),
    Case(
        "EJ-16",
        ("https://sitio.com/descarga?id=8",),
        (p("sitio.com\\CON_.pdf"),),
        responses=(resp(filename="CON.pdf"),),
    ),
    Case(
        "EJ-17",
        ("https://sitio.com/factura%E2%80%AEfdp.exe",),
        (p("sitio.com\\facturafdp.exe", A1),),
    ),
    Case(
        "EJ-18",
        ("https://sitio.com/a.pdf",),
        (p("sitio.com\\a (1).pdf"),),
        disk=((("sitio.com", "a.pdf"), FILE),),
    ),
    Case(
        "EJ-19",
        ("https://sitio.com/x/A.pdf?v=1", "https://sitio.com/x/a.pdf?v=2"),
        (p("sitio.com\\x\\A.pdf"), p("sitio.com\\x\\a (1).pdf")),
        note="solo en orden directo: depende del orden por diseño",
    ),
    Case(
        "EJ-20",
        ("www.sitio.com/a.pdf",),
        (p("www.sitio.com\\a.pdf"),),
        corrected_no_scheme=1,
    ),
    Case("EJ-21", ("https://sitio.com//a///b.pdf",), (p("sitio.com\\a\\b.pdf"),)),
    Case(
        "EJ-22",
        ("https://corto.com/x",),
        (p("corto.com\\x.pdf"),),
        responses=(_final("https://cdn.com/f/real.pdf"),),
    ),
    Case(
        "EJ-23",
        ("https://[::1]:8443/a.pdf",),
        (p("[__1]_8443\\a.pdf"),),
        internal=True,
    ),
    Case(
        "EJ-24",
        ("https://bogotá.com/a.pdf",),
        (p("xn--bogot-1qa.com\\a.pdf"),),
        corrected_encoded=1,
    ),
    Case(
        "EJ-25",
        ("https://sitio.com/docs/a.pdf",),
        (Fails(FailureCode.F27),),
        disk=((("sitio.com", "docs"), FILE),),
    ),
    Case(
        "EJ-26",
        ("https://sitio.com/x/a.pdf",),
        (Fails(FailureCode.F24),),
        disk=((("sitio.com", "x"), LINK),),
    ),
    Case("EJ-27", ("https://2130706433/a.pdf",), (p("2130706433\\a.pdf"),), internal=True),
    Case(
        "EJ-28",
        ("https://169.254.169.254/latest/meta-data",),
        (Invalid(InvalidReason.I06),),
    ),
    Case(
        "EJ-29",
        ("www.sitio.com/ir?u=http://x.com/a.pdf",),
        (p("www.sitio.com\\ir.pdf"),),
        responses=(resp(content_type="application/pdf"),),
        corrected_no_scheme=1,
    ),
    Case(
        "EJ-30",
        ("sitio.com:8080/a.pdf",),
        (p("sitio.com_8080\\a.pdf"),),
        corrected_no_scheme=1,
    ),
    Case("EJ-31", ("https://sitio.com/con.tar.gz",), (p("sitio.com\\con_.tar.gz"),)),
    Case("EJ-32", ("https://nul.com/a.pdf",), (p("nul_.com\\a.pdf"),)),
    Case("EJ-33", ("https://sitio.com/con%20.txt",), (p("sitio.com\\con_ .txt"),)),
    Case("EJ-34", ("https://sitio.com/CONIN$/x.txt",), (p("sitio.com\\CONIN$_\\x.txt"),)),
    Case("EJ-35", ("https://sitio.com\\@127.0.0.1/a.pdf",), (Invalid(InvalidReason.I03),)),
    Case("EJ-36", ("https://sitio.com#@127.0.0.1/a.pdf",), (Invalid(InvalidReason.I03),)),
    Case("EJ-37", ("https://sitio.com/a%2fb/c.pdf",), (p("sitio.com\\a_b\\c.pdf"),)),
    Case("EJ-38", ("https://sitio.com/a%00b.pdf",), (p("sitio.com\\a_b.pdf"),)),
    Case(
        "EJ-39",
        ("https://sitio.com/%252e%252e/x.pdf",),
        (p("sitio.com\\%2e%2e\\x.pdf"),),
    ),
    Case(
        "EJ-40",
        ("https://sitio.com/a/b/..",),
        (p("sitio.com\\a\\b\\index.html"),),
        responses=(resp(content_type="text/html"),),
    ),
    Case(
        "EJ-41",
        ("https://sitio.com/Informe Final/año 2024.pdf",),
        (p("sitio.com\\Informe Final\\año 2024.pdf"),),
        corrected_encoded=1,
    ),
    Case(
        "EJ-42",
        ("https://sitio.com/docs", "https://sitio.com/docs/x.pdf"),
        (p("sitio.com\\docs (1)"), p("sitio.com\\docs\\x.pdf")),
        any_order=True,
    ),
    Case(
        "EJ-43",
        (f"https://sitio.com/{LONG_300}",),
        (Fails(FailureCode.F28),),
    ),
    Case("EJ-44", ("https://localhost./a.pdf",), (p("localhost\\a.pdf"),), internal=True),
    Case("EJ-45", ("https://[2002:7f00:1::]/a.pdf",), (Invalid(InvalidReason.I06),)),
    Case(
        "EJ-46",
        ("https://sitio.com/descarga",),
        (p("sitio.com\\descarga.html"),),
        responses=(resp(content_type="text/html"),),
    ),
    Case(
        "EJ-47",
        ("https://sitio.com/informe.pdf",),
        (p("sitio.com\\informe.pdf", A2),),
        responses=(resp(content_type="text/html"),),
    ),
    Case(
        "EJ-48",
        ("https://archivos.miempresa.com/a.pdf",),
        (p("archivos.miempresa.com\\a.pdf"),),
        note="la validación previa no resuelve nombres: se detecta en el motor (F-30, spec 002)",
    ),
    Case("EJ-49", ("https://sitio.com?email=a@b.com",), (p("sitio.com\\index"),)),
    Case(
        "EJ-50",
        ("https://a.com/x.pdf https://b.com/y.pdf",),
        (Invalid(InvalidReason.I09),),
    ),
    Case(
        "EJ-51",
        ("https://sitio.com/a.pdf?ruta=c:\\temp",),
        (p("sitio.com\\a.pdf"),),
        corrected_encoded=1,
    ),
    Case("EJ-52", ("https://sitio.com?q=a\\b",), (Invalid(InvalidReason.I03),)),
    Case(
        "EJ-53",
        ("https://publico.com/f",),
        (p("publico.com\\f.pdf"),),
        responses=(_final("https://x.corp/f.pdf"),),
        note="el salto a x.corp es interno: la 002 lo detiene con F-30 (solo se prueba el dominio)",
    ),
    Case(
        "EJ-54",
        (),
        (),
        note="carpeta destino: se prueba con evaluate_destination, no con una URL",
    ),
    Case("EJ-55", ("https://sitio .com/a.pdf",), (Invalid(InvalidReason.I03),)),
)
