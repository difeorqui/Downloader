---
type: adr
status: accepted
date: 2026-11-07
supersedes:
superseded_by:
spec: 001-url-a-ruta-segura
tags: [language, platform, distribution]
---
# 0001 - Python 3 como plataforma y ejecutable portable con PyInstaller

## Contexto
Aplicación de escritorio Windows 10 ESU / 11 de 64 bits, de uso interno, instalable **sin permisos de administrador** (RN-039 d), sin actualizaciones automáticas, firma opcional (S-47). El usuario pide una solución **sencilla en Python**, sin nada especializado ni para la Microsoft Store, y quiere probarla cuanto antes.

En el equipo hay: **Python 3.15.0** (`C:\Python315`, Tcl/Tk 9.0.4, OpenSSL 3.5.9), Python 3.13 (Microsoft Store), Node 24.22, Git 2.55. **No** hay .NET SDK ni Rust.

Requisitos que condicionan la plataforma: fijar la IP comprobada al conectar (RN-017 b), validar certificados contra el almacén de Windows con revocación (RN-018), proxy del sistema (RN-020), marca de origen por flujo alterno NTFS (RN-022), crear carpetas sin seguir uniones (RN-013 b), memoria < 300 MB (RNF-07), arranque < 3 s (RNF-05).

## Opciones consideradas
| Opción | Ventajas | Riesgos |
|---|---|---|
| **Python 3 + PyInstaller (portable)** | Instalado ya; decisión del usuario; biblioteca estándar cubre `ssl`, `socket`, `ipaddress`, `unicodedata`, flujos alternos NTFS y `ctypes` para Win32; pruebas muy productivas (pytest, hypothesis) | Ejecutable de 30–150 MB según la interfaz; falsos positivos de antivirus con `--onefile`; Python 3.15 es reciente (soporte de PyInstaller y ruedas a verificar) |
| .NET 10 + WPF | Integración nativa (ConnectCallback, almacén de certificados, accesibilidad UIA) | SDK no instalado; descartado por el usuario |
| Electron (Node 24) | Node instalado; UI web flexible | > 150 MB de memoria base (RNF-07 en riesgo); `https` de Node no usa el almacén de Windows por defecto; más superficie de ataque |
| Tauri (Rust) | Binario pequeño | Rust no instalado; dos lenguajes (Rust + web); curva alta |

## Decisión
**Python** con `requires-python = ">=3.13"`; se desarrolla y empaqueta con **3.15** (instalado). Distribución en **spec 006** como **carpeta portable de PyInstaller (`--onedir`) comprimida en ZIP** con su suma SHA-256, más un acceso directo opcional creado por el usuario. Sin instalador, sin MSIX, firma Authenticode opcional del `.exe` si TI aporta certificado.

Se descarta `--onefile`: se extrae en `%TEMP%` en cada arranque (penaliza RNF-05) y dispara más falsos positivos de antivirus.

## Consecuencias
- Más fácil: un solo lenguaje, cero instalación de SDK, pruebas rápidas y expresivas.
- Más difícil: las funciones Win32 que la biblioteca estándar no cubre (proxy WinHTTP con PAC, notificaciones si la UI no las da) van por `ctypes` en la capa de infraestructura, con pruebas de integración.
- **Riesgo aceptado**: Python 3.15.0 salió en octubre de 2026; si PyInstaller o alguna rueda no lo soporta aún, se empaqueta con 3.13 (ya instalado), que cumple `requires-python`. Se verifica en la tarea de andamiaje.
- **Seguridad**: el ejecutable sin firma muestra SmartScreen (excepción S-47 documentada); integridad por SHA-256 publicada en canal interno. Las pruebas y sus dependencias no entran en el paquete (constitución §17; verificación en spec 006).
- Rutas largas: la infraestructura usará el prefijo `\\?\` en las operaciones de disco para no depender del manifiesto del ejecutable; los límites de RN-016 los impone el dominio.

## Relacionado
[[0002-capas-y-catalogo-de-patrones]] · [[0004-red-urllib3-truststore]] · [[0006-interfaz-pyside6]] · [[0007-calidad-pruebas-y-dependencias]] · [[prd]] · [[roadmap-specs]]
