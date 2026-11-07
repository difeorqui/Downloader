# Spec 001 — De la URL a una ruta segura

- **Estado**: Aprobada
- **Versión**: 0.3 (C1: enmascarado según la autoridad cruda; C2: UTF-32 antes que UTF-16; C3: extensión según Windows para A-1)
- **Fecha**: 2026-11-07
- **Autor**: analista de requerimientos
- **Épicas**: EP-01 Entrada de URLs y EP-02 Organización en carpetas (en ambos casos, la parte de dominio)
- **Documentos base**:
  - `docs/00-producto/prd.md` v0.7 (Aprobado)
  - `docs/01-requerimientos/reglas-negocio.md` v0.7: reglas y anexos 1, 2 y 4
  - `docs/01-requerimientos/glosario.md` v0.6: listas normativas 2.1 a 2.5
  - `docs/00-producto/roadmap-specs.md` v0.2
- **Depende de**: ninguna spec. **La necesitan**: 002, 003 y 004.
- **Historial**:
  - 0.1: primer borrador.
  - 0.2: incorpora la revisión de `revisor-spec` (6 hallazgos bloqueantes y 13 importantes). Las propuestas del revisor se adoptan como supuestos S-001-07 a S-001-14.

> Esta spec **no repite las reglas**: las cita por su ID. Si la spec y una regla parecen contradecirse, manda la regla y la diferencia es un defecto de esta spec.

---

## 1. Qué y por qué

### Qué
Esta spec define la capacidad que decide, de forma **determinista** y **sin acceder a la red ni al disco**, a partir de lo que el usuario escribe o carga y de los datos que se conocen de cada descarga:
1. Cómo se interpreta cada URL: si es válida, corregida, duplicada, interna o bloqueada según su forma escrita.
2. Si el contenido de un archivo masivo es válido.
3. En qué **ruta exacta** queda cada archivo, o con qué fallo se rechaza.
4. Qué avisos A-1 y A-2 corresponden.
5. Cómo se muestra una URL de forma enmascarada.
6. Si una carpeta destino es aceptable, dada su ruta real.

### Por qué
- Es el corazón de la necesidad del usuario: "las subcarpetas... se generarían por medio de la estructura de la URL".
- Concentra el mayor riesgo de seguridad: salto de directorio, nombres reservados, caracteres engañosos y URLs ambiguas.
- Se puede probar por completo sin red, sin disco y sin interfaz. Es la base fiable de las specs 002 y 004.

### Entradas y salidas

| Entrada | Descripción |
|---|---|
| Texto del campo individual | Lo que el usuario escribió o pegó. |
| Archivo masivo | Nombre (para la extensión) y contenido en bytes. La lectura la hace otra spec. |
| Carpeta destino | La ruta elegida y su **ruta real** ya resuelta. Las da la spec 002. |
| Ubicaciones del sistema | Rutas reales de la carpeta de Windows, las carpetas de Archivos de programa (64 y 32 bits), la carpeta de datos de programas, la carpeta de datos de la aplicación y la unidad donde está Windows. Las da la spec 002 (RN-007 c). |
| Datos de la respuesta del servidor (opcional) | Nombre sugerido (formas simple e internacional), tipo de contenido y URL final. |
| Estado conocido del disco | Para cada ruta: qué entradas existen bajo la carpeta destino y de qué clase son (archivo, carpeta, enlace o unión). Lo da la spec 002. |
| Rutas largas | Si Windows las tiene habilitadas o no (RN-016 b). |
| Orden de llamadas | Orden en que se piden las rutas de los elementos. Es el **orden de reserva** de RN-012 a. La spec 002 fija ese orden al decidir cada nombre cuando llega la respuesta (RN-012 d). |

| Salida | Descripción |
|---|---|
| Resultado de validación | Lo que exige RN-005, con los invariantes de CA-001-35. Incluye la URL procesada de cada elemento y el conjunto de carpetas que necesita el lote (RN-012 b). |
| Rechazo del archivo masivo | Mensaje exacto (S-001-10). |
| Ruta resultante | Ruta completa, o un fallo F-24, F-25, F-27 o F-28. |
| Avisos | A-1 y/o A-2. |
| URL enmascarada | Según RN-036 y S-001-08. |
| Validez de la carpeta destino | Válida o inválida (RN-007 c). |

## 2. Historias de usuario (priorizadas)

| ID | Prioridad | Historia |
|---|---|---|
| HU-01 | P1 | Como usuario, quiero pegar una URL aunque le falte `https://` o tenga espacios o tildes, para no tener que corregirla a mano. |
| HU-02 | P1 | Como usuario, quiero saber antes de empezar qué URLs de mi lista son válidas, corregidas, repetidas o inválidas, y por qué, para corregir la lista sin sorpresas. |
| HU-03 | P1 | Como usuario, quiero que cada archivo quede en una carpeta que refleje el sitio y la ruta de su URL, para encontrarlo sin buscar. |
| HU-04 | P1 | Como usuario, quiero la garantía de que ninguna URL ni nada que diga el servidor pueda hacer que se escriba fuera de mi carpeta, ni con nombres que Windows no admite, para no dañar mi equipo. |
| HU-05 | P2 | Como usuario, quiero que el archivo reciba el nombre del servidor o, si no lo hay, uno razonable, para reconocerlo. |
| HU-06 | P2 | Como usuario, quiero que nunca se sobrescriba nada, para no perder información. |
| HU-07 | P2 | Como usuario, quiero saber antes de iniciar si una URL apunta a mi red interna, y que las direcciones prohibidas se rechacen, para no exponer servicios internos. |
| HU-08 | P3 | Como usuario, quiero un aviso si un archivo es ejecutable o con macros, o si recibí una página web en lugar del archivo. |
| HU-09 | P3 | Como usuario, quiero que las URLs que veo no muestren tokens, para que una captura de pantalla no filtre accesos. |
| HU-10 | P2 | Como usuario, quiero que no se me permita elegir una carpeta del sistema como destino, tampoco a través de un enlace, para no dañar Windows. |

## 3. Criterios de aceptación

Convención: **CA-001-NN**. Los ejemplos del anexo 1 se tratan en la sección 3.13.

### 3.1 Interpretación de una URL (HU-01) — RN-001, RN-001a

| ID | Dado | Cuando | Entonces |
|---|---|---|---|
| CA-001-01 | `www.sitio.com/a.pdf` | Se interpreta | `https://www.sitio.com/a.pdf`, corregida (sin esquema) (RN-001 paso 5) |
| CA-001-02 | `ftp://x.com/a` | Se interpreta | I-01 (RN-001 paso 2) |
| CA-001-03 | `javascript:`, `vbscript:`, `data:`, `file:`, `blob:`, `about:` y `mailto:`, en minúsculas y en mayúsculas | Se interpreta | I-01 (RN-001 paso 3) |
| CA-001-04 | `\\servidor\a`, `C:\a` y `c:/a` | Se interpreta | I-02 (RN-001 paso 1) |
| CA-001-05 | `HTTPS://Sitio.COM/a.pdf` | Se interpreta | Válida, dominio `sitio.com`, **sin** marca de corregida (RN-001 paso 8, S-001-14) |
| CA-001-06 | Un espacio interior seguido de `http://` o `https://` | Se interpreta | I-09, detectado antes de codificar (RN-001 paso 4) |
| CA-001-07 | Un dominio con un espacio | Se interpreta | I-03, detectado antes de codificar (RN-001 paso 6) |
| CA-001-08 | Una autoridad cruda con `\`, o con `#` seguido de `@` | Se interpreta | I-03 (RN-001a a) |
| CA-001-09 | Credenciales en la autoridad, cortada en el primero de `/`, `?` o `#` | Se interpreta | I-05 (RN-001a b) |
| CA-001-10 | Puertos `0`, `65536` y `99999` / puertos `1` y `65535` | Se interpreta | I-07 / válida |
| CA-001-11 | Una URL que, ya corregida y codificada, mide 2 048 / 2 049 caracteres | Se interpreta | Válida / I-04 |
| CA-001-12 | En el campo individual: dos líneas con contenido / una línea con contenido rodeada de líneas vacías | Se interpreta | I-08, sin repetir el texto en la salida (S-001-08) / se acepta |
| CA-001-13 | `localhost.` / `intranet.` | Se interpreta | Se usa sin el punto final (RN-001a) |
| CA-001-14 | `BOGOTÁ.com`, `bogotá.com` y `bogota` + U+0301 (tilde combinada) + `.com` | Se interpreta | Las tres dan `xn--bogot-1qa.com` y quedan corregidas (codificadas) (RN-001 paso 8) |
| CA-001-15 | Cualquier URL válida | Se interpreta dos veces | Estructura idéntica: un solo criterio de interpretación (RN-001a) |
| CA-001-16 | El campo individual vacío o solo con espacios | Se interpreta | No se puede iniciar y no cuenta como inválida |

### 3.2 Codificación automática (HU-01) — RN-001 paso 8

| ID | Dado (en la ruta, en los parámetros y en el fragmento, por separado) | Entonces |
|---|---|---|
| CA-001-17 | Cada uno de estos caracteres, uno por caso: espacio, comillas dobles, `<`, `>`, acento grave, `{`, `}`, `\|`, `^` | Se codifican como `%20`, `%22`, `%3C`, `%3E`, `%60`, `%7B`, `%7D`, `%7C` y `%5E`, y la URL queda corregida (codificada) |
| CA-001-18 | `ñ`, `á` y un emoji | Se codifican en porcentaje sobre UTF-8 (`ñ` → `%C3%B1`) |
| CA-001-19 | `\` en los parámetros o el fragmento / `\` en la ruta | `%5C` / se convierte en `/` (RN-001 paso 7) |
| CA-001-20 | Una secuencia ya codificada (`%20`, `%2F`, `%25`) | No se vuelve a codificar, y no cuenta como corregida |
| CA-001-21 | Un `%` sin dos dígitos hexadecimales detrás (`a%zz`, `a%`, `a%2`) | Se codifica como `%25` (`a%25zz`, `a%25`, `a%252`) y la URL queda corregida (S-001-11) |
| CA-001-22 | Una URL solo con caracteres permitidos | No se modifica ni cuenta como corregida |

### 3.3 Archivo masivo (HU-02) — RN-002, RN-003

| ID | Dado | Cuando | Entonces |
|---|---|---|---|
| CA-001-23 | El mismo contenido con BOM y sin BOM | Se valida | Mismo resultado |
| CA-001-24 | CRLF, LF y CR sueltos mezclados | Se valida | Cada uno es un fin de línea; los números de línea cuentan así (S-001-10) |
| CA-001-25 | Líneas vacías, líneas con solo espacios o tabulaciones, y comentarios | Se valida | Se ignoran y no cuentan para el límite |
| CA-001-26 | 10 000 / 10 001 líneas con contenido, incluidas duplicadas e inválidas | Se valida | Se acepta / mensaje exacto de conteo (S-001-10) |
| CA-001-27 | 5 242 880 / 5 242 881 bytes | Se valida | Se acepta / mensaje exacto de tamaño (S-001-01, S-001-10) |
| CA-001-28 | Nombres de archivo `a.txt`, `a.TXT` y `a.csv.txt` / `a.csv` / `a`, `a.txt.exe`, `a.docx` | Se valida | Se aceptan / mensaje de `.csv` / "Solo se admiten archivos .txt" (RN-003 d; extensión según S-001-12) |
| CA-001-29 | Marca inicial de UTF-16 (LE o BE), o ≥ 10 % de bytes nulos en los primeros 4 KB en un archivo que no es UTF-32 | Se valida | Mensaje exacto de RN-003 e (S-001-10) |
| CA-001-30 | Marca inicial de UTF-32, LE (FF FE 00 00) y BE (00 00 FE FF), aunque tenga muchos bytes nulos | Se valida | Mensaje de RN-003 f indicando la línea 1, **no** el de UTF-16: la marca de UTF-32 se comprueba antes (S-001-10) |
| CA-001-31 | Bytes no UTF-8 en la línea 7, también si esa línea es un comentario: secuencias sobrelargas, sustitutos (U+D800–U+DFFF), valores mayores que U+10FFFF o secuencias truncadas | Se valida | Mensaje de RN-003 f con "línea 7" (S-001-10) |
| CA-001-32 | Solo comentarios y líneas vacías / 0 bytes | Se valida | "El archivo no contiene URLs" |
| CA-001-33 | Un único byte nulo dentro de una línea, por debajo del umbral de CA-001-29 | Se valida | El archivo no se rechaza; esa línea es I-03 |
| CA-001-34 | Un archivo `.csv` en UTF-16, de más de 5 MB y con más de 10 000 líneas | Se valida | Solo el mensaje de `.csv`: el primer fallo según el orden de S-001-07 |

### 3.4 Resumen y duplicados (HU-02) — RN-005, RN-006

| ID | Dado | Cuando | Entonces |
|---|---|---|---|
| CA-001-35 | Cualquier lote | Se valida | Se cumplen los invariantes de S-001-09: válidas (únicas) + duplicadas + inválidas = líneas con contenido; internas ⊆ válidas; corregidas ⊆ válidas; total de líneas leídas = todas las líneas del archivo |
| CA-001-36 | Tres líneas: `https://sitio.com/a.pdf`, `https://sitio.com/a.pdf#parte2` y `https://SITIO.com/a.pdf` | Se valida | 1 elemento (el de la línea 1) y 2 duplicadas (RN-006) |
| CA-001-37 | `https://a.com:443/x` y `https://a.com/x` / `http://a.com:443/x` y `http://a.com/x` | Se valida | Duplicadas / distintas (443 no es el puerto estándar de http) |
| CA-001-38 | `HTTPS://a.com/x` y `https://a.com/x`; `https://bogotá.com/x` y `https://xn--bogot-1qa.com/x` | Se valida | Duplicadas en ambos casos |
| CA-001-39 | `https://sitio.com/x/A.pdf` y `https://sitio.com/x/a.pdf` | Se valida y se calculan las rutas | **Dos** elementos: la ruta no se compara sin distinguir mayúsculas en RN-006. El segundo recibe sufijo por RN-012 (ejemplo 19) |
| CA-001-40 | `a.pdf?v=1` y `a.pdf?v=2`; `https://sitio.com/a b.pdf` y `https://sitio.com/a%20b.pdf` | Se valida | Distintas / duplicadas (se comparan después de codificar) |
| CA-001-41 | Una URL sin esquema que además se codifica | Se valida | Cuenta una vez en "corregidas" y aparece en los dos desgloses (S-001-09) |
| CA-001-42 | Tres elementos de `intranet` y uno de `10.0.0.1` | Se valida | Dominios internos: `intranet` (3) y `10.0.0.1` (1). La lista no repite dominios e indica cuántos elementos tiene cada uno (S-001-09) |
| CA-001-43 | Un lote sin válidas / cualquier lote | Se valida | No se puede iniciar / 0 accesos a la red y al disco |

### 3.5 Prioridad entre fallos simultáneos — S-001-07

| ID | Dado | Entonces |
|---|---|---|
| CA-001-44 | `https://169.254.169.254:99999/` | I-07, no I-06 |
| CA-001-45 | `https://u:p@169.254.169.254/` | I-05 |
| CA-001-46 | `ftp://a.com/x https://b.com/y` | I-01 (el paso 2 va antes que el paso 4) |
| CA-001-47 | `\\srv\a https://b.com/y` | I-02 |
| CA-001-48 | Una URL de más de 2 048 caracteres con puerto `0` | I-04 |
| CA-001-49 | `https://sitio.com\@u:p@x.com/` | I-03 (la ambigüedad va antes que las credenciales) |
| CA-001-50 | Un nombre de 300 caracteres que además deja la ruta por encima de 259 (ejemplo 43) | F-28 |
| CA-001-51 | Un nombre de 300 caracteres bajo una unión intermedia | F-28 |
| CA-001-52 | Una unión intermedia y, más abajo, un archivo con el nombre de una carpeta necesaria | F-24 |
| CA-001-53 | Un archivo con el nombre de una carpeta necesaria y la ruta por encima del límite | F-27 |

### 3.6 Ruta resultante (HU-03) — RN-008, RN-009, RN-011

| ID | Dado | Entonces |
|---|---|---|
| CA-001-54 | Dominio, puerto no estándar, segmentos, parámetros y fragmento | Carpeta destino \ dominio (minúsculas, forma ASCII, `_puerto`) \ segmentos \ nombre; ni los parámetros ni el fragmento intervienen |
| CA-001-55 | Una URL final distinta de la original | Las carpetas salen de la URL original (RN-008 a) |
| CA-001-56 | Segmentos con UTF-8 válido / inválido | Se decodifican una vez / se conservan con sus `%` |
| CA-001-57 | Cada uno de estos segmentos, en posición intermedia y como último segmento: `.`, `%2e`, `%2E`, `..`, `.%2e`, `.%2E`, `%2e.`, `%2E.`, `%2e%2e`, `%2E%2E`, `%2e%2E`, `%2E%2e` | Se descartan sin resolverse. Si es el último, la URL se trata como sin nombre (RN-008 f) |
| CA-001-58 | Segmentos `.. ` (con espacio final), `...`, `%20..` y `..%20` | No son `.` ni `..`. Al sanearlos quedan vacíos y se convierten en `_` como carpeta; como último segmento, el nombre pasa al siguiente paso de RN-010 (RN-014 c, d) |
| CA-001-59 | Segmento `%2e%2e%2f` | Se decodifica como `../`, un solo nombre, que queda `.._` |
| CA-001-60 | `https://sitio.com/C:/Windows/x.dll` | `D:\Descargas\sitio.com\C_\Windows\x.dll` + A-1. Una ruta absoluta dentro de la URL no sale del destino |
| CA-001-61 | `https://sitio.com//servidor/recurso/a.pdf` | `D:\Descargas\sitio.com\servidor\recurso\a.pdf` (los segmentos vacíos se ignoran) |

### 3.7 Seguridad del nombre y de la ruta (HU-04) — RN-013, RN-014, RN-015

| ID | Dado | Entonces |
|---|---|---|
| CA-001-62 | Cualquier entrada, incluido el conjunto de RNF-001-05 | El resultado es una ruta que cumple **todos** los invariantes de S-001-13, o un fallo F-24, F-25, F-27 o F-28. Nunca otra cosa |
| CA-001-63 | Los caracteres invisibles de la lista 2.4 | Se eliminan |
| CA-001-64 | Cada uno de `< > : " / \ \| ? *` y U+0000–U+001F | Se reemplaza por `_` |
| CA-001-65 | Un nombre terminado en puntos o espacios / un nombre que queda vacío | Se eliminan esos puntos y espacios / `_` en carpetas y siguiente paso de RN-010 en nombres de archivo |
| CA-001-66 | Cada nombre de la lista 2.5, en minúsculas y mayúsculas: solo, con una extensión, con varias extensiones y con espacios antes del primer punto. Como segmento, como nombre de archivo y como primera etiqueta del dominio | Se inserta `_` justo después del nombre reservado |
| CA-001-67 | `CONSOLA.txt`, `micon.txt`, `COM10.txt` y `.htaccess` | No se modifican |
| CA-001-68 | La carpeta destino elegida es un enlace o una unión | Se permite; su ruta real decide la validez (CA-001-111) |
| CA-001-69 | Una carpeta intermedia, dentro del destino, que ya existe como enlace o unión, apunte a donde apunte | F-24 (RN-013 b) |

### 3.8 Longitudes (HU-04) — RN-016

Se usa siempre la carpeta destino `D:\Descargas` (12 caracteres, incluidos la unidad y la `\`). Así, la carpeta que contiene el archivo, `D:\Descargas\sitio.com\<s>`, mide **23 + s** caracteres, donde s es la longitud del segmento. La ruta final mide carpeta + 1 + nombre. La del temporal mide carpeta + 1 + 53. Se compara siempre la **mayor** de las dos. Las longitudes se cuentan según S-001-02.

| ID | Rutas largas | Construcción | Ruta que manda | Entonces |
|---|---|---|---|---|
| CA-001-70 | No | s = 175 (carpeta de 198) y nombre de 60 caracteres (≥ 53) | Final: 259 | Se acepta |
| CA-001-71 | No | s = 176 (carpeta de 199) y nombre de 60 | Final: 260 | F-25 |
| CA-001-72 | No | s = 182 (carpeta de 205) y nombre `a.pdf` (< 53) | Temporal: 259 (final: 211) | Se acepta |
| CA-001-73 | No | s = 183 (carpeta de 206) y nombre `a.pdf` | Temporal: 260 (final: 212) | F-25, aunque la ruta final cabría |
| CA-001-74 | No | s = 175 y nombre de 60 que, por colisión, necesita ` (1)` (nombre de 64) | Final con sufijo: 263 | F-25 |
| CA-001-75 | No | Nombre de exactamente 53 y carpeta de 205 / de 206 | Las dos son iguales: 259 / 260 | Se acepta / F-25 |
| CA-001-76 | Sí | Destino corto y un nombre de 255 / de 256 caracteres, ya saneado y con sufijo | — | Se acepta / F-28 |
| CA-001-77 | Sí | Un segmento de carpeta de 255 / de 256 | — | Se acepta / F-28 |
| CA-001-78 | Sí | Segmentos de ≤ 255 que dan una ruta final de 32 000 / de 32 001, con un nombre ≥ 53 | Final | Se acepta / F-25 |
| CA-001-79 | Sí | Una carpeta de 31 947 con nombre `a.pdf` (< 53) / de 31 946 | Temporal: 32 001 / 32 000 | F-25 / se acepta |

### 3.9 Nombre de archivo y extensión (HU-05) — RN-010, RN-012

| ID | Dado | Entonces |
|---|---|---|
| CA-001-80 | El servidor sugiere el nombre en forma simple y en forma internacional | Se usa la internacional |
| CA-001-81 | El nombre sugerido contiene `/` o `\` | Se usa lo que va después de la última, saneado y sin decodificarlo otra vez |
| CA-001-82 | Sin nombre sugerido, un último segmento sin extensión, y el tipo en la tabla / fuera de ella | Se añade la extensión de la tabla / se deja sin extensión |
| CA-001-83 | Sin nombre sugerido ni nombre en la URL, y el tipo en la tabla / fuera de ella | `index` + extensión / `index` |
| CA-001-84 | Un nombre sugerido que queda vacío tras sanearlo | Se pasa al siguiente paso de RN-010 |
| CA-001-85 | Tipo `Text/HTML; charset=utf-8` / tipo `application/octet-stream` | `.html` / sin extensión (S-001-06) |
| CA-001-86 | Los nombres `x.`, `.htaccess`, `v1.2`, `a.b.` y `.gitignore`, que necesitan sufijo | `x (1)` (el punto final se quita al sanear), `.htaccess (1)`, `v1 (1).2`, `a (1).b` y `.gitignore (1)`. La extensión se define en S-001-12 |
| CA-001-87 | Un nombre sin extensión que necesita sufijo / `informe.final.pdf` | `docs (1)` / `informe.final (1).pdf` |

### 3.10 Colisiones (HU-06) — RN-012 a–c

| ID | Dado | Entonces |
|---|---|---|
| CA-001-88 | La ruta ya existe en disco como archivo o como carpeta, con otras mayúsculas (S-001-03) | Sufijo ` (1)`, ` (2)`... hasta encontrar uno libre |
| CA-001-89 | Dos elementos con la misma ruta, pedidos en un orden de llamadas dado | El primero de ese orden conserva el nombre y el segundo recibe sufijo. El resultado depende del orden por diseño (RN-012 a) |
| CA-001-90 | Un archivo cuyo nombre coincide con una carpeta que necesita el lote | El archivo recibe sufijo, en cualquier orden de llamadas (RN-012 b) |
| CA-001-91 | Un archivo existente en disco con el nombre de una carpeta necesaria | F-27 |

### 3.11 Direcciones por su forma escrita (HU-07) — RN-017 a

| ID | Dado | Entonces |
|---|---|---|
| CA-001-92 | Para cada nombre y rango de la lista 2.1, la primera, una intermedia y la última dirección | Válida y listada como interna |
| CA-001-93 | Para cada rango de la lista 2.2, los mismos tres puntos | I-06 |
| CA-001-94 | `fd00:ec2::254` | I-06: la bloqueada prevalece |
| CA-001-95 | La semántica clásica de IPv4 (S-001-15): `0x7f.1` → 127.0.0.1; `127.1` → 127.0.0.1; `2130706433` → 127.0.0.1; `0177.0.0.1` → 127.0.0.1; `010.0.0.1` → 8.0.0.1; `4294967295` → 255.255.255.255 | Internas, salvo `010.0.0.1`, que es pública y no se lista, y `4294967295`, que es I-06 |
| CA-001-96 | `4294967296`, `0x100000000`, `1.2.3.256` y `1.2.3.4.5` | I-03: el último segmento es numérico, pero el conjunto no es una IPv4 válida (S-001-15) |
| CA-001-97 | IPv6 de `::ffff:0:0/96` y `64:ff9b::/96` con una IPv4 pública / interna / bloqueada incrustada; también entre corchetes | Pública / interna / I-06 |
| CA-001-98 | `100.128.0.0`, `100.63.255.255`, `172.15.255.255`, `172.32.0.0`, `192.167.255.255`, `192.169.0.0`, `11.0.0.0`, `9.255.255.255`, `126.255.255.255`, `128.0.0.0`, `fbff:ffff:ffff:ffff:ffff:ffff:ffff:ffff` y `fe00::1` | Públicas y no listadas |
| CA-001-99 | Etiquetas completas: `x.local`, `a.localhost`, `local` / `a.notlocal.com`, `ejemplo.corporativo.com`, `foo.localhost.com`, `milan.com` | Internas / públicas. Se compara por etiquetas completas, nunca por partes de una etiqueta |
| CA-001-100 | `archivos.miempresa.com` | Válida y no listada: esta spec no resuelve nombres |

### 3.12 Avisos (HU-08), enmascaramiento (HU-09) y carpeta destino (HU-10)

| ID | Dado | Entonces |
|---|---|---|
| CA-001-101 | Una prueba por cada una de las 50 extensiones de la lista 2.3, en minúsculas y en mayúsculas | A-1 |
| CA-001-102 | `.json`, `.docx`, `.pptx`, `.xlsx`, `.jsx`, `.msixx`, un nombre `exe` sin punto, `informe.exe.pdf` | Sin A-1 |
| CA-001-103 | `.msi`, `.msix`, `factura.pdf.exe`, `a.exe.` (que queda `a.exe` al sanear) y los nombres completos `.exe`, `.bat` y `.lnk` | A-1, según la extensión de Windows (S-001-12) |
| CA-001-103b | `.exe (1)` (nombre `.exe` con sufijo por colisión) y `a (1).exe` | Sin A-1 / A-1: se evalúa el nombre final con su sufijo (S-001-12) |
| CA-001-104 | Un nombre con un carácter invisible que aparenta otra extensión | Se clasifica sobre el nombre ya saneado |
| CA-001-105 | Tipo `text/html` y un nombre que no termina en `.html` ni `.htm` / que sí | A-2 / sin A-2 |
| CA-001-106 | Cada par de la tabla de S-001-08 | La salida coincide exactamente |
| CA-001-107 | Una URL inválida de cada categoría, de I-01 a I-09, con el token canario `CANARIO-<valor aleatorio>` en una posición enmascarable | El canario no aparece en ninguna salida visible (en I-08 no se repite el texto) |
| CA-001-108 | Una URL válida con el canario en los parámetros y en el fragmento | El canario solo aparece en la URL procesada (para conectar y exportar), nunca en las salidas visibles |
| CA-001-109 | Una salida visible de más de 200 caracteres | Se recorta a 199 caracteres + `…` (S-001-08) |
| CA-001-110 | Una ruta real igual a una ubicación del sistema, o dentro de ella, o la raíz de la unidad de Windows, con mayúsculas o separadores distintos (`C:\Windows\`, `c:/windows`, `C:\WINDOWS\Temp`) | Inválida |
| CA-001-111 | Una ruta elegida que es un enlace cuya ruta real es una ubicación del sistema / es una carpeta normal | Inválida / válida (RN-007 c, ejemplo 54) |
| CA-001-112 | `C:\WindowsBackup`, `C:\Archivos de programa viejos` y `D:\` | Válidas: se comparan carpetas completas, no prefijos de texto |

### 3.13 Ejemplos del anexo 1 (un caso de prueba por ejemplo)

**CA-001-EJ-NN** (NN = 01 a 55):
- **Dado** la entrada del ejemplo NN del anexo 1, con la carpeta destino `D:\Descargas` y la respuesta del servidor y el estado del disco que indica el ejemplo,
- **cuando** se valida y se calcula la ruta, siguiendo el orden directo del lote,
- **entonces** el resultado coincide **exactamente** con la columna "Resultado".

Alcance de cada ejemplo:
- **Completos en esta spec (49)**: 1 a 21, 24 a 26, 28 a 43, 45 a 47, 49 a 52, 54 y 55. Los que dependen del disco (18, 25, 26 y 54) o del servidor (12 a 16, 40, 46, 47 y 49) reciben esos datos como entrada.
- **Parciales (6)**:

| Ejemplo | Qué se verifica en esta spec | Qué queda para la spec 002 |
|---|---|---|
| 22 | `D:\Descargas\corto.com\x.pdf`, con la URL final y el tipo como entrada | La redirección real |
| 23 | Interna por su forma escrita; ruta `D:\Descargas\[__1]_8443\a.pdf` | Confirmación y conexión |
| 27 | Interna por su forma escrita | Confirmación y conexión |
| 44 | Interna, ya sin el punto final | Confirmación y conexión |
| 48 | Válida y no listada como interna | Resolución, F-30 y autorización |
| 53 | Ruta `D:\Descargas\publico.com\f.pdf` | Redirección, F-30 y autorización de `x.corp` |

## 4. Requisitos no funcionales

Condiciones: el equipo de referencia del PRD (S-17), midiendo la capacidad sin la interfaz.

| ID | Requisito | Método | Criterio de paso |
|---|---|---|---|
| RNF-001-01 | Validar un lote máximo | 20 ejecuciones con 10 000 líneas (≈ 1 MB) y un 5 % de cada categoría | p95 ≤ 1 s (S-001-05) |
| RNF-001-02 | Calcular las rutas de un lote máximo | 20 ejecuciones con 10 000 elementos, un estado del disco simulado de 10 000 entradas y un 10 % de colisiones | p95 ≤ 1 s |
| RNF-001-03 | Peor caso de tamaño | (a) 5 MB con 2 500 URLs de 2 048 caracteres; (b) una sola línea de 5 MB | (a) ≤ 2 s y ≤ 100 MB de memoria privada adicional; (b) I-04 en ≤ 500 ms |
| RNF-001-04 | Determinismo | Cada caso de la sección 3, 100 veces. El ejemplo 42 y CA-001-90 en orden directo, inverso y aleatorio. El ejemplo 19 y CA-001-89 **solo en orden directo**, porque dependen del orden por diseño | 100 % de resultados idénticos |
| RNF-001-05 | Robustez ante entradas hostiles | 100 000 URLs y nombres sugeridos generados con una **semilla fija que queda registrada** en el informe, a partir del conjunto de abuso de la sección 6: combinaciones de `.`/`%2e`, codificación simple y doble, `\`, `@`, `#`, caracteres invisibles, nombres reservados, IP en notaciones alternativas y longitudes límite | 0 errores no controlados. Toda salida cumple CA-001-62, con los invariantes de S-001-13 como oráculo. Cada entrada se procesa en ≤ 100 ms |
| RNF-001-06 | Sin efectos externos | Toda la batería sin red y con el disco en solo lectura | Todo en verde; 0 conexiones y 0 escrituras |
| RNF-001-07 | Cálculo de rutas largas (parte de cálculo de RNF-12) | 20 URLs que generan rutas de 230 a 400 caracteres y nombres de hasta 300, con y sin rutas largas | Cada una da la ruta esperada, F-25 o F-28, según la sección 3.8; ninguna otra salida |

## 5. Seguridad

- **Clasificación de datos**: las URLs son confidencial potencial (PRD 8.1). Esta spec no guarda ni registra nada. La única salida sin enmascarar es la URL procesada de cada elemento, que usan la spec 002 para conectar y la 004 para exportar (RN-035, S-001-04). Toda salida que se muestre va enmascarada (S-001-08).
- **Permisos**: no accede a la red ni al disco (RNF-001-06). Las rutas reales, las ubicaciones del sistema y el estado del disco llegan como datos.
- **Entradas hostiles**: todo se valida con listas cerradas: esquemas, catálogo I-NN, tabla de tipos y listas 2.1 a 2.5.
- **Ley 1581**: no se tratan datos personales propios; las URLs que puedan contenerlos no se registran (RN-037) y se enmascaran.
- **Riesgo residual aceptado**: los tokens dentro de la ruta no se enmascaran (RN-036).

## 6. Casos de abuso aplicables

| AB | Cubierto por |
|---|---|
| AB-01 Salto de directorio y rutas absolutas | CA-001-19, 57 a 62 y 81; ejemplos 4 a 7, 15, 37, 39 y 51 |
| AB-02 Red interna (forma escrita) | CA-001-42 y 92 a 100; ejemplos 23, 27, 44 y 48 |
| AB-03 Nombres reservados y caracteres inválidos | CA-001-63 a 67; ejemplos 8 a 10, 16 y 31 a 34 |
| AB-04 Longitudes (cálculo) | CA-001-50, 70 a 79; RNF-001-07; ejemplo 43 |
| AB-06 Archivo masivo hostil | CA-001-23 a 34; RNF-001-03 |
| AB-08 Esquemas no permitidos (en la entrada) | CA-001-02 a 04 y 46 a 47 |
| AB-10 Credenciales embebidas | CA-001-09, 45 y 106 |
| AB-12 Nombre sugerido malicioso (lógica) | CA-001-80 a 84 y 103; ejemplos 15 y 16 |
| AB-14 Notación alternativa de IP | CA-001-95 a 97; ejemplos 27 y 45 |
| AB-15 Destino del sistema y uniones (lógica) | CA-001-68, 69 y 110 a 112; ejemplos 26 y 54 |
| AB-16 Caracteres invisibles | CA-001-63 y 104; ejemplo 17 |
| AB-18 Filtración de tokens | CA-001-106 a 109 |
| AB-20 Interpretación ambigua | CA-001-08, 15 y 49; ejemplos 29, 35, 36, 49, 50 y 52 |

## 7. Fuera de alcance

- Red, resolución de nombres, redirecciones reales, certificados, proxy, F-30 y su autorización (spec 002).
- Leer el archivo masivo, consultar el disco, resolver rutas reales u obtener las ubicaciones del sistema, crear carpetas y escribir archivos (spec 002).
- Fijar el orden de reserva de nombres (spec 002, RN-012 d).
- Fallos de red, de espacio, de tamaño y de tiempo; reintentos y cancelación (specs 002 y 003).
- Presentación en pantalla y diálogos (spec 004).

## 8. Supuestos

### 8.1 Heredados del PRD (aprobados)
S-18, S-23, S-36, S-37, S-40, S-41, S-45, S-48, S-49, S-53, S-54, S-57, S-59, S-60 y S-61.

### 8.2 Propios de esta spec (a validar al aprobar la spec)

| ID | Supuesto |
|---|---|
| S-001-01 | 5 MB = 5 242 880 bytes; se acepta hasta ese valor, inclusive. |
| S-001-02 | Las longitudes de RN-016 se cuentan como las cuenta Windows: un carácter fuera del plano básico, como un emoji, cuenta como 2. La de RN-003 h se cuenta sobre la URL ya codificada (solo ASCII). |
| S-001-03 | "Sin distinguir mayúsculas" usa la equivalencia de Unicode, como Windows (`Á` = `á`). Se aplica a RN-012, RN-015, la lista 2.3 y la comparación de dominios con las listas 2.1 y 2.2. **No** se aplica a la ruta en RN-006, donde solo el esquema y el dominio se pasan a minúsculas. |
| S-001-04 | La URL procesada que se exporta y la que se usa para conectar son la misma estructura que se valida (RN-001a). |
| S-001-05 | Reparto del tiempo de RNF-04: 1 s para la validación de dominio y el resto para leer y mostrar. |
| S-001-06 | El tipo de contenido se compara con la tabla sin sus parámetros (`; charset=...`) y sin distinguir mayúsculas. |
| S-001-07 | **Prioridad entre fallos simultáneos** (se informa solo el primero). **Archivo masivo**: extensión → tamaño → UTF-32 (mensaje de UTF-8 inválido, línea 1) → UTF-16 → UTF-8 válido → vacío → conteo. **URL**: I-08 (campo individual) → pasos de RN-001 en su orden (I-02 → I-01 → I-09 → en el paso 6: ambigüedad I-03 → I-05 → dominio con espacio I-03 → paso 9 I-03) → I-04 → I-07 → I-06. **Ruta**: F-28 → F-24 → F-27 → F-25. |
| S-001-08 | **Enmascaramiento de salidas visibles.** (a) **URLs válidas**: se aplica RN-036. Un parámetro sin `=` se trata como valor (`?a` → `?***`), un valor vacío también se oculta (`?a=` → `?a=***`), y un `?` o un `#` sin nada detrás se conserva. (b) **URLs inválidas, de cualquier categoría salvo I-08**: primero se separa cada URL detectada (en I-09, por el espacio que precede a `http`). En cada una se define el **tramo de autoridad cruda**: lo que va desde después de `://` hasta la primera `/`, o desde el inicio hasta la primera `/` si no hay `://`, o hasta el final si no hay `/`. Si ese tramo contiene algún `@`, todo lo que va desde el inicio del tramo hasta el **último** `@` del tramo, inclusive, se reemplaza por `***@`, **aunque ese `@` vaya después de un `?` o de un `#`**. Después, en el texto que queda, lo que sigue al primer `?` o `#` se reemplaza por `***`. Si la URL es analizable (I-05, I-06, I-07), sus parámetros se muestran además como en (a). (c) I-08: no se repite el texto. (d) Toda salida visible se recorta a 200 caracteres: 199 + `…`. La tabla de pares exactos está debajo. |
| S-001-09 | **Invariantes del resumen**: "total de líneas leídas" = todas las líneas del archivo según los fines de línea de RN-002 (un fin de línea al final no añade otra línea); líneas con contenido = total − vacías − comentarios; válidas (únicas) + duplicadas + inválidas = líneas con contenido. Las duplicadas se cuentan solo entre las válidas; una inválida repetida cuenta como inválida cada vez. Corregidas ⊆ válidas, y una URL sin esquema y codificada cuenta una vez, pero aparece en los dos desgloses. Internas ⊆ válidas, listadas por dominio sin repetir y con su número de elementos. |
| S-001-10 | **Mensajes exactos del archivo masivo** (miles con punto, decimales con coma). Conteo: "El archivo tiene 10.001 URLs; el máximo es 10.000." Tamaño: "El archivo pesa 5,01 MB (5.252.345 bytes); el máximo es 5 MB (5.242.880 bytes)." Los demás, como en RN-003 d a g. En el mensaje de UTF-8 inválido, la línea se indica como "línea N", contada desde 1 sobre todas las líneas, incluidos vacías, comentarios y CR sueltos. "UTF-8 válido" es estricto: sin secuencias sobrelargas, sin sustitutos, sin valores por encima de U+10FFFF y sin secuencias truncadas; se valida todo el archivo, incluidos los comentarios. **Detección de la codificación, en este orden**: (1) **UTF-32**: marca inicial 00 00 FE FF o FF FE 00 00. Recibe el mensaje de UTF-8 inválido en la línea 1, y **no** se le aplica la comprobación de bytes nulos. (2) **UTF-16**: marca inicial FF FE o FE FF (que no sea de UTF-32), o ≥ 10 % de bytes nulos en los primeros 4 KB, en un archivo que no es UTF-32. (3) **UTF-8 estricto**: todo lo demás. |
| S-001-11 | Un `%` que no va seguido de dos dígitos hexadecimales se codifica como `%25`. |
| S-001-12 | **Extensión** = lo que sigue al **último** punto, siempre que ese punto no sea ni el primer ni el último carácter del nombre. Se usa **solo** en RN-003 d, RN-010 y RN-012 (el sufijo va justo antes de ese punto, o al final si no hay extensión). Es distinto del "texto antes del primer punto" que usa RN-015. **El aviso A-1 usa otra definición, la "extensión según Windows"**: lo que sigue al último punto, aunque ese punto sea el primer carácter (`.exe` → `exe`). Se evalúa sobre el nombre final ya saneado y con su sufijo, si lo lleva (`.exe (1)` → `exe (1)`, que no está en la lista). |
| S-001-13 | **Invariantes de toda ruta resultante** (oráculo de RNF-001-05): (1) empieza exactamente por la carpeta destino seguida de `\`; (2) cada componente posterior no está vacío y es distinto de `.` y de `..`; (3) ningún componente contiene `\ / : * ? " < > \|` ni U+0000–U+001F ni caracteres de la lista 2.4; (4) ningún componente termina en punto o espacio; (5) ningún componente es un nombre reservado según RN-015; (6) ningún componente mide más de 255; (7) la ruta no contiene otra unidad ni un prefijo de red ni de dispositivo; (8) la longitud respeta RN-016 b. |
| S-001-14 | Pasar el esquema o el dominio a minúsculas, o normalizar a NFC, no marca la URL como corregida; solo la conversión a forma ASCII o la codificación de caracteres (RN-001 paso 8, reglas v0.7). |
| S-001-15 | **IPv4 escrita** con la semántica clásica: de 1 a 4 partes separadas por puntos; cada parte en decimal, en octal (con 0 inicial) o en hexadecimal (con `0x`); la última parte ocupa los bytes que faltan. Si la última etiqueta del dominio es numérica (decimal o `0x...`), el dominio entero debe ser una IPv4 válida en esta semántica; si no lo es (desborde, más de 4 partes o una parte fuera de rango), es I-03. |

#### Pares exactos de enmascaramiento (S-001-08)

| # | Entrada | Categoría | Salida visible exacta |
|---|---|---|---|
| 1 | `https://sitio.com/a.pdf?token=abc&v=2#frag` | Válida | `https://sitio.com/a.pdf?token=***&v=***#***` |
| 2 | `https://sitio.com/a.pdf?a` | Válida | `https://sitio.com/a.pdf?***` |
| 3 | `https://sitio.com/a.pdf?a=` | Válida | `https://sitio.com/a.pdf?a=***` |
| 4 | `https://sitio.com/a.pdf?a=1&a=2` | Válida | `https://sitio.com/a.pdf?a=***&a=***` |
| 5 | `https://sitio.com/a.pdf?` | Válida | `https://sitio.com/a.pdf?` |
| 6 | `https://sitio.com/a.pdf#` | Válida | `https://sitio.com/a.pdf#` |
| 7 | `https://sitio.com/a.pdf?a=1&&b=2` | Válida | `https://sitio.com/a.pdf?a=***&&b=***` |
| 8 | `https://sitio.com/a.pdf?a=b=c` | Válida | `https://sitio.com/a.pdf?a=***` |
| 9 | `https://u:p@sitio.com/a` | I-05 | `https://***@sitio.com/a` |
| 10 | `https://169.254.169.254/x?k=1` | I-06 | `https://169.254.169.254/x?k=***` |
| 11 | `https://sitio.com:99999/a?t=1` | I-07 | `https://sitio.com:99999/a?t=***` |
| 12 | `ftp://u:p@x.com/a?t=1` | I-01 | `ftp://***@x.com/a?***` |
| 13 | `mailto:juan@correo.com` | I-01 | `***@correo.com` |
| 14 | `javascript:alert(1)#x` | I-01 | `javascript:alert(1)#***` |
| 15 | `\\servidor\recurso\a.pdf?t=1` | I-02 | `\\servidor\recurso\a.pdf?***` |
| 16 | `C:\temp\a.pdf` | I-02 | `C:\temp\a.pdf` |
| 17 | `https://sitio.com\@127.0.0.1/?t=1` | I-03 | `https://***@127.0.0.1/?***` |
| 18 | `https://sitio.com#@127.0.0.1/a` | I-03 | `https://***@127.0.0.1/a` |
| 18b | `https://user:pa#ss@host/` | I-03 | `https://***@host/` (no queda visible `user:pa`) |
| 18c | `https://user:pass?@evil.com/` | I-07 (puerto `pass`) | `https://***@evil.com/` (no queda visible `user:pass`) |
| 19 | `https://a.com/x.pdf?t=CANARIO https://u:p@b.com/y#k` | I-09 | `https://a.com/x.pdf?*** https://***@b.com/y#***` |
| 20 | `https://sitio.com/` + 2 100 × `a` + `?t=1` | I-04 | `https://sitio.com/` + 181 × `a` + `…` (200 caracteres) |
| 21 | Dos líneas en el campo individual, con tokens | I-08 | "El campo admite una sola URL. Para varias, use un archivo masivo", sin repetir el texto |

## 9. Preguntas abiertas

Ninguna. Las propuestas de la revisión se adoptaron como los supuestos S-001-07 a S-001-15, para validarlos al aprobar la spec.
