---
type: adr
status: accepted
date: 2026-11-07
supersedes:
superseded_by:
spec: 002-motor-descarga-seguro
tags: [network, security, tls, proxy, dependency]
---
# 0004 - Red con urllib3 + truststore; proxy de Windows por WinHTTP (ctypes)

## Contexto
La spec 002 debe cumplir: fijar la IP comprobada (RN-017 b, AB-13), redirecciones manuales con cada salto validado (RN-017 c, RN-018 e–g), certificados del almacén de Windows con revocación y la excepción acotada "revocación no consultable" (RN-018 a–d), TLS ≥ 1.2, nunca credenciales ni cookies (RN-019), proxy de Windows con detección automática y PAC (RN-020), cancelación ≤ 2 s (RN-030) y tiempos de espera (RN-028). Se decide ahora porque condiciona la viabilidad del stack (ADR 0001); el detalle va en el plan de la 002.

Verificado inspeccionando el código de **urllib3 2.8.0** y **truststore 0.10.5** (descargados, no instalados):
- urllib3: `HTTPSConnectionPool(host=<IP>, server_hostname=<dominio>, assert_hostname=<dominio>, ssl_context=...)` permite conectar a una IP concreta con SNI y comprobación de nombre del dominio; la respuesta tiene un método de cierre forzado del socket invocable desde otro hilo (desbloquea una lectura en curso, para RN-030).
- truststore (Windows): valida con `CertGetCertificateChain` + `CertVerifyCertificateChainPolicy` (almacén de Windows, raíces corporativas y descarga de raíces bajo demanda). Con `VERIFY_CRL_CHECK_CHAIN` activa la revocación y, si falla, lanza `SSLCertVerificationError` con `verify_code` = código de Windows. **No** ignora "revocación desconocida": la rechaza.

## Opciones consideradas
- **urllib3 2.x + truststore**: dos dependencias puras y maduras; control total de conexión, redirecciones (`redirect=False`), cabeceras (sin cookies ni `Authorization`). Riesgo: hay que escribir el bucle de redirecciones y el control de tiempos.
- **requests**: API cómoda. Riesgos: gestiona cookies y `.netrc` por defecto (RN-019), sigue redirecciones y lee proxies por su cuenta; fijar IP exige adaptadores a bajo nivel de urllib3 de todos modos.
- **httpx**: moderno. Riesgo: fijar la IP requiere un backend de red propio de httpcore (API interna); más superficie.
- **`ssl` estándar sin truststore** (`load_default_certs`): sin dependencia. Riesgos: OpenSSL solo ve las raíces ya presentes en el almacén (Windows las descarga bajo demanda → fallos falsos F-18), y sin revocación.
- Proxy: **`urllib.request.getproxies()`** solo lee el proxy manual del registro (sin detección automática ni PAC) → no cumple RN-020; **`pypac`** añade un motor JavaScript; **WinHTTP por `ctypes`** (`WinHttpGetIEProxyConfigForCurrentUser` + `WinHttpGetProxyForUrl` con autodetección y PAC) usa el mismo mecanismo que Windows, sin dependencias.

## Decisión
- **urllib3 2.x + truststore**. Contexto TLS de truststore con `minimum_version = TLSv1_2` y `VERIFY_CRL_CHECK_CHAIN`. **RN-018 d**: si el error tiene `verify_code` de revocación no consultable (`CRYPT_E_REVOCATION_OFFLINE` 0x80092013 o `CRYPT_E_NO_REVOCATION_CHECK` 0x80092012), se reintenta **una vez** el saludo TLS con un contexto sin revocación, se anota en el registro (código + dominio) y se continúa; `CRYPT_E_REVOKED` y cualquier otro código → F-18. Nunca se usa `CERT_NONE`.
- Resolución con `socket.getaddrinfo`, clasificación de **todas** las direcciones con el clasificador del dominio (spec 001) y conexión a la dirección comprobada.
- Proxy por **WinHTTP vía `ctypes`** en un adaptador de infraestructura; túnel `CONNECT` con `ProxyManager` de urllib3 (sin fijar IP, riesgo residual S-38 ya aceptado).
- Sin `requests` ni `httpx`.

## Consecuencias
- Viable para todos los requisitos de red del PRD, sin depender de APIs internas.
- Más difícil: bucle de redirecciones, vigilancia de tiempos y adaptador WinHTTP son código propio con pruebas de integración contra el servidor local de pruebas.
- Riesgo: el reintento del saludo TLS por revocación no consultable duplica una conexión en ese caso raro. Aceptado.
- Riesgo: la detección de errores de revocación depende de los códigos que expone truststore; si una versión futura los cambia, la prueba de integración lo detecta (dependencia fijada).
- Dependencias de ejecución nuevas: `urllib3`, `truststore` (fijadas con hash, auditadas).

## Relacionado
[[0001-python-escritorio-portable]] · [[0003-analizador-url-propio]] · [[0005-concurrencia-con-hilos]] · [[reglas-negocio]] · [[modelo-amenazas]]
