"""Ruta resultante (RN-008 a RN-016, D-07; CA-001-50 a 53 y 60; ejemplos del anexo 1)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.catalog import FailureCode, WarningCode
from downloader.domain.paths import target as target_module
from downloader.domain.paths.collisions import (
    EntryKind,
    InMemoryDiskEntries,
    PathReservations,
)
from downloader.domain.paths.failure import PathFailure
from downloader.domain.paths.length import PathLimits
from downloader.domain.paths.response import ServerResponse
from downloader.domain.paths.target import (
    PathEnvironment,
    TargetPath,
    compute_target_path,
    is_contained,
    join_path,
    normalize_destination,
)
from downloader.domain.result import Ok
from downloader.domain.urls import ParsedUrl
from downloader.domain.urls.parser import parse_url

DEST = "D:\\Descargas"
FILE = EntryKind.FILE
LINK = EntryKind.REPARSE_POINT
A1 = frozenset({WarningCode.A1})
A2 = frozenset({WarningCode.A2})
NONE: frozenset[WarningCode] = frozenset()


def make_env(
    entries: dict[tuple[str, ...], EntryKind] | None = None,
    required: frozenset[str] = frozenset(),
    *,
    long_paths: bool = False,
) -> PathEnvironment:
    return PathEnvironment(
        InMemoryDiskEntries(entries), PathReservations(required), PathLimits(long_paths)
    )


def compute(
    text: str,
    response: ServerResponse | None = None,
    env: PathEnvironment | None = None,
    destination: str = DEST,
) -> TargetPath | PathFailure:
    parsed = parse_url(text)
    assert isinstance(parsed, Ok), text
    return compute_target_path(destination, parsed.value, response, env or make_env())


def path_of(
    text: str,
    response: ServerResponse | None = None,
    env: PathEnvironment | None = None,
    destination: str = DEST,
) -> str:
    result = compute(text, response, env, destination)
    assert isinstance(result, TargetPath), result
    return result.full_path


# --- Ejemplos del anexo 1 ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "https://sitio.com/docs/2024/informe.pdf?v=2",
            "D:\\Descargas\\sitio.com\\docs\\2024\\informe.pdf",
        ),
        ("https://Sitio.COM:443/Docs/A.pdf", "D:\\Descargas\\sitio.com\\Docs\\A.pdf"),
        ("http://sitio.com:8080/a/b.zip", "D:\\Descargas\\sitio.com_8080\\a\\b.zip"),
        ("https://sitio.com/%2e%2e/%2e%2e/secreto.txt", "D:\\Descargas\\sitio.com\\secreto.txt"),
        ("https://sitio.com/a\\..\\..\\b.txt", "D:\\Descargas\\sitio.com\\a\\b.txt"),
        ("https://sitio.com/a%5c..%5c..%5cb.txt", "D:\\Descargas\\sitio.com\\a_.._.._b.txt"),
        ("https://sitio.com/CON/aux.txt", "D:\\Descargas\\sitio.com\\CON_\\aux_.txt"),
        ("https://sitio.com/a%3Ab/c%2Ad%22.pdf", "D:\\Descargas\\sitio.com\\a_b\\c_d_.pdf"),
        (
            "https://sitio.com/carpeta./archivo%20.txt%20",
            "D:\\Descargas\\sitio.com\\carpeta\\archivo .txt",
        ),
        (
            "https://sitio.com/Informe%20A%C3%B1o/Bogot%C3%A1.pdf",
            "D:\\Descargas\\sitio.com\\Informe Año\\Bogotá.pdf",
        ),
        ("www.sitio.com/a.pdf", "D:\\Descargas\\www.sitio.com\\a.pdf"),
        ("https://sitio.com//a///b.pdf", "D:\\Descargas\\sitio.com\\a\\b.pdf"),
        ("https://[::1]:8443/a.pdf", "D:\\Descargas\\[__1]_8443\\a.pdf"),
        ("https://bogotá.com/a.pdf", "D:\\Descargas\\xn--bogot-1qa.com\\a.pdf"),
        ("sitio.com:8080/a.pdf", "D:\\Descargas\\sitio.com_8080\\a.pdf"),
        ("https://sitio.com/con.tar.gz", "D:\\Descargas\\sitio.com\\con_.tar.gz"),
        ("https://nul.com/a.pdf", "D:\\Descargas\\nul_.com\\a.pdf"),
        ("https://sitio.com/con%20.txt", "D:\\Descargas\\sitio.com\\con_ .txt"),
        ("https://sitio.com/CONIN$/x.txt", "D:\\Descargas\\sitio.com\\CONIN$_\\x.txt"),
        ("https://sitio.com/a%2fb/c.pdf", "D:\\Descargas\\sitio.com\\a_b\\c.pdf"),
        ("https://sitio.com/a%00b.pdf", "D:\\Descargas\\sitio.com\\a_b.pdf"),
        ("https://sitio.com/%252e%252e/x.pdf", "D:\\Descargas\\sitio.com\\%2e%2e\\x.pdf"),
        (
            "https://sitio.com/Informe Final/año 2024.pdf",
            "D:\\Descargas\\sitio.com\\Informe Final\\año 2024.pdf",
        ),
        ("https://sitio.com?email=a@b.com", "D:\\Descargas\\sitio.com\\index"),
        ("https://sitio.com/a.pdf?ruta=c:\\temp", "D:\\Descargas\\sitio.com\\a.pdf"),
        ("https://localhost./a.pdf", "D:\\Descargas\\localhost\\a.pdf"),
    ],
)
def test_annex_1_examples_without_a_server_response(text: str, expected: str) -> None:
    assert path_of(text) == expected


def test_example_4_dot_dot_is_not_resolved_and_warns() -> None:
    result = compute("https://sitio.com/a/../../../Windows/System32/x.dll")
    assert isinstance(result, TargetPath)
    assert result.full_path == "D:\\Descargas\\sitio.com\\a\\Windows\\System32\\x.dll"
    assert result.warnings == A1


def test_example_15_server_name_with_directories() -> None:
    result = compute("https://sitio.com/descarga?id=7", ServerResponse(filename="..\\..\\malo.exe"))
    assert isinstance(result, TargetPath)
    assert result.full_path == "D:\\Descargas\\sitio.com\\malo.exe"
    assert result.warnings == A1


def test_example_16_reserved_server_name() -> None:
    assert path_of("https://sitio.com/descarga?id=8", ServerResponse(filename="CON.pdf")) == (
        "D:\\Descargas\\sitio.com\\CON_.pdf"
    )


def test_example_17_invisible_character_cannot_hide_the_executable() -> None:
    result = compute("https://sitio.com/factura%E2%80%AEfdp.exe")
    assert isinstance(result, TargetPath)
    assert result.full_path == "D:\\Descargas\\sitio.com\\facturafdp.exe"
    assert result.warnings == A1


def test_example_12_to_14_names_from_server_type_and_index() -> None:
    assert path_of("https://sitio.com/docs/", ServerResponse(filename="reporte final.pdf")) == (
        "D:\\Descargas\\sitio.com\\docs\\reporte final.pdf"
    )
    assert path_of("https://sitio.com/docs/", ServerResponse(content_type="application/pdf")) == (
        "D:\\Descargas\\sitio.com\\docs\\index.pdf"
    )
    assert path_of("https://sitio.com") == "D:\\Descargas\\sitio.com\\index"


def test_example_22_redirect_does_not_change_the_folders() -> None:
    response = ServerResponse(
        content_type="application/pdf", final_url=_parsed("https://cdn.com/f/real.pdf")
    )
    assert path_of("https://corto.com/x", response) == "D:\\Descargas\\corto.com\\x.pdf"


def test_example_40_and_46_and_47_html_cases() -> None:
    html = ServerResponse(content_type="text/html")
    result = compute("https://sitio.com/a/b/..", html)
    assert isinstance(result, TargetPath)
    assert result.full_path == "D:\\Descargas\\sitio.com\\a\\b\\index.html"
    assert result.warnings == NONE  # termina en .html: sin A-2
    assert path_of("https://sitio.com/descarga", html) == "D:\\Descargas\\sitio.com\\descarga.html"
    result = compute("https://sitio.com/informe.pdf", html)
    assert isinstance(result, TargetPath)
    assert result.full_path == "D:\\Descargas\\sitio.com\\informe.pdf"
    assert result.warnings == A2


def test_ca_001_60_absolute_path_inside_the_url_stays_inside() -> None:
    result = compute("https://sitio.com/C:/Windows/x.dll")
    assert isinstance(result, TargetPath)
    assert result.full_path == "D:\\Descargas\\sitio.com\\C_\\Windows\\x.dll"
    assert result.warnings == A1


def test_example_43_name_of_300_characters_is_f28() -> None:
    assert compute("https://sitio.com/" + "a" * 296 + ".pdf") == PathFailure(FailureCode.F28)
    assert isinstance(
        compute("https://sitio.com/" + "a" * 251 + ".pdf", env=make_env(long_paths=True)),
        TargetPath,
    )


def _parsed(text: str) -> ParsedUrl:
    result = parse_url(text)
    assert isinstance(result, Ok)
    return result.value


# --- Colisiones (ejemplos 18, 19, 25, 26, 42) ----------------------------------------------------


def test_example_18_existing_file_gets_a_suffix() -> None:
    env = make_env({("sitio.com", "a.pdf"): FILE})
    assert path_of("https://sitio.com/a.pdf", env=env) == "D:\\Descargas\\sitio.com\\a (1).pdf"


def test_example_19_same_batch_two_names_differing_in_case() -> None:
    env = make_env()
    first = path_of("https://sitio.com/x/A.pdf?v=1", env=env)
    second = path_of("https://sitio.com/x/a.pdf?v=2", env=env)
    assert (first, second) == (
        "D:\\Descargas\\sitio.com\\x\\A.pdf",
        "D:\\Descargas\\sitio.com\\x\\a (1).pdf",
    )


def test_example_25_file_where_a_folder_goes_is_f27() -> None:
    env = make_env({("sitio.com", "docs"): FILE})
    assert compute("https://sitio.com/docs/a.pdf", env=env) == PathFailure(FailureCode.F27)


def test_example_26_junction_in_an_intermediate_folder_is_f24() -> None:
    env = make_env({("sitio.com", "x"): LINK})
    assert compute("https://sitio.com/x/a.pdf", env=env) == PathFailure(FailureCode.F24)


@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_example_42_folder_prevails_in_any_order(order: tuple[int, int]) -> None:
    urls = ["https://sitio.com/docs", "https://sitio.com/docs/x.pdf"]
    env = make_env(required=frozenset({"SITIO.COM", "SITIO.COM\\DOCS"}))
    paths = {index: path_of(urls[index], env=env) for index in order}
    assert paths[0] == "D:\\Descargas\\sitio.com\\docs (1)"
    assert paths[1] == "D:\\Descargas\\sitio.com\\docs\\x.pdf"


# --- Orden de fallos (S-001-07; CA-001-51 a 53) --------------------------------------------------


def test_ca_001_51_long_name_under_a_junction_is_f28_not_f24() -> None:
    env = make_env({("sitio.com", "x"): LINK})
    assert compute("https://sitio.com/x/" + "a" * 300 + ".pdf", env=env) == PathFailure(
        FailureCode.F28
    )


def test_ca_001_52_junction_above_a_file_with_a_folder_name_is_f24() -> None:
    env = make_env({("sitio.com", "x"): LINK, ("sitio.com", "x", "y"): FILE})
    assert compute("https://sitio.com/x/y/a.pdf", env=env) == PathFailure(FailureCode.F24)


def test_ca_001_53_file_with_a_folder_name_beats_a_path_too_long() -> None:
    env = make_env({("sitio.com", "docs"): FILE})
    too_long = "https://sitio.com/docs/" + "s" * 200 + "/a.pdf"
    assert compute(too_long, env=env) == PathFailure(FailureCode.F27)
    assert compute(too_long, env=make_env()) == PathFailure(FailureCode.F25)


def test_the_suffix_counts_for_the_length_check() -> None:
    """CA-001-74: el sufijo lleva el nombre a 64 y la ruta a 263."""
    folder_segment = "s" * 175  # carpeta de 198
    name = "n" * 56 + ".pdf"  # 60 caracteres: la ruta final mide 259
    url = f"https://sitio.com/{folder_segment}/{name}"
    assert isinstance(compute(url), TargetPath)
    env = make_env({("sitio.com", folder_segment, name): FILE})
    assert compute(url, env=env) == PathFailure(FailureCode.F25)  # con " (1)": 263


def test_with_long_paths_the_limit_is_32000() -> None:
    url = "https://sitio.com/" + "/".join(["s" * 200] * 8) + "/a.pdf"  # ~1 600 caracteres
    assert compute(url) == PathFailure(FailureCode.F25)
    assert isinstance(compute(url, env=make_env(long_paths=True)), TargetPath)


# --- Un fallo no reserva nada --------------------------------------------------------------------


def test_a_failed_item_does_not_keep_its_name() -> None:
    env = make_env({("sitio.com", "docs"): FILE})
    assert isinstance(compute("https://sitio.com/docs/a.pdf", env=env), PathFailure)
    assert not env.reservations.is_reserved(("sitio.com", "docs"), "a.pdf")
    env2 = make_env()
    assert compute("https://sitio.com/" + "a" * 300, env=env2) == PathFailure(FailureCode.F28)
    assert compute("https://sitio.com/" + "a" * 300, env=make_env(long_paths=True)) == PathFailure(
        FailureCode.F28
    )  # F-28 no depende de las rutas largas


def test_a_successful_item_reserves_its_name_for_the_next() -> None:
    env = make_env()
    assert path_of("https://sitio.com/a.pdf", env=env).endswith("\\a.pdf")
    assert path_of("https://sitio.com/a.pdf", env=env).endswith("\\a (1).pdf")
    assert path_of("https://sitio.com/a.pdf", env=env).endswith("\\a (2).pdf")


def test_a_failure_in_the_middle_leaves_the_numbering_without_gaps() -> None:
    env = make_env()
    assert path_of("https://sitio.com/a.pdf", env=env).endswith("\\a.pdf")
    assert path_of("https://sitio.com/a.pdf", env=env).endswith("\\a (1).pdf")
    too_long = "https://sitio.com/" + "s" * 250 + "/a.pdf"
    assert isinstance(compute(too_long, env=env), PathFailure)
    assert path_of("https://sitio.com/a.pdf", env=env).endswith("\\a (2).pdf")


# --- Avisos (RN-021) -----------------------------------------------------------------------------


def test_warnings_are_computed_on_the_final_name_with_its_suffix() -> None:
    env = make_env({("sitio.com", ".exe"): FILE})
    result = compute("https://sitio.com/.exe", env=env)
    assert isinstance(result, TargetPath)
    assert result.file_name == ".exe (1)"
    assert result.warnings == NONE  # CA-001-103b: ``exe (1)`` no está en la lista


def test_both_warnings_together() -> None:
    result = compute("https://sitio.com/setup.exe", ServerResponse(content_type="text/html"))
    assert isinstance(result, TargetPath)
    assert result.warnings == frozenset({WarningCode.A1, WarningCode.A2})


def test_no_response_means_no_html_warning() -> None:
    result = compute("https://sitio.com/informe.pdf")
    assert isinstance(result, TargetPath)
    assert result.warnings == NONE


# --- Carpeta destino -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("destination", "expected"),
    [
        ("D:\\Descargas", "D:\\Descargas\\sitio.com\\a.pdf"),
        ("D:\\Descargas\\", "D:\\Descargas\\sitio.com\\a.pdf"),
        ("D:\\Descargas\\\\", "D:\\Descargas\\sitio.com\\a.pdf"),
        ("D:/Descargas/", "D:\\Descargas\\sitio.com\\a.pdf"),
        ("d:\\descargas", "d:\\descargas\\sitio.com\\a.pdf"),
        ("D:\\", "D:\\sitio.com\\a.pdf"),
        ("D:", "D:\\sitio.com\\a.pdf"),
        ("\\\\servidor\\recurso", "\\\\servidor\\recurso\\sitio.com\\a.pdf"),
        ("D:\\Mis Descargas (2024)", "D:\\Mis Descargas (2024)\\sitio.com\\a.pdf"),
    ],
)
def test_destination_forms(destination: str, expected: str) -> None:
    assert path_of("https://sitio.com/a.pdf", destination=destination) == expected


def test_normalize_destination_and_join_path() -> None:
    assert normalize_destination("D:\\Descargas\\") == "D:\\Descargas"
    assert normalize_destination("D:\\") == "D:\\"
    assert normalize_destination("D:/x/") == "D:\\x"
    assert join_path("D:\\", ("a", "b")) == "D:\\a\\b"
    assert join_path("D:\\x", ("a",)) == "D:\\x\\a"
    assert join_path("D:\\x", ()) == "D:\\x"


def test_the_returned_parts_are_relative_to_the_destination() -> None:
    result = compute("https://sitio.com/docs/2024/informe.pdf")
    assert isinstance(result, TargetPath)
    assert result.folder_parts == ("sitio.com", "docs", "2024")
    assert result.file_name == "informe.pdf"


# --- Guarda de contención (RN-013 a) -------------------------------------------------------------


@pytest.mark.parametrize(
    "unsafe",
    ["", ".", "..", "a.", "a ", "a/b", "a\\b", "a:b", "a*", "a?", 'a"', "a<", "a>", "a|",
     "a\x00", "a\x1f",
     "a\u202eb", "con", "NUL.txt", "x" * 256],
)  # fmt: skip
def test_the_guard_rejects_any_unsafe_component(unsafe: str) -> None:
    assert is_contained(("sitio.com",), unsafe) is False
    assert is_contained(("sitio.com", unsafe), "a.pdf") is False


def test_the_guard_accepts_normal_components() -> None:
    assert is_contained(("sitio.com", "docs", "2024"), "informe (1).pdf") is True
    assert is_contained(("sitio.com",), ".htaccess") is True
    assert is_contained(("[__1]_8443",), "COM10.txt") is True


def test_if_the_guard_ever_fails_the_item_fails_and_reserves_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(target_module, "is_contained", lambda *_: False)
    env = make_env()
    assert compute("https://sitio.com/a.pdf", env=env) == PathFailure(FailureCode.F24)
    assert not env.reservations.is_reserved(("sitio.com",), "a.pdf")


# --- Propiedades (CA-001-50, S-001-13, RNF-001-04) -----------------------------------------------

PIECES = st.sampled_from(
    ["a", "con", "nul", ".", "..", " ", "%2e", "%2E", "%20", "%2f", "%5c", "%00", "%E2%80%AE",
     "%C3%B1",
     "%FF", "ñ", "x.pdf", "\\", "/", "?", "#", "$", "*", "a" * 120]
)  # fmt: skip
URLS = st.lists(PIECES, max_size=8).map(lambda pieces: "https://a.com/" + "".join(pieces))
NAMES = st.one_of(st.none(), st.lists(PIECES, max_size=5).map("".join))
TYPES = st.sampled_from([None, "text/html", "application/pdf", "x/y"])
DISK_PATHS = st.sampled_from([("a.com",), ("a.com", "a"), ("a.com", "x.pdf"), ("a.com", "index")])
DISKS = st.dictionaries(DISK_PATHS, st.sampled_from(list(EntryKind)), max_size=3)


@given(URLS, NAMES, TYPES, DISKS, st.booleans())
def test_ca_001_50_the_result_is_inside_the_destination_or_a_known_failure(
    text: str,
    server_name: str | None,
    content_type: str | None,
    entries: dict[tuple[str, ...], EntryKind],
    long_paths: bool,
) -> None:
    parsed = parse_url(text)
    if not isinstance(parsed, Ok):
        return
    response = ServerResponse(filename=server_name, content_type=content_type)
    env = make_env(entries, long_paths=long_paths)
    result = compute_target_path(DEST, parsed.value, response, env)
    if isinstance(result, PathFailure):
        assert result.code in {FailureCode.F24, FailureCode.F25, FailureCode.F27, FailureCode.F28}
        return
    assert result.full_path.startswith(DEST + "\\")
    relative = result.full_path[len(DEST) + 1 :].split("\\")
    assert relative == [*result.folder_parts, result.file_name]
    assert is_contained(result.folder_parts, result.file_name)
    assert len(result.full_path) <= env.limits.max_path_length
    assert "/" not in result.full_path
    assert result.full_path.count(":") == 1  # solo la de la unidad


@given(URLS, NAMES, TYPES)
def test_same_inputs_same_result(
    text: str, server_name: str | None, content_type: str | None
) -> None:
    parsed = parse_url(text)
    if not isinstance(parsed, Ok):
        return
    response = ServerResponse(filename=server_name, content_type=content_type)
    first = compute_target_path(DEST, parsed.value, response, make_env())
    second = compute_target_path(DEST, parsed.value, response, make_env())
    assert first == second
