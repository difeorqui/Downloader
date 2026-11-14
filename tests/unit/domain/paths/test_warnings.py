"""Avisos A-1 y A-2 (RN-021; CA-001-101 a 105, 103b y 104; glosario 2.3)."""

from __future__ import annotations

import pytest

from downloader.domain.catalog import WarningCode
from downloader.domain.paths.sanitize import sanitize_name
from downloader.domain.warnings import (
    DANGEROUS_EXTENSIONS,
    classify_warnings,
    has_dangerous_extension,
    windows_extension,
)

A1 = frozenset({WarningCode.A1})
A2 = frozenset({WarningCode.A2})
NONE: frozenset[WarningCode] = frozenset()

# Glosario 2.3 escrito a mano, por grupos.
GLOSSARY_2_3 = {
    "ejecutables": "exe com scr pif cpl dll sys msi msp msix msixbundle appx appxbundle "
    "appinstaller application",
    "guiones": "bat cmd ps1 psm1 psd1 vbs vbe js jse wsf wsh hta",
    "accesos directos": "lnk url scf inf reg rdp settingcontent-ms library-ms diagcab msc",
    "contenedores": "jar chm iso img vhd vhdx",
    "office con macros": "docm dotm xlsm xltm xlam pptm ppam",
}
ALL_EXTENSIONS = [ext for group in GLOSSARY_2_3.values() for ext in group.split()]


def test_the_table_has_the_50_extensions_of_the_glossary() -> None:
    assert [len(group.split()) for group in GLOSSARY_2_3.values()] == [15, 12, 10, 6, 7]
    assert len(ALL_EXTENSIONS) == 50
    assert sorted(DANGEROUS_EXTENSIONS) == sorted(ALL_EXTENSIONS)
    assert len(set(DANGEROUS_EXTENSIONS)) == 50


@pytest.mark.parametrize("extension", ALL_EXTENSIONS)
def test_each_listed_extension_warns_in_lower_and_upper_case(extension: str) -> None:
    """CA-001-101."""
    assert classify_warnings(f"archivo.{extension}", None) == A1
    assert classify_warnings(f"archivo.{extension.upper()}", None) == A1
    assert classify_warnings(f"ARCHIVO.{extension.title()}", None) == A1


@pytest.mark.parametrize(
    "name",
    [
        "a.json",
        "a.docx",
        "a.pptx",
        "a.xlsx",
        "a.jsx",
        "a.msixx",
        "exe",  # sin punto no hay extensión
        "informe.exe.pdf",  # solo cuenta la última
        "a.pdf",
        "a.exe2",
        "a.xexe",
        "a.exe (1)",  # CA-001-103b: el sufijo forma parte de la extensión según Windows
        ".exe (1)",
        "a.",
        "",
        ".",
        "..",
        "a.ex e",
    ],
)
def test_names_without_a_listed_last_extension_do_not_warn(name: str) -> None:
    """CA-001-102 y 103b."""
    assert classify_warnings(name, None) == NONE


@pytest.mark.parametrize(
    "name",
    [".msi", ".msix", "factura.pdf.exe", ".exe", ".bat", ".lnk", "a (1).exe", "a.tar.exe"],
)
def test_windows_extension_definition_warns(name: str) -> None:
    """CA-001-103: ``.exe`` entero es la extensión ``exe`` (S-001-12)."""
    assert classify_warnings(name, None) == A1


def test_windows_extension_is_what_follows_the_last_dot() -> None:
    assert windows_extension(".exe") == "exe"
    assert windows_extension("a.tar.gz") == "gz"
    assert windows_extension("a.") == ""
    assert windows_extension("exe") == ""
    assert windows_extension("") == ""
    assert windows_extension(".exe (1)") == "exe (1)"


def test_trailing_dot_name_is_judged_after_sanitizing() -> None:
    """CA-001-103: ``a.exe.`` queda ``a.exe`` al sanear y entonces avisa."""
    assert classify_warnings("a.exe.", None) == NONE  # sin sanear, la extensión está vacía
    assert classify_warnings(sanitize_name("a.exe."), None) == A1


def test_invisible_characters_cannot_hide_or_fake_an_extension() -> None:
    """CA-001-104: se clasifica sobre el nombre ya saneado."""
    assert classify_warnings(sanitize_name("factura.ex\u200be"), None) == A1
    assert classify_warnings(sanitize_name("factura\u202efdp.exe"), None) == A1
    assert classify_warnings(sanitize_name("informe.pd\u200bf"), None) == NONE


def test_case_folding_is_the_one_of_windows() -> None:
    assert has_dangerous_extension("A.ExE")
    assert has_dangerous_extension("a.SCR")  # SCR
    assert not has_dangerous_extension("a.exeß")


# --- A-2 (CA-001-105) ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["informe.pdf", "descarga", "index", "a.xhtml", "a.html.txt", "html", "a.htm.pdf", "a.htmlx"],
)
def test_html_without_html_name_warns_a2(name: str) -> None:
    assert classify_warnings(name, "text/html") == A2
    assert classify_warnings(name, "text/html; charset=utf-8") == A2
    assert classify_warnings(name, "TEXT/HTML") == A2


@pytest.mark.parametrize("name", ["index.html", "a.htm", "A.HTML", "B.Htm", "a.b.html", ".html"])
def test_html_with_html_name_does_not_warn(name: str) -> None:
    assert classify_warnings(name, "text/html") == NONE


@pytest.mark.parametrize("content_type", [None, "", "text/plain", "application/pdf", "image/png"])
def test_other_types_never_warn_a2(content_type: str | None) -> None:
    assert classify_warnings("informe.pdf", content_type) == NONE


def test_ejemplo_47_html_served_for_a_pdf() -> None:
    assert classify_warnings("informe.pdf", "text/html") == A2


def test_ejemplo_46_and_40_html_names_have_no_a2() -> None:
    assert classify_warnings("descarga.html", "text/html") == NONE
    assert classify_warnings("index.html", "text/html") == NONE


def test_both_warnings_can_apply_together() -> None:
    assert classify_warnings("setup.exe", "text/html") == frozenset(
        {WarningCode.A1, WarningCode.A2}
    )


def test_warnings_carry_their_catalog_texts() -> None:
    assert WarningCode.A1.message == (
        "Archivo ejecutable o con macros: no lo abra si no confía en el origen"
    )
    assert WarningCode.A2.message == "Se recibió una página web en lugar de un archivo"
