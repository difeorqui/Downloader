# Constitución del proyecto — Descargador para Windows

- **Estado**: Aprobada
- **Fecha**: 2026-11-07
- **Autor**: arquitecto de software
- **Origen**: reglas globales del usuario (`~/.claude/CLAUDE.md`), PRD v0.5 (supuesto S-28)

Son principios **no negociables**. Una excepción solo es válida si queda en un ADR aceptado por el usuario.

## 1. Proceso
1. **Sin spec no hay código.** Flujo SDD: spec `Aprobada` → plan `Aprobado` → `tareas.md` → implementación TDD → verificación. Rama `feat|fix|refactor|perf/NNN-nombre`; nunca commit directo a `main`.
2. **Prueba primero.** Cada tarea trae su prueba; cada bug, su prueba de regresión.
3. Toda decisión de arquitectura (tecnología, patrón, contrato, seguridad, dependencia relevante) tiene **ADR**.

## 2. Arquitectura
4. **Capas**: `ui → application → domain ← infrastructure`. El dominio no importa nada de las otras capas, ni de red, disco, interfaz, hilos ni reloj.
5. **Dominio puro**: funciones deterministas, sin E/S, sin estado global mutable. El estado del disco, la respuesta del servidor y la configuración entran como **datos**.
6. **SOLID, composición sobre herencia, YAGNI.** Sin lógica de negocio en la interfaz.
7. Los patrones se toman de `docs/02-arquitectura/patrones.md`; cada plan declara cuáles aplica.

## 3. Seguridad (OWASP)
8. **Toda entrada externa es hostil** (texto del usuario, archivo masivo, respuestas y cabeceras del servidor): se valida en el borde con listas cerradas (allow-list).
9. **Una sola interpretación de cada URL** (RN-001a): nunca se vuelve a analizar el texto.
10. **Nada se escribe fuera de la carpeta destino** (RN-013); nunca se sobrescribe (RN-012).
11. **Cero secretos** en código, logs, specs o commits. **Logs sin URLs completas, rutas, nombres de usuario, tokens ni texto de excepciones** (RN-037). Los `__repr__`/`__str__` de objetos con URLs devuelven la forma enmascarada (RN-036).
12. Nunca se construyen comandos de shell, SQL ni rutas concatenando datos del usuario sin pasar por el dominio de rutas seguras. Prohibidos `eval`, `exec`, `pickle` con datos externos, `shell=True` y `os.system`.
13. Sin desactivar la validación TLS en ningún punto (RN-018).
14. **Dependencias mínimas, fijadas con hash y auditadas** (`pip-audit`) antes de añadirlas; cada dependencia de ejecución tiene ADR.

## 4. Pruebas y calidad
15. Tipos de prueba según aplique: unitarias, integración, regresión, contrato y carga. Cada criterio de aceptación y cada caso de abuso tiene al menos una prueba.
16. **Cobertura ≥ 80 % global y ≥ 90 % en `src/downloader/domain`** (líneas y ramas). No se bajan umbrales para pasar.
17. **Las pruebas nunca llegan a producción ni se ejecutan contra producción**: viven en `tests/`, sus dependencias están en `requirements/dev.txt`, el ejecutable distribuido no las incluye y las pruebas de red usan solo el servidor local de pruebas.
18. Antes de dar algo por terminado: `ruff check`, `ruff format --check`, `mypy --strict`, `python -m pre_commit run --all-files` (gitleaks, semgrep) y pruebas en verde. Nunca `--no-verify`.

## 5. Datos y privacidad
19. Minimización (Ley 1581, PRD 8.1): solo se persisten preferencias, registro mínimo de errores y registro transitorio de carpetas. Sin telemetría.
