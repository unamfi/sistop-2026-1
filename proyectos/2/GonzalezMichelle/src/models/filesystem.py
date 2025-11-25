"""
Modelo del Filesystem FiUnamFS

Implementa operaciones de alto nivel sobre el filesystem FiUnamFS,
incluyendo gestión de clusters, lectura/escritura de archivos y
operaciones de directorio.
"""

from typing import Optional


class ClusterMap:
    """
    Mapa de clusters para gestionar espacio libre y ocupado en el filesystem.

    El ClusterMap mantiene un registro de qué clusters están ocupados
    y proporciona métodos para encontrar espacio contiguo libre.

    Atributos:
        total_clusters: Total de clusters en el filesystem (1440)
        allocated: Lista booleana indicando si cada cluster está ocupado
    """

    def __init__(self, total_clusters: int = 1440):
        """
        Inicializa el mapa de clusters.

        Args:
            total_clusters: Total de clusters en el filesystem (default: 1440)
        """
        self.total_clusters = total_clusters
        self.allocated = [False] * total_clusters

        # Reservar clusters 0-4 (superblock + directorio)
        # Cluster 0: Superblock
        # Clusters 1-4: Directorio
        for i in range(5):
            self.allocated[i] = True

    def allocate_file(self, start_cluster: int, num_clusters: int) -> None:
        """
        Marca un rango de clusters como ocupados por un archivo.

        Args:
            start_cluster: Cluster inicial
            num_clusters: Cantidad de clusters a marcar

        Raises:
            ValueError: Si algún cluster está fuera de rango
        """
        for i in range(start_cluster, start_cluster + num_clusters):
            if i >= self.total_clusters:
                raise ValueError(
                    f"Cluster {i} fuera de rango (máximo: {self.total_clusters - 1})"
                )
            self.allocated[i] = True

    def free_file(self, start_cluster: int, num_clusters: int) -> None:
        """
        Marca un rango de clusters como libres (después de eliminar archivo).

        Args:
            start_cluster: Cluster inicial
            num_clusters: Cantidad de clusters a liberar
        """
        for i in range(start_cluster, start_cluster + num_clusters):
            if i >= self.total_clusters:
                continue  # Ignorar clusters fuera de rango
            if i < 5:
                continue  # No liberar clusters reservados
            self.allocated[i] = False

    def find_contiguous_space(self, num_clusters: int) -> Optional[int]:
        """
        Encuentra el primer espacio contiguo libre usando algoritmo first-fit.

        Busca secuencialmente desde el cluster 5 (primer cluster de datos)
        hasta encontrar una secuencia de clusters libres del tamaño necesario.

        Args:
            num_clusters: Cantidad de clusters contiguos necesarios

        Returns:
            Número del cluster inicial, o None si no hay espacio contiguo suficiente

        Ejemplo:
            >>> cmap = ClusterMap()
            >>> cmap.allocate_file(5, 10)  # Ocupar clusters 5-14
            >>> cmap.find_contiguous_space(5)  # Buscar 5 clusters libres
            15  # Primer espacio libre después de cluster 14
        """
        if num_clusters == 0:
            return None

        consecutive = 0  # Contador de clusters consecutivos libres
        start = None     # Cluster inicial del espacio libre encontrado

        # Comenzar búsqueda desde cluster 5 (primer cluster de datos)
        for i in range(5, self.total_clusters):
            if not self.allocated[i]:
                # Cluster libre encontrado
                if consecutive == 0:
                    start = i  # Marcar inicio de secuencia libre

                consecutive += 1

                # ¿Tenemos suficientes clusters consecutivos?
                if consecutive == num_clusters:
                    return start
            else:
                # Cluster ocupado - reiniciar búsqueda
                consecutive = 0
                start = None

        # No se encontró espacio contiguo suficiente
        return None

    def available_clusters(self) -> int:
        """
        Cuenta el total de clusters libres (puede estar fragmentado).

        Returns:
            Número total de clusters no ocupados

        Nota:
            Este conteo incluye clusters fragmentados. Para importar archivos
            se necesita espacio CONTIGUO, usar find_contiguous_space().
        """
        return sum(1 for i in range(5, self.total_clusters) if not self.allocated[i])

    def largest_contiguous_block(self) -> int:
        """
        Encuentra el tamaño del bloque contiguo más grande disponible.

        Returns:
            Número de clusters en el bloque contiguo más grande
        """
        max_consecutive = 0
        current_consecutive = 0

        for i in range(5, self.total_clusters):
            if not self.allocated[i]:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def __str__(self) -> str:
        """Representación en string para debugging."""
        total_libre = self.available_clusters()
        max_contiguo = self.largest_contiguous_block()
        return (
            f"ClusterMap(total={self.total_clusters}, "
            f"libre={total_libre}, "
            f"max_contiguo={max_contiguo})"
        )


class Filesystem:
    """
    Clase principal para operaciones sobre filesystem FiUnamFS.

    Proporciona métodos de alto nivel para listar, exportar, importar
    y eliminar archivos en una imagen de filesystem FiUnamFS.

    Atributos:
        fs_path: Ruta al archivo de imagen del filesystem
        file_handle: File handle abierto en modo lectura/escritura binario
        superblock: Objeto Superblock parseado y validado
        directory_entries: Lista de todas las entradas de directorio (64 entradas)
    """

    def __init__(self, fs_path: str):
        """
        Inicializa el filesystem y valida la estructura.

        Args:
            fs_path: Ruta al archivo de imagen FiUnamFS (.img)

        Raises:
            FileNotFoundError: Si el archivo no existe
            InvalidFilesystemError: Si la estructura no es válida
        """
        self.fs_path = fs_path
        self.file_handle = None
        self.superblock = None
        self.directory_entries = []

        # Abrir archivo en modo lectura/escritura binario
        self.file_handle = open(fs_path, 'r+b')

        # Leer y validar superblock
        self._read_superblock()

        # Leer directorio
        self._read_directory()

    def _read_superblock(self) -> None:
        """
        Lee el superblock (cluster 0) y lo valida.

        Raises:
            InvalidFilesystemError: Si la firma o versión no son correctas
        """
        from .superblock import Superblock

        # Leer cluster 0 (bytes 0-1023)
        self.file_handle.seek(0)
        superblock_data = self.file_handle.read(1024)

        # Parsear superblock
        self.superblock = Superblock.from_bytes(superblock_data)

        # Validar estructura
        self.superblock.validate()

    def _read_directory(self) -> None:
        """
        Lee todas las entradas de directorio (clusters 1-4).

        Lee los 64 entries de 64 bytes cada uno desde los clusters 1-4
        (bytes 1024-5119) y los parsea como DirectoryEntry objects.
        """
        from .directory_entry import DirectoryEntry

        # Leer clusters 1-4 (bytes 1024-5119)
        self.file_handle.seek(1024)
        directory_data = self.file_handle.read(4096)  # 4 clusters × 1024 bytes

        # Parsear las 64 entradas de directorio (64 entries × 64 bytes)
        self.directory_entries = []
        for i in range(64):
            offset = i * 64
            entry_data = directory_data[offset:offset + 64]
            entry = DirectoryEntry.from_bytes(entry_data)
            self.directory_entries.append(entry)

    def list_files(self) -> dict:
        """
        Lista todos los archivos activos en el filesystem.

        Returns:
            Diccionario con:
                - 'files': Lista de diccionarios con info de cada archivo
                - 'total_files': Número total de archivos activos
                - 'used_space': Bytes ocupados
                - 'free_space': Bytes disponibles

        Ejemplo de retorno:
            {
                'files': [
                    {
                        'filename': 'README.txt',
                        'size': 1024,
                        'created': '2025-11-07 14:30:00',
                        'modified': '2025-11-07 14:30:00',
                        'start_cluster': 5,
                        'num_clusters': 1
                    },
                    ...
                ],
                'total_files': 3,
                'used_space': 5120,
                'free_space': 1469440
            }
        """
        from utils.binary_utils import timestamp_legible

        files = []
        used_space = 0

        # Filtrar entradas activas y construir lista de archivos
        for entry in self.directory_entries:
            if entry.is_active():
                files.append({
                    'filename': entry.filename.strip(),  # Remover espacios de padding
                    'size': entry.file_size,
                    'created': timestamp_legible(entry.created_timestamp),
                    'modified': timestamp_legible(entry.modified_timestamp),
                    'start_cluster': entry.start_cluster,
                    'num_clusters': entry.num_clusters_needed()
                })
                used_space += entry.file_size

        # Calcular espacio libre
        # Total de espacio de datos: 1435 clusters × 1024 bytes = 1,469,440 bytes
        total_data_space = 1435 * 1024
        free_space = total_data_space - used_space

        return {
            'files': files,
            'total_files': len(files),
            'used_space': used_space,
            'free_space': free_space
        }

    def _find_file(self, filename: str):
        """
        Busca un archivo en el directorio por nombre.

        Args:
            filename: Nombre del archivo a buscar

        Returns:
            DirectoryEntry del archivo encontrado

        Raises:
            FileNotFoundInFilesystemError: Si el archivo no existe
        """
        from utils.exceptions import FileNotFoundInFilesystemError

        # Buscar en las entradas de directorio
        # Comparar sin espacios de padding (los nombres se guardan en campo fijo de 14 chars)
        for entry in self.directory_entries:
            if entry.is_active() and entry.filename.strip() == filename:
                return entry

        # Archivo no encontrado - construir lista de archivos disponibles
        archivos_disponibles = [
            entry.filename.strip()
            for entry in self.directory_entries
            if entry.is_active()
        ]

        raise FileNotFoundInFilesystemError(filename, archivos_disponibles)

    def _read_file_data(self, entry) -> bytes:
        """
        Lee los datos de un archivo desde el filesystem.

        Args:
            entry: DirectoryEntry del archivo a leer

        Returns:
            Bytes del contenido del archivo
        """
        # Calcular offset en bytes: cluster × 1024
        offset = entry.start_cluster * 1024

        # Posicionarse en el inicio del archivo
        self.file_handle.seek(offset)

        # Leer exactamente file_size bytes
        data = self.file_handle.read(entry.file_size)

        return data

    def export_file(self, filename: str, dest_path: str) -> dict:
        """
        Exporta un archivo del filesystem al sistema local.

        Args:
            filename: Nombre del archivo en FiUnamFS
            dest_path: Ruta destino en el sistema local

        Returns:
            Diccionario con resultado:
                - 'filename': Nombre del archivo
                - 'bytes_copied': Bytes copiados
                - 'dest_path': Ruta destino

        Raises:
            FileNotFoundInFilesystemError: Si el archivo no existe
            IOError: Si hay error al escribir el archivo destino
        """
        import os

        # Buscar el archivo
        entry = self._find_file(filename)

        # Leer los datos del archivo
        data = self._read_file_data(entry)

        # Crear directorio padre si no existe
        dest_dir = os.path.dirname(dest_path)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # Escribir archivo destino
        with open(dest_path, 'wb') as f:
            f.write(data)

        return {
            'filename': filename,
            'bytes_copied': len(data),
            'dest_path': dest_path
        }

    def _build_cluster_map(self) -> ClusterMap:
        """
        Construye un mapa de clusters ocupados/libres basado en el directorio.

        Returns:
            ClusterMap con todos los archivos activos marcados
        """
        cluster_map = ClusterMap(self.superblock.total_clusters)

        # Marcar clusters ocupados por cada archivo activo
        for entry in self.directory_entries:
            if entry.is_active():
                cluster_map.allocate_file(
                    entry.start_cluster,
                    entry.num_clusters_needed()
                )

        return cluster_map

    def _find_empty_directory_slot(self) -> int:
        """
        Encuentra la primera entrada de directorio vacía.

        Returns:
            Índice de la entrada vacía (0-63)

        Raises:
            DirectoryFullError: Si no hay entradas disponibles
        """
        from utils.exceptions import DirectoryFullError

        for i, entry in enumerate(self.directory_entries):
            if entry.is_empty():
                return i

        raise DirectoryFullError()

    def _write_directory_entry(self, index: int, entry) -> None:
        """
        Escribe una entrada de directorio en el filesystem.

        Args:
            index: Índice de la entrada (0-63)
            entry: DirectoryEntry a escribir
        """
        # Calcular offset: 1024 (superblock) + index × 64
        offset = 1024 + (index * 64)

        # Posicionarse en el offset
        self.file_handle.seek(offset)

        # Escribir los 64 bytes de la entrada
        self.file_handle.write(entry.to_bytes())

        # Flush para asegurar escritura
        self.file_handle.flush()

        # Actualizar cache local
        self.directory_entries[index] = entry

    def _write_file_data(self, start_cluster: int, data: bytes) -> None:
        """
        Escribe datos de archivo en el área de datos.

        Args:
            start_cluster: Cluster inicial donde escribir
            data: Bytes a escribir
        """
        # Calcular offset: start_cluster × 1024
        offset = start_cluster * 1024

        # Posicionarse en el offset
        self.file_handle.seek(offset)

        # Escribir los datos
        self.file_handle.write(data)

        # Flush para asegurar escritura
        self.file_handle.flush()

    def import_file(self, src_path: str, filename: str = None) -> dict:
        """
        Importa un archivo del sistema local al filesystem.

        Args:
            src_path: Ruta del archivo local a importar
            filename: Nombre para el archivo en FiUnamFS (opcional,
                     usa nombre del archivo fuente si no se especifica)

        Returns:
            Diccionario con resultado:
                - 'filename': Nombre del archivo
                - 'bytes_copied': Bytes copiados
                - 'start_cluster': Cluster inicial asignado
                - 'num_clusters': Clusters utilizados

        Raises:
            ValueError: Si el nombre de archivo es inválido
            FilenameConflictError: Si ya existe un archivo con ese nombre
            NoSpaceError: Si no hay espacio contiguo suficiente
            DirectoryFullError: Si el directorio está lleno
        """
        import os
        from utils.validation import validar_nombre_archivo, calcular_clusters_necesarios
        from utils.exceptions import FilenameConflictError, NoSpaceError
        from .directory_entry import DirectoryEntry

        # Determinar nombre de archivo
        if filename is None:
            filename = os.path.basename(src_path)

        # Validar nombre de archivo
        validar_nombre_archivo(filename)

        # Verificar que no exista archivo con ese nombre
        for entry in self.directory_entries:
            if entry.is_active() and entry.filename.strip() == filename:
                raise FilenameConflictError(filename)

        # Leer archivo fuente
        with open(src_path, 'rb') as f:
            data = f.read()

        file_size = len(data)

        # Calcular clusters necesarios
        clusters_necesarios = calcular_clusters_necesarios(file_size)

        # Construir mapa de clusters
        cluster_map = self._build_cluster_map()

        # Buscar espacio contiguo
        start_cluster = cluster_map.find_contiguous_space(clusters_necesarios)

        if start_cluster is None:
            # No hay espacio contiguo suficiente
            clusters_disponibles = cluster_map.largest_contiguous_block()
            raise NoSpaceError(
                bytes_necesarios=file_size,
                bytes_disponibles=clusters_disponibles * 1024,
                clusters_necesarios=clusters_necesarios,
                clusters_disponibles=clusters_disponibles
            )

        # Escribir datos del archivo
        self._write_file_data(start_cluster, data)

        # Crear entrada de directorio
        new_entry = DirectoryEntry.create_file(filename, start_cluster, file_size)

        # Encontrar slot vacío en directorio
        slot_index = self._find_empty_directory_slot()

        # Escribir entrada de directorio
        self._write_directory_entry(slot_index, new_entry)

        return {
            'filename': filename,
            'bytes_copied': file_size,
            'start_cluster': start_cluster,
            'num_clusters': clusters_necesarios
        }

    def delete_file(self, filename: str) -> dict:
        """
        Elimina un archivo del filesystem.

        Args:
            filename: Nombre del archivo a eliminar

        Returns:
            Diccionario con resultado:
                - 'filename': Nombre del archivo eliminado
                - 'freed_clusters': Clusters liberados
                - 'freed_bytes': Bytes liberados

        Raises:
            FileNotFoundInFilesystemError: Si el archivo no existe
        """
        from .directory_entry import DirectoryEntry

        # Buscar el archivo
        entry = self._find_file(filename)

        # Calcular espacio liberado
        freed_clusters = entry.num_clusters_needed()
        freed_bytes = entry.file_size

        # Encontrar índice de la entrada en el directorio
        entry_index = None
        for i, e in enumerate(self.directory_entries):
            if e.is_active() and e.filename == filename:
                entry_index = i
                break

        # Crear entrada vacía
        empty_entry = DirectoryEntry.create_empty()

        # Escribir entrada vacía
        self._write_directory_entry(entry_index, empty_entry)

        return {
            'filename': filename,
            'freed_clusters': freed_clusters,
            'freed_bytes': freed_bytes
        }

    def close(self):
        """Cierra el file handle del filesystem."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

    def __enter__(self):
        """Soporte para context manager (with statement)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierre automático al salir del context manager."""
        self.close()
        return False
