"""Precedencia entre motivos de invalidez (S-001-07): I-02 → I-01 → I-09 → I-03 → I-05 → I-03."""

from __future__ import annotations

import pytest

from downloader.domain.catalog import InvalidReason
from downloader.domain.result import Err
from downloader.domain.urls.parser import split_raw_url


def reason(text: str) -> InvalidReason:
    result = split_raw_url(text)
    assert isinstance(result, Err), text
    return result.error


@pytest.mark.parametrize(
    ("text", "expected", "why"),
    [
        # I-02 antes que cualquier otro
        ("C:\\x https://b.com", InvalidReason.I02, "ruta local y dos URLs"),
        ("c:/a\\@x", InvalidReason.I02, "ruta local y barra invertida"),
        ("\\\\srv\\a ftp://x", InvalidReason.I02, "ruta de red y esquema"),
        # I-01 antes que I-09, I-03 e I-05
        ("ftp://a.com/x https://b.com", InvalidReason.I01, "esquema ftp y dos URLs"),
        ("javascript:alert(1) https://b.com", InvalidReason.I01, "prefijo peligroso y dos URLs"),
        ("data:text/html,x http://b.com", InvalidReason.I01, "data: y dos URLs"),
        ("ftp://user@a.com", InvalidReason.I01, "esquema ftp y credenciales"),
        ("ftp://a.com\\b", InvalidReason.I01, "esquema ftp y barra invertida"),
        # I-09 antes que la ambigüedad, las credenciales y el espacio en el dominio
        ("https://a\\.com https://b.com", InvalidReason.I09, "dos URLs y barra invertida"),
        ("https://u@a.com https://b.com", InvalidReason.I09, "dos URLs y credenciales"),
        ("https://si tio.com https://b.com", InvalidReason.I09, "dos URLs y espacio en dominio"),
        # I-03 (ambigüedad) antes que I-05 y que el espacio en el dominio
        ("https://u@a.com#@x", InvalidReason.I03, "credenciales y #...@"),
        ("https://u@a.com\\b", InvalidReason.I03, "credenciales y barra invertida"),
        ("https://si tio.com\\b", InvalidReason.I03, "espacio y barra invertida"),
        ("https://si tio.com#@x", InvalidReason.I03, "espacio y #...@"),
        # I-05 antes que el espacio en el dominio
        ("https://u@si tio.com/a", InvalidReason.I05, "credenciales y espacio"),
        ("https://user pass@a.com", InvalidReason.I05, "espacio dentro de las credenciales"),
    ],
)
def test_first_applicable_reason_wins(text: str, expected: InvalidReason, why: str) -> None:
    assert reason(text) is expected, why


def test_the_whole_catalog_of_this_stage_is_reachable() -> None:
    reached = {
        reason("C:\\a"),
        reason("ftp://x"),
        reason("https://a.com/x https://b.com"),
        reason("https://a.com\\b"),
        reason("https://u@a.com"),
        reason("https://a .com"),
    }
    assert reached == {
        InvalidReason.I01,
        InvalidReason.I02,
        InvalidReason.I03,
        InvalidReason.I05,
        InvalidReason.I09,
    }
