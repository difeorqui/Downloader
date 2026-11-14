"""Generadores del alfabeto hostil de la spec (sección 6, RNF-001-05) para las propiedades.

Cubren: ``.``/``..`` en todas sus grafías, codificación simple y doble, ``\\``, ``%5c``, ``%2f``,
``@``, ``#``, ``?``, ``:``, caracteres invisibles (glosario 2.4), nombres reservados (2.5) con
extensiones y espacios, IP en todas las notaciones y longitudes límite (254-256 y 2 047-2 049).
"""

from __future__ import annotations

from hypothesis import strategies as st

from downloader.domain.paths.collisions import EntryKind
from downloader.domain.paths.response import ServerResponse

#: Semilla fija de la batería de robustez: queda registrada para reproducir cualquier fallo.
SEED = 20_261_107

RLO = chr(0x202E)  # inversión de dirección
ZWSP = chr(0x200B)
BOM = chr(0xFEFF)
SOFT_HYPHEN = chr(0xAD)

DOT_SPELLINGS = [
    ".", "..", "%2e", "%2E", ".%2e", "%2e.", "%2e%2e", "%2E%2E", "%252e", "%252e%252e", "...",
    ".. ",
]  # fmt: skip
RESERVED = [
    "con", "CON", "prn", "aux", "nul", "NUL", "com1", "COM9", "lpt1", "LPT\u00b2", "conin$",
    "CONOUT$", "clock$", "con.txt", "con.tar.gz", "con .txt", "nul.com", "Aux.", "COM10", "consola",
]  # fmt: skip
SEPARATORS = ["/", "\\", "%5c", "%5C", "%2f", "%2F", "//", "\\\\"]
SPECIALS = [
    "@",
    "#",
    "?",
    ":",
    "*",
    '"',
    "<",
    ">",
    "|",
    "%",
    "%zz",
    "%00",
    "%0a",
    "$",
    "~",
    "&",
    "=",
]
UNICODE = [
    "ñ",
    "á",
    "Á",
    "ß",
    "\U0001f600",
    "%C3%B1",
    "%FF",
    "%C3",
    "%E2%80%AE",
    RLO,
    ZWSP,
    BOM,
    SOFT_HYPHEN,
]
LENGTHS = [253, 254, 255, 256, 257, 2047, 2048, 2049]

SEGMENT_PIECES = st.sampled_from(
    [
        *DOT_SPELLINGS,
        *RESERVED,
        *SEPARATORS,
        *SPECIALS,
        *UNICODE,
        "a",
        "x.pdf",
        "informe",
        " ",
        "  ",
    ]
)
LONG_RUN = st.sampled_from(LENGTHS).map(lambda n: "a" * n)
SEGMENTS = st.one_of(
    st.lists(SEGMENT_PIECES, max_size=4).map("".join),
    st.lists(SEGMENT_PIECES, max_size=3)
    .map("".join)
    .flatmap(lambda prefix: LONG_RUN.map(lambda run: prefix + run)),
)

HOSTS = st.sampled_from(
    [
        "a.com", "Sitio.COM", "a.com.", "www.a.com", "bogotá.com", "BOGOTÁ.com", "nul.com", "con",
        "localhost", "localhost.", "intranet", "servidor01", "x.corp", "x.local",
        "127.0.0.1", "2130706433", "0x7f.1", "0177.0.0.1", "127.1", "10.1.2.3", "8.8.8.8",
        "169.254.169.254", "4294967295", "4294967296", "256.1.1.1", "1.2.3.4.5", "010.0.0.1",
        "[::1]", "[::ffff:127.0.0.1]", "[::ffff:8.8.8.8]", "[2002:7f00:1::]", "[fd00:ec2::254]",
        "[fe80::1%25eth0]", "[2001:db8::1]", "[64:ff9b::7f00:1]", "[2606:4700::1111]", "[::1",
        "a..com", ".com", "a b.com", "a_b.com", "-a.com", "a" * 63 + ".com", "a" * 64 + ".com",
    ]
)  # fmt: skip
PORTS = st.sampled_from(
    ["", ":80", ":443", ":8080", ":0", ":65535", ":65536", ":99999", ":abc", ":"]
)
SCHEMES = st.sampled_from(
    ["https://", "http://", "HTTPS://", "", "ftp://", "//", "javascript:", "C:\\"]
)


@st.composite
def structured_urls(draw: st.DrawFn) -> str:
    """Una URL con forma de URL, pero con cada tramo tomado del alfabeto hostil."""
    scheme = draw(SCHEMES)
    segments = draw(st.lists(SEGMENTS, max_size=5))
    path = draw(st.sampled_from(["/", "/", "", "\\"])) + draw(st.sampled_from(["/", "\\"])).join(
        segments
    )
    query = draw(st.one_of(st.none(), st.lists(SEGMENT_PIECES, max_size=4).map("".join)))
    fragment = draw(st.one_of(st.none(), st.lists(SEGMENT_PIECES, max_size=3).map("".join)))
    text = f"{scheme}{draw(HOSTS)}{draw(PORTS)}{path}"
    if query is not None:
        text += f"?{query}"
    if fragment is not None:
        text += f"#{fragment}"
    return text


ARBITRARY_TEXT = st.text(alphabet=st.characters(blacklist_categories=()), max_size=80)
HOSTILE_URLS = st.one_of(structured_urls(), structured_urls(), ARBITRARY_TEXT)

#: Estructuras sobre un solo dominio para provocar colisiones y conflictos de carpeta.
COLLIDING_URLS = st.lists(SEGMENT_PIECES, max_size=4).map(
    lambda pieces: "https://a.com/" + "/".join(pieces)
)

SERVER_NAMES = st.one_of(
    st.none(), st.lists(SEGMENT_PIECES, max_size=5).map("".join), ARBITRARY_TEXT
)
CONTENT_TYPES = st.sampled_from(
    [
        None,
        "",
        "text/html",
        "TEXT/HTML; charset=utf-8",
        "application/pdf",
        "image/png",
        "x/y",
        "text/",
    ]
)
RESPONSES = st.builds(
    ServerResponse,
    filename=SERVER_NAMES,
    filename_ext=SERVER_NAMES,
    content_type=CONTENT_TYPES,
)

DISK_KEYS = st.sampled_from(
    [("a.com",), ("a.com", "a"), ("a.com", "docs"), ("a.com", "index"), ("a.com", "x.pdf"),
     ("a.com", "a", "b"), ("A.COM", "A")]
)  # fmt: skip
DISK_STATES = st.dictionaries(DISK_KEYS, st.sampled_from(list(EntryKind)), max_size=4)

# --- Posiciones del canario: las que RN-036 y S-001-08 obligan a enmascarar ----------------------

CANARY = "CANARIO-0a1b2c3d"
SAFE_HOSTS = st.sampled_from(
    ["a.com", "10.0.0.1", "localhost", "[::1]", "169.254.169.254", "x.corp", "a b"]
)
CANARY_URLS = st.one_of(
    st.tuples(SCHEMES, SAFE_HOSTS, st.sampled_from(["", "/p", "/a/b.pdf", "/"])).map(
        lambda t: f"{t[0]}{t[1]}{t[2]}?k={CANARY}&z=1"
    ),
    st.tuples(SCHEMES, SAFE_HOSTS, st.sampled_from(["", "/p", "/a/b.pdf"])).map(
        lambda t: f"{t[0]}{t[1]}{t[2]}#{CANARY}"
    ),
    st.tuples(SCHEMES, SAFE_HOSTS, st.sampled_from(["", "/p", "/q.pdf"])).map(
        lambda t: f"{t[0]}u:{CANARY}@{t[1]}{t[2]}?t=1#f"
    ),
    st.tuples(SCHEMES, SAFE_HOSTS).map(lambda t: f"{t[0]}{CANARY}@{t[1]}/x"),
    st.tuples(SCHEMES, SAFE_HOSTS, SEGMENT_PIECES).map(
        lambda t: f"{t[0]}{t[1]}{t[2].replace('#', '').replace('?', '')}?token={CANARY}"
    ),
    st.tuples(SCHEMES, SAFE_HOSTS).map(
        lambda t: f"{t[0]}{t[1]}/a.pdf?t={CANARY} https://u:{CANARY}@b.com/y#{CANARY}"
    ),
)
