"""
Modelo del Superblock de FiUnamFS

El superblock contiene los metadatos del filesystem y ocupa el cluster 0
(los primeros 1024 bytes de la imagen). Define parámetros críticos como
firma, versión, tamaño de cluster y distribución de clusters.
"""

import struct
from typing import NamedTuple

from utils.exceptions import InvalidFilesystemError


# Formato del superblock según especificación FiUnamFS
# Total: 54 bytes usados de 1024 (resto es padding reservado)
SUPERBLOCK_FORMAT = (
    '<'    # little-endian byte order
    '9s'   # signature (bytes 0-8): "FiUnamFS"
    'x'    # padding (byte 9)
    '5s'   # version (bytes 10-14): "26-2" + null o padding
    '5x'   # padding (bytes 15-19)
    '16s'  # volume_label (bytes 20-35): etiqueta de volumen
    '4x'   # padding (bytes 36-39)
    'I'    # cluster_size (bytes 40-43): tamaño de cluster en bytes (1024)
    'x'    # padding (byte 44)
    'I'    # directory_clusters (bytes 45-48): clusters para directorio (4)
    'x'    # padding (byte 49)
    'I'    # total_clusters (bytes 50-53): total de clusters (1440)
)


class Superblock(NamedTuple):
    """
    Estructura del superblock de FiUnamFS.

    Atributos:
        signature: Debe ser b'FiUnamFS' (9 bytes)
        version: Debe ser b'26-1' o b'26-2' (versión del formato)
        volume_label: Etiqueta del volumen (hasta 16 bytes)
        cluster_size: Tamaño de cada cluster en bytes (debe ser 1024)
        directory_clusters: Clusters reservados para directorio (típicamente 3-4)
        total_clusters: Total de clusters en el filesystem (debe ser 1440)
    """
    signature: bytes
    version: bytes
    volume_label: bytes
    cluster_size: int
    directory_clusters: int
    total_clusters: int

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Superblock':
        """
        Parsea un superblock desde los primeros 1024 bytes del filesystem.

        Args:
            data: Datos binarios del superblock (mínimo 54 bytes)

        Returns:
            Instancia de Superblock con los campos parseados

        Raises:
            struct.error: Si los datos no tienen el formato correcto
        """
        # Desempaquetar los primeros 54 bytes usando el formato definido
        fields = struct.unpack(SUPERBLOCK_FORMAT, data[:54])

        return cls(
            signature=fields[0].rstrip(b'\x00'),         # Remover nulls
            version=fields[1].rstrip(b'\x00'),           # Remover nulls
            volume_label=fields[2].rstrip(b'\x00 '),     # Remover nulls y espacios
            cluster_size=fields[3],                       # uint32 little-endian
            directory_clusters=fields[4],                 # uint32 little-endian
            total_clusters=fields[5]                      # uint32 little-endian
        )

    def validate(self) -> None:
        """
        Valida que el superblock cumpla con la especificación FiUnamFS.

        Verifica:
        - Firma correcta: "FiUnamFS"
        - Versión soportada: "26-1" o "26-2"
        - Tamaño de cluster: 1024 bytes
        - Clusters de directorio: entre 1 y 64
        - Total de clusters: 1440

        Raises:
            InvalidFilesystemError: Si algún campo no cumple la especificación
        """
        if self.signature != b'FiUnamFS':
            raise InvalidFilesystemError(
                f"Firma inválida: se esperaba b'FiUnamFS', "
                f"se encontró {self.signature!r}"
            )

        if self.version not in (b'26-1', b'26-2'):
            raise InvalidFilesystemError(
                f"Versión no soportada: se esperaba b'26-1' o b'26-2', "
                f"se encontró {self.version!r}"
            )

        if self.cluster_size != 1024:
            raise InvalidFilesystemError(
                f"Tamaño de cluster inválido: se esperaba 1024, "
                f"se encontró {self.cluster_size}"
            )

        if self.directory_clusters < 1 or self.directory_clusters > 64:
            raise InvalidFilesystemError(
                f"Número de clusters de directorio inválido: debe estar entre 1 y 64, "
                f"se encontró {self.directory_clusters}"
            )

        if self.total_clusters != 1440:
            raise InvalidFilesystemError(
                f"Total de clusters inválido: se esperaba 1440, "
                f"se encontró {self.total_clusters}"
            )

    def __str__(self) -> str:
        """Representación en string para debugging."""
        try:
            label = self.volume_label.decode('ascii', errors='ignore')
        except:
            label = repr(self.volume_label)

        return (
            f"Superblock(\n"
            f"  signature={self.signature!r},\n"
            f"  version={self.version!r},\n"
            f"  volume_label={label!r},\n"
            f"  cluster_size={self.cluster_size},\n"
            f"  directory_clusters={self.directory_clusters},\n"
            f"  total_clusters={self.total_clusters}\n"
            f")"
        )
