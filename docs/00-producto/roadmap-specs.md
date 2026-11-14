# Hoja de ruta de specs — Descargador para Windows

- **Estado**: Aprobada (rebanada rápida tras la 001: ver nota del usuario)
- **Versión**: 0.2
- **Fecha**: 2026-11-07
- **Origen**: `docs/00-producto/prd.md` v0.7 (Aprobado) y `docs/01-requerimientos/reglas-negocio.md` v0.7
- **Historial**:
  - 0.1: propuesta inicial.
  - 0.2: incorpora la revisión de `revisor-spec`:
    - la fila 001 se alinea con los 6 ejemplos parciales;
    - se asignan a la 002 AB-08 (por redirección), AB-12, AB-04 (parte real), RNF-12 en equipo real, RN-010 paso 1 y RN-012 d;
    - se asignan a la 004 los diálogos de RN-017 a, RN-017 d y RN-027 d;
    - se reparte RN-026 entre la 002 y la 003;
    - se aclara que las dependencias son transitivas;
    - la 006 se simplifica por el cambio del usuario de la v0.6 (app Python sencilla, sin instalador).

## Criterio de división

1. Cada spec se puede entregar y verificar por sí sola, con sus pruebas.
2. Primero va el **dominio puro**: de la URL a una ruta segura. Se puede probar sin red, sin disco y sin interfaz, y concentra las reglas de seguridad de rutas (anexo 1).
3. **El MVP son las specs 001 a 004**. Con ellas el usuario ya puede descargar de forma segura, ver el avance y cancelar. Las specs 005 y 006 completan la versión 1.
4. Cuando una regla aparece en dos specs, una decide la **lógica**, normalmente la 001, y la otra la **aplica en el equipo real**, con red o disco. Cada spec indica qué parte cubre.
5. **Las dependencias son transitivas**: una spec depende de todas las que necesitan las specs de las que depende.

## Specs propuestas (en orden de entrega)

| Spec | Nombre | Qué entrega | Reglas | Casos de abuso | RNF | Ejemplos del anexo 1 | Depende de |
|---|---|---|---|---|---|---|---|
| 001 | `001-url-a-ruta-segura` | Interpretación y validación de URLs y del contenido del archivo masivo, ruta resultante segura, nombre, colisiones, comprobación léxica de direcciones, clasificación de avisos A-1/A-2 y enmascaramiento. Todo sin red, sin disco y sin interfaz | RN-001, RN-001a, RN-002, RN-003, RN-004, RN-005 (datos), RN-006, RN-007 c (regla, sobre la ruta real y las ubicaciones del sistema recibidas), RN-008 a RN-011, RN-012 a–c, RN-013 a, RN-013 b (regla, sobre el estado del disco recibido), RN-014 a RN-016, RN-017 a (datos), RN-021 (solo clasificación A-1/A-2), RN-036 (regla) | AB-01, AB-02 (léxica), AB-03, AB-04 (cálculo), AB-06, AB-08 (en la entrada), AB-10, AB-12 (lógica), AB-14, AB-15 (lógica), AB-16, AB-18 (enmascaramiento), AB-20 | RNF-04 (parte de dominio), RNF-12 (cálculo) | Los 55. Completos: 49. Parciales, con la parte de red en la 002: **22, 23, 27, 44, 48 y 53** | — |
| 002 | `002-motor-descarga-seguro` | Descarga real con concurrencia. Incluye: proxy de Windows, certificados, resolución con dirección fijada, redirecciones, F-30 y autorización por dominio, nombre sugerido real, orden de reserva de nombres, temporales, marca de origen, creación de carpetas sin seguir enlaces, validación real de la carpeta destino y de las ubicaciones del sistema, y registro de errores mínimo | RN-001a (redirecciones), RN-007, RN-010 paso 1 (formas simple e internacional en respuestas reales), RN-012 d (orden de reserva), RN-013 b, RN-016 (aplicación real), RN-017 b–e (lógica), RN-018, RN-019, RN-020, RN-022, RN-025, RN-026 (parte 002), RN-031 a–b, RN-037 | AB-01 y AB-15 (en disco real), AB-02, AB-04 (real), AB-07, AB-08 (por redirección, F-22), AB-09, AB-11, AB-12 (respuestas reales), AB-13, AB-17, AB-21 | RNF-01 (motor), RNF-06, RNF-07, RNF-08, RNF-12 (en equipo real, con y sin rutas largas) | 18, 25, 26 y 54 con disco real; 22, 48 y 53 con red real; 23, 27 y 44 con conexión tras confirmar | 001 |
| 003 | `003-robustez-y-control` | Reintentos automáticos de la clase temporal, tiempos de espera, duración máxima, tope de tamaño, reserva de espacio, cancelación con plazos, limpieza de huérfanos e instancia única | RN-023, RN-024, RN-026 (parte 003), RN-027 a–c, RN-028, RN-030, RN-031 c–d, RN-032 | AB-05 | RNF-09, RNF-10, RNF-13 | — | 002 (y, por transitividad, 001) |
| 004 | `004-interfaz-principal` | Vista principal minimalista, entrada individual y archivo masivo (también arrastrando), panel de validación, **diálogos de confirmación de direcciones internas** (antes de iniciar, "Permitir y reintentar" y al reintentar fallidas), avance, resumen, avisos, exportación, cierre, notificación y preferencias. **Cierra el MVP** | RN-005 (presentación), RN-017 a y d (diálogos), RN-021, RN-027 d (diálogo y acción), RN-029, RN-033, RN-034, RN-035, RN-036 (aplicación en pantalla), RN-040, RN-041, RN-043 | AB-06 (arrastrar), AB-07 (avisos), AB-18 (token canario de punta a punta) | RNF-01, RNF-04 (de punta a punta), RNF-02, RNF-03, RNF-05 | Recorrido de punta a punta de una muestra (1, 18, 20, 23, 47, 50 y 53) | 001, 002 y 003 |
| 005 | `005-apariencia-y-accesibilidad` | Temas, contraste, teclado, Narrador y escalado | RN-038, RN-042 | — | RNF-11 | — | 004 (y, por transitividad, las anteriores) |
| 006 | `006-distribucion-y-compatibilidad` | Paquete portátil que funciona sin instalar nada (tampoco Python), suma SHA-256 recomendada, notas de la versión (posible advertencia de SmartScreen) y batería de compatibilidad en Windows 10 con ESU y Windows 11. Sin instalador ni firma | RN-039 | AB-19 | RNF-14, RNF-15 | — | 004 (y 005 para la versión final) |

### Reparto del catálogo de fallos (RN-026)

| Spec | Códigos que asigna |
|---|---|
| 001 (cálculo, sin red ni disco) | F-24, F-25, F-27 y F-28 |
| 002 | F-01, F-05, F-06, F-07, F-08, F-10 a F-23, F-30, F-32 y F-99. Además aplica en el equipo real F-24, F-25, F-27 y F-28. Asigna cada código, pero **sin** reintentos automáticos |
| 003 | F-02, F-03, F-04 (tiempos de espera), F-26 (tope de tamaño), F-31 (espacio) y F-33 (duración), más el comportamiento de reintento automático de toda la clase temporal (RN-027 a–c) |

## Cobertura

- **Reglas**: las RN-001 a RN-043 quedan todas asignadas al menos a una spec.
- **Casos de abuso**: AB-01 a AB-21, todos asignados.
- **RNF**: RNF-01 a RNF-15, todos asignados.
- **Ejemplos**: los 55 se prueban en la 001. Los que dependen de red o de disco se vuelven a verificar en el equipo real en la 002.
