# Catálogo de patrones — Descargador

- **Estado**: Aprobada · **Fecha**: 2026-11-07 · **ADR**: [0002](adr/0002-capas-y-catalogo-de-patrones.md)

Cada plan declara qué patrones aplica por ID. Un patrón nuevo o una excepción requieren ADR y actualizar este archivo.

## Patrones adoptados

| ID | Patrón | Cuándo se usa | Cómo se implementa aquí | Cómo se verifica |
|---|---|---|---|---|
| PA-01 | **Capas con regla de dependencias** | Siempre | `ui → application → domain ← infrastructure`. `domain` solo importa la biblioteca estándar pura (`dataclasses`, `enum`, `typing`, `unicodedata`, `ipaddress`, `functools`, `itertools`, `collections`, `re`) y `idna`. `application` importa `domain`. `infrastructure` implementa puertos de `application`. `ui` solo habla con `application` | `tests/architecture/test_layers.py` (AST) + `banned-api` de ruff en `domain/` |
| PA-02 | **Puertos y adaptadores** | Toda E/S (red, disco, DNS, proxy, reloj, registro, preferencias) | Puertos como `typing.Protocol` en `application/ports.py`; adaptadores en `infrastructure/`. El dominio recibe datos o puertos de **solo lectura** (`KnownDiskEntries`) | Pruebas de `application` con dobles; integración de cada adaptador |
| PA-03 | **Objetos de valor inmutables** | Conceptos del dominio (URL interpretada, ruta, nombre, resultado) | `@dataclass(frozen=True, slots=True)`; construcción solo mediante funciones del dominio que validan (constructor inteligente). Tuplas en lugar de listas | mypy `--strict`; pruebas de igualdad/hash |
| PA-04 | **Resultado explícito en lugar de excepciones de negocio** | Toda validación con desenlace previsto (I-NN, F-NN, rechazos del archivo) | Unión etiquetada: `Ok[T] \| Err[E]` (dataclasses) o tipos resultado específicos; códigos de **catálogos cerrados** (`enum`). Las excepciones quedan para defectos de programación | Pruebas de propiedades: toda entrada termina en `Ok` o en un código del catálogo; 0 excepciones |
| PA-05 | **Núcleo funcional, cáscara imperativa** | Lógica decidible sin E/S | Funciones puras y deterministas en `domain`; la orquestación con E/S en `application` | Gancho de auditoría (RNF-001-06); prueba de determinismo |
| PA-06 | **Tablas normativas como datos** | Listas del glosario y tablas de reglas (2.1–2.5, tipos de contenido, catálogos I/F/A) | Un único módulo por tabla, con constantes inmutables (`frozenset`, `Mapping` de solo lectura) y referencia a la regla en el docstring | Prueba que compara cada tabla con el número de entradas del glosario |
| PA-07 | **MVVM ligero** (spec 004) | Interfaz | Vista Qt sin lógica; ViewModel (Python puro, probado sin Qt) que llama a casos de uso de `application` y expone estado observable | Pruebas unitarias de ViewModels sin interfaz |
| PA-08 | **Raíz de composición única** (spec 002+) | Arranque | `downloader/__main__.py` construye adaptadores y casos de uso y los inyecta por constructor. Sin contenedor de DI ni singletons | Prueba de arranque; prueba AST de ausencia de estado global mutable |

## Antipatrones prohibidos

| ID | Antipatrón | Por qué |
|---|---|---|
| AP-01 | Lógica de negocio en la vista o en manejadores de eventos | Imposible de probar; viola PA-01/PA-07 |
| AP-02 | Analizar texto de URL fuera de `domain.urls` (`urllib.parse`, `urllib3.util.parse_url`, `yarl`, regex ad hoc) | Rompe el analizador único (RN-001a, AB-20) |
| AP-03 | Construir rutas de disco con datos externos fuera de `domain.paths` (`os.path.join`, `pathlib` con segmentos de URL o nombres del servidor) | Salto de directorio (AB-01) |
| AP-04 | Excepciones para flujo de negocio o `except Exception: pass` | Fallos silenciosos; RN-016 c |
| AP-05 | Estado global mutable (módulos con listas/dicts modificados, singletons) | No determinista; carreras entre hilos |
| AP-06 | Registrar o mostrar URLs completas, rutas, `str(exception)` o `repr` de objetos con URL sin enmascarar | RN-036, RN-037, AB-18 |
| AP-07 | Desactivar validaciones (`verify=False`, `CERT_NONE`, `check_hostname=False`) | RN-018 |
| AP-08 | Tocar widgets desde hilos de trabajo | Cuelgues; usar la cola de eventos (ADR 0005) |
