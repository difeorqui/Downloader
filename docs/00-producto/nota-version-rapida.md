# Nota: versión rápida de la aplicación (fuera del flujo SDD)

- **Fecha**: 2026-11-07
- **Motivo**: el usuario necesitaba empezar a probar la aplicación y pidió expresamente una versión ejecutable cuanto antes. Las reglas globales piden spec, plan y tareas aprobados antes de escribir código; ante la insistencia del usuario se procedió sin ellos y se deja constancia aquí.
- **Alcance construido** (sin spec propia): `application/` (ejecutor del lote), `infrastructure/` (red y disco) y `ui/` (ventana tkinter). Se apoya en el dominio de la spec 001, que sí siguió el flujo completo.
- **Pruebas**: `tests/integration/test_runner.py` (motor contra un servidor local) y `tests/integration/test_app_smoke.py` (ventana real).

## Qué cubre
Entrada por URL o archivo `.txt`, carpeta destino, subcarpetas por la estructura de la URL, avance por elemento y global, cancelación inmediata, tres temas (claro, oscuro, cálido) recordados entre sesiones, confirmación de direcciones internas, bloqueo de direcciones no permitidas (también en redirecciones), nombres del servidor, colisiones sin sobrescribir y archivos temporales que no quedan al fallar o cancelar.

## Qué NO cubre todavía (deuda frente a las specs 002 a 006)
- Proxy de Windows y consulta de revocación de certificados (RN-018, RN-020).
- Reintentos automáticos y esperas escalonadas (RN-027), tiempo máximo por descarga y reserva de espacio en disco (RN-023).
- Marca de origen del archivo descargado (A-3, RN-022) y exportación de no completadas.
- Instancia única, "Permitir y reintentar" para dominios que resuelven a una dirección interna (hoy fallan con un mensaje) y arrastrar archivos.
- Accesibilidad completa (Narrador, atajos, escalado) y empaquetado portátil.
- Registro de errores en archivo.

## Para regularizarlo
Redactar las specs 002 a 004 con estos puntos como criterios y comprobar que el comportamiento actual los cumple o ajustarlo.
