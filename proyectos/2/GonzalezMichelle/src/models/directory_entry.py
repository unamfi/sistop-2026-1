"""
Modelo de DirectoryEntry para FiUnamFS

Cada entrada de directorio ocupa 64 bytes y describe un archivo en el filesystem.
El directorio ocupa los clusters 1-4 (bytes 1024-5119), permitiendo hasta 64 archivos.
"""

import struct
from typing import NamedTuple

from utils.binary_utils import timestamp_actual
from utils.validation import calcular_clusters_necesarios


# Formato de entrada de directorio según especificación FiUnamFS
# Total: 64 bytes por entrada
DIRECTORY_ENTRY_FORMAT = (
    '<'    # little-endian byte order
    'c'    # file_type (byte 0): '.' para archivo activo, '-' para vacío
    '15s'  # filename (bytes 1-15): nombre de archivo (14 chars + null)
    'I'    # start_cluster (bytes 16-19): cluster inicial del archivo
    'I'    # file_size (bytes 20-23): tamaño en bytes
    '14s'  # created_timestamp (bytes 24-37): AAAAMMDDHHMMSS
    '14s'  # modified_timestamp (bytes 38-51): AAAAMMDDHHMMSS
    '12x'  # reserved (bytes 52-63): reservado para uso futuro
)


class DirectoryEntry(NamedTuple):
    """
    Estructura de una entrada de directorio en FiUnamFS.

    Atributos:
        file_type: Tipo de entrada (b'.' = archivo activo, b'-' = vacío)
        filename: Nombre del archivo (hasta 14 caracteres ASCII)
        start_cluster: Cluster inicial donde comienza el archivo (5-1439)
        file_size: Tamaño del archivo en bytes
        created_timestamp: Timestamp de creación (formato AAAAMMDDHHMMSS)
        modified_timestamp: Timestamp de última modificación (AAAAMMDDHHMMSS)
    """
    file_type: bytes
    filename: str
    start_cluster: int
    file_size: int
    created_timestamp: str
    modified_timestamp: str

    @classmethod
    def from_bytes(cls, data: bytes) -> 'DirectoryEntry':
        """
        Parsea una entrada de directorio desde 64 bytes.

        Args:
            data: Datos binarios de la entrada (64 bytes)

        Returns:
            Instancia de DirectoryEntry

        Raises:
            struct.error: Si los datos no tienen 64 bytes
        """
        fields = struct.unpack(DIRECTORY_ENTRY_FORMAT, data)

        return cls(
            file_type=fields[0],
            filename=fields[1].rstrip(b'\x00').decode('ascii', errors='ignore'),
            start_cluster=fields[2],
            file_size=fields[3],
            created_timestamp=fields[4].decode('ascii', errors='ignore'),
            modified_timestamp=fields[5].decode('ascii', errors='ignore')
        )

    def to_bytes(self) -> bytes:
        """
        Serializa la entrada de directorio a 64 bytes.

        Returns:
            64 bytes representando la entrada de directorio

        Raises:
            struct.error: Si algún campo tiene un valor inválido
        """
        # Asegurar que el filename tenga exactamente 15 bytes (padding con nulls)
        filename_bytes = self.filename.encode('ascii')[:14]  # Máximo 14 chars
        filename_bytes = filename_bytes.ljust(15, b'\x00')

        return struct.pack(
            DIRECTORY_ENTRY_FORMAT,
            self.file_type,
            filename_bytes,
            self.start_cluster,
            self.file_size,
            self.created_timestamp.encode('ascii'),
            self.modified_timestamp.encode('ascii')
        )

    def is_active(self) -> bool:
        """
        Verifica si esta entrada representa un archivo activo.

        Returns:
            True si el archivo está activo (file_type == b'.')
        """
        return self.file_type == b'.'

    def is_empty(self) -> bool:
        """
        Verifica si esta entrada está disponible para un nuevo archivo.

        Returns:
            True si la entrada está vacía o marcada como eliminada
        """
        return self.file_type == b'-' or self.filename == '.' * 14 or self.filename == ''

    def num_clusters_needed(self) -> int:
        """
        Calcula cuántos clusters ocupa este archivo.

        Returns:
            Número de clusters necesarios para el tamaño del archivo
        """
        return calcular_clusters_necesarios(self.file_size)

    @staticmethod
    def create_empty() -> 'DirectoryEntry':
        """
        Crea una entrada de directorio vacía.

        Returns:
            DirectoryEntry marcada como vacía (tipo '-')
        """
        return DirectoryEntry(
            file_type=b'-',
            filename='.' * 14,  # Patrón convencional para entradas vacías
            start_cluster=0,
            file_size=0,
            created_timestamp='0' * 14,
            modified_timestamp='0' * 14
        )

    @staticmethod
    def create_file(filename: str, start_cluster: int, file_size: int) -> 'DirectoryEntry':
        """
        Crea una entrada de directorio para un nuevo archivo.

        Args:
            filename: Nombre del archivo (máximo 14 caracteres)
            start_cluster: Cluster inicial asignado (5-1439)
            file_size: Tamaño del archivo en bytes

        Returns:
            DirectoryEntry nueva con timestamps actuales
        """
        # Truncar filename a 14 caracteres si es necesario
        filename_truncado = filename[:14]

        # Generar timestamp actual en formato AAAAMMDDHHMMSS
        timestamp = timestamp_actual()

        return DirectoryEntry(
            file_type=b'.',
            filename=filename_truncado,
            start_cluster=start_cluster,
            file_size=file_size,
            created_timestamp=timestamp,
            modified_timestamp=timestamp
        )

    def __str__(self) -> str:
        """Representación en string para debugging."""
        tipo = 'ACTIVO' if self.is_active() else 'VACIO'
        return (
            f"DirectoryEntry({tipo}: '{self.filename}', "
            f"{self.file_size} bytes, cluster {self.start_cluster})"
        )
