# Contrato del dominio — spec 001 (URL → ruta segura)

- **Versión**: 0.1 (Borrador, con `specs/001-url-a-ruta-segura/plan.md`) · **Fecha**: 2026-11-07
- Todo es **puro**: sin E/S, sin hilos, sin reloj, determinista. Tipos inmutables (`@dataclass(frozen=True, slots=True)`), colecciones `tuple`/`frozenset`. Ningún método lanza excepciones por entradas del usuario o del servidor: devuelven un resultado con código de catálogo (PA-04). Una excepción es siempre un defecto.
- `__repr__`/`__str__` de cualquier tipo que contenga una URL devuelve la forma enmascarada (RN-036).

## 1. Catálogos — `downloader.domain.catalog`
```python
class InvalidReason(StrEnum): I01 = "I-01"; ...; I09 = "I-09"   # .message → texto exacto de RN-004
class FailureCode(StrEnum):   F01 = "F-01"; ...; F33 = "F-33"; F99 = "F-99"   # anexo 2 completo
    # .message, .failure_class -> FailureClass(TEMPORARY|PERMANENT|RECOVERABLE)
class WarningCode(StrEnum):   A1 = "A-1"; A2 = "A-2"; A3 = "A-3"   # .message
```

## 2. URLs — `downloader.domain.urls`
```python
class Correction(Flag): NONE = 0; SCHEME_ADDED = auto(); ENCODED = auto()
class HostKind(Enum): NAME; IPV4; IPV6

@dataclass(frozen=True, slots=True)
class ParsedUrl:
    scheme: Literal["http", "https"]
    host: str                 # ASCII, minúsculas, sin punto final; IPv6 entre corchetes
    host_kind: HostKind
    ip: IPv4Address | IPv6Address | None   # valor interpretado si el host es un literal IP (cualquier notación)
    port: int | None          # None = puerto estándar del esquema
    path: str                 # codificado; "" o empieza por "/"
    query: str | None         # sin "?"
    fragment: str | None      # sin "#"
    corrections: Correction
    def processed(self) -> str: ...        # URL completa SIN enmascarar (solo conexión y exportación)
    def masked(self) -> str: ...           # RN-036

@dataclass(frozen=True, slots=True)
class InvalidUrl:
    reason: InvalidReason
    masked_text: str          # texto original enmascarado de forma conservadora (CA-001-112)

def interpret_url(text: str) -> ParsedUrl | InvalidUrl: ...       # RN-001, RN-001a, RN-003 h, RN-004
def mask_text(text: str) -> str: ...                              # enmascarado de texto no analizable
def dedup_key(url: ParsedUrl) -> str: ...                          # RN-006
```

## 3. Direcciones — `downloader.domain.addresses`
```python
class AddressClass(Enum): PUBLIC; INTERNAL; BLOCKED
def classify_url_host(url: ParsedUrl) -> AddressClass: ...         # RN-017 a (léxica)
def classify_ip(ip: IPv4Address | IPv6Address) -> AddressClass: ... # glosario 2.1/2.2; la usa también la 002 con IP resueltas
```

## 4. Lote — `downloader.domain.batch`
```python
@dataclass(frozen=True, slots=True)
class SourceLine: number: int; text: str           # ya recortada

@dataclass(frozen=True, slots=True)
class BatchFileRejection: kind: RejectionKind; message: str   # texto exacto RN-003 c–g (con valor y límite / línea)

def decode_batch_file(file_name: str, content: bytes) -> tuple[SourceLine, ...] | BatchFileRejection: ...
def read_single_input(text: str) -> SourceLine | InvalidUrl | None: ...   # None = vacío (CA-001-17); I-08

@dataclass(frozen=True, slots=True)
class BatchItem: index: int; line: int; url: ParsedUrl; address_class: AddressClass   # PUBLIC o INTERNAL

@dataclass(frozen=True, slots=True)
class InvalidLine: line: int; masked_text: str; reason: InvalidReason

@dataclass(frozen=True, slots=True)
class BatchValidation:
    total_lines: int
    items: tuple[BatchItem, ...]            # válidas y únicas, en orden del lote
    corrected_no_scheme: int
    corrected_encoded: int
    duplicates: int
    invalid: tuple[InvalidLine, ...]
    internal_hosts: tuple[str, ...]         # orden de primera aparición
    required_folders: frozenset[str]        # rutas relativas de carpeta, plegadas (RN-012 b)
    @property
    def can_start(self) -> bool: ...        # hay al menos un elemento

def validate_batch(lines: Sequence[SourceLine]) -> BatchValidation: ...   # RN-004..006
```

## 5. Rutas — `downloader.domain.paths`
```python
class EntryKind(Enum): FILE; DIRECTORY; REPARSE_POINT

class KnownDiskEntries(Protocol):           # puerto de SOLO LECTURA; la 002 lo implementa sobre el disco
    def kind_of(self, relative_parts: tuple[str, ...]) -> EntryKind | None: ...

@dataclass(frozen=True, slots=True)
class InMemoryDiskEntries: ...              # implementación de datos (pruebas y 002 si conviene)

@dataclass(frozen=True, slots=True)
class ServerResponse:
    filename: str | None = None             # forma simple, ya decodificada por la 002
    filename_ext: str | None = None         # forma internacional (filename*), ya decodificada
    content_type: str | None = None         # valor crudo de la cabecera
    final_url: ParsedUrl | None = None      # solo informativo: las carpetas salen de la original

@dataclass(frozen=True, slots=True)
class PathLimits: long_paths_enabled: bool

class PathReservations:                     # mutable, UNO POR LOTE; no es seguro entre hilos (la 002 lo protege)
    def __init__(self, required_folders: frozenset[str]) -> None: ...

@dataclass(frozen=True, slots=True)
class TargetPath:
    full_path: str                          # p. ej. "D:\\Descargas\\sitio.com\\a (1).pdf"
    folder_parts: tuple[str, ...]           # componentes de carpeta relativos a la destino
    file_name: str
    warnings: frozenset[WarningCode]        # A-1/A-2 (RN-021)

@dataclass(frozen=True, slots=True)
class PathFailure: code: FailureCode        # F-24 | F-25 | F-27 | F-28

def relative_folders(url: ParsedUrl) -> tuple[str, ...]: ...      # RN-008 (sin respuesta del servidor)
def compute_target_path(
    destination: str, url: ParsedUrl, response: ServerResponse | None,
    disk: KnownDiskEntries, reservations: PathReservations, limits: PathLimits,
) -> TargetPath | PathFailure: ...                                 # RN-008..016; reserva el nombre si es Ok

@dataclass(frozen=True, slots=True)
class SystemFolders:
    windows: str; program_files: str; program_files_x86: str
    program_data: str; app_data: str; system_drive_root: str

def evaluate_destination(real_path: str, system: SystemFolders) -> bool: ...   # RN-007 c (True = aceptable)
```

## 6. Avisos — `downloader.domain.warnings`
```python
def classify_warnings(final_name: str, content_type: str | None) -> frozenset[WarningCode]: ...  # A-1, A-2
```

## Garantías verificadas por pruebas
1. `compute_target_path` devuelve una ruta dentro de `destination` o `PathFailure` (CA-001-50, 100 000 entradas).
2. Mismas entradas → mismo resultado (RNF-001-04).
3. Ninguna salida salvo `ParsedUrl.processed()` contiene valores de parámetros, fragmento ni credenciales (CA-001-111).
4. `interpret_url(url.processed())` devuelve una estructura igual a `url` (salvo `corrections`) — idempotencia del analizador (CA-001-16).
