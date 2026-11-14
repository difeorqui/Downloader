# Plan técnico — Spec 001: De la URL a una ruta segura

- **Estado:** Aprobado
- **Versión**: 0.1
- **Fecha**: 2026-11-07
- **Autor**: arquitecto de software
- **Spec**: [spec.md](spec.md) (v0.1, en revisión final; se asume estable)
- **ADR**: [0001](../../docs/02-arquitectura/adr/0001-python-escritorio-portable.md) · [0002](../../docs/02-arquitectura/adr/0002-capas-y-catalogo-de-patrones.md) · [0003](../../docs/02-arquitectura/adr/0003-analizador-url-propio.md) · [0007](../../docs/02-arquitectura/adr/0007-calidad-pruebas-y-dependencias.md) (todos `proposed`)
- **Contrato**: [docs/03-api/dominio-001.md](../../docs/03-api/dominio-001.md)
- **Arquitectura**: [arquitectura.md](../../docs/02-arquitectura/arquitectura.md) · **Patrones**: [patrones.md](../../docs/02-arquitectura/patrones.md)

## 1. Resumen
Se construye solo la capa **`downloader.domain`**: funciones puras y deterministas que, a partir del texto del usuario, los bytes del archivo masivo, la respuesta del servidor (como datos) y el estado conocido del disco (puerto de solo lectura), deciden validez, URL procesada, ruta exacta o fallo, avisos y enmascaramiento. No hay red, disco, hilos, reloj ni interfaz (RNF-001-06). No hay datos persistidos ni migraciones.

Dependencia de ejecución: `idna` (ADR 0003). Todo lo demás es biblioteca estándar pura.

## 2. Componentes (una responsabilidad cada uno)

Ruta base `src/downloader/domain/`. Dependencias solo hacia la izquierda de la lista o hacia `catalog`/`text`/`result`.

| Módulo | Responsabilidad única | Reglas | Depende de |
|---|---|---|---|
| `catalog.py` | Catálogos cerrados I-NN, F-NN (con clase), A-N y sus textos | RN-004, anexo 2, RN-021 | — |
| `result.py` | `Ok`/`Err` genéricos mínimos (si un módulo no tiene tipo de resultado propio) | PA-04 | — |
| `text.py` | `windows_fold` (S-001-03), `utf16_len` (S-001-02), recorte de espacios/tabulaciones | — | — |
| `addresses/ipv4.py` | Interpretar IPv4 en notación decimal entera, octal, hexadecimal y abreviada (regla WHATWG "termina en número") | RN-017 a, AB-14 | — |
| `addresses/lists.py` | Glosario 2.1 y 2.2 como `frozenset` de `ip_network` y sufijos de nombre | glosario | — |
| `addresses/classifier.py` | `classify_ip`, `classify_url_host` → PUBLIC/INTERNAL/BLOCKED, bloqueada prevalece, IPv4 incrustada en `::ffff:0:0/96` y `64:ff9b::/96` | RN-017 a | `ipv4`, `lists` |
| `urls/encoding.py` | Codificación selectiva en porcentaje (RN-001 paso 8) y decodificación única de segmentos con conservación de secuencias no UTF-8 | RN-001 (8), RN-011 | — |
| `urls/host.py` | Punto final, minúsculas, NFC, `idna` (solo si no ASCII), validación de caracteres y etiquetas, literal IPv6 entre corchetes, puerto | RN-001 (6, 8, 9), RN-001a, RN-004 I-03/I-07 | `addresses.ipv4`, `idna` |
| `urls/parser.py` | Canal único RN-001 pasos 1–9 en su orden; autoridad cruda vs autoridad; produce `ParsedUrl` o `InvalidUrl` | RN-001, RN-001a, RN-003 h | `host`, `encoding`, `masking` |
| `urls/model.py` | `ParsedUrl` inmutable, `processed()`, `__repr__` enmascarado | RN-001a | — |
| `urls/masking.py` | Enmascarar `ParsedUrl` y texto no analizable | RN-036 | — |
| `urls/dedup.py` | Clave de duplicado | RN-006 | `model` |
| `batch/file_decoder.py` | Extensión, tamaño, UTF-16, UTF-8 con línea del error, finales de línea, comentarios, conteo ≤ 10 000 | RN-002, RN-003 a–g | `text` |
| `batch/single_input.py` | Campo individual: vacío, I-08 | RN-004 I-08 | `text` |
| `batch/validator.py` | Resultado RN-005: conteos, duplicados, inválidas enmascaradas, internas, `required_folders` | RN-004–006, RN-012 b | `urls`, `addresses`, `paths.relative` |
| `paths/sanitize.py` | Invisibles, caracteres inválidos, puntos/espacios finales, reservados | RN-014, RN-015 | `text` |
| `paths/relative.py` | Carpeta de dominio (+`_puerto`) y segmentos de carpeta; descarte de vacíos, `.`, `..` (también `%2e`) | RN-008, RN-009, RN-011 | `encoding`, `sanitize` |
| `paths/content_types.py` | Tabla cerrada tipo → extensión; normalización sin parámetros | RN-010, S-001-06 | — |
| `paths/filename.py` | Prioridad de nombre: `filename*` > `filename` > último segmento (+ext) > `index`(+ext) | RN-010 | `sanitize`, `content_types`, `encoding` |
| `paths/length.py` | Componentes ≤ 255, ruta final y temporal (53) frente a 259/247/32 000 | RN-016 | `text` |
| `paths/collisions.py` | `PathReservations` del lote, sufijos ` (n)`, comprobación de enlaces/uniones y archivos en carpetas | RN-012, RN-013 b | `text` |
| `paths/target.py` | Orquesta el cálculo y aplica la **guarda de contención** final | RN-008–016 | todos los de `paths`, `warnings` |
| `paths/destination.py` | Carpeta destino aceptable según su ruta real, por componentes completos | RN-007 c | `text` |
| `warnings.py` | A-1 (glosario 2.3, última extensión) y A-2 | RN-021 | `content_types` |

## 3. Patrones aplicados
- **PA-01** Capas: todo vive en `domain`; prueba AST + `banned-api` de ruff (`os`, `pathlib`, `io`, `shutil`, `socket`, `ssl`, `urllib`, `http`, `threading`, `asyncio`, `subprocess`, `time`, `datetime.now`, `random`, `open`, `print`, `input`, `eval`, `exec`).
- **PA-03** Objetos de valor inmutables: `ParsedUrl`, `SourceLine`, `BatchItem`, `TargetPath`, `ServerResponse`, etc.
- **PA-04** Resultado explícito: toda función pública devuelve `X | Fallo` con código de catálogo; 0 excepciones por datos externos.
- **PA-05** Núcleo funcional: el estado del disco entra por `KnownDiskEntries` (solo lectura); `PathReservations` es el único objeto mutable, con alcance de un lote y creado por quien lo usa (no global).
- **PA-06** Tablas normativas como datos: `lists.py`, `content_types.py`, `warnings.py` (2.3), `sanitize.py` (2.4, 2.5), `catalog.py`.
- **Patrón adicional — Canal (pipeline) de pasos ordenados** en `urls/parser.py`: cada paso de RN-001 es una función `(estado) -> estado | InvalidUrl`; el orden está en una tupla única y lo verifican pruebas de precedencia (p. ej. I-09 antes de codificar, I-02 antes de esquema). Lo pide el problema: el orden es normativo.
- **Guarda de contención** (defensa en profundidad) en `paths/target.py`: aunque el saneamiento ya lo impide, antes de devolver se verifica que cada componente es no vacío, distinto de `.`/`..`, sin `\ / :` ni controles, y que `full_path == destino + "\" + "\".join(componentes)`. Si falla → F-24.

## 4. Decisiones de detalle (dentro del margen de la spec)
No cambian la spec; si el analista discrepa, se ajusta la spec y luego este plan.

| ID | Decisión | Motivo |
|---|---|---|
| D-01 | Orden de rechazos del archivo masivo: extensión (d) → tamaño (b) → UTF-16 (e) → UTF-8 (f) → conteo (a) → vacío (g) | Lo más barato y seguro primero; no se decodifica un archivo demasiado grande |
| D-02 | Puerto vacío (`sitio.com:/a`) = puerto estándar; puerto con caracteres no numéricos o numérico fuera de 1–65535 = I-07 (se evalúa después de I-04). **Corregida en la implementación**: la versión anterior decía I-03 para lo no numérico, pero el ejemplo 18c de S-001-08 (spec aprobada) exige I-07 para `user:pass?@evil.com`. Un literal IPv6 con texto ajeno tras `]` sigue siendo I-03 | La spec manda sobre el plan |
| D-03 | Host: se rechazan con I-03 etiquetas vacías, longitud > 253, y los caracteres prohibidos de WHATWG (espacio, `#`, `%`, `/`, `:`, `<`, `>`, `?`, `@`, `[`, `\`, `]`, `^`, `\|`) fuera del literal IPv6; si la última etiqueta es numérica (o `0x…`) se interpreta como IPv4 y si no es válida → I-03; IPv6 con zona (`%`) → I-03 | Analizador único y conservador (AB-20) |
| D-04 | Decodificación (RN-011): `bytes` → `str` con `surrogateescape`, y cada byte no decodificable se vuelve a escribir como `%XX` (por secuencia, no por segmento entero). Sin registrar manejadores globales de códecs | Puro y sin estado global |
| D-05 | Detección de `.`/`..` codificados: se decodifica solo `%2e`/`%2E` para la comparación; `%252e` no es punto (ejemplo 39) | RN-008 f + RN-011 |
| D-06 | "Tiene extensión" = hay un `.` que no es el primer carácter y le sigue al menos un carácter. Sufijo ` (n)` antes de la **última** extensión (`a.tar.gz` → `a.tar (1).gz`) | RN-010 (2), RN-012 a |
| D-07 | Orden de fallos de ruta: sufijo de colisión → **F-28** → carpetas de la raíz hacia dentro (**F-24** unión/enlace, **F-27** archivo donde va una carpeta) → **F-25** → guarda de contención (F-24). **Corregida en la implementación**: la versión anterior ponía F-24/F-27 antes que F-28; S-001-07 y CA-001-51 a 53 dicen F-28 → F-24 → F-27 → F-25. El nombre solo se reserva si el resultado es correcto | La spec manda sobre el plan; se mide con el sufijo (CA-001-60) |
| D-08 | El nombre de carpeta de un literal IP usa el host tal como quedó escrito (minúsculas): `2130706433`, `[::1]` → `[__1]`. La clasificación usa el valor interpretado | RN-008 b no pide canonizar; la 002 conecta con el valor interpretado |
| D-09 | Enmascarado de URL válida (S-001-08 a): un parámetro sin `=` se trata como valor (`?a` → `?***`); con `=` vacío (`?a=`) → `a=***`; un `?` o `#` sin nada detrás se conserva; fragmento con contenido → `#***`. **Corregida en la implementación**: la versión anterior conservaba `?flag` y ocultaba `#` vacío, contra la tabla de S-001-08 (filas 2, 5 y 6) | La spec manda sobre el plan |
| D-10 | `mask_text` (S-001-08 b): por cada URL detectada (en I-09, separadas por el espacio previo a `http`), se reemplaza por `***@` desde el inicio de la autoridad cruda hasta su último `@`, y lo que sigue al primer `?` o `#` por `***`. Con I-05 e I-07 los parámetros se muestran por nombre, como en una válida. Toda salida visible se recorta a 199 caracteres + `…` (200). **Corregida**: la versión anterior decía "200 + …" y truncaba solo por encima de 2 048 | La spec manda sobre el plan |
| D-11 | Unidad de rutas: el dominio trabaja con texto de ruta de Windows (`\`). Destino: se quita la `\` final salvo en la raíz (`D:\`). Para RN-007 c se quitan los prefijos `\\?\` y `\\?\UNC\` y se compara por componentes con `windows_fold` | CA-001-122/123 |
| D-12 | Coste de colisiones: contador por nombre base en `PathReservations` para que 10 000 nombres iguales no sean O(n²) | RNF-001-02 |

## 5. Modelo de datos
Sin persistencia. Tipos en el [contrato](../../docs/03-api/dominio-001.md). `required_folders` y las claves de reserva son rutas relativas **plegadas** con `windows_fold`, unidas por `\`.

## 6. Modelo STRIDE (solo la capa de dominio)

| Amenaza | Ejemplo | Mitigación | Prueba |
|---|---|---|---|
| **S** Suplantación de destino por URL ambigua | `https://sitio.com\@127.0.0.1/`, `#@` (AB-20) | Autoridad cruda vs autoridad (RN-001a); analizador único; prohibido re-analizar (AP-02) | CA-001-09, ejemplos 35, 36, 49, 52; propiedad de idempotencia CA-001-16 |
| **S** Dirección interna disfrazada en notación alternativa | `2130706433`, `0x7f.1`, `[::ffff:127.0.0.1]`, `[2002:7f00:1::]` (AB-14) | Intérprete IPv4 WHATWG + `ipaddress`; IPv4 incrustada | CA-001-90..95; ejemplos 27, 45; generadores de notaciones en la propiedad |
| **T** Escritura fuera de la carpeta destino | `..`, `%2e%2e`, `\`, `%5c`, `%2f`, nombre sugerido `..\..\x` (AB-01, AB-12) | Descarte de puntos, `\`→`/` antes de codificar, saneamiento, toma del nombre tras la última `/`/`\`, **guarda de contención** | CA-001-43, 44, 50, 71; ejemplos 4–7, 15, 37, 39, 51; **100 000 entradas** (RNF-001-05) |
| **T** Escritura a través de unión de carpetas | unión dentro del destino (AB-15) | `REPARSE_POINT` en cualquier carpeta intermedia → F-24 | CA-001-84, ejemplo 26 |
| **T** Sobrescritura | colisiones en disco/lote, mayúsculas | `PathReservations` + `windows_fold` + prevalencia de carpetas | CA-001-80..83; ejemplos 18, 19, 25, 42; determinismo con orden directo/inverso/aleatorio |
| **R** No repudio | — | N/A en el dominio (no registra); el registro es de la 002 | — |
| **I** Filtración de tokens | `?token=…#access_token=…` (AB-18) | `masked()` y `__repr__` enmascarados; `InvalidUrl` solo guarda texto enmascarado; ningún mensaje incluye la URL | CA-001-110..112; **prueba del canario** sobre todas las salidas y `repr` (propiedad) |
| **I** Credenciales embebidas (AB-10) | `https://u:p@sitio.com` | I-05 sobre la autoridad; nunca se guarda el texto sin enmascarar | CA-001-10 |
| **D** Agotamiento con archivo enorme o patológico (AB-06) | 5 MB+1, 10 001 líneas, URLs de 2 048 | Límites antes de decodificar/validar (D-01); sin expresiones regulares con retroceso catastrófico (solo patrones lineales anclados, revisados); D-12 | CA-001-23..28; RNF-001-01..03 |
| **E** Elevación: destino en carpetas del sistema (AB-15) | `D:\Atajo` → `C:\Windows\Temp` | Decisión sobre la ruta real por componentes | CA-001-120..123; ejemplo 54 |
| **E/T** Disfraz de ejecutable (AB-16) | `factura\u202Efdp.exe` | Eliminación de invisibles antes de clasificar A-1 | CA-001-51, 103; ejemplo 17 |
| **T** Nombres reservados (AB-03) | `CON`, `nul.com`, `con .txt`, `COM¹` | RN-015 sobre el tramo anterior al primer punto | CA-001-54, 55; ejemplos 8, 16, 31–34 |

## 7. Estrategia de pruebas
Coordinada con `docs/04-pruebas/estrategia-pruebas.md` (**aún no existe**; lo redacta `ingeniero-pruebas`; este apartado es la entrada para la 001).

| Tipo | Qué | Herramienta / ubicación | Cuándo corre |
|---|---|---|---|
| Unitarias | Cada módulo de §2, con `pytest.mark.parametrize`; un archivo por módulo | `tests/unit/domain/test_<módulo>.py` | Cada commit (pre-commit) |
| Regresión (anexo 1) | **Los 55 ejemplos** como una tabla de datos `ANNEX1` (id, entrada, respuesta, disco, resultado esperado) y una prueba parametrizada con `ids="EJ-NN"`; resultado comparado **carácter a carácter**. Una prueba adicional exige que existan exactamente los ID 1..55. Los 6 parciales (22, 23, 27, 44, 48, 53) verifican solo la parte de esta spec | `tests/regression/annex1_data.py`, `test_annex1.py` | Cada commit |
| Precedencia | Pares de entradas que disparan dos reglas a la vez para fijar el orden de RN-001 (I-02 vs I-01, I-09 vs codificación, I-03 por espacio en dominio vs codificación) | `tests/unit/domain/test_parser_order.py` | Cada commit |
| Propiedades / fuzz (RNF-001-05) | **100 000** entradas: generadores de URLs a partir del alfabeto hostil de la §6 de la spec (`..`, `%2e`, `%252e`, `\`, `%5c`, `%2f`, `@`, `#`, `?`, `:`, invisibles 2.4, reservados 2.5 con extensiones y espacios, IP en todas las notaciones, longitudes 254–256 y 2 047–2 049) + texto Unicode arbitrario; nombres sugeridos y estados de disco aleatorios. Propiedades: (1) 0 excepciones; (2) toda salida es `TargetPath` dentro del destino con componentes seguros, o código del catálogo; (3) idempotencia del analizador; (4) canario ausente de toda salida salvo `processed()`; (5) determinismo | hypothesis; `tests/property/` | Perfil `dev` 2 000 en cada commit; perfil `ci` **100 000** (marca `fuzz`) antes de integrar |
| Determinismo (RNF-001-04) | Cada caso de §3 100 veces; ejemplos 19 y 42 en orden directo, inverso y aleatorio con semilla fija | `tests/regression/test_determinism.py` | Cada commit |
| Rendimiento (RNF-001-01..03) | Datos sintéticos con semilla fija; 20 ejecuciones; p95 con `statistics.quantiles`; memoria pico con `tracemalloc` en una ejecución aparte (mide asignaciones de Python, aproximación aceptada de la memoria privada adicional) | `tests/performance/` (marca `perf`) | Antes de integrar, en el equipo de referencia |
| Sin efectos externos (RNF-001-06) | Gancho `sys.addaudithook` activo durante las pruebas del dominio: falla ante `socket.*`, `open` en escritura, `os.mkdir/remove/rename/...`; base de datos de hypothesis desactivada en esa suite | `tests/conftest.py` + `tests/architecture/test_no_side_effects.py` | Cada commit |
| Arquitectura | AST: `domain` solo importa la lista permitida de PA-01; ningún estado global mutable (asignaciones de `list`/`dict`/`set` a nivel de módulo) | `tests/architecture/test_layers.py` | Cada commit |
| Tablas normativas | Cada tabla tiene el número exacto de entradas del glosario/reglas (2.1, 2.2, 2.3, 2.4, 2.5, tipos, I-NN, F-NN) | `tests/unit/domain/test_tables.py` | Cada commit |
| Integración, contrato, carga | **No aplican** en la 001 (no hay E/S ni API). La 002 vuelve a verificar con disco y red reales los ejemplos 18, 22, 25, 26, 48, 53, 54 | — | — |

**Cobertura**: `pytest --cov=downloader --cov-branch`; `fail_under = 80` global y `coverage report --include="src/downloader/domain/*" --fail-under=90` (líneas y ramas).

## 8. Trazabilidad criterio → componente → prueba

| Criterios | Componente | Prueba |
|---|---|---|
| CA-001-01..05, 07..11, 14, 17 | `urls/parser.py`, `urls/host.py` | `test_parser.py`, `test_parser_order.py`, `test_host.py` |
| CA-001-06, 12, 15 | `urls/encoding.py`, `urls/host.py`, `urls/parser.py` | `test_encoding.py`, `test_host.py` |
| CA-001-13, 17 | `batch/single_input.py` | `test_single_input.py` |
| CA-001-16 | `urls/parser.py`, `urls/model.py` | `test_parser.py::test_idempotent`, propiedad (3) |
| CA-001-20..28 | `batch/file_decoder.py` | `test_file_decoder.py` |
| CA-001-29..34 | `batch/validator.py`, `urls/dedup.py` | `test_validator.py`, `test_dedup.py`, `test_no_side_effects.py` |
| CA-001-40..44 | `paths/relative.py`, `urls/encoding.py` | `test_relative.py` |
| CA-001-50 | `paths/target.py` (guarda) | `test_target.py`, propiedad (2) |
| CA-001-51..55 | `paths/sanitize.py` | `test_sanitize.py` |
| CA-001-56..60 | `paths/length.py`, `paths/target.py` | `test_length.py`, `test_target.py` |
| CA-001-70..75 | `paths/filename.py`, `paths/content_types.py` | `test_filename.py`, `test_content_types.py` |
| CA-001-80..84 | `paths/collisions.py`, `paths/target.py` | `test_collisions.py`, `test_determinism.py` |
| CA-001-90..96 | `addresses/*` | `test_ipv4.py`, `test_classifier.py` |
| CA-001-100..103 | `warnings.py` | `test_warnings.py` |
| CA-001-110..112 | `urls/masking.py`, `batch/validator.py` | `test_masking.py`, propiedad (4) |
| CA-001-120..123 | `paths/destination.py` | `test_destination.py` |
| CA-001-EJ-01..55 | todos | `tests/regression/test_annex1.py` |
| RNF-001-01..03 | `batch/validator.py`, `paths/target.py` | `tests/performance/` |
| RNF-001-04 | todos | `test_determinism.py` |
| RNF-001-05 | todos | `tests/property/` |
| RNF-001-06 | todos | `test_no_side_effects.py`, `test_layers.py` |

## 9. Riesgos y pendientes
- **Para la spec 002** (no bloquean la 001): (a) qué ruta se envía al servidor si la URL procesada contiene `.`/`..` (ADR 0003); (b) la 002 debe proteger `PathReservations` con un candado y llamar a `compute_target_path` al recibir la respuesta (RN-012 d); (c) si Windows considera iguales dos nombres que `windows_fold` no (tablas Unicode distintas), la creación exclusiva en disco lo detecta y se vuelve a pedir ruta.
- `idna` y la normalización NFC dependen de la versión de Unicode de Python; se fija la versión de Python del paquete (ADR 0001).
- Prerrequisito del flujo: el repositorio **no es git todavía**; ver T-00 en [tareas.md](tareas.md).

## 8 bis. Trazabilidad real (cierre de la spec, T-25)

La tabla de la sección 8 se escribió antes de implementar y varios números de CA no coincidían con los de la spec. Esta es la correspondencia **verificada** con la spec 001 v. aprobada. Los archivos de prueba están en `tests/unit/domain/` salvo indicación.

| Criterios de la spec | Prueba |
|---|---|
| CA-001-01 a 09 (esquema, I-01, I-02, I-09, ambigüedad, credenciales, dominio con espacio) | `urls/test_parser.py`, `urls/test_parser_order.py` |
| CA-001-10, 11, 13, 14, 15 (puerto, largo, punto final, IDN, idempotencia) | `urls/test_parse_url.py`, `urls/test_host.py` |
| CA-001-12, 16 (campo individual) | `batch/test_single_input.py` |
| CA-001-17 a 22 (codificación) | `urls/test_encoding.py`, `urls/test_parse_url.py` |
| CA-001-23 a 34 (archivo masivo) | `batch/test_file_decoder.py` |
| CA-001-35 a 44 (lote, duplicados, internas) | `batch/test_validator.py`, `urls/test_dedup.py` |
| CA-001-50 a 53 (contención y orden de fallos) | `paths/test_target.py`, `tests/property/test_properties.py` (P2) |
| CA-001-54 a 61 (ruta resultante) | `paths/test_relative.py`, `paths/test_target.py` |
| CA-001-62 (invariantes de toda ruta) | `tests/property/test_properties.py` (P2, oráculo S-001-13) |
| CA-001-63 a 67 (caracteres y reservados) | `paths/test_sanitize.py` |
| CA-001-70 a 79 (longitudes) | `paths/test_length.py`, `paths/test_target.py` |
| CA-001-80 a 87 (nombre y extensión) | `paths/test_filename.py`, `paths/test_content_types.py`, `paths/test_collisions.py` |
| CA-001-88 a 91 (colisiones) | `paths/test_collisions.py`, `paths/test_target.py`, `tests/regression/test_determinism.py` |
| CA-001-92 a 97 (direcciones) | `addresses/test_classifier.py`, `addresses/test_ipv4.py`, `addresses/test_tables.py` |
| CA-001-100 a 106 (avisos, tipos) | `paths/test_warnings.py`, `paths/test_content_types.py` |
| CA-001-107 a 109 (enmascarado) | `urls/test_masking.py`, `tests/property/test_properties.py` (P4) |
| CA-001-110 a 112 (carpeta destino) | `paths/test_destination.py` |
| Ejemplos EJ-01 a EJ-55 | `tests/regression/test_annex1.py` |
| RNF-001-01 a 03 | `tests/performance/test_performance.py` |
| RNF-001-04 | `tests/regression/test_determinism.py`, `tests/property/test_properties.py` (P5) |
| RNF-001-05 | `tests/property/test_properties.py` (P1 a P5, semilla `20261107`) |
| RNF-001-06 | `tests/architecture/`, gancho de auditoría en `tests/conftest.py` |

### Cambios de diseño respecto al plan original (todos por seguir la spec)
- **D-02, D-07, D-09 y D-10** corregidas en la sección 4.
- `compute_target_path` recibe un `PathEnvironment` (disco, reservas, límites).
- `decode_batch_file` devuelve `DecodedBatch`; `internal_hosts` lleva `InternalHost(host, count)`.
- `classify_host(host, ip)` sustituye a `classify_url_host(url)`.
- Defensa añadida por las propiedades: `SourceLine` y `RawUrl` muestran solo su forma enmascarada, y el enmascarado de texto no analizable salta las barras iniciales antes de buscar credenciales (hueco de S-001-08 b).
- Optimización: una URL cuyo tramo tras la autoridad ya supera 2 048 caracteres es I-04 sin codificarla (RNF-001-03 b).
