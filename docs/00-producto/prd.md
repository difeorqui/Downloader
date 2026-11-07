# PRD — Descargador de archivos para Windows

- **Estado**: Aprobado
- **Versión**: 0.7
- **Fecha**: 2026-11-07
- **Solicitante**: usuario de Eficacia (Colombia)
- **Autor**: analista de requerimientos
- **Documentos relacionados**:
  - `docs/01-requerimientos/glosario.md`: términos y listas normativas.
  - `docs/01-requerimientos/reglas-negocio.md`: reglas RN-001 a RN-043, ejemplos, catálogo de fallos, exportación y trazabilidad.
- **Historial**:
  - 0.1: primer borrador con preguntas.
  - 0.2: incorpora las 8 respuestas del usuario.
  - 0.3: incorpora el primer informe de `revisor-spec` y renumera las reglas.
  - 0.4: incorpora el segundo informe de `revisor-spec` (cambios menores) y nuevas decisiones del usuario:
    - proxy sin autenticación;
    - registro de errores con datos mínimos (cierra S-27);
    - versiones de Windows;
    - codificación automática de URLs;
    - rechazo de varias líneas en el campo individual;
    - duración máxima por archivo;
    - firma de código opcional;
    - detección en el motor de dominios internos con forma pública.
  - 0.5: tercera revisión de `revisor-spec`. Son redacciones puntuales en RN-001, RN-001a, RN-007, RN-008, RN-010, RN-017, RN-033, RN-035 y RN-038, con los ejemplos 49 a 55. No cambia ninguna decisión del usuario.
  - 0.6: **cambio de usuario: app Python sencilla, sin instalador.** Se distribuye como paquete portátil que ya incluye todo lo necesario, sin instalador, sin tienda de aplicaciones y sin requisitos de permisos. La firma de código pasa a ser opcional y futura. Solo cambia lo que dependía de la distribución: 4.1.1, 4.2, sección 6 (fila "Transversal"), 8.1 (preferencias), RNF-15, AB-19, S-07, S-47 y la sección 10. El resto de las reglas y las decisiones de seguridad no cambian.
  - **Supuestos que cambiaron en la 0.6, para confirmar al aprobar la próxima spec**: S-07 (instalador por usuario → paquete portátil sin instalar) y S-47 (firma deseable con decisión pendiente de TI → firma opcional y futura, con SHA-256 recomendada). Nuevo: S-62 (el usuario no instala Python ni ningún otro componente).
  - 0.7: corrección técnica, sin cambiar ninguna decisión. S-60 retira el límite de 247 caracteres para carpetas (redundante), en línea con las reglas v0.7. Sigue Aprobado.

> **Cómo leer este documento**: lo marcado **(supuesto S-NN)** no lo dijo el usuario; es un valor por defecto que se confirma o se corrige al aprobar el PRD. La sección 9 separa los supuestos **críticos** de los **de detalle**, y la sección 10 lista lo que hay que confirmar de forma explícita al aprobar.

---

## 1. Necesidad textual del usuario

> "necesito una aplicación para windows que me permita hacer descargas ya sea colocando una url o cargando un archivo masivo con todas las url que se deben descargar. al elegir la carpeta destino se deben generar las subcarpetas dónde debe quedar cada descarga, esto se generaría por medio de la estructura de la url de descarga. debe mostrar el avance en todo momento, opción para cancelar el proceso y un diseño minimalista y que el usuario pueda cambiarlo a modo oscuro o a tonos cálidos. Fácil de usar e intuitivo"

## 2. Problema

Descargar muchos archivos desde direcciones web y dejarlos **organizados** en carpetas es lento y propenso a errores si se hace a mano: hay que descargar uno por uno con el navegador, crear carpetas, renombrar y mover. El usuario necesita lanzar una descarga individual o masiva y obtener los archivos ya ordenados según el origen de cada URL, viendo en todo momento cuánto falta y pudiendo detenerla.

- **¿A quién le duele?** Al personal de oficina de Eficacia que descarga lotes de archivos, sin conocimientos técnicos avanzados. Es de uso interno **(supuesto S-01)**.
- **¿Cómo se resuelve hoy?** Con el navegador, archivo por archivo, y ordenando a mano **(supuesto S-02)**.
- **¿Qué contenido se descarga?** Documentos, imágenes y archivos comprimidos, desde sitios públicos o servidores internos **(supuesto S-03)**.

## 3. Objetivos y métricas de éxito

| Objetivo | Métrica y forma de medirla | Meta |
|---|---|---|
| Ahorrar tiempo frente al proceso manual | En el entorno de pruebas se ejecuta un lote de referencia de 500 URLs, con archivos de 1 KB a 50 MB y un 5 % de fallos simulados. Se cuentan los diálogos que exigen una acción del usuario entre "Iniciar" y el resumen final | 0 diálogos, salvo la confirmación de direcciones internas (RN-017) **(supuesto S-04)** |
| Que todo quede ordenado | Se compara la ruta obtenida con la esperada en ese lote de 500 y en los 55 ejemplos del anexo 1 de las reglas | 100 % de coincidencia en las completadas y 100 % de los resultados esperados en los ejemplos |
| Saber siempre qué pasó | En el lote de 500, cada elemento termina en Completada, Fallida (con su F-NN) o Cancelada | 100 % |
| Fácil de usar | Al menos 3 usuarios de Eficacia que no conocen la aplicación cargan un archivo de 20 URLs, eligen la carpeta, inician y abren la carpeta resultante, sin instrucciones. Se cronometra | Todos lo logran en menos de 2 minutos y sin ayuda **(supuesto S-05)** |

## 4. Alcance

### 4.1 Dentro del alcance
1. Aplicación de escritorio para **Windows 10 con actualizaciones de seguridad extendidas (ESU) y las versiones de Windows 11 con soporte vigente de Microsoft en la fecha de entrega, de 64 bits (supuesto S-06)**. **Restricción del usuario**: una aplicación de escritorio **sencilla, hecha en Python y con interfaz gráfica**. Se entrega como **paquete portátil**: se ejecuta sin instalar y sin pedir permisos de administrador, y el usuario no instala Python ni ningún otro componente (RN-039, S-07, S-62). Las herramientas concretas las decide el plan. La firma digital es opcional y futura (S-47). Solo puede haber una ventana abierta (RN-032).
2. **Descarga individual**: escribir o pegar una URL. Se corrige sola cuando le falta el esquema o tiene espacios o caracteres no ASCII (RN-001). Si el texto tiene varias líneas, se rechaza (I-08).
3. **Descarga masiva**: archivo `.txt` en UTF-8, con una URL por línea y hasta 10 000 URLs (RN-002, RN-003). Se carga con un botón o arrastrando el archivo a la ventana (RN-040).
4. **Validación previa** sin consultar la red: válidas, corregidas, duplicadas, inválidas (catálogo cerrado) y dominios internos reconocibles por su nombre (RN-004 a RN-006).
5. **Carpeta destino** obligatoria y validada; se recuerda la última (RN-007).
6. **Subcarpetas automáticas**: dominio + ruta de la URL original, con saneamiento seguro para Windows (RN-008 a RN-016).
7. **Avance visible en todo momento**, por elemento y por lote (RN-033).
8. **Descargas simultáneas**: 3 por defecto, configurable de 1 a 8 (RN-025).
9. **Reintentos** automáticos, hasta 3, ante fallos temporales; botón "Reintentar fallidas" (RN-026, RN-027).
10. **Límites por archivo**: tamaño máximo, duración máxima, velocidad mínima y reserva de espacio en disco (RN-023, RN-024, RN-028).
11. **Cancelación** del lote o de un elemento, con plazos máximos (RN-030).
12. **Resumen final** con "Abrir carpeta", "Reintentar fallidas" y "Exportar no completadas" (RN-034, RN-035). Notificación de Windows al terminar si la ventana no está en primer plano (RN-041).
13. **Seguridad de red**: proxy de Windows, certificados del almacén de Windows sin excepciones manuales, confirmación de direcciones internas por dominio y bloqueo de direcciones prohibidas (RN-017 a RN-020).
14. **Protección de lo descargado**: marca de origen de Windows y avisos A-1 a A-3 (RN-021, RN-022).
15. **Diseño minimalista**: en su estado inicial (al abrir, sin lote validado), la vista principal tiene como máximo 6 controles. No cuentan el panel de resumen de validación (donde está "Exportar no completadas" antes de iniciar), la lista de avance ni el resumen final. Temas claro, oscuro, cálido y "según Windows", que es el predeterminado (RN-033 e, RN-038).
16. **Accesibilidad**: uso completo con teclado, Narrador y escalado de pantalla (RN-042).
17. Interfaz solo en español **(supuesto S-12)**.

### 4.2 Fuera del alcance (versión 1)
- Reanudar descargas o recordar el lote al cerrar la aplicación (RN-029).
- Pausar descargas; solo se pueden cancelar **(supuesto S-14)**.
- Cualquier autenticación: usuario y contraseña, credenciales de Windows, cookies, cabeceras o proxy con autenticación (RN-019).
- Excepciones manuales a certificados no válidos (RN-018).
- Protocolos distintos de `http` y `https`.
- Abrir, ejecutar o mostrar en vista previa los archivos descargados (RN-021).
- Descargar páginas web completas o contenido de plataformas de streaming.
- Archivo masivo en `.csv`, en UTF-16 u otros formatos.
- Programar descargas.
- Historial persistente de lotes **(supuesto S-15)**; la única excepción es el registro de carpetas de RN-031.
- Telemetría y actualizaciones automáticas **(supuesto S-25)**.
- Instalador, paquetes de instalación de Windows, publicación en la Microsoft Store y firma de código en la versión 1 (cambio de usuario v0.6).
- Sistemas operativos distintos de Windows, y Windows de 32 bits.

## 5. Actores

| Actor | Descripción |
|---|---|
| Usuario | Persona que usa la aplicación en su equipo Windows. Hay un único tipo de usuario, sin roles ni cuentas **(supuesto S-16)**. |
| Servidor remoto | Origen de los archivos. |
| Proxy corporativo | Intermediario de salida a Internet, si existe. Según el usuario, en Eficacia no hay proxy o no pide autenticación (S-42 resuelto). |

## 6. Épicas

| ID | Épica | Descripción breve | Reglas |
|---|---|---|---|
| EP-01 | Entrada de URLs | URL individual o archivo masivo; corrección y codificación automáticas; validación previa y resumen; arrastrar y soltar. | RN-001 a RN-006, RN-017 a, RN-019 d, RN-040 |
| EP-02 | Organización en carpetas | Carpeta destino y cálculo seguro de la ruta. | RN-007 a RN-016 |
| EP-03 | Motor de descargas | Concurrencia, reintentos, límites, seguridad de red, temporales, espacio y marca de origen. | RN-001a, RN-017 a RN-020, RN-022 a RN-028, RN-031 |
| EP-04 | Avance y control | Progreso, cancelación, cierre, resumen, avisos, exportación y notificación. | RN-021, RN-029, RN-030, RN-033 a RN-036, RN-041 |
| EP-05 | Apariencia y usabilidad | Diseño minimalista, temas, accesibilidad y preferencias. | RN-033 e, RN-038, RN-042, RN-043 |
| Transversal | Privacidad, registro, instancia única y distribución | Enmascaramiento, registro mínimo, una sola ventana, paquete portátil. | RN-032, RN-036, RN-037, RN-039 |

La trazabilidad completa está en el anexo 4 de `reglas-negocio.md`.

## 7. Requisitos no funcionales

**Condiciones comunes a todas las mediciones (supuesto S-17):**
- **Equipo de referencia**: 4 núcleos, 8 GB de RAM, SSD y Windows 11 de 64 bits, sin otras aplicaciones pesadas abiertas.
- **Entorno de pruebas**: servidor local de pruebas, **nunca productivo**, que sirve archivos de tamaño, velocidad y respuestas controladas. Ojo con dos detalles:
  - Ese servidor está en `127.0.0.1`, que es una dirección interna, así que cada prueba debe **confirmarla explícitamente** según RN-017. Eso sirve, además, como prueba de esa regla.
  - Para las pruebas HTTPS hace falta un certificado de pruebas instalado en el almacén de Windows **solo del equipo de pruebas**, porque RN-018 no admite excepciones.
- **Herramientas**: pruebas automatizadas de extremo a extremo de la interfaz, con marca de tiempo de cada evento, y monitor de recursos del sistema.
- **Percentiles**: se calculan sobre todas las muestras de la ejecución.

Las cifras son el **supuesto S-20**, salvo donde se indica otra fuente.

| ID | Requisito | Método y conjunto de datos | Criterio de paso |
|---|---|---|---|
| RNF-01 | Capacidad del lote | Lote sintético de 10 000 URLs únicas de 10 KB, con 8 descargas simultáneas | Los 10 000 elementos llegan a un estado final; 0 cierres inesperados |
| RNF-02 | Respuesta de la interfaz | Durante RNF-01, un guion ejecuta 100 acciones (cancelar un elemento, cambiar de tema, desplazarse, abrir ajustes) y mide el tiempo hasta la respuesta visible | p95 < 200 ms; máximo < 500 ms |
| RNF-03 | Frecuencia del avance | 5 minutos con 8 descargas activas de 500 MB a velocidad limitada; se registra cada actualización por elemento y del total | p99 del intervalo ≤ 1 s; ningún intervalo > 1,5 s |
| RNF-04 | Validación del archivo masivo | 20 cargas de un archivo de 10 000 URLs (≈ 1 MB) con un 5 % de inválidas, duplicadas, corregidas y codificadas | p95 < 3 s hasta que se muestra el resumen |
| RNF-05 | Arranque | 20 arranques en caliente y 5 tras reiniciar el equipo, cada uno con limpieza de huérfanos pendiente (10 carpetas registradas) y preferencias válidas | p95 < 3 s en caliente y < 5 s tras reiniciar, hasta que la ventana acepta acciones |
| RNF-06 | Aprovechamiento de la red | Servidor limitado a 50 MB/s en total; 3 descargas simultáneas de 500 MB | Velocidad media ≥ 45 MB/s |
| RNF-07 | Memoria | Durante RNF-01 se mide la **memoria privada pico** de todos los procesos de la aplicación | < 300 MB |
| RNF-08 | Procesador | 3 descargas limitadas a 5 MB/s cada una, durante 10 minutos | Uso medio < 15 % del procesador total |
| RNF-09 | Plazo de cancelación (RN-030) | 50 cancelaciones de un elemento y 20 del lote completo, con 8 descargas activas | Elemento: deja de recibir datos en ≤ 2 s y el temporal se borra en ≤ 5 s. Lote: todo detenido y los temporales borrados en ≤ 5 s. En el 100 % de los casos **(supuesto S-44)** |
| RNF-10 | Tiempos de espera y duración (RN-027, RN-028) | El servidor simula tres casos: no acepta la conexión, deja de enviar datos y envía a 0,5 KB/s. La duración máxima se configura en su mínimo (10 min) con un archivo que tarda más | **Primer intento** (tolerancia ±1 s): F-02 a los 15 s, F-03 a los 30 s y F-04 a los 60 s. **Estado final** tras 3 reintentos con esperas de 2/4/8 s (tolerancia ±4 s): F-02 a los 74 s, F-03 a los 134 s y F-04 a los 254 s. **Duración**: F-33 a los 10 min ±2 s, sin reintento automático **(supuestos S-21, S-33 y S-56)** |
| RNF-11 | Accesibilidad (RN-038, RN-042) | (1) Se mide el contraste de cada par de colores en los 4 temas y en los estados normal, al pasar el ratón, con foco y deshabilitado. (2) Se recorren solo con el teclado los 5 flujos principales: URL individual, archivo masivo, cancelar, exportar y cambiar tema. (3) Se recorren los mismos flujos con el Narrador. (4) Se revisan las pantallas con escalado de 100 %, 125 % y 150 % | (1) Texto ≥ 4.5:1, controles y foco ≥ 3:1, texto deshabilitado ≥ 3:1. (2) Los 5 flujos se completan sin ratón y el foco es siempre visible. (3) El Narrador anuncia el nombre y el estado de cada control y los cambios de estado del lote. (4) Sin cortes ni superposiciones **(supuesto S-22)** |
| RNF-12 | Rutas largas (RN-016) | 20 URLs que generan rutas de 230 a 400 caracteres y nombres de hasta 300, en un equipo con rutas largas habilitadas y en otro sin ellas | Cada elemento se completa o falla con F-25 o F-28 según los límites de RN-016; ninguna pérdida silenciosa **(supuestos S-23 y S-60)** |
| RNF-13 | Fiabilidad ante cierres (RN-031) | 20 veces: cierre forzado con 8 descargas activas y nuevo arranque | 0 temporales en las carpetas registradas y 0 archivos con nombre final incompletos (se comparan tamaño y suma con el servidor) **(supuesto S-24)** |
| RNF-14 | Compatibilidad | Batería completa de regresión, en una cuenta de usuario estándar, en la versión de Windows 10 cubierta por ESU y en cada versión de Windows 11 con soporte vigente en la fecha de entrega, todas de 64 bits | 100 % de las pruebas en verde en todas las versiones **(supuesto S-06)** |
| RNF-15 | Distribución (RN-039) | Se copia el paquete portátil a una carpeta del usuario en un equipo **sin Python instalado**, con una cuenta estándar, y se ejecuta; se verifica la suma SHA-256 publicada | Arranca y funciona sin instalar nada ni pedir permisos de administrador; la suma coincide; las notas de la versión explican la posible advertencia de Windows SmartScreen al ejecutar un programa sin firma **(supuestos S-07, S-47 y S-62)** |

## 8. Seguridad y privacidad

### 8.1 Clasificación de datos

| Dato | Clasificación | Dónde se guarda | Retención |
|---|---|---|---|
| URLs del lote | **Confidencial potencial**: pueden contener tokens en los parámetros, el fragmento o la ruta | Solo en memoria. Lo que se ve en pantalla va enmascarado (RN-036) | Se descartan al cerrar o al empezar otro lote |
| Archivo masivo | Del usuario; la aplicación solo lo lee | Donde lo tenga el usuario | No se copia |
| Archivos descargados | Según su contenido; pueden contener datos personales | Carpeta destino | Los gestiona el usuario |
| Exportación de no completadas | **Confidencial**: URLs completas sin enmascarar (excepción a RN-036 decidida por el usuario) | Donde elija el usuario, tras aceptar un aviso (RN-035) | La gestiona el usuario |
| Registro de errores | Interno, con **datos mínimos** (decisión del usuario): fecha y hora, código, esquema + dominio + puerto, motivo y versión. **Sin rutas, sin nombres de archivo, sin nombre de usuario, sin parámetros** | Carpeta de datos de la aplicación del usuario de Windows | Máx. 10 MB y 30 días (RN-037) |
| Registro de carpetas usadas | Interno; contiene **rutas de carpetas** (que pueden incluir nombres derivados de las URLs), necesarias para limpiar temporales huérfanos | Carpeta de datos de la aplicación | Se vacía tras cada limpieza, al terminar cada lote o en el siguiente arranque (RN-031) |
| Preferencias | Interno: tema, descargas simultáneas, tope de tamaño, duración máxima, última carpeta destino | Carpeta de datos de la aplicación del usuario de Windows (no la carpeta del paquete portátil) | Hasta que el usuario borre esa carpeta; borrar el paquete no la elimina |

- La aplicación **no envía datos a terceros**: no hay telemetría ni actualizaciones automáticas **(supuesto S-25)**. Solo se comunica por red para las descargas, directas o por el proxy de Windows. Con proxy, la comprobación de direcciones consulta al servidor de nombres de la red los dominios del lote (RN-020, riesgo residual).
- No maneja credenciales (RN-019).
- **Ley 1581 de 2012 (protección de datos personales). Decisión del usuario: minimizar datos.** La aplicación no recolecta datos personales del usuario. El registro de errores no guarda rutas, nombres de archivo, nombre de usuario ni URLs completas. El registro de carpetas usadas guarda rutas solo de forma transitoria, para limpiar temporales. La exportación contiene URLs completas, solo cuando el usuario la pide y después de un aviso. Los archivos descargados quedan en la carpeta que elija el usuario, y su tratamiento es responsabilidad de Eficacia según su política interna. La aplicación no añade cifrado propio.
  *Nota*: es **recomendable**, pero **no bloquea** la aprobación, validar este tratamiento con el responsable de protección de datos de Eficacia, sobre todo si se descargarán archivos con datos personales de clientes.

### 8.2 Permisos: qué puede hacer la aplicación y sobre qué

Hay un único usuario local (S-16). La aplicación:
- **Escribe** solo en tres lugares: (1) dentro de la carpeta destino validada (RN-007, RN-013); (2) en su carpeta de datos (preferencias, registro de errores, registro de carpetas); (3) en el archivo de exportación, en la ubicación que el usuario elige en el diálogo de Windows después de aceptar el aviso (RN-035). Esta última es la única escritura fuera de la carpeta destino y nunca ocurre de forma automática.
- **Borra** solo sus propios temporales (patrón exacto de RN-031), en las carpetas registradas, y las carpetas vacías que ella misma creó en el lote.
- **Lee** el archivo masivo que elige o suelta el usuario.
- **Abre** únicamente el Explorador de Windows en la carpeta destino ("Abrir carpeta"). Nunca abre ni ejecuta archivos descargados (RN-021).
- **Se conecta** solo a las URLs del lote y a sus redirecciones, bajo RN-017 a RN-020.

### 8.3 Casos de abuso

| ID | Caso de abuso | Comportamiento esperado | Reglas |
|---|---|---|---|
| AB-01 | Salto de directorio: `..`, `%2e%2e`, `\`, `%5c`, `%2f` o rutas absolutas en la URL o en el nombre sugerido | Nada se crea fuera de la carpeta destino (ejemplos 4 a 7, 15, 37, 39 y 51 del anexo 1) | RN-001a, RN-008, RN-010, RN-011, RN-013 |
| AB-02 | URL que apunta a la red interna o al propio equipo, directamente, por redirección o con un nombre de apariencia pública | Confirmación por dominio; sin ella, F-30. En redirecciones se autoriza el dominio de destino (ejemplos 23, 27, 44, 48 y 53) | RN-001a, RN-005, RN-017, RN-020, RN-027 |
| AB-03 | Nombres reservados (también en el dominio o con extensiones múltiples), caracteres inválidos, puntos o espacios finales | Saneamiento predecible (ejemplos 8 a 10, 16 y 31 a 34) | RN-014, RN-015 |
| AB-04 | Rutas o nombres demasiado largos | F-25 o F-28; nunca se pierden en silencio | RN-016 |
| AB-05 | Archivo enorme, servidor que envía sin fin, muy lento o durante horas | F-26, F-31, F-04 o F-33 | RN-023, RN-024, RN-028 |
| AB-06 | Archivo masivo enorme, binario, en UTF-16, de otra extensión o con más de 10 000 URLs | Rechazo completo con mensaje específico, sin congelar la aplicación | RN-003, RN-040 |
| AB-07 | Ejecutables o documentos con macros | Se descargan con aviso A-1 y marca de origen; nunca se abren | RN-021, RN-022, RN-034 |
| AB-08 | Esquemas no permitidos (`file:`, `javascript:`, `data:`, UNC, `C:\`), también por redirección | Inválidas (I-01, I-02) o F-22 | RN-001, RN-004, RN-018 f |
| AB-09 | Certificado no válido, TLS antiguo o redirección de HTTPS a HTTP | F-18, F-19 o F-20. Solo existe la excepción acotada de revocación no consultable | RN-018 |
| AB-10 | Credenciales embebidas en la URL | Inválida (I-05), detectada en la autoridad hasta `/`, `?` o `#`; nunca se muestran completas | RN-001a, RN-004, RN-019, RN-036 |
| AB-11 | Bucle o cadena larga de redirecciones | F-21 tras 10 redirecciones | RN-018 g |
| AB-12 | Nombre sugerido malicioso (rutas, reservados, doble extensión, caracteres invisibles) | Solo se usa como nombre, saneado; el aviso se basa en la última extensión real | RN-010, RN-014, RN-015, RN-021 |
| AB-13 | Cambio de dirección entre la comprobación y la conexión | Conexión a la dirección comprobada; por proxy, riesgo residual aceptado (S-38) | RN-017 b, RN-020 |
| AB-14 | Notación alternativa de IP (`2130706433`, `0177.0.0.1`, `0x7f.1`, `127.1`, `[::ffff:127.0.0.1]`, `[2002:7f00:1::]`) | Se detecta igual que la forma normal (ejemplos 27 y 45) | RN-001a, RN-004, RN-017 a |
| AB-15 | Carpeta destino del sistema o de la aplicación, también si se llega a ella mediante un enlace o una unión elegida como destino; o unión de carpetas dentro del destino | Carpeta rechazada al comprobar su ruta real (RN-007 c, ejemplo 54) o F-24 (ejemplo 26) | RN-007, RN-013 |
| AB-16 | Caracteres invisibles o de inversión de texto para disfrazar la extensión | Se eliminan (ejemplo 17) | RN-014, RN-021 |
| AB-17 | Sitio o proxy que pide credenciales para capturar las de Windows | No se envían; F-13 o F-14 | RN-019 |
| AB-18 | Filtración de tokens | Enmascaramiento de parámetros y fragmento; registro sin URLs completas; aviso antes de exportar. **Prueba del token canario**: un lote con `https://sitio.com/a.pdf?token=CANARIO-<valor aleatorio>#access_token=CANARIO-<valor aleatorio>` se lleva por éxito, fallo, cancelación, error inesperado y cierre. El canario **no debe aparecer** en la pantalla, el registro de errores, los mensajes de error o de excepción, la notificación, el título de la ventana, el registro de carpetas, las preferencias ni en ningún informe de fallo que genere la aplicación. Solo puede aparecer en la exportación. Riesgo residual: los tokens dentro de la ruta (RN-036) | RN-035, RN-036, RN-037, RN-041 |
| AB-19 | Paquete portátil alterado o suplantado | Suma SHA-256 publicada por un canal interno de confianza (recomendada); firma digital en el futuro, si se adopta | RN-039 |
| AB-20 | Diferencias de interpretación de la URL entre programas (`https://sitio.com\@127.0.0.1/`, `https://sitio.com#@127.0.0.1/`, falsos esquemas) | Analizador único; las autoridades ambiguas son I-03; las credenciales se buscan solo en la autoridad hasta `/`, `?` o `#` (ejemplos 29, 35, 36, 49, 50 y 52) | RN-001, RN-001a, RN-004, RN-008 |
| AB-21 | Proxy suplantado mediante la detección automática en la red local | Las descargas `https` siguen protegidas por la validación de certificados. Las `http` podrían alterarse: riesgo residual aceptado (S-38) | RN-018, RN-020 |

## 9. Supuestos (a validar al aprobar el PRD)

### 9.1 Supuestos críticos (cambian el alcance, la seguridad o el esfuerzo)

| ID | Supuesto | Regla |
|---|---|---|
| S-18 | Archivo masivo de máximo 5 MB; URL de máximo 2 048 caracteres. **Justificación**: una URL típica tiene de 100 a 200 caracteres, así que 10 000 URLs ocupan entre 1 y 2 MB. Con 5 MB caben 10 000 URLs de hasta unos 500 caracteres de media. Un lote de 10 000 URLs muy largas, cerca de las 2 048, puede superar los 5 MB y se rechazaría; se acepta ese límite para proteger la memoria y el tiempo de validación. | RN-003 |
| S-19 | Tope por archivo de 10 GB por defecto, configurable entre 1 y 500 GB. | RN-024 |
| S-21 | 30 s sin recibir datos = fallo temporal. | RN-028 |
| S-23 | Se admiten rutas largas si Windows lo permite; si no, F-25. Los nombres no se acortan. | RN-016 |
| S-24 | Limpieza de temporales huérfanos con el registro de carpetas usadas. | RN-031 |
| S-30 | TLS mínimo 1.2. **Excepción acotada**: si no se puede consultar el estado de revocación, el certificado se acepta y se anota en el registro (un certificado revocado se rechaza siempre). | RN-018 d |
| S-31 | Reserva mínima de espacio: el mayor valor entre 500 MB y el 2 % de la unidad. | RN-023 |
| S-33 | Conexión: 15 s. Velocidad mínima: 1 KB/s durante 60 s. | RN-028 |
| S-37 | Listas de direcciones internas y bloqueadas; la bloqueada prevalece. Los nombres sin punto y los terminados en `.local`, `.corp`, etc. son internos. Un rechazo no confirmado es Fallida con F-30. | RN-017, glosario 2.1 y 2.2 |
| S-38 | Riesgos residuales del proxy: no se puede fijar la dirección, la resolución local revela los dominios al servidor de nombres de la red y la detección automática de proxy puede ser suplantada. | RN-020 |
| S-60 | Límites de longitud: 255 caracteres por nombre (F-28). Ruta: 259 caracteres sin rutas largas y 32 000 con ellas, midiendo la mayor entre la ruta final y la del temporal. *(v0.7: se retiró el límite de 247 para carpetas, que era redundante.)* | RN-016 |

### 9.2 Supuestos de detalle

| ID | Supuesto |
|---|---|
| S-01 | Usuarios: personal de oficina de Eficacia, no técnico; uso interno. |
| S-02 | Hoy se descarga a mano con el navegador. |
| S-03 | Contenido habitual: documentos, imágenes y archivos comprimidos. |
| S-04 | Métrica de ahorro con el lote de 500 URLs. |
| S-05 | Métrica de facilidad: 3 usuarios, menos de 2 minutos. |
| S-06 | Windows 10 con ESU y las versiones de Windows 11 con soporte vigente en la fecha de entrega, de 64 bits. |
| S-07 | *(Cambiado en la 0.6)* Paquete portátil, sin instalador: puede ser una carpeta o un ejecutable único. Se ejecuta sin permisos de administrador desde una carpeta del usuario. Los datos de la aplicación se guardan en la carpeta de datos del usuario de Windows, no junto al paquete. |
| S-47 | *(Cambiado en la 0.6; antes era crítico)* La firma de código es opcional y futura; la versión 1 se distribuye sin firma. Se recomienda publicar la suma SHA-256 del paquete. |
| S-62 | *(Nuevo en la 0.6)* El paquete incluye todo lo necesario para ejecutarse; el usuario no instala Python ni ningún otro componente. |
| S-08 | Se recuerda la última carpeta destino. |
| S-09 | Datos y cálculos del avance (RN-033 a a d). |
| S-11 | Arrastrar y soltar (RN-040). |
| S-12 | Interfaz solo en español. |
| S-13 | Notificación al terminar, sin URLs ni rutas (RN-041). |
| S-14 | No hay pausa. |
| S-15 | Sin historial persistente; la única excepción es el registro de carpetas (RN-031). |
| S-16 | Un único tipo de usuario. |
| S-17 | Equipo y entorno de referencia para los RNF. |
| S-20 | Cifras de los RNF. |
| S-22 | Accesibilidad: contrastes, teclado, Narrador y escalado (RN-038, RN-042). |
| S-25 | Sin telemetría ni actualizaciones automáticas. |
| S-26 | Registro de errores local. |
| S-28 | `docs/constitucion.md` la redacta el arquitecto al inicio de la planeación; hasta entonces, la referencia son este PRD y las reglas. |
| S-29 | Paleta del tema cálido (RN-038). |
| S-34 | Instancia única. |
| S-35 | Registro de carpetas usadas, escrito antes del primer temporal, y patrón exacto del temporal. |
| S-36 | Interpretación de la entrada: orden de RN-001, forma de contar, duplicados, decodificación única, catálogo de invalidez. |
| S-39 | Marca de origen de la zona Internet en todo lo descargado, sin la URL. |
| S-40 | Lista cerrada de extensiones peligrosas (glosario 2.3). |
| S-41 | Lista de caracteres invisibles (glosario 2.4). |
| S-43 | Catálogo de fallos y sus clases; esperas de 2/4/8 s; espera indicada por el servidor de hasta 60 s, conservando el código original. |
| S-44 | Plazos de cancelación: 2 s y 5 s. Solo se confirma la cancelación del lote. |
| S-45 | Criterios de validez de la carpeta destino. |
| S-46 | Retención del registro de errores: 5 archivos de 2 MB, 30 días. |
| S-48 | Se añade la extensión por tipo de contenido cuando el nombre de la URL no la tiene. |
| S-49 | Los dominios se guardan en forma ASCII. |
| S-50 | Se eliminan las carpetas vacías que la aplicación creó. |
| S-51 | "Permitir y reintentar" autoriza el dominio rechazado (en redirecciones, el de destino) para todos los elementos del lote que lleguen a él. |
| S-52 | Formato, nombre y disponibilidad de la exportación. |
| S-53 | La barra invertida literal en la ruta es separador; `%5c` es un carácter que se sanea. |
| S-54 | Caracteres que se codifican automáticamente: espacios, caracteres no ASCII, comillas dobles, `<`, `>`, acento grave, `{`, `}`, `\|` y `^`. En los parámetros y el fragmento, también `\`; en la ruta, `\` se convierte en `/`. El resumen desglosa las corregidas. I-09 para varias URLs en una línea, detectado antes de codificar. |
| S-55 | Criterio de diseño minimalista: máximo 6 controles en la vista principal en su estado inicial; los paneles de validación, avance y resumen no cuentan; las opciones avanzadas van en ajustes. |
| S-56 | Duración máxima configurable entre 10 min y 24 h. |
| S-57 | Avisos A-1 a A-3, incluido A-2 para páginas web recibidas en lugar de archivos. |
| S-58 | Preferencias dañadas → valores por defecto y aviso único. |
| S-59 | En un conflicto archivo/carpeta dentro del lote, prevalece la carpeta y el archivo recibe sufijo. |
| S-61 | Se acepta CR suelto como fin de línea; mensajes específicos para `.csv` y otras extensiones. |

*Retirados*: S-10 (decidido por el usuario, RN-035) y S-32 (fusionado en S-19). *Resueltos por el usuario*: S-27 (Ley 1581, minimización de datos) y S-42 (sin proxy con autenticación).

## 10. Confirmaciones explícitas al aprobar el PRD

No quedan preguntas abiertas. Al aprobar, el usuario confirma de forma explícita:
1. **S-42 (resuelto)**: en Eficacia no hay proxy o no pide autenticación. Por eso la versión 1 no envía credenciales de Windows ni cookies.
2. **S-47 (cambiado en la 0.6)**: la versión 1 se distribuye como paquete portátil sin firma. La firma es opcional y futura, y la suma SHA-256 es recomendada.
3. **S-30 (excepción acotada)**: un certificado cuyo estado de revocación no se puede consultar se acepta y se anota en el registro.
4. **Los demás supuestos críticos** de la sección 9.1.
5. **S-27 (resuelto)**: minimización de datos. Es recomendable, pero no bloquea, validarla con el responsable de protección de datos de Eficacia.
