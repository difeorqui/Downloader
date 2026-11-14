"""Direcciones: interpretación de IPv4 escrita y clasificación interna/bloqueada (RN-017 a)."""

from downloader.domain.addresses.classifier import AddressClass, classify_host, classify_ip

__all__ = ["AddressClass", "classify_host", "classify_ip"]
