"""URLs: interpretación, codificación, enmascarado y deduplicación (RN-001 a RN-006, RN-036)."""

from downloader.domain.urls.masking import mask_text
from downloader.domain.urls.model import Correction, HostKind, InvalidUrl, ParsedUrl
from downloader.domain.urls.parser import interpret_url

__all__ = [
    "Correction",
    "HostKind",
    "InvalidUrl",
    "ParsedUrl",
    "interpret_url",
    "mask_text",
]
