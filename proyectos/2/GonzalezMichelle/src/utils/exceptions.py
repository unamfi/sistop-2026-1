"""
Excepciones personalizadas para FiUnamFS Manager

Define la jerarquía de excepciones específicas del filesystem
para manejo de errores más preciso y mensajes informativos.
"""

from typing import List, Optional


class FiUnamFSError(Exception):
    """
    Excepción base para todos los errores de FiUnamFS.

    Todas las excepciones específicas del filesystem heredan de esta clase.
    """
    pass


class InvalidFilesystemError(FiUnamFSError):
    """
    Error cuando la imagen del filesystem es inválida.

    Se lanza cuando:
    - La firma no es "FiUnamFS"
    - La versión no es "26-2"
    - El tamaño de cluster no es 1024
    - Los clusters de directorio no son 4
    - El total de clusters no es 1440
    """

    def __init__(self, mensaje: str):
        self.mensaje = mensaje
        super().__init__(mensaje)


class FileNotFoundInFilesystemError(FiUnamFSError):
    """
    Error cuando un archivo no existe en el filesystem.

    Incluye lista de archivos disponibles para ayudar al usuario.
    """

    def __init__(self, nombre_archivo: str, archivos_disponibles: Optional[List[str]] = None):
        self.nombre_archivo = nombre_archivo
        self.archivos_disponibles = archivos_disponibles or []

        if self.archivos_disponibles:
            mensaje = (
                f"Archivo '{nombre_archivo}' no encontrado en el filesystem.\n"
                f"Archivos disponibles: {', '.join(self.archivos_disponibles)}"
            )
        else:
            mensaje = f"Archivo '{nombre_archivo}' no encontrado en el filesystem (filesystem vacío)"

        super().__init__(mensaje)


class NoSpaceError(FiUnamFSError):
    """
    Error cuando no hay espacio contiguo suficiente en el filesystem.

    Incluye información sobre espacio necesario vs disponible.
    """

    def __init__(
        self,
        bytes_necesarios: int,
        bytes_disponibles: int,
        clusters_necesarios: int,
        clusters_disponibles: int
    ):
        self.bytes_necesarios = bytes_necesarios
        self.bytes_disponibles = bytes_disponibles
        self.clusters_necesarios = clusters_necesarios
        self.clusters_disponibles = clusters_disponibles

        mensaje = (
            f"No hay espacio contiguo suficiente en el filesystem.\n"
            f"Necesario: {bytes_necesarios} bytes ({clusters_necesarios} clusters)\n"
            f"Disponible: {bytes_disponibles} bytes ({clusters_disponibles} clusters)\n"
            f"Sugerencia: Elimina algunos archivos para liberar espacio contiguo"
        )

        super().__init__(mensaje)


class FilenameConflictError(FiUnamFSError):
    """
    Error cuando un archivo con el mismo nombre ya existe.

    Se lanza durante operaciones de importación cuando hay conflicto de nombres.
    """

    def __init__(self, nombre_archivo: str):
        self.nombre_archivo = nombre_archivo

        mensaje = (
            f"El archivo '{nombre_archivo}' ya existe en el filesystem.\n"
            f"Sugerencia: Elimina el archivo existente primero o usa un nombre diferente"
        )

        super().__init__(mensaje)


class DirectoryFullError(FiUnamFSError):
    """
    Error cuando el directorio está lleno (64 archivos máximo).

    Se lanza cuando se intenta importar un archivo y no hay entradas
    de directorio disponibles.
    """

    def __init__(self):
        mensaje = (
            "El directorio está lleno (máximo 64 archivos).\n"
            "Sugerencia: Elimina algunos archivos antes de importar nuevos"
        )
        super().__init__(mensaje)


class InvalidFilenameError(FiUnamFSError):
    """
    Error cuando un nombre de archivo no cumple con los requisitos.

    Se lanza cuando:
    - El nombre excede 14 caracteres
    - Contiene caracteres no-ASCII
    - Contiene separadores de ruta
    """

    def __init__(self, nombre_archivo: str, razon: str):
        self.nombre_archivo = nombre_archivo
        self.razon = razon

        mensaje = f"Nombre de archivo inválido '{nombre_archivo}': {razon}"

        super().__init__(mensaje)
