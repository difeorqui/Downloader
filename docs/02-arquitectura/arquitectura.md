# Arquitectura — Descargador para Windows

- **Estado**: Aprobada · **Fecha**: 2026-11-07
- **Decisiones**: [ADR 0001–0007](adr/README.md) · **Patrones**: [patrones.md](patrones.md) · **Constitución**: [../constitucion.md](../constitucion.md)

## 1. Stack (resumen)
Python ≥ 3.13 (se usa 3.15) · dominio puro con `idna` · red con `urllib3` + `truststore` + WinHTTP por `ctypes` · concurrencia con hilos y cola de eventos · interfaz **PySide6** (propuesto; alternativa tkinter, ver ADR 0006) · pytest + hypothesis + ruff + mypy · pip-tools con hashes + pip-audit · distribución portable PyInstaller `--onedir` en ZIP + SHA-256.

## 2. Estilo: capas con puertos y adaptadores (PA-01, PA-02)

```
            ┌──────────────┐
            │      ui      │  PySide6, ViewModels (004)
            └──────┬───────┘
                   ▼
            ┌──────────────┐        ┌──────────────────┐
            │ application  │◄───────│  infrastructure  │  urllib3, truststore,
            │ casos de uso │ puertos│  adaptadores     │  socket, os, ctypes/Win32
            └──────┬───────┘        └────────┬─────────┘
                   ▼                         │
            ┌──────────────┐                 │
            │    domain    │◄────────────────┘ (solo tipos/funciones puras)
            │  sin E/S     │
            └──────────────┘
```

Límites de confianza: (1) texto del usuario y archivo masivo → `domain.batch`/`domain.urls`; (2) respuestas del servidor (cabeceras, nombre sugerido, tipo) → `infrastructure.http` → datos para `domain.paths`; (3) sistema de archivos → `infrastructure.fs` (sin seguir uniones). Ver [modelo de amenazas](../05-seguridad/modelo-amenazas.md).

## 3. Estructura del repositorio

```
pyproject.toml                  # metadatos, ruff, mypy, pytest, coverage
requirements/{app,dev}.in|.txt  # fijadas con hashes (pip-tools)
.pre-commit-config.yaml
src/downloader/
  __init__.py
  __main__.py                   # raíz de composición (PA-08)           [002/004]
  domain/                       #                                        [001]
    ruff.toml                   # banned-api: os, pathlib, io, socket, urllib, http, threading, time, open…
    catalog.py                  # I-01..I-09, F-01..F-99 (clase), A-1..A-3
    text.py                     # windows_fold (S-001-03), utf16_len (S-001-02)
    result.py                   # Ok / Err
    urls/        parser.py, encoding.py, host.py, model.py (ParsedUrl), masking.py, dedup.py
    addresses/   ipv4.py (notaciones WHATWG), classifier.py, lists.py (glosario 2.1/2.2)
    batch/       file_decoder.py (RN-002/003), single_input.py (I-08), validator.py (RN-005/006)
    paths/       decode.py (RN-011), sanitize.py (RN-014/015), relative.py (RN-008),
                 content_types.py, filename.py (RN-010), length.py (RN-016),
                 collisions.py (RN-012/013 b), target.py (orquestador), destination.py (RN-007 c)
    warnings.py                 # A-1/A-2 (RN-021, glosario 2.3)
    failures.py                 # [003] código HTTP/excepción → F-NN y clase; política de reintentos
    export.py                   # [004] formato del anexo 3
  application/                  #                                        [002–004]
    ports.py                    # Protocol: HttpGateway, Resolver, ProxyResolver, FileSystem,
                                #   FolderRegistry, ErrorLog, Clock, PreferencesStore, Notifier
    batch_runner.py             # planificador con cupos ajustables (ADR 0005)
    download_item.py            # ciclo de un elemento: resolver → conectar → redirecciones → temporal → MOTW → nombre final
    authorizations.py           # dominios autorizados por lote (RN-017 d), con candado
    events.py                   # eventos inmutables hacia la UI
    use_cases.py                # validate_input, start_batch, cancel, retry_failed, export_not_completed
  infrastructure/               #                                        [002–003]
    http/  pinned_pool.py (IP fijada, SNI), tls.py (truststore + RN-018 d), redirects.py
    proxy_winhttp.py            # ctypes WinHTTP (autodetección + PAC)
    dns.py                      # getaddrinfo
    fs.py                       # \\?\, mkdir sin seguir uniones, temporal 'xb', MOTW, rename sin reemplazo
    error_log.py                # RN-037 (rotación 5×2 MB, 30 días)
    folder_registry.py          # RN-031 b
    preferences.py              # RN-043 (JSON)
    system_folders.py           # rutas del sistema para RN-007 c
  ui/                           #                                        [004–005]
    app.py, main_window.py, viewmodels/, themes/ (claro, oscuro, cálido, sistema)
tests/                          # NUNCA se empaqueta
  architecture/  unit/domain/  regression/  property/  performance/
  integration/ (002+, servidor local de pruebas en 127.0.0.1)  ui/ (004)
```

## 4. Módulos por spec

| Spec | Capa | Módulos | Notas clave |
|---|---|---|---|
| **001** | domain | `catalog`, `text`, `result`, `urls/*`, `addresses/*`, `batch/*`, `paths/*`, `warnings` | Puro, sin E/S. Plan completo en `specs/001-*/plan.md` |
| **002** | application + infrastructure | `ports`, `batch_runner`, `download_item`, `authorizations`, `events`; `http/*`, `proxy_winhttp`, `dns`, `fs`, `error_log`, `folder_registry`, `system_folders` | Reutiliza `domain.addresses.classifier` para las IP resueltas (RN-017 b), `domain.paths.target` en el momento de la respuesta (RN-012 d) y `domain.paths.destination` con `os.path.realpath`. Reservas de rutas con candado por lote. Servidor local de pruebas en `tests/integration/server/` |
| **003** | domain + application + infrastructure | `domain/failures.py` (clasificación, esperas 2/4/8, `Retry-After` ≤ 60 s), vigilante de tiempos (15/30/60 s, duración máx.), cancelación (`Event` + cierre forzado del socket), reserva de espacio (`shutil.disk_usage`), limpieza de huérfanos, instancia única | Las decisiones (¿reintento?, ¿qué F-NN?) son puras en el dominio; los relojes se inyectan (`Clock`) para probar plazos sin esperar |
| **004** | ui + application | `ui/*` (MVVM, PA-07), `use_cases.export_not_completed`, `domain/export.py`, preferencias, notificación, "Abrir carpeta" (solo `os.startfile` sobre un **directorio** verificado) | La UI drena la cola de eventos cada ≈ 100 ms y agrega el avance (RNF-03). Token canario de punta a punta |
| 005 | ui | temas, contraste, teclado, Narrador | — |
| 006 | build | `build/pyinstaller.spec`, script de ZIP + SHA-256, notas de la versión | Verifica que el paquete no contiene `tests/` ni dependencias de desarrollo |

## 5. Decisiones transversales
- **Comparación sin distinguir mayúsculas como Windows** (S-001-03): `windows_fold` aplica mayúscula simple carácter a carácter solo si la conversión da un único carácter del plano básico; no se usa `casefold()` (convierte `ß` en `ss`, que Windows no iguala).
- **Longitudes** (S-001-02): unidades UTF-16 (`len(s.encode("utf-16-le")) // 2`).
- **Nunca sobrescribir** aunque el dominio prediga mal: la infraestructura crea con `open(..., "xb")` y renombra con `os.rename` (falla si existe) y, ante conflicto, vuelve a pedir ruta al dominio.
- **Enmascaramiento por defecto**: `__repr__`/`__str__` de `ParsedUrl` y de todo objeto con URL devuelve la forma de RN-036.
