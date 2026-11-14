---
type: adr
status: accepted
date: 2026-11-07
supersedes:
superseded_by:
spec: 001-url-a-ruta-segura
tags: [domain, security, url, dependency]
---
# 0003 - Analizador de URL propio en el dominio; `idna` para dominios internacionales

## Contexto
RN-001 y RN-001a fijan un orden exacto de comprobaciones (I-02 → esquema → I-09 → corrección → ambigüedad sobre la **autoridad cruda** → credenciales sobre la **autoridad** → `\` a `/` → codificación selectiva → IDN) y exigen **una sola interpretación** reutilizada para validar, calcular rutas, comprobar direcciones y conectar. Las notaciones alternativas de IP (AB-14) deben detectarse.

## Opciones consideradas
- **`urllib.parse` (biblioteca estándar)**: sin dependencias. Riesgos: no valida (acepta casi todo), no detecta la ambigüedad de RN-001a, no interpreta IPv4 en octal/hexadecimal/abreviada, y su forma de partir la autoridad difiere de la exigida (AB-20).
- **`urllib3.util.parse_url` / `rfc3986` / `yarl`**: más estrictos. Riesgos: aplican su propia normalización (puntos, mayúsculas, codificación) que contradice RN-008 f y RN-011; dos criterios de análisis en el sistema.
- **Analizador propio, pequeño y basado en las reglas**, con `ipaddress` (estándar) para IPv6 y rangos, un intérprete IPv4 propio estilo WHATWG (decimal, octal, hexadecimal, abreviado) y la biblioteca **`idna`** (pura Python, UTS #46 no transicional) para la forma ASCII del dominio. Riesgos: código propio crítico; se mitiga con los 55 ejemplos, pruebas de propiedades (100 000 entradas) y cobertura ≥ 90 %.
- Para IDN, alternativa: códec estándar `"idna"` (IDNA 2003). Riesgo: difiere de los navegadores (p. ej. `ß` → `ss`), con lo que la app podría conectar a otro dominio que el que el usuario ve en el navegador.

## Decisión
**Analizador propio** en `downloader.domain.urls`, que produce un `ParsedUrl` inmutable; **ninguna otra capa analiza texto de URL** (AP-02). Para IDN se usa `idna` (`uts46=True, transitional=False, std3_rules=False`) **solo si el dominio tiene caracteres no ASCII**; los dominios ASCII se pasan a minúsculas sin más (así no se rechazan nombres internos con `_`). El IPv4 con notación alternativa se clasifica por su valor; el nombre de carpeta usa el dominio tal como quedó escrito (en minúsculas).

La spec 002 debe construir la petición HTTP a partir de `ParsedUrl` (host, puerto, ruta y consulta ya codificados) y conectar a la IP **resuelta y clasificada** (o a la del literal ya interpretado), nunca re-analizando el texto.

## Consecuencias
- Más fácil: trazabilidad directa regla → función; comportamiento idéntico en todo el sistema.
- Más difícil: mantener el analizador; cualquier caso nuevo exige prueba.
- Dependencia de ejecución nueva en el dominio: `idna` (pura, sin E/S, ampliamente usada). Se fija con hash y se audita.
- Pendiente para la spec 002 (no bloquea la 001): decidir qué ruta se envía al servidor cuando la URL procesada contiene segmentos `.`/`..` (p. ej. ejemplo 4). La 001 no los elimina de la URL procesada; solo los descarta al calcular carpetas.

## Relacionado
[[spec]] (001) · [[reglas-negocio]] · [[glosario]] · [[0002-capas-y-catalogo-de-patrones]] · [[0004-red-urllib3-truststore]]
