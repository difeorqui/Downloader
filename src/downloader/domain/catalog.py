"""Catálogos cerrados del dominio (PA-06): motivos de invalidez I-NN, fallos F-NN y avisos A-N.

Los textos son los normativos de ``docs/01-requerimientos/reglas-negocio.md``: RN-004 (I-NN),
anexo 2 (F-NN y su clase, RN-026) y RN-021 (A-N). Ninguna URL se rechaza ni ningún elemento
falla por un motivo que no esté aquí.
"""

from enum import Enum, StrEnum
from typing import Self


class FailureClass(Enum):
    """Clase de un fallo (RN-026): decide si se reintenta y cómo se resuelve."""

    TEMPORARY = "temporal"
    PERMANENT = "permanente"
    RECOVERABLE = "recuperable"


class InvalidReason(StrEnum):
    """Motivo de invalidez de una URL (RN-004). ``message`` es el texto visible exacto."""

    message: str

    def __new__(cls, code: str, message: str) -> Self:
        member = str.__new__(cls, code)
        member._value_ = code
        member.message = message
        return member

    I01 = "I-01", "Protocolo no soportado"
    I02 = "I-02", "Ruta local o de red no soportada"
    I03 = "I-03", "URL mal formada o ambigua"
    I04 = "I-04", "URL demasiado larga"
    I05 = "I-05", "Requiere autenticación (no soportado)"
    I06 = "I-06", "Dirección no permitida"
    I07 = "I-07", "Puerto no válido"
    I08 = "I-08", "El campo admite una sola URL. Para varias, use un archivo masivo"
    I09 = "I-09", "Parece haber varias URLs en una misma línea"


class FailureCode(StrEnum):
    """Fallo de un elemento (RN-026, anexo 2): motivo visible y clase.

    Numeración por clase: F-01..F-09 temporales, F-10..F-29 permanentes, F-30..F-39
    recuperables; F-99 es el error inesperado (permanente).
    """

    message: str
    failure_class: FailureClass

    def __new__(cls, code: str, message: str, failure_class: FailureClass) -> Self:
        member = str.__new__(cls, code)
        member._value_ = code
        member.message = message
        member.failure_class = failure_class
        return member

    F01 = "F-01", "No se pudo conectar", FailureClass.TEMPORARY
    F02 = "F-02", "Tiempo de conexión agotado", FailureClass.TEMPORARY
    F03 = "F-03", "El servidor dejó de enviar datos", FailureClass.TEMPORARY
    F04 = "F-04", "Velocidad demasiado baja", FailureClass.TEMPORARY
    F05 = "F-05", "Conexión interrumpida", FailureClass.TEMPORARY
    F06 = "F-06", "Servidor ocupado", FailureClass.TEMPORARY
    F07 = "F-07", "Error temporal del servidor", FailureClass.TEMPORARY
    F08 = "F-08", "No se pudo resolver el nombre (temporal)", FailureClass.TEMPORARY
    F10 = "F-10", "El dominio no existe", FailureClass.PERMANENT
    F11 = "F-11", "Archivo no encontrado", FailureClass.PERMANENT
    F12 = "F-12", "Acceso prohibido", FailureClass.PERMANENT
    F13 = "F-13", "Requiere autenticación", FailureClass.PERMANENT
    F14 = "F-14", "El proxy requiere autenticación (no soportado)", FailureClass.PERMANENT
    F15 = "F-15", "Solicitud rechazada por el servidor", FailureClass.PERMANENT
    F16 = "F-16", "Error del servidor", FailureClass.PERMANENT
    F17 = "F-17", "Respuesta inesperada del servidor", FailureClass.PERMANENT
    F18 = "F-18", "Certificado de seguridad no válido", FailureClass.PERMANENT
    F19 = "F-19", "Conexión insegura (cifrado no permitido)", FailureClass.PERMANENT
    F20 = "F-20", "Redirección insegura (de HTTPS a HTTP)", FailureClass.PERMANENT
    F21 = "F-21", "Demasiadas redirecciones", FailureClass.PERMANENT
    F22 = "F-22", "Redirección a protocolo no soportado", FailureClass.PERMANENT
    F23 = "F-23", "Dirección no permitida", FailureClass.PERMANENT
    F24 = "F-24", "Ruta no permitida", FailureClass.PERMANENT
    F25 = "F-25", "Ruta demasiado larga", FailureClass.PERMANENT
    F26 = "F-26", "Supera el tamaño máximo por archivo", FailureClass.PERMANENT
    F27 = (
        "F-27",
        "Conflicto de ruta: existe un archivo con el nombre de una carpeta necesaria",
        FailureClass.PERMANENT,
    )
    F28 = (
        "F-28",
        "Nombre de carpeta o archivo demasiado largo (más de 255 caracteres)",
        FailureClass.PERMANENT,
    )
    F30 = "F-30", "Dirección interna no confirmada", FailureClass.RECOVERABLE
    F31 = "F-31", "Espacio en disco insuficiente", FailureClass.RECOVERABLE
    F32 = "F-32", "No se puede escribir en la carpeta destino", FailureClass.RECOVERABLE
    F33 = "F-33", "Se superó la duración máxima de descarga", FailureClass.RECOVERABLE
    F99 = "F-99", "Error inesperado", FailureClass.PERMANENT


class WarningCode(StrEnum):
    """Aviso de un archivo descargado (RN-021). Ninguno impide la descarga."""

    message: str

    def __new__(cls, code: str, message: str) -> Self:
        member = str.__new__(cls, code)
        member._value_ = code
        member.message = message
        return member

    A1 = "A-1", "Archivo ejecutable o con macros: no lo abra si no confía en el origen"
    A2 = "A-2", "Se recibió una página web en lugar de un archivo"
    A3 = "A-3", "No se pudo marcar el origen"
