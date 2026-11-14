"""Carpeta destino sobre su ruta real (RN-007 c, D-11; CA-001-110 a 112; ejemplo 54)."""

from __future__ import annotations

import pytest

from downloader.domain.paths.destination import SystemFolders, evaluate_destination

SYSTEM = SystemFolders(
    windows="C:\\Windows",
    program_files="C:\\Program Files",
    program_files_x86="C:\\Program Files (x86)",
    program_data="C:\\ProgramData",
    app_data="C:\\Users\\Ana\\AppData\\Local\\Descargador",
    system_drive_root="C:\\",
)


def acceptable(path: str, system: SystemFolders = SYSTEM) -> bool:
    return evaluate_destination(path, system)


# --- Ubicaciones del sistema y todo lo que hay dentro (CA-001-110) --------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "C:\\Windows",
        "C:\\Windows\\",
        "C:\\Windows\\Temp",
        "C:\\Windows\\System32\\drivers\\etc",
        "C:\\Program Files",
        "C:\\Program Files\\Empresa\\App",
        "C:\\Program Files (x86)",
        "C:\\Program Files (x86)\\Empresa",
        "C:\\ProgramData",
        "C:\\ProgramData\\Empresa",
        "C:\\Users\\Ana\\AppData\\Local\\Descargador",
        "C:\\Users\\Ana\\AppData\\Local\\Descargador\\cache",
        "C:\\",
        "C:/",
    ],
)
def test_system_locations_and_their_contents_are_invalid(path: str) -> None:
    assert acceptable(path) is False


@pytest.mark.parametrize(
    "path",
    [
        "c:/windows",  # barras normales y minúsculas
        "C:\\WINDOWS\\Temp",
        "c:\\windows\\",
        "C:\\\\Windows",  # barra doble
        "C:\\Windows\\.\\Temp",
        "C:\\Windows\\\\Temp",
        "C:/Windows/System32/",
        "C:\\PROGRAM FILES",
        "C:\\program files (X86)\\x",
        "C:\\programdata\\x",
        "C:\\Users\\Ana\\appdata\\local\\DESCARGADOR",
    ],
)
def test_ca_001_110_case_and_separators_do_not_change_the_verdict(path: str) -> None:
    assert acceptable(path) is False


@pytest.mark.parametrize(
    "path",
    [
        "C:\\Temp\\..\\Windows",
        "C:\\Users\\..\\Windows\\x",
        "C:\\Descargas\\..\\..\\..\\Windows",
        "C:\\a\\b\\..\\..\\Windows\\Temp",
        "C:\\Windows\\Temp\\..",
        "C:\\Windows\\..",
    ],
)
def test_dot_dot_is_resolved_lexically_without_leaving_the_drive(path: str) -> None:
    """Una ruta real no debería traer ``..``; si lo trae se resuelve antes de comparar."""
    assert acceptable(path) is False


def test_dot_dot_that_ends_outside_the_system_locations_is_fine() -> None:
    assert acceptable("C:\\Windows\\..\\Datos") is True
    assert acceptable("D:\\a\\..\\Descargas") is True


# --- Prefijos extendidos (D-11) -------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "\\\\?\\C:\\Windows",
        "\\\\?\\C:\\Windows\\Temp",
        "\\\\?\\c:\\windows\\system32",
        "\\\\?\\C:\\",
        "\\\\?\\C:/Windows/Temp",
    ],
)
def test_extended_prefix_is_removed_before_comparing(path: str) -> None:
    assert acceptable(path) is False


def test_extended_prefix_with_a_valid_path_is_fine() -> None:
    assert acceptable("\\\\?\\D:\\Descargas") is True
    assert acceptable("\\\\?\\UNC\\servidor\\recurso\\carpeta") is True


# --- Carpetas completas, no prefijos de texto (CA-001-112) ----------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "C:\\WindowsBackup",
        "C:\\Windows.old",
        "C:\\Windows Backup\\x",
        "C:\\Archivos de programa viejos",
        "C:\\Program Files Extra",
        "C:\\Program Files (x86)2",
        "C:\\ProgramData2\\x",
        "C:\\Users\\Ana\\AppData\\Local\\DescargadorViejo",
        "C:\\Users\\Ana\\AppData\\Local",
        "C:\\Users\\Ana",
        "D:\\",
        "D:\\Windows",  # otra unidad: solo cuenta la ruta completa
        "D:\\Program Files",
        "C:\\Descargas",
        "C:\\Users\\Ana\\Downloads",
    ],
)
def test_ca_001_112_only_whole_folders_are_compared(path: str) -> None:
    assert acceptable(path) is True


def test_a_parent_of_a_system_location_is_valid() -> None:
    """Solo la raíz de la unidad de Windows es inválida; sus hijos (que no sean del sistema) no."""
    assert acceptable("C:\\Users") is True
    assert acceptable("C:\\Users\\Ana\\AppData\\Local") is True


# --- Unidades locales, extraíbles y de red (RN-007) -----------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "D:\\Descargas",
        "E:\\USB\\Archivos",
        "\\\\servidor\\recurso",
        "\\\\servidor\\recurso\\carpeta\\sub",
        "//servidor/recurso/x",
        "Z:\\",
    ],
)
def test_other_drives_and_network_shares_are_accepted(path: str) -> None:
    assert acceptable(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "",
        "Descargas",
        "..\\Descargas",
        "\\Descargas",
        "C:",
        "C:Windows",
        "C:Descargas",
        "\\\\",
        "\\\\servidor",
        "\\\\?\\",
        "1:\\x",
        "\u00e9:\\x",
        "http://x.com/a",
    ],
)
def test_paths_that_are_not_absolute_are_never_acceptable(path: str) -> None:
    assert acceptable(path) is False


def test_unc_dot_dot_cannot_leave_the_share() -> None:
    """Un recurso compartido es un destino válido y ``..`` no sale de él."""
    assert acceptable("\\\\servidor\\recurso\\..\\..\\..") is True
    assert acceptable("\\\\servidor\\recurso\\a\\..") is True


# --- Ejemplo 54 y entradas del sistema ------------------------------------------------------------


def test_example_54_the_link_is_judged_by_its_real_path() -> None:
    """``D:\\Atajo`` apunta a ``C:\\Windows\\Temp``: la 002 entrega la ruta real (inválida)."""
    assert acceptable("C:\\Windows\\Temp") is False
    assert acceptable("D:\\Atajo") is True  # el texto solo no basta; por eso se evalúa la ruta real


def test_system_folders_on_another_drive_are_compared_in_full() -> None:
    other = SystemFolders(
        windows="D:\\WINDOWS",
        program_files="D:\\Programas",
        program_files_x86="D:\\Programas (x86)",
        program_data="D:\\Datos",
        app_data="E:\\App",
        system_drive_root="D:\\",
    )
    assert acceptable("D:\\Windows\\x", other) is False
    assert acceptable("D:\\", other) is False
    assert acceptable("C:\\Windows", other) is True
    assert acceptable("E:\\App\\cache", other) is False


def test_an_unknown_system_folder_is_ignored_not_treated_as_everything() -> None:
    partial = SystemFolders("", "", "", "", "", "")
    assert acceptable("C:\\Windows", partial) is True
    assert acceptable("C:\\", partial) is True


def test_unicode_case_is_folded_like_windows() -> None:
    system = SystemFolders(
        windows="C:\\Windows",
        program_files="C:\\Archivos de programa",
        program_files_x86="C:\\Archivos de programa (x86)",
        program_data="C:\\ProgramData",
        app_data="C:\\Datos\\Descargador",
        system_drive_root="C:\\",
    )
    assert acceptable("C:\\ARCHIVOS DE PROGRAMA\\x", system) is False
    assert acceptable("C:\\Datos\\DESCARGADOR\\\u00c1", system) is False
    assert acceptable("C:\\archivos de programa", system) is False


def test_the_verdict_is_deterministic() -> None:
    assert {acceptable("c:/WINDOWS/temp") for _ in range(100)} == {False}
