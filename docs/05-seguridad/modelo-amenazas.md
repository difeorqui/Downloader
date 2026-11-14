# Modelo de amenazas — Descargador

- **Estado**: Borrador · **Fecha**: 2026-11-07 · Base: PRD 8.3 (AB-01 a AB-21)

## Activos
Integridad del sistema de archivos del usuario fuera de la carpeta destino; servicios de la red interna; tokens dentro de las URLs; confianza del usuario en lo descargado (ejecutables disfrazados); integridad del ejecutable distribuido.

## Límites de confianza
| # | Límite | Datos hostiles que lo cruzan | Componente que valida |
|---|---|---|---|
| L1 | Usuario / archivo masivo → aplicación | Texto, bytes del `.txt` | `domain.batch`, `domain.urls` (001) |
| L2 | Servidor remoto / proxy → aplicación | Cabeceras, nombre sugerido, tipo, redirecciones, certificados, cuerpo | `infrastructure.http` + `domain.paths` (001/002) |
| L3 | Aplicación → red | Conexiones a IP resueltas | `domain.addresses` + `infrastructure.http` (001/002) |
| L4 | Aplicación → disco | Carpetas, temporales, nombres finales | `domain.paths` + `infrastructure.fs` (001/002) |
| L5 | Aplicación → pantalla / registro / exportación | URLs y errores | `domain.urls.masking`, `error_log` (001/002/004) |
| L6 | Distribución → equipo del usuario | ZIP con el ejecutable | SHA-256 + firma opcional (006) |

## STRIDE por spec
- **001**: ver `specs/001-url-a-ruta-segura/plan.md` §6.
- 002–006: se completa en cada plan.

## Riesgos residuales aceptados (del PRD)
S-38 (proxy: sin fijar IP, fuga de dominios al DNS, WPAD suplantable), tokens en la ruta (RN-036), excepción de revocación no consultable (S-30), distribución sin firma (S-47), carrera entre comprobar y crear carpetas en disco por un proceso local malicioso (Python en Windows no ofrece `dir_fd`; se mitiga comprobando cada componente justo antes y después de crearlo — detalle en el plan 002).
