# Tareas — Spec 001: De la URL a una ruta segura

- **Estado:** Aprobadas
- **Fecha**: 2026-11-07
- **Plan**: [plan.md](plan.md) · **Contrato**: [dominio-001.md](../../docs/03-api/dominio-001.md)

Convenciones: cada tarea dura **≤ medio día**, se hace en TDD (la prueba indicada se escribe primero y falla) y termina con un commit Conventional Commits en la rama `feat/001-url-a-ruta-segura`. **[P]** = paralelizable con las otras [P] de su mismo bloque una vez cumplidas sus dependencias. "Hecho" = prueba en verde + `ruff check` + `ruff format --check` + `mypy --strict` + `python -m pre_commit run --all-files`.

## Bloque 0 — Preparación (hilo principal)

| ID | Tarea | Prueba / evidencia | Depende |
|---|---|---|---|
| T-00 | `git init` en `c:\Dev\Downloader`, commit de `docs/` y `specs/` en `main` (`docs: prd, reglas, spec 001, plan y ADR`), crear rama `feat/001-url-a-ruta-segura`. Requiere spec `Estado: Aprobada` y plan `Estado: Aprobado` (hook `puerta_spec.py`) | `git status` limpio en la rama | aprobaciones |
| T-01 | **Andamiaje**: `pyproject.toml` (proyecto `downloader`, `src/` layout, `requires-python = ">=3.13"`, backend setuptools fijado); `.venv` con Python 3.15 (`py -3.15 -m venv .venv`); `requirements/app.in` (`idna`) y `requirements/dev.in` (`pip-tools`, `pytest`, `pytest-cov`, `hypothesis`, `ruff`, `mypy`, `pip-audit`, `pre-commit`) compilados con `pip-compile --generate-hashes` e instalados con `--require-hashes`; configuración de ruff (reglas `E,F,W,I,B,UP,S,SIM,RUF,TID,PL` + `banned-api`), `src/downloader/domain/ruff.toml` con la lista de PA-01, mypy `strict`, pytest (`testpaths`, marcas `perf`, `fuzz`, `--strict-markers`), coverage (`branch`, `fail_under = 80`), perfiles de hypothesis `dev`/`ci`; `.gitignore`, `.editorconfig`; `.pre-commit-config.yaml` con ruff, ruff-format, mypy (local), **gitleaks** (`language: system`, previo `winget install Gitleaks.Gitleaks`), **semgrep** (`p/python`, `p/owasp-top-ten`) y pytest rápido (`-m "not perf and not fuzz"`); `pip-audit -r requirements/app.txt -r requirements/dev.txt` | `tests/test_smoke.py` (importa `downloader.domain`); `pre-commit run --all-files` en verde; `pip-audit` sin vulnerabilidades. Si semgrep o alguna rueda no funciona en Windows/3.15, se informa y se aplica la alternativa del ADR 0007/0001 (nunca se desactiva) | T-00 |
| T-02 | **Guardas de arquitectura**: `tests/architecture/test_layers.py` (AST: imports permitidos en `domain`, sin estado global mutable) y gancho `sys.addaudithook` en `tests/conftest.py` activado para `tests/unit/domain`, `tests/regression`, `tests/property` | Prueba que un módulo de ejemplo con `import socket` o `open(..., "w")` dentro de una función del dominio es detectado (archivo de muestra en `tests/architecture/samples/`) | T-01 |

## Bloque 1 — Base del dominio

| ID | Tarea | Prueba | Depende |
|---|---|---|---|
| T-03 | `catalog.py` (I-01..I-09 con textos exactos, F-01..F-99 con clase y texto, A-1..A-3), `result.py`, `text.py` (`windows_fold`, `utf16_len`, recorte) | `test_catalog.py` (conteos y clases según anexo 2), `test_text.py` (`ß`≠`ss`, `Á`=`á`, emoji cuenta 2) | T-02 |
| T-04 [P] | `addresses/ipv4.py`: decimal entera, octal, hexadecimal, abreviada, regla "termina en número", desbordes | `test_ipv4.py` (AB-14: `2130706433`, `0177.0.0.1`, `0x7f.1`, `127.1`, inválidas `1.2.3.999`, `0x1g`) | T-03 |
| T-05 [P] | `addresses/lists.py` + `classifier.py`: glosario 2.1/2.2, prevalencia de bloqueada, IPv4 incrustada, nombres (`localhost`, sin punto, sufijos) | `test_classifier.py` (CA-001-90..95 con inicio/medio/fin de cada rango; `fd00:ec2::254`) + `test_tables.py` (conteos) | T-03 (T-04 para notaciones) |
| T-06 [P] | `paths/sanitize.py`: RN-014 a–d y RN-015 | `test_sanitize.py` (CA-001-51..55; cada reservado ×{mayúsculas, extensión, varias extensiones, espacios antes del punto}) | T-03 |
| T-07 [P] | `urls/encoding.py`: codificación selectiva (ruta vs parámetros/fragmento) y decodificación única con `%XX` conservado (D-04) | `test_encoding.py` (`año 2024.pdf`, `%252e`, `%C3` suelto, `%00`) | T-03 |
| T-08 [P] | `paths/content_types.py` + `warnings.py` (A-1 sobre última extensión, A-2) | `test_content_types.py` (CA-001-75), `test_warnings.py` (CA-001-100..103) | T-03 |

## Bloque 2 — Analizador de URL

| ID | Tarea | Prueba | Depende |
|---|---|---|---|
| T-09 | `urls/model.py` + `urls/parser.py` pasos 1–6: I-02, esquema con patrón, I-01 (incluida la lista `javascript:`…), I-09, corrección `https://`, autoridad cruda (I-03 por `\` o `#…@`), autoridad (I-05), espacio en dominio (I-03), punto final | `test_parser.py` (CA-001-01..05, 07..10, 14), `test_parser_order.py` (precedencias); ejemplos 20, 29, 35, 36, 50, 52, 55 | T-07 |
| T-10 | `urls/host.py` + pasos 7–9: `\`→`/` en ruta, codificación, host (minúsculas, NFC, `idna` solo no ASCII, D-03), IPv6 entre corchetes, puerto (D-02), I-04 sobre la URL final, `processed()` | `test_host.py`, `test_parser.py` (CA-001-06, 11, 12, 15, 16 idempotencia); ejemplos 2, 3, 24, 30, 41, 49, 51 | T-04, T-09 |
| T-11 [P] | `urls/masking.py` (`masked()`, `mask_text`, D-09, D-10) y `__repr__`/`__str__` enmascarados | `test_masking.py` (CA-001-110..112; canario en `repr`, `str`, f-strings) | T-10 |
| T-12 [P] | `urls/dedup.py` + `batch/single_input.py` | `test_dedup.py` (CA-001-29..31), `test_single_input.py` (CA-001-13, 17) | T-10 |

## Bloque 3 — Archivo masivo y validación del lote

| ID | Tarea | Prueba | Depende |
|---|---|---|---|
| T-13 [P] | `batch/file_decoder.py` (D-01): extensión, 5 242 880 bytes, UTF-16, UTF-8 con línea del error, BOM, CRLF/LF/CR, comentarios, 10 000 | `test_file_decoder.py` (CA-001-20..28 con mensajes exactos) | T-03 (paralela a todo el bloque 2) |
| T-14 | `paths/relative.py`: carpeta de dominio `_puerto`, segmentos de carpeta, descarte de vacíos/`.`/`..` (D-05), RN-011 → RN-014 → RN-015 | `test_relative.py` (CA-001-40..44); ejemplos 1, 4–11, 21, 23, 32, 34, 37–39 (solo carpetas) | T-06, T-10 |
| T-15 | `batch/validator.py`: `BatchValidation` completo (conteos de corregidas por tipo, duplicadas, inválidas enmascaradas, internas, `required_folders`, `can_start`) | `test_validator.py` (CA-001-32..34); ejemplos 27, 28, 44, 45, 48 | T-05, T-11, T-12, T-13, T-14 |

## Bloque 4 — Ruta resultante

| ID | Tarea | Prueba | Depende |
|---|---|---|---|
| T-16 | `paths/filename.py`: prioridad RN-010 con `ServerResponse`, nombre tras la última `/`/`\`, sin re-decodificar, extensión por tipo, `index` | `test_filename.py` (CA-001-70..74); ejemplos 12–16, 22, 29, 40, 46, 49 | T-08, T-14 |
| T-17 [P] | `paths/length.py`: 255 por componente, ruta final vs temporal (53), 259/247/32 000 | `test_length.py` (CA-001-56..59 con límites exactos ±1) | T-03 |
| T-18 [P] | `paths/destination.py` (RN-007 c, D-11) | `test_destination.py` (CA-001-120..123; ejemplo 54 con ruta real como dato) | T-03 |
| T-19 | `paths/collisions.py`: `PathReservations`, sufijo antes de la última extensión, contador por base (D-12), prevalencia de carpetas, `KnownDiskEntries`/`InMemoryDiskEntries`, F-24 por `REPARSE_POINT`, F-27 | `test_collisions.py` (CA-001-80..84); ejemplos 18, 19, 25, 26, 42 | T-14 |
| T-20 | `paths/target.py`: orquestación D-07, avisos, **guarda de contención** | `test_target.py` (CA-001-50, 60; ejemplos 17, 43, 47) | T-16, T-17, T-19 |

## Bloque 5 — Verificación de la spec

| ID | Tarea | Prueba | Depende |
|---|---|---|---|
| T-21 | Regresión: `tests/regression/annex1_data.py` con **los 55 ejemplos** y `test_annex1.py` parametrizada (`EJ-01`…`EJ-55`); prueba de completitud de IDs | 55 casos en verde, comparación carácter a carácter | T-15, T-18, T-20 |
| T-22 [P] | Determinismo (RNF-001-04): cada caso 100 veces; ejemplos 19 y 42 en 3 órdenes | `test_determinism.py` | T-21 |
| T-23 [P] | Propiedades/fuzz (RNF-001-05, CA-001-50, 111, 16): estrategias de hypothesis del alfabeto hostil; 5 propiedades del plan §7; perfil `ci` con 100 000 | `pytest -m fuzz --hypothesis-profile=ci` en verde; tiempo registrado | T-21 |
| T-24 [P] | Rendimiento (RNF-001-01..03) con datos de semilla fija y `tracemalloc` | `pytest -m perf` en el equipo de referencia: p95 ≤ 1 s / ≤ 1 s / ≤ 2 s y ≤ 100 MB | T-21 |
| T-25 | Cierre: cobertura ≥ 80 % global y ≥ 90 % dominio (líneas y ramas), `pip-audit`, `pre-commit run --all-files`, actualizar trazabilidad del plan si cambió algo | Informe de cobertura y salida de las herramientas (resultados reales, también si algo falla) | T-22, T-23, T-24 |

**Camino crítico**: T-00 → T-01 → T-02 → T-03 → T-07 → T-09 → T-10 → T-14 → T-19 → T-20 → T-21 → T-23 → T-25 (≈ 13 medias jornadas). Con paralelismo, T-04/05/06/08/13/17/18 salen del camino crítico.

## Esquema inicial de las specs 002–004 (solo módulos; sin plan todavía)
Detalle de capas y archivos en [arquitectura.md §4](../../docs/02-arquitectura/arquitectura.md).
- **002 motor seguro**: `application/{ports, batch_runner, download_item, authorizations, events}`; `infrastructure/{http/pinned_pool, http/tls, http/redirects, proxy_winhttp, dns, fs, error_log, folder_registry, system_folders}`; servidor local de pruebas `tests/integration/server/` (HTTP/HTTPS en 127.0.0.1 con certificado de pruebas solo en el equipo de pruebas). Primera tarea propuesta: prueba de concepto (≤ medio día) de IP fijada + SNI + truststore + revocación no consultable + WinHTTP.
- **003 robustez y control**: `domain/failures.py` (F-NN, clases, esperas 2/4/8, `Retry-After`), vigilante de tiempos con `Clock` inyectado, cancelación por `Event` + cierre forzado del socket, reserva de espacio, limpieza de huérfanos, instancia única.
- **004 interfaz principal**: `ui/` con PySide6 (o tkinter según ADR 0006) en MVVM; `application/use_cases`; `domain/export.py` (anexo 3); preferencias, notificación, "Abrir carpeta".
