"""Avisos A-1 y A-2 sobre el nombre final y el tipo de contenido (RN-021, glosario 2.3).

Los avisos nunca impiden la descarga. A-3 (no se pudo marcar el origen) lo asigna la spec 002.
Se evalúan sobre el nombre final **ya saneado y con su sufijo de colisión**, si lo lleva.
"""

from typing import Final

from downloader.domain.catalog import WarningCode
from downloader.domain.paths.content_types import is_html
from downloader.domain.text import windows_fold

# Glosario 2.3: lista cerrada de 50 extensiones, sin el punto y sin distinguir mayúsculas.
DANGEROUS_EXTENSIONS: Final = (
    # Ejecutables e instaladores
    "exe",
    "com",
    "scr",
    "pif",
    "cpl",
    "dll",
    "sys",
    "msi",
    "msp",
    "msix",
    "msixbundle",
    "appx",
    "appxbundle",
    "appinstaller",
    "application",
    # Guiones
    "bat",
    "cmd",
    "ps1",
    "psm1",
    "psd1",
    "vbs",
    "vbe",
    "js",
    "jse",
    "wsf",
    "wsh",
    "hta",
    # Accesos directos y configuración
    "lnk",
    "url",
    "scf",
    "inf",
    "reg",
    "rdp",
    "settingcontent-ms",
    "library-ms",
    "diagcab",
    "msc",
    # Contenedores e imágenes de disco
    "jar",
    "chm",
    "iso",
    "img",
    "vhd",
    "vhdx",
    # Office con macros
    "docm",
    "dotm",
    "xlsm",
    "xltm",
    "xlam",
    "pptm",
    "ppam",
)

_FOLDED_DANGEROUS: Final = frozenset(windows_fold(extension) for extension in DANGEROUS_EXTENSIONS)
_HTML_ENDINGS: Final = (windows_fold(".html"), windows_fold(".htm"))


def windows_extension(name: str) -> str:
    """Extensión "según Windows": lo que sigue al último punto, aunque sea el primer carácter.

    ``.exe`` → ``exe``; ``a.tar.gz`` → ``gz``; ``a.`` → ``""``; ``exe`` (sin punto) → ``""``.
    No es la extensión de RN-010/RN-012 (D-06), que exige que el punto no sea el primer carácter.
    """
    _, dot, tail = name.rpartition(".")
    return tail if dot else ""


def has_dangerous_extension(final_name: str) -> bool:
    """A-1: la extensión según Windows está en la lista cerrada del glosario 2.3."""
    return windows_fold(windows_extension(final_name)) in _FOLDED_DANGEROUS


def is_html_mismatch(final_name: str, content_type: str | None) -> bool:
    """A-2: el servidor envió ``text/html`` y el nombre final no termina en ``.html``/``.htm``."""
    return is_html(content_type) and not windows_fold(final_name).endswith(_HTML_ENDINGS)


def classify_warnings(final_name: str, content_type: str | None) -> frozenset[WarningCode]:
    """Avisos A-1 y A-2 que corresponden a un archivo descargado con éxito (RN-021)."""
    warnings: set[WarningCode] = set()
    if has_dangerous_extension(final_name):
        warnings.add(WarningCode.A1)
    if is_html_mismatch(final_name, content_type):
        warnings.add(WarningCode.A2)
    return frozenset(warnings)
