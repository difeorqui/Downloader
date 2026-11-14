"""Humo: el paquete del dominio se puede importar (T-01)."""

from downloader import domain


def test_domain_package_imports() -> None:
    assert domain.__name__ == "downloader.domain"
