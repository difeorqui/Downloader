---
type: adr
status: accepted
date: 2026-11-07
supersedes:
superseded_by:
spec: 004-interfaz-principal
tags: [ui, accessibility, dependency]
---
# 0006 - Interfaz gráfica con PySide6 (Qt 6) en lugar de tkinter

## Contexto
La interfaz se construye en la spec 004 (y 005), pero la elección afecta al empaquetado y conviene cerrarla ya. Requisitos aprobados en el PRD que la condicionan:
- **RN-042 / RNF-11 (3)**: el **Narrador** anuncia nombre y estado de cada control y los cambios de estado del lote.
- RN-042 / RNF-11 (4): escalado 100/125/150 % sin cortes.
- RN-038: temas claro, oscuro, cálido y "según Windows", siguiendo el cambio del sistema en caliente; contrastes ≥ 4.5:1.
- RN-040: arrastrar y soltar un `.txt` sobre la ventana.
- RN-041: notificación de Windows al terminar.
- RNF-01/02: lista de avance con 10 000 filas fluida; RNF-07 < 300 MB.

El usuario prefiere tkinter/ttk por sencillez (biblioteca estándar, cero dependencias). El Python instalado trae Tk **9.0.4**.

## Opciones consideradas
| Requisito | tkinter/ttk (Tk 9.0) | PySide6 (Qt 6, LGPL) |
|---|---|---|
| Narrador (RN-042) | **Riesgo alto**: los controles de Tk se dibujan por Tk y, hasta donde conozco, Tk 9.0 no los expone a UI Automation/MSAA de forma útil; el Narrador lee poco más que el título. No hay forma razonable de arreglarlo desde Python | Expone los widgets a UI Automation; nombres y estados accesibles con `setAccessibleName`/`setAccessibleDescription` |
| Escalado DPI | Manual (`SetProcessDpiAwareness` por `ctypes` y escalar fuentes) | Automático (Per-Monitor v2) |
| Temas y "según Windows" | Estilos ttk propios; detectar el tema del sistema por registro y sondeo | Paletas/QSS propios; `QStyleHints.colorScheme` + señal de cambio |
| Arrastrar y soltar | **No hay soporte nativo**; requiere `tkinterdnd2` (binario tkdnd, compatibilidad con Tk 9 dudosa) o subclasificar la ventana con `ctypes` | Nativo |
| Notificación | `ctypes` + `Shell_NotifyIconW` | `QSystemTrayIcon.showMessage` |
| Lista de 10 000 filas | `ttk.Treeview` aguanta, con actualizaciones agregadas | `QTableView` + modelo (virtualizado) |
| Instancia única (RN-032) | Mutex por `ctypes` | `QLocalServer`/`QLocalSocket` |
| Tamaño del paquete | ≈ 30 MB | ≈ 100–150 MB (solo módulos QtCore/QtGui/QtWidgets) |
| Dependencias | 0 | 1 (con ruedas abi3, compatibles con Python 3.15) |

## Decisión
Se **propone PySide6** (solo QtWidgets, sin QML ni WebEngine), con MVVM ligero (PA-07). Motivo: tkinter no permite cumplir el criterio aprobado RNF-11 (3) del Narrador y obliga a varias soluciones por `ctypes` (arrastrar, DPI, notificación, tema del sistema) que suman más complejidad que la dependencia que se evita. Con PySide6 la interfaz resulta **más sencilla de escribir y mantener**.

**Alternativa aceptable si el usuario la prefiere**: tkinter/ttk, siempre que el analista modifique RN-042/RNF-11 (3) (Narrador fuera de la versión 1) y RN-040 (arrastrar y soltar fuera o vía `ctypes`). Esa modificación es del analista, no del arquitecto. Antes de la spec 004 se hará una prueba corta (≤ 1 h) con el Narrador sobre ambas opciones para confirmar.

## Consecuencias
- Más fácil: accesibilidad, DPI, arrastrar, notificaciones, instancia única y temas sin código Win32.
- Más difícil: paquete más grande (aceptable para app interna); memoria base ≈ 60–80 MB (dentro de RNF-07); licencia LGPL v3 — uso interno y enlace dinámico, sin obligaciones relevantes; se documenta en las notas de la versión.
- Nada de esto afecta a la spec 001 (dominio puro) ni a la 002/003.

## Relacionado
[[0001-python-escritorio-portable]] · [[0005-concurrencia-con-hilos]] · [[prd]] · [[reglas-negocio]] · [[patrones]]
