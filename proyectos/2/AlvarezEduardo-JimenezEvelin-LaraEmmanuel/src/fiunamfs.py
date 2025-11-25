# fiunamfs.py
# Implementación principal de las operaciones sobre FiUnamFS.

import os
import struct
import time
import math
import threading

from constantes import (
    CLUSTER_SIZE_SUPERBLOQUE,
    ENTRY_SIZE,
    MAGIC,
    VERSION,
    DIR_START_CLUSTER,
)
from entradas import DirEntry
    # Representa cada entrada de directorio leída del área de directorios.
from estado import EstadoFS
    # Estructura para acumular estadísticas de uso (lecturas, escrituras, etc.)


class FiUnamFS:
    """
    Implementa las operaciones básicas de FiUnamFS:
    - Listar directorio
    - Copiar archivo desde la imagen al sistema local
    - Copiar archivo desde el sistema local a la imagen
    - Eliminar archivo de la imagen

    Además expone un método para calcular espacio libre que
    usa el hilo monitor.

    Internamente mantiene:
    - Un archivo binario abierto sobre la imagen (self.f)
    - El tamaño de cluster y número de clusters totales
    - La zona de directorio y la zona de datos (clusters de inicio)
    - Un lock para sincronizar operaciones concurrentes
    """

    def __init__(self, filename: str, estado: EstadoFS):
        # Validamos que la ruta de la imagen exista antes de abrirla.
        if not os.path.exists(filename):
            raise FileNotFoundError(f"[ERROR] No existe la imagen {filename}")

        # Ruta al archivo de imagen de FiUnamFS.
        self.filename = filename
        
        # Objeto de estado compartido con otros componentes (monitor, GUI).
        self.estado = estado
        
        # Lock para proteger operaciones de lectura/escritura concurrentes
        # desde distintos hilos.
        self.lock = threading.Lock()

        # Archivo subyacente abierto en modo lectura/escritura binario.
        self.f = open(filename, "r+b")

        # Propiedades leídas del superbloque.
        # Se inicializan a valores por defecto y luego se sobrescriben.
        self.etiqueta = ""
        self.cluster_size = CLUSTER_SIZE_SUPERBLOQUE
        self.dir_clusters = 0
        self.total_clusters = 0

        # Clusters lógicos de inicio de directorio y datos.
        self.dir_start_cluster = DIR_START_CLUSTER
        self.data_start_cluster = 0

        # Cargamos y validamos el superbloque al construir el objeto.
        self._leer_superbloque()

    # ============================================================
    #      SUPERBLOQUE
    # ============================================================
    def _leer_superbloque(self) -> None:
        """
        Lee el superbloque (cluster 0) y valida que la imagen
        corresponda a FiUnamFS de la versión correcta.

        Aquí se extrae:
        - cadena mágica
        - versión
        - etiqueta (nombre del volumen)
        - tamaño de cluster
        - número de clusters de directorio
        - número total de clusters
        """
        # Nos posicionamos al inicio del archivo (cluster 0).
        self.f.seek(0)
        
        # Leemos exactamente el tamaño de un cluster de superbloque.
        sb = self.f.read(CLUSTER_SIZE_SUPERBLOQUE)

        # Magic 0–8 (identificador del FS).
        magic = sb[0:8].decode("ascii")
        if magic != MAGIC:
            # Si no coincide con la constante, no es una imagen FiUnamFS válida.
            raise ValueError("[ERROR] Imagen inválida: no es FiUnamFS")

        # Versión 10–14
        version = sb[10:14].decode("ascii")
        if version != VERSION:
            # La versión de la imagen no corresponde con la esperada.
            raise ValueError(
                f"[ERROR] Versión incorrecta ({version}). Se requiere {VERSION}."
            )

        # Datos propios del superbloque:
        # Etiqueta (20–36).
        self.etiqueta = sb[20:36].decode("ascii").strip()
        
        # Tamaño de cluster (40–44), entero en little-endian.
        self.cluster_size = struct.unpack("<I", sb[40:44])[0]
        
        # Número de clusters asignados al directorio (45–49).
        self.dir_clusters = struct.unpack("<I", sb[45:49])[0]
        
        # Total de clusters en la imagen (50–54).
        self.total_clusters = struct.unpack("<I", sb[50:54])[0]

        # A partir de aquí, el directorio está en
        # [dir_start_cluster, dir_start_cluster + dir_clusters)
        # y la zona de datos queda después.
        self.data_start_cluster = self.dir_start_cluster + self.dir_clusters

        # Información útil para depuración.
        print("=== SUPERBLOQUE ===")
        print("Magic:", magic)
        print("Versión:", version)
        print("Etiqueta:", self.etiqueta)
        print("Tamaño de cluster:", self.cluster_size)
        print("Clusters de directorio:", self.dir_clusters)
        print("Clusters totales:", self.total_clusters)
        print("===================\n")

    # ============================================================
    #      DIRECTORIO
    # ============================================================
    def leer_directorio(self):
        """
        Lee todas las entradas del directorio y devuelve una lista de DirEntry.

        El directorio es contiguo en disco y ocupa 'dir_clusters' clusters
        a partir de 'dir_start_cluster'. Cada entrada tiene tamaño fijo de
        ENTRY_SIZE bytes; aquí se recorre la región de directorio y se
        interpretan dichos bloques como objetos DirEntry.
        """
        # Offset en bytes donde empieza el área de directorio.
        offset = self.dir_start_cluster * self.cluster_size
        self.f.seek(offset)
        
        # Leemos todos los clusters dedicados al directorio.
        raw = self.f.read(self.dir_clusters * self.cluster_size)

        entries = []
        # Recorremos el bloque crudo en "saltos" de ENTRY_SIZE.
        for i in range(0, len(raw), ENTRY_SIZE):
            entries.append(DirEntry(raw[i : i + ENTRY_SIZE]))
        return entries

    # ============================================================
    #      OPERACIONES DE ARCHIVO
    # ============================================================
    def copiar_desde(self, name: str, destino_local: str) -> None:
        """
        Copiar un archivo de la imagen FiUnamFS al sistema local.

        Parámetros:
        - name          : nombre del archivo dentro de FiUnamFS.
        - destino_local : ruta de salida en el sistema anfitrión.
        """
        # Protegemos la operación completa con el lock para evitar
        # inconsistencias si otro hilo escribe o elimina al mismo tiempo.
        with self.lock:
            entries = self.leer_directorio()
            # Buscamos la entrada cuyo nombre coincida exactamente.
            entry = next((e for e in entries if e.name == name), None)

            # Si no existe o está marcada como libre, avisamos y salimos.
            if entry is None or entry.is_empty():
                print(f"[ERROR] '{name}' no existe.")
                return
            
            # Posicionamos en el cluster de inicio del archivo y leemos
            # exactamente 'entry.size' bytes.
            self.f.seek(entry.start * self.cluster_size)
            data = self.f.read(entry.size)

            # Escribimos los datos en un archivo local.
            with open(destino_local, "wb") as f:
                f.write(data)

            # Actualizamos estadísticas y texto del último evento.
            self.estado.leidos += 1
            self.estado.ultimo_evento = (
                f"Copiado desde FS '{name}' a '{destino_local}'"
            )

            print(f"[OK] '{name}' copiado como '{destino_local}'")

    def copiar_hacia(self, archivo_local: str, nombre_fs: str) -> None:
        """
        Copiar un archivo del sistema local hacia la imagen FiUnamFS.

        Parámetros:
        - archivo_local : ruta del archivo en el sistema anfitrión.
        - nombre_fs     : nombre que tendrá dentro de FiUnamFS (máx. 14 chars).
        """
        with self.lock:
            # Validamos que el archivo local exista.
            if not os.path.exists(archivo_local):
                print("[ERROR] Archivo local no existe.")
                return

            # Tamaño en bytes del archivo a copiar.
            tam = os.path.getsize(archivo_local)
            
            # Leemos el directorio para:
            # - encontrar una entrada libre
            # - marcar los clusters ocupados por otros archivos.
            entries = self.leer_directorio()

            # Buscar índice de la primera entrada libre
            libre = next((i for i, e in enumerate(entries) if e.is_empty()), None)
            if libre is None:
                print("[ERROR] No hay entradas libres.")
                return

            # Conjunto de clusters actualmente utilizados por archivos existentes.
            usados = set()
            for e in entries:
                if not e.is_empty():
                    # Calculamos cuántos clusters ocupa el archivo,
                    # redondeando hacia arriba.
                    clusters_archivo = (e.size + self.cluster_size - 1) // self.cluster_size
                    # Marcamos cada cluster de ese rango como ocupado.
                    for c in range(e.start, e.start + clusters_archivo):
                        usados.add(c)

            # Cuántos clusters necesitamos para el nuevo archivo
            # (también con redondeo hacia arriba).
            clusters_necesarios = (tam + self.cluster_size - 1) // self.cluster_size

            # Buscamos un bloque contiguo de clusters libres en la zona de datos.
            cluster = self.data_start_cluster
            encontrado = False
            # Último cluster inicial posible para un bloque de 'clusters_necesarios'.
            limite = self.total_clusters - clusters_necesarios + 1

            while cluster < limite:
                # Verificamos que todos los clusters del bloque [cluster, cluster + k)
                # estén libres (no aparezcan en el conjunto 'usados').
                if all((cluster + k) not in usados for k in range(clusters_necesarios)):
                    encontrado = True
                    break
                cluster += 1

            if not encontrado:
                print("[ERROR] No hay clusters suficientes para almacenar el archivo.")
                return
            
            # Si llegamos aquí, 'cluster' es el primer cluster libre contiguo
            # donde vamos a escribir el archivo.

            # Leemos el archivo local completo en memoria.
            with open(archivo_local, "rb") as src:
                data = src.read()

            # Escribimos los datos en la zona de datos correspondiente.
            self.f.seek(cluster * self.cluster_size)
            self.f.write(data)

            # Construimos la nueva entrada de directorio en memoria como bytearray.
            nuevo = bytearray(ENTRY_SIZE)
            
            # Tipo: usamos '.' siguiendo la convención de FiUnamFS.
            nuevo[0:1] = b"."
            
            # Nombre: 14 caracteres, justificado a la izquierda con espacios.
            nuevo[1:15] = nombre_fs.ljust(14)[:14].encode("ascii")
            
            # Cluster de inicio y tamaño del archivo (little-endian).
            nuevo[16:20] = struct.pack("<I", cluster)
            nuevo[20:24] = struct.pack("<I", tam)

            # Fecha/hora actual para creación y modificación.
            fecha = time.strftime("%Y%m%d%H%M%S").encode("ascii")
            nuevo[24:38] = fecha
            nuevo[38:52] = fecha

            # Calculamos el offset en bytes de la entrada libre dentro del directorio.
            entrada_offset = (
                self.dir_start_cluster * self.cluster_size + libre * ENTRY_SIZE
            )
            self.f.seek(entrada_offset)
            self.f.write(nuevo)

            # Actualizamos estadísticas y último evento.
            self.estado.escritos += 1
            self.estado.ultimo_evento = (
                f"Copiado desde local '{archivo_local}' como '{nombre_fs}'"
            )

            print(f"[OK] '{archivo_local}' copiado como '{nombre_fs}'")

    def eliminar(self, name: str) -> None:
        """
        Eliminar un archivo de la imagen FiUnamFS (marcar entrada como libre).

        Nota: solo se marca la entrada como libre (se sobrescribe con puntos).
        Los datos en la zona de clusters quedan como "basura" reutilizable.
        """
        with self.lock:
            entries = self.leer_directorio()
            
            # Buscamos el índice de la entrada cuyo nombre coincide.
            idx = next((i for i, e in enumerate(entries) if e.name == name), None)

            if idx is None:
                print("[ERROR] Archivo no existe.")
                return

            # Offset en bytes donde se encuentra la entrada de directorio a eliminar.
            entrada_offset = (
                self.dir_start_cluster * self.cluster_size + idx * ENTRY_SIZE
            )
            
            # Nos posicionamos en la entrada y la llenamos completamente con puntos.
            # Esto hace que is_empty() la detecte como libre.
            self.f.seek(entrada_offset)
            self.f.write(b"." * ENTRY_SIZE)

            # Actualizamos estadísticas y último evento.
            self.estado.eliminados += 1
            self.estado.ultimo_evento = f"Eliminado '{name}'"

            print(f"[OK] '{name}' eliminado.")

    # ============================================================
    #      ESTADÍSTICAS Y ESPACIO LIBRE
    # ============================================================
    def calcular_espacio_libre(self):
        """
        Devuelve (clusters_libres, bytes_libres) aproximados en la zona de datos.

        El cálculo se basa en:
        - sumar los clusters ocupados por cada archivo (según su tamaño)
        - restarlo del total de clusters de datos
        - multiplicar por el tamaño de cluster para obtener bytes libres
        """
        entries = self.leer_directorio()

        # Contador de clusters ocupados por archivos.
        usados = 0
        for e in entries:
            if not e.is_empty():
                # Redondeo hacia arriba del número de clusters usados.
                clusters_archivo = (e.size + self.cluster_size - 1) // self.cluster_size
                usados += clusters_archivo

        # Total de clusters destinados a datos (excluyendo superbloque + directorio).
        total_datos = self.total_clusters - self.data_start_cluster
        
        # Clusters libres aproximados (no negativos).
        libres_clusters = max(total_datos - usados, 0)
        
        # Bytes libres a partir del número de clusters libres.
        libres_bytes = libres_clusters * self.cluster_size

        return libres_clusters, libres_bytes