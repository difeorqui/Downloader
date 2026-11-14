# Glosario

- **Estado**: Listo para revisión
- **Fecha**: 2026-11-07
- **Versión**: 0.6 (cambio de usuario: app Python sencilla, sin instalador; se actualizan los términos de distribución). Las listas normativas de la sección 2 son la única fuente para todas las reglas.

## 1. Términos

| Término | Definición |
|---|---|
| URL | Dirección de un archivo (p. ej. `https://sitio.com/docs/2024/informe.pdf?v=2`). Sus partes son: **esquema** (`https`), **dominio** (`sitio.com`), **puerto** (opcional, `:8080`), **ruta** (`/docs/2024/informe.pdf`), **parámetros** (después de `?`) y **fragmento** (después de `#`). |
| Esquema | Texto al inicio de la URL, antes de `://`, que cumple el patrón `[A-Za-z][A-Za-z0-9+.-]*` (RN-001). Solo se aceptan `http` y `https`. |
| Autoridad cruda | Texto entre `://` y la primera `/`. Se usa solo para rechazar URLs ambiguas (RN-001a a). |
| Autoridad | Texto entre `://` y el primero de `/`, `?` o `#`. De ella salen el dominio y el puerto, y sobre ella se detectan las credenciales embebidas (RN-001a b). |
| Analizador único | Criterio único con el que se interpreta cada URL una sola vez; su resultado se usa para validar, calcular la ruta, comprobar direcciones y conectar (RN-001a). |
| URL original | La URL tal como está en el lote, ya corregida. De ella salen siempre las carpetas (RN-008). |
| URL corregida | URL a la que la aplicación le antepuso `https://` o le codificó caracteres automáticamente (RN-001). Se cuenta en el resumen. |
| Codificación en porcentaje | Forma de escribir en una URL caracteres no permitidos, como `%20` para el espacio. La aplicación la aplica sola (RN-001) y la deshace una sola vez para los nombres en disco (RN-011). |
| Puerto estándar | 80 para `http` y 443 para `https`. |
| Descarga individual | Una sola URL escrita o pegada en el campo; se procesa como un lote de un elemento. Si el campo tiene más de una línea, se rechaza (I-08). |
| Archivo masivo | Archivo `.txt` en UTF-8 con una URL por línea (RN-002, RN-003). Se puede cargar con un botón o arrastrándolo a la ventana (RN-040). |
| Línea con contenido | Línea del archivo masivo que no está vacía ni es un comentario (`#`). Es lo que cuenta para el límite de 10 000. |
| Lote | Conjunto de URLs que se procesan en una misma ejecución. |
| Elemento del lote | Cada URL válida y única del lote, con su estado, avance y motivo. |
| Validación previa | Revisión del lote antes de iniciar, sin consultar la red (RN-005). |
| Motivo de invalidez | Código I-NN del catálogo cerrado de RN-004. |
| Carpeta destino | Carpeta elegida por el usuario, que debe cumplir RN-007. Nada puede quedar fuera de ella (RN-013). |
| Subcarpeta generada | Carpeta creada dentro de la carpeta destino a partir del dominio y los segmentos de la URL original (RN-008). |
| Ruta resultante | Carpeta destino + subcarpetas generadas + nombre de archivo. |
| Nombre sugerido por el servidor | Nombre que el servidor propone para el archivo. Si lo envía en dos formas, prevalece la internacional en UTF-8. Se usa solo como nombre (RN-010). |
| Tipo de contenido | Clase de archivo que informa el servidor; se traduce a extensión solo con la tabla cerrada de RN-010. |
| Saneamiento | Transformación de segmentos, dominio y nombres en nombres válidos y seguros para Windows (RN-014, RN-015). |
| Nombres reservados de Windows | Lista cerrada de la sección 2.5. Se evalúan sobre el texto anterior al primer punto (RN-015). |
| Enlace o unión de carpetas (punto de reanálisis) | Carpeta de Windows que apunta a otra ubicación. Si ya existe dentro del destino y forma parte de la ruta, el elemento falla con F-24 (RN-013). |
| Sufijo de duplicado | ` (1)`, ` (2)`... antes de la última extensión (RN-012). |
| Archivo temporal | Archivo de una descarga en curso, con el patrón exacto `~descargador-<32 caracteres hexadecimales>.parcial` (RN-031). |
| Archivo parcial | Temporal de una descarga no terminada; se borra siempre. |
| Temporal huérfano | Temporal que quedó en disco tras un cierre inesperado; se limpia según RN-031. |
| Registro de carpetas usadas | Lista interna con solo las rutas de las carpetas donde se crearon temporales; se vacía tras la limpieza (RN-031). |
| Instancia única | Una sola ventana de la aplicación por usuario (RN-032). |
| Marca de origen (Mark of the Web) | Marca de Windows que indica que un archivo viene de Internet; hace que Windows y Office adviertan al abrirlo (RN-022). |
| Aviso | Ícono y texto en la fila de un elemento, con conteo y filtro en el resumen. No impide la descarga. Tipos: A-1 (ejecutable o con macros), A-2 (se recibió una página web), A-3 (sin marca de origen) (RN-021). |
| Extensión peligrosa | Extensión de la lista cerrada 2.3; genera el aviso A-1. |
| Abrir carpeta | Abre el Explorador de Windows en la carpeta destino. Es la única acción sobre lo descargado; la aplicación nunca abre ni ejecuta archivos (RN-021). |
| Avance | Progreso por elemento y por lote (RN-033). |
| Estado de un elemento | **Pendiente**, **Descargando** (incluye "reintentando N de 3"), **Completada**, **Fallida** (con F-NN) o **Cancelada**. Los tres últimos son estados finales. |
| Clase de fallo | **Temporal**, **Permanente** o **Recuperable** (RN-026; catálogo en el anexo 2 de las reglas). |
| Reintento | Nuevo intento automático tras un fallo temporal; máximo 3 (RN-027). |
| Reintentar fallidas | Acción manual que vuelve a poner en cola todos los Fallidos del lote (RN-027). |
| Permitir y reintentar | Acción sobre un elemento con F-30 que autoriza el **dominio rechazado** para todos los elementos del lote que lleguen a él. Si el F-30 vino de una redirección, se autoriza el dominio de destino de la redirección, no el de la URL original (RN-017 d). |
| Duración máxima por archivo | Tiempo máximo de descarga por intento: 2 h por defecto, configurable; al vencer, F-33 (RN-028 d). |
| Reanudación | Continuar una descarga desde donde quedó. **Fuera del alcance.** |
| Concurrencia | Descargas simultáneas: de 1 a 8, por defecto 3 (RN-025). |
| Cancelar | Detener el lote o un elemento (RN-030). |
| Exportación de no completadas | `.txt` con las URLs completas, sin enmascarar, de los elementos no completados; se puede recargar (RN-035). |
| Enmascaramiento | Ocultar credenciales, valores de parámetros y fragmento de una URL visible (RN-036). |
| Token canario | Valor único y reconocible que se coloca en una URL de prueba para comprobar que no aparece donde no debe (AB-18). |
| Registro de errores | Archivo local con datos mínimos: código, esquema + dominio + puerto, motivo, fecha y versión; sin rutas ni usuario (RN-037). |
| Preferencias | Ajustes guardados del usuario; si están dañados, se usan los valores por defecto (RN-043). |
| Reserva mínima de espacio | Espacio libre que siempre debe quedar: el mayor valor entre 500 MB y el 2 % de la unidad (RN-023). |
| Tope de tamaño por archivo | 10 GB por defecto, configurable (RN-024). |
| Proxy | Intermediario de salida a Internet. Se usa la configuración de Windows (RN-020). |
| Detección automática de proxy | Mecanismo de Windows que busca la configuración del proxy en la red local. Puede ser suplantado (riesgo residual, RN-020). |
| Almacén de certificados de Windows | Autoridades de confianza del equipo, incluidas las corporativas. Es la única fuente de confianza para HTTPS (RN-018). |
| Comprobación léxica | Comparar el dominio escrito, sin punto final, con las listas de la sección 2, sin usar la red (RN-017 a). |
| Comprobación por resolución | Traducir el nombre a sus direcciones reales, compararlas con las listas y conectar a la dirección comprobada (RN-017 b). |
| Dirección interna | Dirección de la lista 2.1; requiere confirmación. |
| Dirección bloqueada | Dirección de la lista 2.2; nunca se permite. **Prevalece sobre la interna** si una dirección está en las dos listas. |
| Redirección | Respuesta que envía la descarga a otra URL; cada salto pasa por las mismas comprobaciones. |
| Tema visual | Claro, oscuro, cálido o "según Windows", que es el predeterminado (RN-038). |
| Narrador | Lector de pantalla incluido en Windows (RN-042). |
| Paquete portátil | Forma de entrega de la aplicación: una carpeta o un ejecutable único que funciona sin instalar nada y sin permisos de administrador (RN-039). |
| Firma de código | Firma digital de Windows de los ejecutables. Es opcional y futura; la versión 1 no la lleva (RN-039). |
| SmartScreen | Protección de Windows que puede advertir al ejecutar por primera vez un programa sin firma o poco conocido (RN-039). |
| Suma de verificación | Huella SHA-256 que se recomienda publicar junto al paquete para comprobar que no fue alterado (RN-039). |
| Windows 10 con ESU | Windows 10 con el programa de actualizaciones de seguridad extendidas de Microsoft (S-06). |

## 2. Listas normativas

**Normalización previa**: antes de comparar, se quita el punto final del dominio (`localhost.` → `localhost`, `intranet.` → `intranet`) y se pasa a minúsculas. **Prevalencia**: si una dirección o rango aparece en 2.1 y en 2.2, se trata como **bloqueada**.

### 2.1 Direcciones internas (solo con confirmación, RN-017)

Por nombre (comprobación léxica):
- `localhost` y cualquier nombre que termine en `.localhost`.
- Nombres sin punto, de una sola etiqueta (p. ej. `intranet`, `servidor01`).
- Nombres que terminan en `.local`, `.internal`, `.intranet`, `.lan`, `.corp` o `.home.arpa`.

Por dirección, en cualquier notación (decimal entera, octal, hexadecimal, abreviada, IPv6 con IPv4 incrustada):
- IPv4: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `100.64.0.0/10`.
- IPv6: `::1` y `fc00::/7`, excepto las direcciones de la lista 2.2, que prevalecen (p. ej. `fd00:ec2::254`).
- IPv6 que incrustan una IPv4 y se evalúan por ella: `::ffff:0:0/96` y `64:ff9b::/96`. Si la IPv4 incrustada es interna, la dirección es interna; si es bloqueada, es bloqueada.

### 2.2 Direcciones bloqueadas (nunca se permiten, RN-004 I-06 y RN-017)

- IPv4: `0.0.0.0/8`, `169.254.0.0/16` (enlace local; incluye `169.254.169.254`, servicio de metadatos de nubes y escritorios virtuales), `192.0.0.0/24`, `192.0.2.0/24`, `198.18.0.0/15`, `198.51.100.0/24`, `203.0.113.0/24`, `224.0.0.0/4`, `240.0.0.0/4` y `255.255.255.255`.
- IPv6:
  - `::` (sin especificar);
  - `::/96` (IPv4 compatibles en desuso, de forma `::a.b.c.d`, salvo `::` y `::1`, que tienen su propia entrada);
  - `fe80::/10` (enlace local);
  - `ff00::/8` (multidifusión);
  - `2001:db8::/32` (documentación);
  - `2001::/32` (Teredo);
  - `2002::/16` (6to4);
  - `64:ff9b:1::/48` (traducción local);
  - `fd00:ec2::254` (metadatos de nube).

### 2.3 Extensiones peligrosas (lista cerrada, RN-021, aviso A-1)

Se evalúa la **última** extensión del nombre final, ya saneado y con su sufijo, sin distinguir mayúsculas. Se toma como la toma Windows: lo que sigue al último punto, aunque sea el primer carácter (el nombre `.exe` tiene extensión `exe`).

| Grupo | Extensiones |
|---|---|
| Ejecutables e instaladores | `.exe` `.com` `.scr` `.pif` `.cpl` `.dll` `.sys` `.msi` `.msp` `.msix` `.msixbundle` `.appx` `.appxbundle` `.appinstaller` `.application` |
| Guiones | `.bat` `.cmd` `.ps1` `.psm1` `.psd1` `.vbs` `.vbe` `.js` `.jse` `.wsf` `.wsh` `.hta` |
| Accesos directos y configuración | `.lnk` `.url` `.scf` `.inf` `.reg` `.rdp` `.settingcontent-ms` `.library-ms` `.diagcab` `.msc` |
| Contenedores e imágenes de disco | `.jar` `.chm` `.iso` `.img` `.vhd` `.vhdx` |
| Office con macros | `.docm` `.dotm` `.xlsm` `.xltm` `.xlam` `.pptm` `.ppam` |

### 2.4 Caracteres invisibles y de control de dirección (se eliminan, RN-014 a)

U+00AD (guion suave), U+061C (marca de letra árabe), U+200B a U+200F (espacios de ancho cero y marcas de dirección), U+202A a U+202E (incrustaciones e inversiones de dirección), U+2060 a U+2064 (unión de palabras y operadores invisibles), U+2066 a U+2069 (aislamientos de dirección) y U+FEFF (marca de orden de bytes).

### 2.5 Nombres reservados de Windows (RN-015)

`CON`, `PRN`, `AUX`, `NUL`, `COM0`–`COM9`, `LPT0`–`LPT9`, `COM¹`, `COM²`, `COM³`, `LPT¹`, `LPT²`, `LPT³`, `CONIN$`, `CONOUT$` y `CLOCK$`, sin distinguir mayúsculas.
