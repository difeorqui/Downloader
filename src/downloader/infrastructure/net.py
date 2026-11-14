"""Conexión HTTP(S) segura: dirección comprobada y fijada, redirecciones manuales (RN-017, RN-018).

Para cada salto (la URL inicial y cada redirección):

1. se resuelve el nombre y se clasifica **cada** dirección con el dominio (``classify_ip``);
2. una dirección bloqueada nunca se permite, y una interna solo si el usuario autorizó ese
   dominio;
3. se conecta **a la dirección ya comprobada** (no se vuelve a resolver el nombre, lo que evita el
   cambio de DNS entre la comprobación y la conexión) y, en HTTPS, se valida el certificado contra
   el almacén de Windows con el nombre original.

Límites de esta versión: no usa el proxy de Windows ni consulta la revocación de certificados.
"""

import http.client
import ipaddress
import re
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import unquote, urljoin

from downloader.domain.addresses import AddressClass, classify_ip
from downloader.domain.result import Ok
from downloader.domain.urls import ParsedUrl
from downloader.domain.urls.parser import parse_url

MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 30.0
HTTP_OK = 200
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
USER_AGENT = "Descargador/0.1"
_DEFAULT_PORTS = {"http": 80, "https": 443}


class DownloadError(Exception):
    """Fallo previsto de una descarga; ``str(error)`` es el texto que ve el usuario."""


@dataclass(frozen=True, slots=True)
class Opened:
    """Respuesta 200 lista para leer. Quien la recibe debe llamar a ``close``."""

    connection: http.client.HTTPConnection
    response: http.client.HTTPResponse
    final_url: ParsedUrl

    def close(self) -> None:
        self.response.close()
        self.connection.close()


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self, host: str, port: int, ip: str, timeout: float, context: ssl.SSLContext
    ) -> None:
        super().__init__(host, port, timeout=timeout, context=context)
        self._ip = ip
        self._tls_context = context

    def connect(self) -> None:
        raw = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._tls_context.wrap_socket(raw, server_hostname=self.host)


def open_url(url: ParsedUrl, authorized_hosts: frozenset[str]) -> Opened:
    """Abre ``url`` siguiendo redirecciones a mano y comprobando cada salto."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        opened = _request(current, authorized_hosts)
        status = opened.response.status
        if status in REDIRECT_STATUSES:
            location = opened.response.getheader("Location")
            opened.close()
            if not location:
                raise DownloadError("El servidor redirigió sin indicar el destino")
            parsed = parse_url(urljoin(current.processed(), location))
            if not isinstance(parsed, Ok):
                raise DownloadError("El servidor redirigió a una dirección no válida")
            current = parsed.value
            continue
        if status != HTTP_OK:
            opened.close()
            raise DownloadError(f"El servidor respondió {status}")
        return opened
    raise DownloadError("Demasiadas redirecciones")


def _request(url: ParsedUrl, authorized_hosts: frozenset[str]) -> Opened:
    port = url.port or _DEFAULT_PORTS[url.scheme]
    addresses = _allowed_addresses(url, port, authorized_hosts)
    target = (url.path or "/") + ("" if url.query is None else f"?{url.query}")
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "identity"}
    host = url.host.strip("[]")
    context = ssl.create_default_context()  # almacén de certificados del sistema
    last_error: Exception | None = None
    for ip in addresses:
        connection: http.client.HTTPConnection
        if url.scheme == "https":
            connection = _PinnedHTTPSConnection(host, port, ip, TIMEOUT_SECONDS, context)
        else:
            connection = _PinnedHTTPConnection(host, port, ip, TIMEOUT_SECONDS)
        try:
            connection.request("GET", target, headers=headers)
            return Opened(connection, connection.getresponse(), url)
        except ssl.SSLCertVerificationError as error:
            connection.close()
            raise DownloadError("El certificado del servidor no es de confianza") from error
        except (OSError, http.client.HTTPException) as error:
            connection.close()
            last_error = error
    raise DownloadError(_describe(last_error))


def _allowed_addresses(url: ParsedUrl, port: int, authorized_hosts: frozenset[str]) -> list[str]:
    """Direcciones del dominio, todas comprobadas (RN-017 b); falla si alguna no es aceptable."""
    if url.ip is not None:
        resolved: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = [url.ip]
    else:
        try:
            infos = socket.getaddrinfo(url.host, port, type=socket.SOCK_STREAM)
        except OSError as error:
            raise DownloadError("No se pudo encontrar el servidor") from error
        resolved = [ipaddress.ip_address(str(info[4][0]).partition("%")[0]) for info in infos]
    classes = {classify_ip(ip) for ip in resolved}
    if AddressClass.BLOCKED in classes:
        raise DownloadError("Dirección no permitida")
    if AddressClass.INTERNAL in classes and url.host not in authorized_hosts:
        raise DownloadError("Dirección interna no autorizada")
    return [str(ip) for ip in resolved]


def _describe(error: Exception | None) -> str:
    if isinstance(error, TimeoutError):
        return "Se agotó el tiempo de espera del servidor"
    if isinstance(error, ssl.SSLError):
        return "No se pudo establecer la conexión segura"
    return "No se pudo conectar con el servidor"


_FILENAME_EXT = re.compile(r"filename\*\s*=\s*([^';]*)'[^']*'([^;]+)", re.IGNORECASE)
_FILENAME_QUOTED = re.compile(r'(?<![\w*])filename\s*=\s*"((?:[^"\\]|\\.)*)"', re.IGNORECASE)
_FILENAME_TOKEN = re.compile(r"(?<![\w*])filename\s*=\s*([^\s;\"]+)", re.IGNORECASE)


def suggested_names(content_disposition: str | None) -> tuple[str | None, str | None]:
    """``(filename, filename*)`` de la cabecera, ya decodificados (RN-010 paso 1)."""
    if not content_disposition:
        return None, None
    extended = _FILENAME_EXT.search(content_disposition)
    decoded_ext = None
    if extended:
        charset = extended.group(1).strip() or "utf-8"
        try:
            decoded_ext = unquote(extended.group(2).strip(), encoding=charset, errors="replace")
        except LookupError:
            decoded_ext = unquote(extended.group(2).strip(), errors="replace")
    simple = None
    quoted = _FILENAME_QUOTED.search(content_disposition)
    if quoted:
        # Solo se des-escapa la comilla: una barra invertida se queda, porque es un separador de
        # directorios que RN-010 quita después (como hacen los navegadores).
        simple = quoted.group(1).replace('\\"', '"')
    else:
        token = _FILENAME_TOKEN.search(content_disposition)
        if token:
            simple = token.group(1)
    return simple, decoded_ext
