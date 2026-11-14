"""Clave de duplicado (RN-006; CA-001-36 a 40; ejemplo 19)."""

from __future__ import annotations

import pytest

from downloader.domain.result import Ok
from downloader.domain.urls import ParsedUrl
from downloader.domain.urls.dedup import dedup_key
from downloader.domain.urls.parser import parse_url


def key(text: str) -> str:
    result = parse_url(text)
    assert isinstance(result, Ok), text
    return dedup_key(result.value)


def parsed(text: str) -> ParsedUrl:
    result = parse_url(text)
    assert isinstance(result, Ok), text
    return result.value


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("https://sitio.com/a.pdf", "https://sitio.com/a.pdf#parte2"),  # CA-001-36: sin fragmento
        ("https://sitio.com/a.pdf", "https://SITIO.com/a.pdf"),  # CA-001-36: dominio en minúsculas
        ("https://sitio.com/a.pdf#a", "https://sitio.com/a.pdf#b"),
        ("https://a.com:443/x", "https://a.com/x"),  # CA-001-37: puerto estándar
        ("http://a.com:80/x", "http://a.com/x"),
        ("HTTPS://a.com/x", "https://a.com/x"),  # CA-001-38: esquema en minúsculas
        ("https://bogotá.com/x", "https://xn--bogot-1qa.com/x"),  # CA-001-38: forma ASCII
        ("https://sitio.com/a b.pdf", "https://sitio.com/a%20b.pdf"),  # CA-001-40: tras codificar
        ("sitio.com/a.pdf", "https://sitio.com/a.pdf"),  # corregida = escrita con esquema
        ("https://a.com/x", "https://a.com./x"),  # punto final del dominio
        ("https://a.com/p?x=1#f", "https://a.com/p?x=1"),
        ("https://a.com/a\\b", "https://a.com/a/b"),  # la barra invertida de la ruta es "/"
    ],
)
def test_same_key(first: str, second: str) -> None:
    assert key(first) == key(second)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (
            "https://sitio.com/a.pdf?v=1",
            "https://sitio.com/a.pdf?v=2",
        ),  # CA-001-40: los parámetros cuentan
        ("http://a.com:443/x", "http://a.com/x"),  # CA-001-37: 443 no es el estándar de http
        ("https://a.com:80/x", "https://a.com/x"),
        ("https://sitio.com/x/A.pdf", "https://sitio.com/x/a.pdf"),  # CA-001-39 / ejemplo 19
        ("http://a.com/x", "https://a.com/x"),
        ("https://a.com/x", "https://b.com/x"),
        ("https://a.com:8080/x", "https://a.com:8081/x"),
        ("https://a.com/x", "https://a.com/x?"),  # un "?" vacío es un parámetro distinto
        ("https://a.com/x", "https://a.com/x/"),
        ("https://a.com/%2e%2e/x", "https://a.com/x"),  # los segmentos no se resuelven aquí
        ("https://a.com/x?a=1&b=2", "https://a.com/x?b=2&a=1"),  # el orden de parámetros cuenta
    ],
)
def test_different_key(first: str, second: str) -> None:
    assert key(first) != key(second)


def test_the_key_has_no_fragment_and_keeps_the_query() -> None:
    assert key("https://Sitio.COM:443/a.pdf?t=1#frag") == "https://sitio.com/a.pdf?t=1"


def test_ipv4_and_ipv6_literals_compare_as_written() -> None:
    assert key("https://[::1]:8443/a") == "https://[::1]:8443/a"
    assert key("https://127.1/a") != key(
        "https://127.0.0.1/a"
    )  # se comparan tal como se escribieron


def test_key_of_the_reinterpreted_processed_url_is_the_same() -> None:
    url = parsed("sitio.com:8443/a b.pdf?x=ñ#f")
    assert dedup_key(parsed(url.processed())) == dedup_key(url)
