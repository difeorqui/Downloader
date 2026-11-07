---
type: adr
status: accepted
date: 2026-11-07
supersedes:
superseded_by:
spec: 002-motor-descarga-seguro
tags: [concurrency, architecture]
---
# 0005 - Concurrencia con hilos de trabajo y cola de eventos hacia la interfaz

## Contexto
1 a 8 descargas simultáneas, ajustables en caliente (RN-025); cancelación ≤ 2 s por elemento y ≤ 5 s el lote (RN-030); avance al menos una vez por segundo y UI con p95 < 200 ms (RNF-02, RNF-03); 50 MB/s con 3 descargas (RNF-06). urllib3 es síncrona (ADR 0004).

## Opciones consideradas
- **Hilos (pool propio de hasta 8 trabajadores) + `queue.Queue` de eventos que la UI consume en su bucle**: encaja con urllib3 síncrona; la E/S libera el GIL; cancelación con `threading.Event` + cierre forzado del socket. Riesgo: cuidado con el estado compartido (reservas de rutas, autorizaciones de dominio) → objetos con candado propio, nunca globales.
- **asyncio**: un solo hilo, cancelación nativa. Riesgos: obliga a httpx/aiohttp (fijar IP más difícil, ADR 0004), y la integración del bucle asyncio con el bucle de la interfaz añade complejidad.
- **Procesos**: aislamiento. Riesgo: memoria (RNF-07) y complejidad sin beneficio.

## Decisión
**Hilos**: un planificador en `application` con un semáforo de cupos ajustable (no `ThreadPoolExecutor` fijo, para aplicar RN-025 en caliente) y trabajadores daemon. Los trabajadores **nunca tocan la interfaz**: publican eventos inmutables en una cola; la UI la drena con un temporizador (≈ 100 ms) y agrega el avance (≥ 1 vez/s). Lectura en bloques de 64 KiB con comprobación de cancelación por bloque.

## Consecuencias
- Simple y suficiente para 8 descargas; la UI no se bloquea.
- Las piezas compartidas (registro de reservas de rutas RN-012, autorizaciones RN-017 d) son objetos con `threading.Lock`, creados por lote (sin estado global, AP-05).
- Riesgo bajo de rendimiento por el GIL al calcular sumas/avance: medido en RNF-06/RNF-08.

## Relacionado
[[0004-red-urllib3-truststore]] · [[0006-interfaz-pyside6]] · [[arquitectura]]
