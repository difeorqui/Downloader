"""Listas normativas de direcciones y nombres (glosario 2.1 y 2.2, PA-06).

Son datos, no lógica: el clasificador las consulta y las pruebas fijan sus conteos. Cualquier
cambio de la lista exige cambiar el glosario, la spec y las pruebas a la vez.
"""

from ipaddress import IPv4Network, IPv6Address, IPv6Network
from typing import Final

# --- 2.1 Direcciones internas (solo con confirmación, RN-017) -------------------------------

INTERNAL_IPV4_NETWORKS: Final = frozenset(
    IPv4Network(cidr)
    for cidr in (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "100.64.0.0/10",
    )
)

INTERNAL_IPV6_NETWORKS: Final = frozenset(
    IPv6Network(cidr)
    for cidr in (
        "::1/128",
        "fc00::/7",
    )
)

# ``::1`` está dentro de ``::/96`` (bloqueada) pero tiene entrada propia como interna: es la
# única excepción a la prevalencia de la lista 2.2 (glosario 2.2, entrada ``::/96``).
IPV6_LOOPBACK: Final = IPv6Address("::1")

# Por nombre (comprobación léxica). ``localhost`` exacto y los sufijos con punto inicial.
INTERNAL_EXACT_NAMES: Final = frozenset({"localhost"})
INTERNAL_NAME_SUFFIXES: Final = (
    ".localhost",
    ".local",
    ".internal",
    ".intranet",
    ".lan",
    ".corp",
    ".home.arpa",
)

# --- 2.2 Direcciones bloqueadas (nunca se permiten, RN-004 I-06) ----------------------------

BLOCKED_IPV4_NETWORKS: Final = frozenset(
    IPv4Network(cidr)
    for cidr in (
        "0.0.0.0/8",
        "169.254.0.0/16",  # enlace local; incluye 169.254.169.254 (metadatos de nube)
        "192.0.0.0/24",
        "192.0.2.0/24",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "255.255.255.255/32",
    )
)

BLOCKED_IPV6_NETWORKS: Final = frozenset(
    IPv6Network(cidr)
    for cidr in (
        "::/128",  # sin especificar
        "::/96",  # IPv4 compatibles en desuso (salvo ::1, ver IPV6_LOOPBACK)
        "fe80::/10",  # enlace local
        "ff00::/8",  # multidifusión
        "2001:db8::/32",  # documentación
        "2001::/32",  # Teredo
        "2002::/16",  # 6to4
        "64:ff9b:1::/48",  # traducción local
        "fd00:ec2::254/128",  # metadatos de nube
    )
)

# IPv6 que incrustan una IPv4 en sus últimos 32 bits y se evalúan por ella.
EMBEDDED_IPV4_NETWORKS: Final = frozenset(
    IPv6Network(cidr)
    for cidr in (
        "::ffff:0:0/96",
        "64:ff9b::/96",
    )
)
