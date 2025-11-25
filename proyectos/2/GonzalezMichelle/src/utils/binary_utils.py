"""
Utilidades para manejo de estructuras binarias en FiUnamFS

Proporciona funciones helper para empaquetar/desempaquetar datos binarios
usando el formato little-endian de 32 bits requerido por la especificación.
"""

import struct
from datetime import datetime
from typing import Optional


def leer_uint32_le(datos: bytes) -> int:
    """
    Lee un entero sin signo de 32 bits en formato little-endian.

    Args:
        datos: Bytes a interpretar (mínimo 4 bytes)

    Returns:
        Entero de 32 bits sin signo

    Raises:
        struct.error: Si los datos no tienen al menos 4 bytes
    """
    return struct.unpack('<I', datos[:4])[0]


def escribir_uint32_le(valor: int) -> bytes:
    """
    Escribe un entero sin signo de 32 bits en formato little-endian.

    Args:
        valor: Entero a convertir (0 a 4294967295)

    Returns:
        4 bytes en formato little-endian

    Raises:
        struct.error: Si el valor está fuera de rango
    """
    return struct.pack('<I', valor)


def parsear_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Convierte un timestamp en formato AAAAMMDDHHMMSS a objeto datetime.

    Args:
        timestamp_str: String de 14 caracteres en formato AAAAMMDDHHMMSS

    Returns:
        Objeto datetime o None si el timestamp es inválido

    Ejemplo:
        >>> parsear_timestamp('20251107143000')
        datetime.datetime(2025, 11, 7, 14, 30)
    """
    if not timestamp_str or len(timestamp_str) != 14:
        return None

    try:
        anio = int(timestamp_str[0:4])
        mes = int(timestamp_str[4:6])
        dia = int(timestamp_str[6:8])
        hora = int(timestamp_str[8:10])
        minuto = int(timestamp_str[10:12])
        segundo = int(timestamp_str[12:14])

        return datetime(anio, mes, dia, hora, minuto, segundo)
    except (ValueError, IndexError):
        return None


def formatear_timestamp(dt: datetime) -> str:
    """
    Convierte un objeto datetime a formato AAAAMMDDHHMMSS.

    Args:
        dt: Objeto datetime a formatear

    Returns:
        String de 14 caracteres en formato AAAAMMDDHHMMSS

    Ejemplo:
        >>> formatear_timestamp(datetime(2025, 11, 7, 14, 30, 0))
        '20251107143000'
    """
    return dt.strftime('%Y%m%d%H%M%S')


def timestamp_legible(timestamp_str: str) -> str:
    """
    Convierte timestamp AAAAMMDDHHMMSS a formato legible AAAA-MM-DD HH:MM:SS.

    Args:
        timestamp_str: String de 14 caracteres en formato AAAAMMDDHHMMSS

    Returns:
        String formateado para lectura humana o el original si es inválido

    Ejemplo:
        >>> timestamp_legible('20251107143000')
        '2025-11-07 14:30:00'
    """
    dt = parsear_timestamp(timestamp_str)
    if dt is None:
        return timestamp_str  # Retornar original si no es válido
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def timestamp_actual() -> str:
    """
    Genera un timestamp en formato AAAAMMDDHHMMSS con la fecha/hora actual.

    Returns:
        String de 14 caracteres con el timestamp actual

    Ejemplo:
        >>> timestamp_actual()  # Si es 2025-11-07 14:30:00
        '20251107143000'
    """
    return formatear_timestamp(datetime.now())
