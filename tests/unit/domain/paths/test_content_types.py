"""Tabla de tipos de contenido (RN-010) y su normalización (S-001-06)."""

from __future__ import annotations

import pytest

from downloader.domain.paths.content_types import (
    CONTENT_TYPE_EXTENSIONS,
    extension_for_content_type,
    is_html,
    normalize_media_type,
)

# La tabla de RN-010, escrita a mano (16 tipos en 15 filas).
RN_010_TABLE = [
    ("text/html", ".html"),
    ("text/plain", ".txt"),
    ("text/csv", ".csv"),
    ("application/json", ".json"),
    ("application/xml", ".xml"),
    ("text/xml", ".xml"),
    ("application/pdf", ".pdf"),
    ("image/jpeg", ".jpg"),
    ("image/png", ".png"),
    ("image/gif", ".gif"),
    ("image/webp", ".webp"),
    ("application/zip", ".zip"),
    ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    ("video/mp4", ".mp4"),
]


def test_table_matches_rn_010() -> None:
    assert list(CONTENT_TYPE_EXTENSIONS) == RN_010_TABLE
    assert len(CONTENT_TYPE_EXTENSIONS) == 16
    assert len({extension for _, extension in CONTENT_TYPE_EXTENSIONS}) == 15


@pytest.mark.parametrize(("content_type", "extension"), RN_010_TABLE)
def test_every_table_entry_maps_to_its_extension(content_type: str, extension: str) -> None:
    assert extension_for_content_type(content_type) == extension


@pytest.mark.parametrize(("content_type", "extension"), RN_010_TABLE)
def test_matching_ignores_case_parameters_and_blanks(content_type: str, extension: str) -> None:
    assert extension_for_content_type(content_type.upper()) == extension
    assert extension_for_content_type(f"{content_type}; charset=utf-8") == extension
    assert extension_for_content_type(f"  {content_type.title()} ;charset=UTF-8;x=y ") == extension
    assert extension_for_content_type(f"{content_type};") == extension


@pytest.mark.parametrize(
    "content_type",
    [
        None,
        "",
        " ",
        ";",
        "; charset=utf-8",
        "application/octet-stream",
        "image/jpg",  # no está en la tabla (el tipo correcto es image/jpeg)
        "text/htmlx",
        "xtext/html",
        "text/html extra",
        "text/",
        "text",
        "application/x-msdownload",
        "text/hтml",  # una letra cirílica no coincide
        "TEXT/PLAIN\u212a",  # KELVIN SIGN: no ASCII, nunca coincide
    ],
)
def test_unknown_types_are_not_in_the_table(content_type: str | None) -> None:
    assert extension_for_content_type(content_type) is None


def test_normalize_media_type() -> None:
    assert normalize_media_type("Text/HTML; charset=iso-8859-1") == "text/html"
    assert normalize_media_type("  application/PDF  ") == "application/pdf"
    assert normalize_media_type(None) is None
    assert normalize_media_type("é/x") is None
    assert normalize_media_type("") == ""


def test_is_html() -> None:
    assert is_html("text/html")
    assert is_html("TEXT/HTML; charset=utf-8")
    assert not is_html("application/xhtml+xml")
    assert not is_html("text/plain")
    assert not is_html(None)
