---
type: adr
status: accepted
date: 2026-11-07
supersedes:
superseded_by:
spec: 001-url-a-ruta-segura
tags: [testing, quality, dependencies, security]
---
# 0007 - Herramientas de pruebas, calidad y gestión de dependencias

## Contexto
La constitución exige: pruebas unitarias, de regresión, propiedades (100 000 entradas, RNF-001-05), rendimiento (RNF-001-01..03); cobertura ≥ 80 % / ≥ 90 % dominio; linter, formateador, tipos; pre-commit con gitleaks y semgrep; dependencias fijadas y auditadas; pruebas fuera de producción. Solo hay Python y pip instalados (sin uv, pipx ni Go).

## Opciones consideradas
- Pruebas: **pytest + hypothesis + pytest-cov** (estándar de facto; hypothesis reduce los contraejemplos) / `unittest` (sin dependencias, sin propiedades ni parametrización cómoda).
- Lint/formato/tipos: **ruff (lint + format) + mypy --strict** / flake8 + black + isort + pyright (más piezas).
- Fijación: **pip-tools (`pip-compile --generate-hashes`) + `pip install --require-hashes`** (solo pip; archivos `requirements/*.txt` legibles) / **uv** (más rápido, `uv.lock` con hashes; requiere instalar otra herramienta) / Poetry (más pesado).
- Auditoría: **pip-audit** (base de datos PyPA/OSV).
- Regla de capas: **prueba propia por AST** (0 dependencias) / `import-linter` (otra dependencia).
- "Sin efectos externos" del dominio (RNF-001-06): **gancho de auditoría `sys.addaudithook`** activo durante las pruebas del dominio (detecta `socket.connect`, `socket.getaddrinfo`, `open` en escritura, `os.mkdir`, `os.remove`, `os.rename`) / `pytest-socket` (solo red).

## Decisión
pytest, hypothesis, pytest-cov, ruff, mypy `--strict`, pip-tools con hashes, pip-audit, pre-commit (hooks: ruff, ruff-format, mypy, gitleaks, semgrep `p/python` + `p/owasp-top-ten`, pytest rápido). Regla de capas con prueba AST propia y `banned-api` de ruff en `domain/`. Efectos externos con gancho de auditoría propio.

- `requirements/app.in` → `app.txt` (ejecución: `idna`, `urllib3`, `truststore`, `PySide6` si se acepta ADR 0006).
- `requirements/dev.in` → `dev.txt` (con `-c app.txt`): pruebas, calidad y `pyinstaller`. **Nunca se empaquetan.**
- Perfiles de hypothesis: `dev` (2 000 ejemplos, en cada commit) y `ci` (100 000, marca `fuzz`, antes de integrar).

## Consecuencias
- Todo se instala con pip en `.venv`; sin herramientas globales extra salvo gitleaks.
- **Riesgo en Windows**: el hook oficial de gitleaks compila con Go (no instalado) → se usa `gitleaks` instalado con `winget install Gitleaks.Gitleaks` y hook `language: system`. Semgrep tiene soporte nativo de Windows limitado; si falla, se ejecuta desde WSL o contenedor y se informa (no se desactiva). Se comprueba en la tarea T-01.
- mypy y hypothesis pueden tardar en publicar ruedas para 3.15; ambos tienen versión pura Python, así que funcionan (más lento).

## Relacionado
[[constitucion]] · [[0001-python-escritorio-portable]] · [[0002-capas-y-catalogo-de-patrones]] · [[plan]] (001)
