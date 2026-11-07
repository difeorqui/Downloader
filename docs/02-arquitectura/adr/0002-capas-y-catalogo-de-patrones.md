---
type: adr
status: accepted
date: 2026-11-07
supersedes:
superseded_by:
spec: 001-url-a-ruta-segura
tags: [architecture, patterns]
---
# 0002 - Arquitectura en capas con puertos y adaptadores, y catálogo de patrones

## Contexto
La lógica de mayor riesgo (URL → ruta segura, direcciones internas, enmascaramiento) debe probarse sin red, sin disco y sin interfaz (spec 001, RNF-001-06), y reutilizarse sin cambios por el motor (002/003) y la interfaz (004). La constitución exige capas `ui → application → domain ← infrastructure`.

## Opciones consideradas
- **Capas + puertos y adaptadores (hexagonal ligera), un solo paquete Python `downloader` con subpaquetes por capa**: dominio aislado y probado al 90 %; dependencias verificables con una prueba de arquitectura. Riesgo: algo más de ceremonia (interfaces `Protocol`) en 002.
- **Script modular sin capas** (UI que llama a funciones de descarga): más rápido el primer día. Riesgo: la lógica de rutas acaba mezclada con E/S e interfaz; imposible cumplir RNF-001-06 y la cobertura del dominio.
- **Varios paquetes instalables (uno por capa)**: aislamiento fuerte. Riesgo: sobreingeniería para una app interna de un solo ejecutable.

## Decisión
Capas con puertos y adaptadores en **un único paquete** (`src/downloader/{domain,application,infrastructure,ui}`). La regla de dependencias se hace cumplir con una **prueba de arquitectura propia** (análisis AST de imports, sin dependencias) y con `banned-api` de ruff en el dominio. Catálogo de patrones PA-01 a PA-08 y antipatrones AP-01 a AP-08 en [[patrones]].

## Consecuencias
- Más fácil: probar el dominio de forma exhaustiva (ejemplos, propiedades, rendimiento) y cambiar la interfaz o la biblioteca HTTP sin tocarlo.
- Más difícil: el motor debe pasar al dominio el estado del disco y las respuestas como datos (puerto de solo lectura `KnownDiskEntries`).
- Deuda aceptada: ninguna.

## Relacionado
[[arquitectura]] · [[patrones]] · [[0003-analizador-url-propio]] · [[constitucion]]
