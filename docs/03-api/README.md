# Contratos

La aplicación **no expone API de red** (no hay servidor ni OpenAPI). Los contratos son las **interfaces públicas entre capas**, definidas antes del código y versionadas con cada spec:

| Contrato | Productor | Consumidores | Archivo |
|---|---|---|---|
| Dominio: URL → ruta segura | `downloader.domain` (spec 001) | `application` (002, 003, 004) | [dominio-001.md](dominio-001.md) |
| Puertos de E/S | `application/ports.py` (spec 002) | `infrastructure` | pendiente (plan 002) |
| Eventos de avance hacia la UI | `application/events.py` (spec 002) | `ui` (004) | pendiente (plan 002) |

Cambiar una firma pública de un contrato exige actualizar este directorio y, si rompe consumidores, un ADR.
