# Reglas de negocio

- **Estado**: Listo para revisión
- **Fecha**: 2026-11-07
- **Versión**: 0.7
- **Historial**:
  - 0.7: correcciones técnicas surgidas de la revisión de la spec 001, sin cambiar ninguna decisión:
    - RN-001 paso 8: pasar a minúsculas y normalizar a NFC no marca la URL como corregida;
    - RN-016 b: se retira el límite de 247 caracteres para carpetas, que era redundante, y se explica el máximo de 205 que impone el temporal.
  - 0.6: **cambio de usuario: app Python sencilla, sin instalador.** Solo cambia RN-039 (paquete portátil, sin instalador ni requisitos de permisos, firma opcional y futura, SHA-256 recomendada). El resto de las reglas no cambia.
  - 0.5: tercera revisión de `revisor-spec`. Cambios:
    - orden de las comprobaciones de RN-001, con I-09 y el dominio con espacio antes de codificar;
    - la `\` de la ruta se convierte en `/` y la de los parámetros se codifica;
    - autoridad cruda frente a autoridad en RN-001a;
    - ubicación de "Exportar no completadas" antes de iniciar;
    - autorización del dominio de destino en las redirecciones;
    - ruta real de la carpeta destino;
    - normalización NFC del dominio;
    - sin doble decodificación del nombre del servidor;
    - contraste verificado de la paleta cálida;
    - ejemplos 49 a 55.
  - 0.2: incorporó las respuestas del usuario a las 8 preguntas iniciales.
  - 0.3: incorporó el primer informe de `revisor-spec` y renumeró las reglas (los ID de la 0.2 dejaron de ser válidos).
  - 0.4: incorpora el segundo informe de `revisor-spec` (cambios menores) y nuevas decisiones del usuario: proxy sin autenticación, registro de errores mínimo, versiones de Windows, codificación automática de URLs, duración máxima por archivo, firma de código opcional y detección de dominios internos en el motor. Se mantienen los ID RN-001 a RN-039 y se añaden RN-040 a RN-043.

Convención: cada regla tiene un ID `RN-NNN` y se referencia desde el PRD y las specs. La columna **Origen** indica de dónde sale cada regla:
- **Usuario**: la decidió el usuario.
- **Seguridad**: exigencia de seguridad propuesta por el analista.
- **Supuesto S-NN**: propuesta pendiente de validar al aprobar el PRD (ver PRD, sección 9).

Las listas cerradas que usan varias reglas (direcciones internas y bloqueadas, extensiones peligrosas, caracteres invisibles, nombres reservados) están en `glosario.md` y son la **única fuente normativa**.

---

## A. Entrada de URLs (EP-01)

| ID | Regla | Origen |
|---|---|---|
| RN-001 | **Interpretación de cada URL.** Cada línea del archivo masivo, o el texto del campo individual, ya recortado, se interpreta en este orden: **(1)** si empieza por `\\` o por letra de unidad seguida de `:\` o `:/` (p. ej. `C:\`), es inválida (I-02). **(2)** Si la línea **empieza** por un esquema seguido de `://`, se comprueba ese esquema. Hay esquema solo si el texto anterior al primer `://` cumple el patrón `[A-Za-z][A-Za-z0-9+.-]*`, es decir, empieza por una letra y solo contiene letras, dígitos, `+`, `.` o `-`. El esquema debe ser `http` o `https` (sin distinguir mayúsculas); si es otro, la URL es inválida (I-01). **(3)** Si empieza por `javascript:`, `vbscript:`, `data:`, `file:`, `blob:`, `about:` o `mailto:`, es inválida (I-01). **(4)** Si un espacio interior va seguido de `http://` o `https://`, la línea es inválida (I-09), porque probablemente contiene dos URLs. Esto se comprueba **antes** de codificar, de modo que `https://a.com/x.pdf https://b.com/y.pdf` es I-09 y no una sola URL con `%20`. **(5)** En cualquier otro caso sin esquema, incluido cuando el texto antes de `://` no cumple el patrón (p. ej. `www.sitio.com/ir?u=http://x.com/a.pdf`), se antepone `https://` y la URL se marca como **corregida**. **(6)** Sobre el texto **todavía sin codificar** se aplican las comprobaciones de RN-001a: ambigüedad, credenciales embebidas (I-05), punto final del dominio. Además, un dominio con espacios es inválido (I-03). **(7) Barra invertida en la ruta**: en la ruta (después de la autoridad y antes de `?` o `#`), cada `\` literal se convierte en `/` antes de codificar (RN-008 e). **(8) Codificación automática**: en la ruta, los parámetros y el fragmento se codifican en porcentaje sobre UTF-8 los espacios interiores, los caracteres no ASCII y estos caracteres: comillas dobles, `<`, `>`, acento grave, `{`, `}`, `\|` y `^`. En los parámetros y el fragmento también se codifica `\` como `%5C` (en la ruta ya no queda ninguna, por el paso 7). Ejemplo: `año 2024.pdf` → `a%C3%B1o%202024.pdf`. El dominio se pasa a minúsculas, se normaliza a la forma Unicode NFC y, si tiene caracteres no ASCII, se convierte a su forma ASCII (`bogotá.com` → `xn--bogot-1qa.com`). La URL se marca como corregida (codificada) **solo** si se codificó algún carácter o si el dominio se convirtió a forma ASCII. Pasar el esquema o el dominio a minúsculas y normalizarlo a NFC **no** la marca como corregida (p. ej. `https://Sitio.COM/a.pdf` no cuenta como corregida). **(9)** Al final debe quedar una URL bien formada con dominio; si no, es inválida (I-03). | Usuario: http/https, `https://` por defecto, codificación automática. Seguridad: patrón del esquema, orden de las comprobaciones. Supuestos S-36 (orden) y S-54 (caracteres codificados, I-09). |
| RN-001a | **Analizador único.** Cada URL (del lote o de una redirección) se analiza **una sola vez**, con un único criterio, y la misma estructura resultante (esquema, dominio, puerto, segmentos, parámetros y fragmento) se usa para validar, calcular la ruta, comprobar las direcciones y conectar. Nunca se vuelve a interpretar el texto en otro paso. Se distinguen dos tramos. **(a) Autoridad cruda**: el texto entre `://` y la primera `/` (o hasta el final si no hay `/`). Se usa **solo** para detectar ambigüedad: la URL es inválida por ambigua (I-03) si la autoridad cruda contiene `\`, o `#` seguido más adelante de `@` (p. ej. `https://sitio.com\@127.0.0.1/` o `https://sitio.com#@127.0.0.1/`), porque distintos programas la interpretarían con dominios distintos. Esta comprobación es conservadora a propósito: también rechaza casos como `https://sitio.com?q=a\b`, y se acepta. **(b) Autoridad**: el texto entre `://` y el primero de `/`, `?` o `#`. Sobre ella se extraen el dominio y el puerto y se detectan las credenciales embebidas (I-05, si contiene `@`). Así, `https://sitio.com?email=a@b.com` es válida, con dominio `sitio.com`. Antes de cualquier comprobación se quita el punto final del dominio (`localhost.` → `localhost`). | Seguridad |
| RN-002 | **Formato del archivo masivo.** `.txt` en UTF-8, con o sin BOM. Se aceptan finales de línea CRLF, LF y CR suelto, incluso mezclados; cada uno cuenta como un fin de línea (S-61). Cada línea se recorta de espacios y tabulaciones al inicio y al final. Se ignoran las líneas vacías (o solo con espacios) y las que, ya recortadas, empiezan por `#` (comentarios). Cada línea restante es una URL. | Usuario (txt UTF-8, una por línea, vacías y `#`). Supuestos S-36 y S-61. |
| RN-003 | **Límites y rechazos del archivo masivo.** **(a)** Máximo 10 000 URLs: cuentan las líneas con contenido que quedan tras quitar vacías y comentarios, **antes** de eliminar duplicados y antes de validar. **(b)** Tamaño máximo: 5 MB (justificación en S-18). **(c)** Si se supera (a) o (b), el archivo se rechaza completo con un mensaje que indica el valor encontrado y el límite. **(d)** Solo se aceptan archivos con extensión `.txt`, sin distinguir mayúsculas (`.TXT` es válido). Un `.csv` se rechaza con "Los archivos .csv no se admiten. Guarde la lista como .txt, con una URL por línea." Cualquier otra extensión se rechaza con "Solo se admiten archivos .txt" (S-61). **(e)** Si el archivo está en UTF-16 (detectado por su marca inicial o por bytes nulos), se rechaza con "El archivo está guardado en UTF-16. Guárdelo como UTF-8 e inténtelo de nuevo". **(f)** Cualquier otro contenido que no sea UTF-8 válido se rechaza con "El archivo no es texto UTF-8 válido", indicando la primera línea con problema. **(g)** Si no queda ninguna línea con contenido: "El archivo no contiene URLs". **(h)** Una URL de más de 2 048 caracteres, después de corregirla y codificarla, es inválida (I-04). | Usuario (10 000). Supuestos S-18, S-36 y S-61. |
| RN-004 | **Catálogo cerrado de motivos de invalidez.** Se muestran en la validación previa. Una URL inválida no se descarga ni es elemento del lote. **I-01** "Protocolo no soportado". **I-02** "Ruta local o de red no soportada". **I-03** "URL mal formada o ambigua" (RN-001 pasos 6 y 9, RN-001a). **I-04** "URL demasiado larga". **I-05** "Requiere autenticación (no soportado)": URL con usuario o clave embebidos. **I-06** "Dirección no permitida": dominio con una IP de la lista de bloqueadas, en cualquier notación. **I-07** "Puerto no válido": fuera de 1–65535. **I-08** "El campo admite una sola URL. Para varias, use un archivo masivo": el texto del campo individual tiene más de una línea con contenido (las líneas vacías al inicio y al final no cuentan); se rechaza todo el texto. **I-09** "Parece haber varias URLs en una misma línea". Ninguna URL se rechaza por un motivo que no esté en este catálogo. | Usuario (I-08). Supuestos S-36 y S-54. |
| RN-005 | **Validación previa y resumen.** Antes de iniciar se muestra: total de líneas leídas, URLs válidas, **URLs corregidas** (desglosadas en "sin esquema" y "con caracteres codificados"), duplicadas (RN-006), inválidas (con número de línea, URL enmascarada según RN-036 y motivo de RN-004) y **dominios internos detectados por su nombre o por ser una IP escrita** (comprobación léxica, RN-017 a). La validación previa **nunca consulta la red**, por lo que **no** detecta los dominios con forma pública que en realidad apuntan a una dirección interna: esos se detectan en el motor y fallan con F-30 (RN-017 b). Si hay inválidas, el usuario puede iniciar solo con las válidas. Si no hay ninguna válida, Iniciar queda deshabilitado. | Usuario (conteo de corregidas, detección de internos en el motor). Supuesto S-36. |
| RN-006 | **Duplicados.** Las URLs repetidas del mismo lote se descargan una sola vez; se conserva la primera aparición. Se comparan **después** de corregirlas y codificarlas (RN-001), sin fragmento, con el esquema y el dominio en minúsculas y sin el puerto estándar. Los parámetros cuentan: `a.pdf?v=1` y `a.pdf?v=2` son distintas. | Supuesto S-36 |
| RN-007 | **Carpeta destino.** Es obligatoria: Iniciar queda deshabilitado hasta que haya una carpeta válida. Es válida si **(a)** existe; **(b)** el usuario puede escribir en ella, lo que se comprueba creando y borrando un archivo con el patrón temporal de RN-031; y **(c)** no es, ni está dentro de: la carpeta de Windows, las carpetas de Archivos de programa (de 64 y 32 bits), la carpeta de datos de programas de Windows ni la carpeta de datos de esta aplicación. Tampoco es válida la raíz de la unidad donde está instalado Windows. La comprobación (c) se hace sobre la **ruta real** de la carpeta destino, después de seguir los enlaces y uniones, y no solo sobre el texto de la ruta. Así, un enlace `D:\Atajo` que apunta a `C:\Windows\Temp` es inválido (ejemplo 54, AB-15). Se aceptan unidades locales, extraíbles y de red. Si deja de ser válida durante el lote (p. ej. se desconecta la unidad), los elementos afectados fallan con F-32. Se recuerda la última carpeta válida (S-08). | Supuesto S-45 |

## B. Organización en carpetas (EP-02)

| ID | Regla | Origen |
|---|---|---|
| RN-008 | **Ruta resultante.** Ruta = carpeta destino \ dominio \ segmentos de carpeta \ nombre de archivo. **(a)** Las carpetas salen **siempre de la URL original** (la del lote, ya corregida), nunca de la URL a la que se llega por redirección. **(b)** El dominio va sin punto final, pasado a minúsculas y normalizado a la forma Unicode NFC **antes** de convertirlo a forma ASCII (`bogotá.com` → `xn--bogot-1qa.com`, S-49). **(c)** El puerto se incluye solo si no es el estándar, unido con `_` (`sitio.com_8443`). **(d)** Los segmentos de carpeta son todos los segmentos de la ruta menos el último; si la ruta termina en `/`, todos son carpetas. **(e)** La barra invertida literal `\` de la ruta (después de la autoridad) se convierte en el separador `/` **antes de codificar** (RN-001 paso 7), igual que en los navegadores. La codificada `%5c`, escrita así por el autor de la URL, se decodifica como carácter y se sanea con RN-014 (S-53). Por eso los ejemplos 6 y 7 del anexo 1 dan resultados distintos. Una `\` en los parámetros o el fragmento se codifica como `%5C` y no afecta a la ruta (ejemplo 51). **(f)** Los segmentos vacíos (`//`) y los segmentos `.` y `..`, también codificados (`%2e`, `%2e%2e`, `.%2e`), se descartan sin resolverse. Si se descarta el **último** segmento, la URL se trata como si terminara en `/`, es decir, sin nombre (RN-010 pasos 3 y 4). **(g)** A cada segmento **y al dominio** se le aplican, en este orden, RN-011, RN-014 y RN-015. Ejemplos en el anexo 1. | Usuario (dominio + ruta, carpeta de la URL original, puerto). Supuestos S-49 y S-53. |
| RN-009 | **Parámetros y fragmento.** Lo que va después de `?` o de `#` no interviene en las carpetas ni en el nombre del archivo. | Usuario |
| RN-010 | **Nombre del archivo**, en este orden de prioridad: **(1)** si el servidor sugiere un nombre, se usa ese. Si lo envía de dos formas, prevalece la forma internacional en UTF-8 (`filename*`, norma RFC 6266) sobre la simple (`filename`). Se toma solo lo que va después de la última `/` o `\` y se sanea con RN-014 y RN-015. El nombre que entrega el servidor ya llega decodificado al analizarlo, así que **no se vuelve a decodificar** con RN-011. **(2)** Si no, el último segmento de la ruta de la URL original. Si no tiene extensión y el tipo de contenido está en la tabla de abajo, se le añade la extensión de la tabla (`x` → `x.pdf`) (S-48). **(3)** Si la URL no trae nombre, se usa `index` más la extensión de la tabla. **(4)** Si el tipo no está en la tabla o no se informa, `index` sin extensión. Si tras sanear el nombre queda vacío, se pasa al siguiente paso. | Usuario (prioridad servidor → URL → tipo → `index`). Supuesto S-48. |
| RN-011 | **Decodificación.** Cada segmento se decodifica **una sola vez** desde UTF-8 para que sea legible (`Informe%20A%C3%B1o` → `Informe Año`). `%252e` se convierte en el texto `%2e` y no se vuelve a decodificar. Si una secuencia no es UTF-8 válida, se conserva con sus `%`. El saneamiento se aplica siempre **después** de decodificar. Así, el nombre en disco queda decodificado y saneado aunque la URL se haya codificado automáticamente (RN-001 paso 8). | Usuario (nombre decodificado). Supuesto S-36. |
| RN-012 | **Archivo o ruta ya existente.** **(a)** Si la ruta resultante ya existe en disco (como archivo o como carpeta), o está reservada por otro elemento del mismo lote, se añade un sufijo antes de la última extensión, `informe (1).pdf`, `informe (2).pdf`..., hasta encontrar uno libre; si no hay extensión, va al final (`docs (1)`). Nunca se sobrescribe nada. La comparación no distingue mayúsculas, igual que Windows. **(b) Prevalecen las carpetas**: al validar el lote se calcula el conjunto de carpetas que necesitan todas sus URLs. Si el nombre final de un archivo coincide con una de esas carpetas, el archivo recibe sufijo, **sin importar el orden** en que se descarguen (p. ej. `/docs` y `/docs/x.pdf` en el mismo lote → `docs (1)` y `docs\x.pdf`). **(c)** Si ya existe en disco un **archivo** con el nombre de una carpeta que hace falta crear, el elemento falla con F-27. **(d)** El nombre definitivo se decide cuando se conoce el nombre sugerido por el servidor, al empezar a recibir la respuesta. | Usuario (sufijo). Supuesto S-59 (prevalencia de carpetas). |

### Tabla de tipos de contenido (RN-010)

Es una lista cerrada; cualquier otro tipo se trata como "no está en la tabla".

| Tipo informado por el servidor | Extensión |
|---|---|
| `text/html` | `.html` |
| `text/plain` | `.txt` |
| `text/csv` | `.csv` |
| `application/json` | `.json` |
| `application/xml`, `text/xml` | `.xml` |
| `application/pdf` | `.pdf` |
| `image/jpeg` | `.jpg` |
| `image/png` | `.png` |
| `image/gif` | `.gif` |
| `image/webp` | `.webp` |
| `application/zip` | `.zip` |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `.xlsx` |
| `application/vnd.openxmlformats-officedocument.presentationml.presentation` | `.pptx` |
| `video/mp4` | `.mp4` |

## C. Seguridad de rutas (EP-02)

| ID | Regla | Origen |
|---|---|---|
| RN-013 | **Contención en la carpeta destino.** Ningún archivo ni carpeta se crea fuera de la carpeta destino. **(a)** Además de RN-008 (f), antes de crear cada carpeta y antes de dar al archivo su nombre final se comprueba que la ruta quede dentro de la carpeta destino. **(b)** Las carpetas se crean **sin seguir enlaces ni uniones de carpetas** (puntos de reanálisis). Si una carpeta intermedia que ya existe dentro del destino es un enlace o una unión, el elemento falla con F-24, **sin importar a dónde apunte**, y no se escribe nada. La propia carpeta destino que eligió el usuario sí puede ser un enlace. | Seguridad |
| RN-014 | **Caracteres.** **(a)** Se eliminan los caracteres invisibles y de control de dirección del glosario 2.4. **(b)** Los caracteres no válidos en Windows (`< > : " / \ \| ? *` y U+0000–U+001F) se reemplazan por `_`. **(c)** Se eliminan los puntos y espacios al final del nombre. **(d)** Si el nombre queda vacío: `_` en carpetas, o el siguiente paso de RN-010 en nombres de archivo. | Seguridad. Supuesto S-41. |
| RN-015 | **Nombres reservados de Windows** (lista del glosario, sección 2.5). Se evalúan en cada segmento, en el nombre del archivo y en el dominio, sin distinguir mayúsculas, sobre el **texto anterior al primer punto** y sin los espacios finales de ese tramo. Si ese texto es un nombre reservado, se inserta `_` justo después de él: `con.tar.gz` → `con_.tar.gz`; `nul.com` (dominio) → `nul_.com`; `con .txt` → `con_ .txt`; `CON` → `CON_`; `CONIN$` → `CONIN$_`. | Seguridad (forma: supuesto) |
| RN-016 | **Longitud de las rutas.** **(a) Componentes**: si algún nombre de carpeta o de archivo, ya saneado y con su sufijo, supera 255 caracteres, el elemento falla con F-28 y los nombres no se acortan. **(b) Ruta completa**: se mide la **mayor** de dos rutas: la final, con el sufijo de RN-012 si lo lleva, y la del temporal (carpeta + `~descargador-<32>.parcial`, 53 caracteres). Límites: con rutas largas habilitadas en Windows, 32 000 caracteres; sin ellas, 259 caracteres. Como toda carpeta que contiene un archivo debe admitir también su temporal (carpeta + `\` + 53 caracteres), sin rutas largas la carpeta que contiene el archivo no puede superar 205 caracteres. Por eso no hace falta un límite aparte para las carpetas: el límite de carpeta de Windows (247) nunca llega a aplicarse. Si se supera el límite aplicable, el elemento falla con F-25 y el mensaje sugiere elegir una carpeta destino más corta. **(c)** Nunca se pierde un archivo en silencio. | Supuestos S-23 y S-60 (críticos) |

## D. Seguridad de red (EP-03)

| ID | Regla | Origen |
|---|---|---|
| RN-017 | **Direcciones internas y bloqueadas.** Se usan las listas normativas del glosario (2.1 y 2.2). **Si una dirección aparece en las dos, prevalece la bloqueada.** **(a) Comprobación léxica** (validación previa, sin red): el dominio, ya sin punto final (RN-001a), se compara con las listas, aceptando cualquier notación de IP (decimal entera, octal, hexadecimal, abreviada, IPv6 con IPv4 incrustada, entre corchetes). Si es **bloqueada**, la URL es inválida (I-06). Si es **interna**, el dominio entra en una única confirmación que se muestra antes de iniciar. **(b) Comprobación por resolución** (motor): antes de conectar se resuelve el nombre. Si **alguna** de las direcciones obtenidas es bloqueada, el elemento falla con F-23. Si alguna es interna y el dominio no está autorizado, falla con F-30. Así se detectan los nombres con forma pública que apuntan a la red interna (RN-005). La conexión se hace **exactamente a la dirección comprobada**, sin volver a resolver. **(c) Redirecciones**: cada salto se analiza con RN-001a y pasa por (a) y (b). **(d) Confirmación y autorización**: si el usuario no confirma antes de iniciar, esos elementos quedan Fallidos con F-30 y el resto continúa. Un elemento con F-30 ofrece "Permitir y reintentar", que pide confirmación y **autoriza el dominio rechazado para todos los elementos de ese dominio en el lote**. El dominio rechazado es el que provocó el F-30: si el fallo vino de una redirección, se autoriza el dominio **de destino** de la redirección, no el de la URL original (ejemplo 53). Al autorizarlo, vuelven a la cola todos los elementos Fallidos con F-30 cuyo dominio rechazado sea ese, y ningún elemento pendiente volverá a fallar por llegar a ese dominio, ni directamente ni por redirección. La autorización no se recuerda entre lotes. **(e)** Con proxy, ver RN-020. | Usuario (advertir y confirmar, también por redirección; detección en el motor; autorización por dominio). Seguridad: (b) y (c). Supuestos S-37 y S-51. |
| RN-018 | **Certificados, TLS y redirecciones.** **(a)** Los certificados se validan contra el almacén de confianza de Windows, que incluye las autoridades corporativas de Eficacia. **(b)** Un certificado no confiable, vencido, revocado o emitido para otro nombre provoca F-18. **No existe ninguna forma de saltarse la validación** ni excepciones manuales por sitio. **(c)** Cifrado mínimo TLS 1.2; uno inferior provoca F-19. **(d) Excepción acotada de revocación**: un certificado revocado se rechaza siempre. Si **no se puede consultar** su estado de revocación (servicio de consulta inaccesible), el certificado se acepta y se anota en el registro (código y dominio). Es la única excepción a la validación y queda documentada (S-30). **(e)** Una redirección de `https` a `http` provoca F-20. **(f)** Una redirección a un protocolo distinto de `http`/`https` provoca F-22. **(g)** Se siguen como máximo 10 redirecciones; la siguiente provoca F-21. | Usuario (almacén de Windows, sin saltarse la validación, sin excepciones por sitio, HTTPS a HTTP). Supuesto S-30 (crítico) y máximo de 10. |
| RN-019 | **Autenticación, credenciales y cookies.** No se soporta ninguna autenticación. **(a)** La aplicación nunca envía credenciales de Windows ni cookies, y no guarda las cookies que reciba. **(b)** Si el **sitio** pide autenticación (401): F-13 "Requiere autenticación". **(c)** Si el **proxy** la pide (407): F-14 "El proxy requiere autenticación (no soportado)". **(d)** Las URLs con usuario o clave embebidos son inválidas (I-05) y nunca se muestran completas. | Usuario: falla, 401 distinto de 407, y confirmado que el proxy de Eficacia no pide autenticación (S-42 resuelto). |
| RN-020 | **Proxy.** Se usa la configuración de proxy de Windows del usuario, incluidas la detección automática y el script de configuración si Windows los tiene; sin proxy, la conexión es directa. Las direcciones excluidas del proxy se conectan directamente, con la comprobación completa de RN-017. Por proxy: **(a)** el propio proxy no se evalúa como dirección interna; **(b)** se aplica la comprobación léxica y además el nombre se resuelve localmente, solo para comprobarlo; **(c)** si no se puede resolver localmente, se sigue solo con la comprobación léxica; **(d)** la dirección no se puede fijar porque conecta el proxy. **Riesgos residuales aceptados y documentados (S-38):** (1) cambio de dirección por proxy (AB-13); (2) la resolución local para comprobar envía al servidor de nombres de la red los dominios del lote (no las rutas ni los parámetros); (3) la detección automática de proxy de Windows puede ser suplantada por un atacante en la red local. Las descargas `https` siguen protegidas por RN-018; las `http` podrían alterarse en tránsito (AB-21). | Usuario (proxy de Windows; si no hay, directa). Supuesto S-38 (crítico). |

## E. Seguridad de los archivos descargados (EP-03, EP-04)

| ID | Regla | Origen |
|---|---|---|
| RN-021 | **Nunca abrir ni ejecutar; avisos.** La aplicación nunca abre, ejecuta ni muestra en vista previa un archivo descargado. La única acción relacionada es **"Abrir carpeta"**, que abre el Explorador de Windows en la carpeta destino del lote. Un **aviso** es un ícono más un texto corto en la fila del elemento; además, en el resumen final se muestra el conteo de cada tipo de aviso y se puede filtrar la lista por él. Tipos de aviso: **A-1** "Archivo ejecutable o con macros: no lo abra si no confía en el origen": extensión de la lista cerrada del glosario 2.3, evaluada sobre la última extensión del nombre final. **A-2** "Se recibió una página web en lugar de un archivo": el servidor respondió con éxito y tipo `text/html`, y el nombre final no termina en `.html` ni en `.htm`. El contenido se guarda tal cual. **A-3** "No se pudo marcar el origen" (RN-022). Ningún aviso impide la descarga. | Usuario (solo "Abrir carpeta"). Supuestos S-40 y S-57. |
| RN-022 | **Marca de origen (Mark of the Web).** Todo archivo descargado recibe la marca de origen de Windows de la zona Internet, también si viene de una dirección interna. La marca **no incluye la URL**. Se aplica sobre el temporal, antes del nombre final. Si la unidad no la admite (p. ej. FAT32/exFAT o algunas carpetas de red), la descarga se completa, se anota en el registro y el elemento lleva el aviso A-3. | Seguridad. Supuesto S-39. |
| RN-023 | **Espacio en disco y reserva mínima.** La reserva es el mayor valor entre 500 MB y el 2 % de la capacidad de la unidad destino. **(a)** Antes de iniciar un elemento con tamaño informado, si el espacio libre menos ese tamaño queda por debajo de la reserva, el elemento falla con F-31 y el lote continúa. **(b)** Durante las descargas, si el espacio libre cae por debajo de la reserva, el lote se detiene: se borran los temporales en curso, y los elementos en curso y pendientes quedan Fallidos con F-31. | Supuesto S-31 (crítico) |
| RN-024 | **Tope de tamaño por archivo.** 10 GB por defecto, configurable entre 1 GB y 500 GB. Si el tamaño informado supera el tope, falla con F-26 sin descargar nada. Si no se informa, la descarga se corta al superar el tope, se borra el temporal y falla con F-26. | Supuesto S-19 (crítico) |

## F. Ejecución (EP-03)

| ID | Regla | Origen |
|---|---|---|
| RN-025 | **Descargas simultáneas.** 3 por defecto, configurable de 1 a 8. Si se cambia durante un lote, se aplica a medida que se liberan cupos, sin interrumpir las descargas en curso. | Usuario (3; de 1 a 8). Supuesto: se aplica en caliente. |
| RN-026 | **Clasificación de fallos.** Catálogo cerrado en el anexo 2: cada fallo tiene un código F-NN, un motivo visible y una clase. **Temporal**: se reintenta automáticamente. **Permanente**: no se reintenta automáticamente. **Recuperable**: no se reintenta automáticamente; se resuelve con una acción del usuario y luego "Reintentar fallidas" o "Permitir y reintentar". Cualquier situación no prevista es F-99. | Supuesto S-43 |
| RN-027 | **Reintentos.** **(a)** Solo los fallos temporales se reintentan automáticamente: hasta 3 veces por elemento, con esperas de 2 s, 4 s y 8 s. **(b)** Si el servidor indica cuánto esperar, se usa el mayor valor entre el indicado y el propio, hasta 60 s. Si indica más de 60 s, el elemento falla sin más reintentos y **conserva el código original** (p. ej. F-06). **(c)** Cada reintento empieza desde cero. **(d)** "Reintentar fallidas" vuelve a poner en cola todos los elementos Fallidos del lote, de cualquier clase (incluido F-99), con sus 3 reintentos automáticos disponibles de nuevo. Si entre ellos hay elementos con F-30, antes se muestra **una sola confirmación con la lista de sus dominios**: los dominios confirmados quedan autorizados (RN-017 d) y los elementos de dominios no confirmados siguen Fallidos con F-30. | Usuario (3 reintentos, botón). Supuesto S-43. |
| RN-028 | **Tiempos de espera y duración máxima.** **(a)** Conexión: 15 s (F-02). **(b)** Sin recibir datos: 30 s (F-03). **(c)** Velocidad mínima sostenida: menos de 1 KB/s de media durante 60 s seguidos (F-04). Los tres son temporales y se miden **por intento**. **(d) Duración máxima por archivo**: 2 h por defecto, configurable entre 10 min y 24 h. Se mide desde que empieza a recibir datos en cada intento. Al vencer, se borra el temporal y el elemento falla con F-33 (recuperable: no se reintenta automáticamente, pero sí con "Reintentar fallidas"). | Usuario (duración de 2 h configurable, recuperable). Supuestos S-21, S-33 (críticos) y S-56 (rango). |
| RN-029 | **Sin reanudación; cierre.** No hay reanudación, ni en la sesión ni entre sesiones. Si el usuario cierra la aplicación con un lote en curso o con elementos no completados, se muestra un diálogo con tres opciones: **"Exportar no completadas"** (RN-035; al terminar, vuelve al diálogo), **"Cerrar de todos modos"** y **"Volver"**. Al cerrar, se borran los temporales y el lote no se recuerda. | Usuario (sin reanudación). Supuesto: diálogo de cierre. |
| RN-030 | **Cancelación.** El usuario puede cancelar el lote completo (con confirmación) o un elemento, en curso o pendiente (sin confirmación). Lo cancelado queda Cancelado; lo completado se conserva. **Plazos**: un elemento deja de recibir datos en ≤ 2 s y su temporal se borra en ≤ 5 s; la cancelación del lote con 8 descargas activas termina en ≤ 5 s. Los Cancelados no entran en "Reintentar fallidas", pero sí en la exportación. | Usuario (lote e individual, borrar parciales, conservar completados). Supuesto S-44. |
| RN-031 | **Temporales y limpieza de huérfanos.** **(a)** Cada descarga se escribe en un temporal, en su carpeta final, con el patrón exacto `~descargador-<32 caracteres hexadecimales aleatorios>.parcial` (53 caracteres). Solo al completarse y recibir la marca de origen toma su nombre final. Un archivo con nombre final siempre está completo. **(b)** La aplicación mantiene un **registro de carpetas usadas**, con solo rutas de carpetas y nunca URLs. Cada carpeta se escribe en el registro, de forma persistente, **antes** de crear en ella el primer temporal. **(c)** Al arrancar, y al terminar o cancelar un lote, se borran de esas carpetas, sin recorrer subcarpetas, los archivos que cumplen exactamente el patrón y no pertenecen a una descarga activa; después se vacía el registro. **(d)** Se eliminan las carpetas que la aplicación creó en el lote y que quedan vacías porque sus elementos no se completaron. **(e)** Este registro es la única excepción a S-15 (sin historial). | Supuestos S-24 (crítico), S-35 y S-50. |
| RN-032 | **Instancia única.** Solo una ventana de la aplicación por usuario de Windows; si se intenta abrir otra, se trae al frente la existente. | Supuesto S-34 |

## G. Avance, resultado y avisos al usuario (EP-04)

| ID | Regla | Origen |
|---|---|---|
| RN-033 | **Avance y vista principal.** **(a) Por elemento**: estado, porcentaje, bytes descargados, velocidad y tiempo restante, y "reintentando N de 3" cuando aplique. Si no se conoce el tamaño: "{bytes} descargados · tamaño desconocido", sin porcentaje ni tiempo restante. **(b) Por lote**: completados/total, porcentaje global (por número de elementos), velocidad total y tiempo restante. **(c) Cálculos**: la velocidad es la media de los últimos 5 s. El tiempo restante de un elemento es bytes restantes ÷ velocidad. El del lote es elementos restantes × duración media de los completados ÷ descargas simultáneas, y se muestra a partir de 3 completados; antes, "Calculando…". **(d)** Todo se actualiza al menos una vez por segundo. **(e) Criterio de diseño minimalista**: en su **estado inicial** (al abrir la aplicación, sin lote validado), la vista principal muestra **como máximo 6 controles interactivos**: campo de URL, cargar archivo, elegir carpeta, Iniciar, ajustes y tema. Los controles que aparecen después dentro de paneles propios no cuentan para ese máximo: el panel de resumen de validación (con "Exportar no completadas", RN-035 f), la lista de avance y el resumen final. Las opciones avanzadas (descargas simultáneas, tope de tamaño, duración máxima) van en una pantalla de ajustes aparte. | Usuario (avance en todo momento, minimalista). Supuestos S-09 y S-55. |
| RN-034 | **Resumen final.** Muestra: completadas, fallidas (con motivo), canceladas, URLs corregidas y el conteo de cada aviso (A-1, A-2, A-3), con filtro. Acciones: **"Abrir carpeta"** (RN-021), **"Reintentar fallidas"** (RN-027) y **"Exportar no completadas"** (RN-035). | Usuario ("Abrir carpeta"). Supuesto S-57. |
| RN-035 | **Exportación de no completadas.** **(a)** Contenido: todos los elementos que no estén en estado Completada al exportar (Fallidos, Cancelados, Pendientes y en curso); no incluye las líneas inválidas. **(b)** Cada URL se exporta **sin enmascarar**, tal como se procesó (corregida y codificada), para poder recargarla. Las URLs con credenciales embebidas nunca son elementos (I-05), así que nunca se exportan. **(c)** Antes de guardar se muestra el aviso "Este archivo contiene las URLs completas, que pueden incluir tokens o claves de acceso. Guárdelo en un lugar seguro y no lo comparta.", que el usuario debe aceptar. **(d)** El usuario elige la ubicación con el diálogo de Windows; nombre propuesto: `no-completadas-AAAAMMDD-HHMM.txt`. Es la única escritura fuera de la carpeta destino que decide el usuario. **(e)** Formato: UTF-8 sin BOM, CRLF, un encabezado de comentarios con `#` y una URL por línea, en el orden del lote. **(f)** Está disponible desde que hay un lote validado. Antes de iniciar, el control "Exportar no completadas" está dentro del panel de resumen de validación (RN-005), no en la vista principal (RN-033 e). Durante el lote, en la lista de avance, y al final, en el resumen (RN-034). Ejemplo exacto en el anexo 3. | Usuario (no completadas, URL original, aviso, ubicación elegida). Supuesto S-52. |
| RN-040 | **Arrastrar y soltar.** Soltar un archivo sobre la ventana equivale a cargarlo como archivo masivo, con las mismas reglas (RN-002, RN-003). Si se sueltan varios archivos o una carpeta, se rechaza con "Suelte un solo archivo .txt". No se admite durante un lote en curso. | Supuesto S-11 |
| RN-041 | **Notificación al terminar.** Si la ventana no está en primer plano al terminar un lote, se muestra una notificación de Windows con los conteos de completadas, fallidas y canceladas. **Nunca incluye URLs, dominios, rutas ni nombres de archivo.** | Supuesto S-13. Seguridad: contenido. |

## H. Privacidad y registro (transversal)

| ID | Regla | Origen |
|---|---|---|
| RN-036 | **Enmascaramiento de URLs.** En pantalla, en los mensajes de error, en los diálogos y en cualquier texto visible, las URLs se muestran: sin credenciales (`***@`), con el valor de cada parámetro reemplazado por `***` y con el fragmento reemplazado por `#***`. Ejemplo: `https://sitio.com/a.pdf?token=***&v=***#***`. El título de la ventana y las notificaciones nunca contienen URLs. Única excepción: la exportación (RN-035). **Riesgo residual documentado**: los tokens que vienen **dentro de la ruta** (p. ej. `/descarga/abc123/archivo.pdf`) no se distinguen de un nombre de carpeta normal, así que no se enmascaran y además se convierten en nombres de carpeta en disco. | Seguridad. Excepción: Usuario. |
| RN-037 | **Registro de errores con datos mínimos.** **(a)** Se guarda en la carpeta de datos de la aplicación del usuario de Windows y no sale del equipo. **(b)** Cada entrada contiene **solo**: fecha y hora, código (F-NN, o I-NN en errores de validación, o un identificador interno de tipo de error), **esquema + dominio + puerto** (sin ruta, sin parámetros ni fragmento), el motivo del catálogo y la versión de la aplicación. **(c)** Nunca contiene rutas de disco, nombres de archivo, el nombre de usuario de Windows, URLs completas, cabeceras, cookies, credenciales ni contenido de los archivos. En F-99 se registra solo el identificador del tipo de error, **nunca el texto de la excepción**, porque podría incluir rutas o URLs. **(d)** Retención: archivos de máximo 2 MB, como máximo 5 (10 MB en total); se borran los más antiguos y cualquier entrada de más de 30 días. | Usuario (sin rutas ni usuario; código, dominio y motivo). Supuesto S-46 (retención). |
| RN-043 | **Preferencias.** Se guardan en la carpeta de datos de la aplicación: tema, descargas simultáneas, tope de tamaño, duración máxima y última carpeta destino. Si el archivo de preferencias falta, está dañado o tiene valores fuera de rango, se usan los valores por defecto para todo lo que no se pueda leer. Se avisa una vez con "No se pudieron leer sus preferencias; se usaron los valores por defecto", se registra (sin contenido) y se reescribe el archivo. | Supuesto S-58 |

## I. Apariencia y accesibilidad (EP-05)

| ID | Regla | Origen |
|---|---|---|
| RN-038 | **Temas.** Claro, oscuro, cálido y "según Windows" (el predeterminado). El cambio es inmediato, sin reiniciar, y se recuerda. "Según Windows" sigue la configuración claro/oscuro del sistema, incluso si cambia con la aplicación abierta. **En todos los temas y estados** (normal, al pasar el ratón, con foco, deshabilitado): el texto tiene un contraste de al menos 4.5:1, y los bordes de los controles y el indicador de foco, de al menos 3:1. El texto deshabilitado debe seguir siendo legible, con un contraste de al menos 3:1. **Paleta propuesta para el tema cálido (a validar)**: fondo `#FBF3E4`, superficie `#F3E3C8`, texto `#3B2A20`, acento `#A84A2A`, éxito `#4F6A24`, error `#A23B2A`. **Contraste verificado**: el acento sobre la superficie da ≈ 4,52:1 (el par más ajustado; cumple). Los demás pares de texto sobre fondo y sobre superficie dan entre 4,9:1 y más de 10:1. **La superficie no debe oscurecerse**, porque el acento sobre ella dejaría de cumplir 4.5:1. Los estados al pasar el ratón, con foco y deshabilitado se verifican con RNF-11. | Usuario (temas, predeterminado, que se recuerde). Supuestos S-22 y S-29. |
| RN-042 | **Teclado, lector de pantalla y escalado.** Todas las funciones se pueden usar solo con el teclado, en un orden lógico y con el foco siempre visible. Hay atajos para Iniciar, Cancelar lote y Cargar archivo. El Narrador de Windows anuncia el nombre y el estado de cada control, y los cambios de estado del lote (iniciado, completado, detenido). La interfaz se ve completa, sin cortes ni superposiciones, con escalado de pantalla al 100 %, 125 % y 150 %. | Supuesto S-22 |

## J. Distribución (transversal)

| ID | Regla | Origen |
|---|---|---|
| RN-039 | **Paquete portátil e integridad.** **(a)** La aplicación se entrega como **paquete portátil**: una carpeta o un ejecutable único que incluye todo lo necesario para funcionar. El usuario no instala Python ni ningún otro componente. **(b)** No hay instalador ni publicación en tiendas de aplicaciones. Se ejecuta sin permisos de administrador desde cualquier carpeta del usuario. **(c)** Las preferencias y los registros se guardan en la carpeta de datos de la aplicación del usuario de Windows, nunca dentro de la carpeta del paquete. **(d)** Se recomienda publicar, junto a cada versión, la suma de verificación SHA-256 del paquete por un canal interno de confianza de Eficacia. **(e)** La versión 1 se distribuye sin firma de código; la firma es opcional y futura. Las notas de la versión explican que Windows SmartScreen puede advertir al ejecutar el paquete por primera vez. **(f)** No hay actualizaciones automáticas. | Usuario (v0.6: app Python sencilla, sin instalador). Supuestos S-07, S-47 y S-62. |

---

## Anexo 1. Ejemplos de URL → ruta resultante

Carpeta destino: `D:\Descargas`. "Sugiere" = nombre sugerido por el servidor. Cada ejemplo es un caso de prueba obligatorio.

| # | URL del lote (y respuesta del servidor) | Resultado | Reglas |
|---|---|---|---|
| 1 | `https://sitio.com/docs/2024/informe.pdf?v=2` | `D:\Descargas\sitio.com\docs\2024\informe.pdf` | RN-008, RN-009 |
| 2 | `https://Sitio.COM:443/Docs/A.pdf` | `D:\Descargas\sitio.com\Docs\A.pdf` | RN-008 b, c |
| 3 | `http://sitio.com:8080/a/b.zip` | `D:\Descargas\sitio.com_8080\a\b.zip` | RN-008 c |
| 4 | `https://sitio.com/a/../../../Windows/System32/x.dll` | `D:\Descargas\sitio.com\a\Windows\System32\x.dll` + aviso A-1 | RN-008 f, RN-021 |
| 5 | `https://sitio.com/%2e%2e/%2e%2e/secreto.txt` | `D:\Descargas\sitio.com\secreto.txt` | RN-008 f |
| 6 | `https://sitio.com/a\..\..\b.txt` | Cada `\` de la ruta se convierte en `/` antes de codificar → `D:\Descargas\sitio.com\a\b.txt` | RN-001 (7), RN-008 e, f |
| 7 | `https://sitio.com/a%5c..%5c..%5cb.txt` | `D:\Descargas\sitio.com\a_.._.._b.txt` | RN-008 e, RN-014 |
| 8 | `https://sitio.com/CON/aux.txt` | `D:\Descargas\sitio.com\CON_\aux_.txt` | RN-015 |
| 9 | `https://sitio.com/a%3Ab/c%2Ad%22.pdf` | `D:\Descargas\sitio.com\a_b\c_d_.pdf` | RN-011, RN-014 b |
| 10 | `https://sitio.com/carpeta./archivo%20.txt%20` | `D:\Descargas\sitio.com\carpeta\archivo .txt` | RN-014 c |
| 11 | `https://sitio.com/Informe%20A%C3%B1o/Bogot%C3%A1.pdf` | `D:\Descargas\sitio.com\Informe Año\Bogotá.pdf` | RN-011 |
| 12 | `https://sitio.com/docs/` (sugiere `reporte final.pdf`) | `D:\Descargas\sitio.com\docs\reporte final.pdf` | RN-010 (1) |
| 13 | `https://sitio.com/docs/` (no sugiere; `application/pdf`) | `D:\Descargas\sitio.com\docs\index.pdf` | RN-010 (3) |
| 14 | `https://sitio.com` (no sugiere; tipo desconocido) | `D:\Descargas\sitio.com\index` | RN-010 (4) |
| 15 | `https://sitio.com/descarga?id=7` (sugiere `..\..\malo.exe`) | `D:\Descargas\sitio.com\malo.exe` + aviso A-1 | RN-010 (1), RN-021 |
| 16 | `https://sitio.com/descarga?id=8` (sugiere `CON.pdf`) | `D:\Descargas\sitio.com\CON_.pdf` | RN-010 (1), RN-015 |
| 17 | `https://sitio.com/factura%E2%80%AEfdp.exe` | `D:\Descargas\sitio.com\facturafdp.exe` + aviso A-1 | RN-014 a, RN-021 |
| 18 | `https://sitio.com/a.pdf` con `D:\Descargas\sitio.com\a.pdf` ya existente | `D:\Descargas\sitio.com\a (1).pdf` | RN-012 a |
| 19 | En el lote: `https://sitio.com/x/A.pdf?v=1` y luego `https://sitio.com/x/a.pdf?v=2` | `...\sitio.com\x\A.pdf` y `...\sitio.com\x\a (1).pdf` | RN-006, RN-012 a |
| 20 | `www.sitio.com/a.pdf` | Corregida (sin esquema) → `https://www.sitio.com/a.pdf` → `D:\Descargas\www.sitio.com\a.pdf` | RN-001 (5) |
| 21 | `https://sitio.com//a///b.pdf` | `D:\Descargas\sitio.com\a\b.pdf` | RN-008 f |
| 22 | `https://corto.com/x` → redirige a `https://cdn.com/f/real.pdf` (no sugiere; `application/pdf`) | `D:\Descargas\corto.com\x.pdf` | RN-008 a, RN-010 (2) |
| 23 | `https://[::1]:8443/a.pdf` | Interna: requiere confirmación. Si se confirma: `D:\Descargas\[__1]_8443\a.pdf` | RN-017, RN-014 b |
| 24 | `https://bogotá.com/a.pdf` | Corregida (codificada) → `D:\Descargas\xn--bogot-1qa.com\a.pdf` | RN-001 (8), RN-008 b |
| 25 | `https://sitio.com/docs/a.pdf` con `D:\Descargas\sitio.com\docs` existente como **archivo** | Fallida F-27 | RN-012 c |
| 26 | `https://sitio.com/x/a.pdf` con `D:\Descargas\sitio.com\x` existente como unión de carpetas (apunte a donde apunte) | Fallida F-24; no se escribe nada | RN-013 b |
| 27 | `https://2130706433/a.pdf` (127.0.0.1 en decimal) | Interna por comprobación léxica: requiere confirmación | RN-017 a |
| 28 | `https://169.254.169.254/latest/meta-data` | Inválida I-06 | RN-004, RN-017 a |
| 29 | `www.sitio.com/ir?u=http://x.com/a.pdf` (no sugiere; `application/pdf`) | **No es I-01**: el texto antes de `://` no cumple el patrón de esquema. Corregida → `https://www.sitio.com/ir?u=http://x.com/a.pdf` → `D:\Descargas\www.sitio.com\ir.pdf` | RN-001 (2), (5), RN-010 (2) |
| 30 | `sitio.com:8080/a.pdf` | Corregida → `https://sitio.com:8080/a.pdf` → `D:\Descargas\sitio.com_8080\a.pdf` | RN-001 (5), RN-008 c |
| 31 | `https://sitio.com/con.tar.gz` | `D:\Descargas\sitio.com\con_.tar.gz` | RN-015 |
| 32 | `https://nul.com/a.pdf` | `D:\Descargas\nul_.com\a.pdf` | RN-008 g, RN-015 |
| 33 | `https://sitio.com/con%20.txt` | `D:\Descargas\sitio.com\con_ .txt` | RN-015 |
| 34 | `https://sitio.com/CONIN$/x.txt` | `D:\Descargas\sitio.com\CONIN$_\x.txt` | RN-015 |
| 35 | `https://sitio.com\@127.0.0.1/a.pdf` | Inválida I-03 (ambigua: `\` en la autoridad) | RN-001a |
| 36 | `https://sitio.com#@127.0.0.1/a.pdf` | Inválida I-03 (ambigua: `#` seguido de `@` en la autoridad) | RN-001a |
| 37 | `https://sitio.com/a%2fb/c.pdf` | `D:\Descargas\sitio.com\a_b\c.pdf` (la `/` decodificada es un carácter, no un separador) | RN-011, RN-014 b |
| 38 | `https://sitio.com/a%00b.pdf` | `D:\Descargas\sitio.com\a_b.pdf` | RN-014 b |
| 39 | `https://sitio.com/%252e%252e/x.pdf` | `D:\Descargas\sitio.com\%2e%2e\x.pdf` (se decodifica una sola vez) | RN-011 |
| 40 | `https://sitio.com/a/b/..` (no sugiere; `text/html`) | `D:\Descargas\sitio.com\a\b\index.html` (sin aviso A-2 porque termina en `.html`) | RN-008 f, RN-010 (3) |
| 41 | `https://sitio.com/Informe Final/año 2024.pdf` (sin codificar) | Corregida (codificada) → `D:\Descargas\sitio.com\Informe Final\año 2024.pdf` | RN-001 (8), RN-011 |
| 42 | En el lote, en cualquier orden: `https://sitio.com/docs` (no sugiere; tipo desconocido) y `https://sitio.com/docs/x.pdf` | `D:\Descargas\sitio.com\docs (1)` y `D:\Descargas\sitio.com\docs\x.pdf` | RN-012 b |
| 43 | `https://sitio.com/<nombre de 300 caracteres>.pdf` | Fallida F-28 | RN-016 a |
| 44 | `https://localhost./a.pdf` | Interna (se quita el punto final): requiere confirmación | RN-001a, RN-017 a |
| 45 | `https://[2002:7f00:1::]/a.pdf` | Inválida I-06 (dirección bloqueada) | RN-017 a, glosario 2.2 |
| 46 | `https://sitio.com/descarga` (servidor responde con éxito, tipo `text/html`, no sugiere) | `D:\Descargas\sitio.com\descarga.html` (S-48) | RN-010 (2) |
| 47 | `https://sitio.com/informe.pdf` (servidor responde con éxito y tipo `text/html`) | `D:\Descargas\sitio.com\informe.pdf` + aviso A-2 | RN-021 |
| 48 | `https://archivos.miempresa.com/a.pdf`, que resuelve a `10.0.0.5` (no detectable en la validación previa) | Fallida F-30 en el motor; "Permitir y reintentar" autoriza `archivos.miempresa.com` para todo el lote | RN-005, RN-017 b, d |
| 49 | `https://sitio.com?email=a@b.com` (no sugiere; tipo desconocido) | **Válida**: la autoridad termina en `?`, el dominio es `sitio.com` y no hay credenciales → `D:\Descargas\sitio.com\index` | RN-001a (b), RN-010 (4) |
| 50 | `https://a.com/x.pdf https://b.com/y.pdf` (en una sola línea) | Inválida I-09; se detecta antes de codificar los espacios | RN-001 (4), RN-004 |
| 51 | `https://sitio.com/a.pdf?ruta=c:\temp` | Corregida (codificada) → `https://sitio.com/a.pdf?ruta=c:%5Ctemp` → `D:\Descargas\sitio.com\a.pdf` (la `\` de los parámetros no afecta a la ruta) | RN-001 (8), RN-008 e, RN-009 |
| 52 | `https://sitio.com?q=a\b` | Inválida I-03 (ambigua: `\` en la autoridad cruda). Rechazo conservador aceptado | RN-001a (a) |
| 53 | `https://publico.com/f`, que redirige a `https://x.corp/f.pdf` (no sugiere; `application/pdf`) | Fallida F-30 al llegar a `x.corp`. "Permitir y reintentar" autoriza **`x.corp`**, no `publico.com`. Si se completa: `D:\Descargas\publico.com\f.pdf` | RN-008 a, RN-017 c, d |
| 54 | Carpeta destino elegida: `D:\Atajo`, que es una unión que apunta a `C:\Windows\Temp` | Carpeta destino inválida: no se puede iniciar | RN-007 c, AB-15 |
| 55 | `https://sitio .com/a.pdf` | Inválida I-03 (dominio con espacio; se comprueba antes de codificar) | RN-001 (6) |

## Anexo 2. Catálogo cerrado de fallos (RN-026)

**Numeración por clase**: F-01 a F-09 son temporales, F-10 a F-29 permanentes y F-30 a F-39 recuperables; F-99 es el error inesperado. Los números libres de cada tramo quedan reservados para fallos futuros de esa clase.

| Código | Motivo visible | Clase | Cuándo ocurre (incluidos los códigos de respuesta del servidor) |
|---|---|---|---|
| F-01 | No se pudo conectar | Temporal | Sin red, conexión rechazada o reiniciada al conectar |
| F-02 | Tiempo de conexión agotado | Temporal | No se conecta en 15 s (RN-028 a) |
| F-03 | El servidor dejó de enviar datos | Temporal | 30 s sin datos (RN-028 b) |
| F-04 | Velocidad demasiado baja | Temporal | < 1 KB/s durante 60 s (RN-028 c) |
| F-05 | Conexión interrumpida | Temporal | Se corta antes de completar, o llegan menos bytes de los informados |
| F-06 | Servidor ocupado | Temporal | 429, 503. Si pide esperar más de 60 s, falla sin más reintentos y conserva F-06 |
| F-07 | Error temporal del servidor | Temporal | 408, 500, 502, 504 |
| F-08 | No se pudo resolver el nombre (temporal) | Temporal | El servicio de nombres no responde |
| F-10 | El dominio no existe | Permanente | El nombre no existe |
| F-11 | Archivo no encontrado | Permanente | 404, 410 |
| F-12 | Acceso prohibido | Permanente | 403, 451 |
| F-13 | Requiere autenticación | Permanente | 401 |
| F-14 | El proxy requiere autenticación (no soportado) | Permanente | 407 |
| F-15 | Solicitud rechazada por el servidor | Permanente | Cualquier otro 4xx |
| F-16 | Error del servidor | Permanente | 501, 505 y cualquier otro 5xx no listado en F-06 ni F-07 |
| F-17 | Respuesta inesperada del servidor | Permanente | Respuesta distinta de 200 que no es redirección ni error (incluida 204), o redirección sin destino |
| F-18 | Certificado de seguridad no válido | Permanente | No confiable, vencido, revocado o de otro nombre |
| F-19 | Conexión insegura (cifrado no permitido) | Permanente | TLS inferior a 1.2 |
| F-20 | Redirección insegura (de HTTPS a HTTP) | Permanente | RN-018 e |
| F-21 | Demasiadas redirecciones | Permanente | Más de 10 |
| F-22 | Redirección a protocolo no soportado | Permanente | RN-018 f |
| F-23 | Dirección no permitida | Permanente | Resuelve o redirige a una dirección bloqueada |
| F-24 | Ruta no permitida | Permanente | RN-013 |
| F-25 | Ruta demasiado larga | Permanente | RN-016 b |
| F-26 | Supera el tamaño máximo por archivo | Permanente | RN-024 |
| F-27 | Conflicto de ruta: existe un archivo con el nombre de una carpeta necesaria | Permanente | RN-012 c |
| F-28 | Nombre de carpeta o archivo demasiado largo (más de 255 caracteres) | Permanente | RN-016 a |
| F-30 | Dirección interna no confirmada | Recuperable | RN-017 d. Acción: "Permitir y reintentar" |
| F-31 | Espacio en disco insuficiente | Recuperable | RN-023. Acción: liberar espacio y "Reintentar fallidas" |
| F-32 | No se puede escribir en la carpeta destino | Recuperable | Sin permiso, archivo bloqueado o unidad desconectada. Acción: corregir y "Reintentar fallidas" |
| F-33 | Se superó la duración máxima de descarga | Recuperable | RN-028 d. Acción: ampliar la duración en los ajustes si se desea y "Reintentar fallidas" |
| F-99 | Error inesperado | Permanente | Cualquier situación no prevista en este catálogo. "Reintentar fallidas" lo incluye. En el registro solo se anota el identificador del tipo de error (RN-037 c) |

## Anexo 3. Ejemplo exacto del archivo exportado (RN-035)

Nombre propuesto: `no-completadas-20261107-1542.txt`

```
# Descargador - URLs no completadas
# Exportado: 2026-11-07 15:42
# Carpeta destino del lote: D:\Descargas
# Fallidas: 2 | Canceladas: 1 | Pendientes o en curso: 1
# ATENCION: contiene URLs completas que pueden incluir tokens. No lo comparta.
https://sitio.com/docs/2024/informe.pdf?token=abc123
https://otro.com/img/foto.jpg
https://www.sitio.com/a.pdf
https://cdn.ejemplo.org/files/datos.zip
```

Al cargarlo como archivo masivo, las líneas con `#` se ignoran (RN-002) y quedan 4 URLs.

## Anexo 4. Trazabilidad

RNF-14 (compatibilidad con Windows) aplica a todas las reglas.

| Regla | Épica | Casos de abuso (PRD 8.3) | RNF (PRD 7) |
|---|---|---|---|
| RN-001 | EP-01 | AB-01, AB-06, AB-08, AB-20 | RNF-04 |
| RN-001a | EP-01, EP-03 | AB-01, AB-02, AB-10, AB-14, AB-20 | — |
| RN-002 | EP-01 | AB-06 | RNF-04 |
| RN-003 | EP-01 | AB-06 | RNF-01, RNF-04 |
| RN-004 | EP-01 | AB-08, AB-10, AB-14, AB-20 | RNF-04 |
| RN-005 | EP-01 | AB-02 | RNF-04 |
| RN-006 | EP-01 | — | RNF-04 |
| RN-007 | EP-02 | AB-15 | — |
| RN-008 | EP-02 | AB-01, AB-20 | — |
| RN-009 | EP-02 | — | — |
| RN-010 | EP-02 | AB-01, AB-12 | — |
| RN-011 | EP-02 | AB-01 | — |
| RN-012 | EP-02 | — | — |
| RN-013 | EP-02 | AB-01, AB-15 | — |
| RN-014 | EP-02 | AB-03, AB-12, AB-16 | — |
| RN-015 | EP-02 | AB-03, AB-12 | — |
| RN-016 | EP-02 | AB-04 | RNF-12 |
| RN-017 | EP-01, EP-03 | AB-02, AB-13, AB-14 | — |
| RN-018 | EP-03 | AB-08, AB-09, AB-11 | — |
| RN-019 | EP-01, EP-03 | AB-10, AB-17 | — |
| RN-020 | EP-03 | AB-02, AB-13, AB-21 | — |
| RN-021 | EP-04 | AB-07, AB-12, AB-16 | — |
| RN-022 | EP-03 | AB-07 | — |
| RN-023 | EP-03 | AB-05 | — |
| RN-024 | EP-03 | AB-05 | — |
| RN-025 | EP-03 | — | RNF-01, RNF-02, RNF-06, RNF-07, RNF-08 |
| RN-026 | EP-03 | — | RNF-10 |
| RN-027 | EP-03 | AB-02 | RNF-10 |
| RN-028 | EP-03 | AB-05 | RNF-10 |
| RN-029 | EP-04 | — | — |
| RN-030 | EP-04 | — | RNF-09 |
| RN-031 | EP-03 | — | RNF-05, RNF-13 |
| RN-032 | Transversal | — | RNF-05 |
| RN-033 | EP-04, EP-05 | — | RNF-03 |
| RN-034 | EP-04 | AB-07 | — |
| RN-035 | EP-04 | AB-18 | — |
| RN-036 | EP-04, Transversal | AB-18 | — |
| RN-037 | Transversal | AB-18 | — |
| RN-038 | EP-05 | — | RNF-11 |
| RN-039 | Transversal | AB-19 | RNF-15 |
| RN-040 | EP-01 | AB-06 | — |
| RN-041 | EP-04 | AB-18 | — |
| RN-042 | EP-05 | — | RNF-11 |
| RN-043 | EP-05 | — | RNF-05 |
