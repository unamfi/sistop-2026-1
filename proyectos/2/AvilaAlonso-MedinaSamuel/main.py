import struct
from threading import RLock, Condition
import math
import os
from datetime import datetime

# ============================================================================
# CAPA DE ACCESO AL DISCO
# ============================================================================

class DiscoVirtual:
    SECTOR_SIZE = 512
    CLUSTER_SIZE = 1024
    SUPERBLOCK_CLUSTER = 0
    DIR_START_CLUSTER = 1
    DIR_CLUSTERS = 4  # Clusters 1-4 para directorio
    TOTAL_SIZE = 1440 * 1024  # 1440 KB

    def __init__(self, path):
        self.path = path
        self.lock = RLock()

    def leer_cluster(self, cluster_num):
        with self.lock:
            with open(self.path, 'rb') as f:
                f.seek(cluster_num * self.CLUSTER_SIZE)
                return f.read(self.CLUSTER_SIZE)

    def escribir_cluster(self, cluster_num, data):
        with self.lock:
            with open(self.path, 'r+b') as f:
                f.seek(cluster_num * self.CLUSTER_SIZE)
                f.write(data)

    def leer_bytes(self, offset, size):
        with self.lock:
            with open(self.path, 'rb') as f:
                f.seek(offset)
                return f.read(size)

    def escribir_bytes(self, offset, data):
        with self.lock:
            with open(self.path, 'r+b') as f:
                f.seek(offset)
                f.write(data)
    
    def leer_multiples_clusters(self, cluster_inicial, num_clusters):
        """Lee múltiples clusters contiguos"""
        with self.lock:
            data = b''
            for i in range(num_clusters):
                data += self.leer_cluster(cluster_inicial + i)
            return data
    
    def escribir_multiples_clusters(self, cluster_inicial, data):
        """Escribe datos en múltiples clusters contiguos"""
        with self.lock:
            num_clusters = math.ceil(len(data) / self.CLUSTER_SIZE)
            for i in range(num_clusters):
                inicio = i * self.CLUSTER_SIZE
                fin = min(inicio + self.CLUSTER_SIZE, len(data))
                cluster_data = data[inicio:fin]
                
                if len(cluster_data) < self.CLUSTER_SIZE:
                    cluster_data += b'\x00' * (self.CLUSTER_SIZE - len(cluster_data))
                self.escribir_cluster(cluster_inicial + i, cluster_data)
                
  # ============================================================================
# VALIDADOR Y METADATOS
# ============================================================================

class Superbloque:
    def __init__(self, disco):
        self.disco = disco
        self._cargar_y_validar()

    def _cargar_y_validar(self):
        sb_data = self.disco.leer_cluster(0)

        try:
            nombre, version, etiqueta, tam_cluster, dir_clusters, total_clusters = struct.unpack(
                '<9s1x5s5x16s4xI1xI1xI', sb_data[:54]
            )
            
            self.nombre = nombre.decode('ascii').strip('\x00')
            self.version = version.decode('ascii').strip('\x00')
            self.label = etiqueta.decode('ascii').strip('\x00')
            self.cluster_size = tam_cluster
            self.dir_clusters = dir_clusters
            self.total_clusters = total_clusters
            
        except:
            raise ValueError("Error leyendo superbloque")

        if self.nombre != 'FiUnamFS':
            raise ValueError(f"Sistema de archivos no válido: {self.nombre}")
        
        
        if self.version != '26-1':
            raise ValueError(f"Versión incorrecta: esperada 26-1, encontrada {self.version}")

    def obtener_info(self):
        """Retorna información formateada del superbloque"""
        return {
            "Nombre": self.nombre,
            "Versión": self.version,
            "Etiqueta de Volumen": self.label,
            "Tamaño de Cluster": f"{self.cluster_size} bytes",
            "Clusters de Directorio": self.dir_clusters,
            "Total de Clusters": self.total_clusters
        }
        
        
# ============================================================================
# GESTOR DE ENTRADAS DE DIRECTORIO
# ============================================================================

class EntradaDirectorio:
    SIZE = 64
    EMPTY_MARKER = b'-'  
    DELETED_MARKER = b'#'
    VALID_TYPE = b'.'  
    EMPTY_NAME = '...............'

    def __init__(self, raw_data=None):
        if raw_data:
            self._parse(raw_data)
        else:
            self.tipo = '-'
            self.nombre = self.EMPTY_NAME
            self.cluster_inicial = 0
            self.tamano = 0
            self.fecha_creacion = ''
            self.fecha_modificacion = ''

    def _parse(self, data):
        self.tipo = chr(data[0])
        self.nombre = data[1:16].decode('ascii', errors='ignore').strip('\x00').strip()
        self.cluster_inicial = struct.unpack('<I', data[16:20])[0]
        self.tamano = struct.unpack('<I', data[20:24])[0]
        self.fecha_creacion = data[24:38].decode('ascii', errors='ignore').strip('\x00')
        self.fecha_modificacion = data[38:52].decode('ascii', errors='ignore').strip('\x00')

    def is_empty(self):
        return (self.tipo == '-' or 
                self.tipo == '#' or
                self.nombre == self.EMPTY_NAME or 
                self.nombre == '' or
                '...............' in self.nombre)

    def to_bytes(self):
        nombre_enc = self.nombre.encode('ascii')[:15].ljust(15, b'\x00')
        fecha_cr = self.fecha_creacion.encode('ascii')[:14].ljust(14, b'\x00')
        fecha_mod = self.fecha_modificacion.encode('ascii')[:14].ljust(14, b'\x00')

        return struct.pack('<c15sII14s14s12s',
                          self.tipo.encode('ascii') if self.tipo else b'.',
                          nombre_enc,
                          self.cluster_inicial,
                          self.tamano,
                          fecha_cr,
                          fecha_mod,
                          b'\x00' * 12)

class Directorio:
    def __init__(self, disco):
        self.disco = disco
        self.lock = RLock()
        self.entradas = self._cargar_entradas()

    def _cargar_entradas(self):
        entradas = []
        # Clusters 1-4 para directorio
        for cluster in range(1, 5):
            for entrada_idx in range(16):
                offset = (cluster * DiscoVirtual.CLUSTER_SIZE) + (entrada_idx * EntradaDirectorio.SIZE)
                data = self.disco.leer_bytes(offset, EntradaDirectorio.SIZE)
                entrada = EntradaDirectorio(data)
                idx_global = (cluster - 1) * 16 + entrada_idx
                entradas.append((idx_global, entrada))
        return entradas

    def recargar(self):
        """Recarga las entradas del directorio desde disco"""
        with self.lock:
            self.entradas = self._cargar_entradas()

    def listar_archivos(self):
        with self.lock:
            return [(idx, e) for idx, e in self.entradas if not e.is_empty()]

    def buscar_por_nombre(self, nombre):
        with self.lock:
            for idx, entrada in self.entradas:
                if entrada.nombre == nombre and not entrada.is_empty():
                    return idx, entrada
            return None, None

    def encontrar_entrada_libre(self):
        with self.lock:
            for idx, entrada in self.entradas:
                if entrada.is_empty():
                    return idx
            return None

    def actualizar_entrada(self, indice, entrada):
        with self.lock:
            cluster = 1 + (indice // 16)
            entrada_en_cluster = indice % 16
            offset = (cluster * DiscoVirtual.CLUSTER_SIZE) + (entrada_en_cluster * EntradaDirectorio.SIZE)
            
            self.disco.escribir_bytes(offset, entrada.to_bytes())
            self.entradas[indice] = (indice, entrada)

    def marcar_como_libre(self, indice):
        entrada = EntradaDirectorio()
        entrada.tipo = '-'  # Marcar como vacío con '-'
        entrada.nombre = '...............'
        self.actualizar_entrada(indice, entrada)

# ============================================================================
# GESTOR DE ESPACIO EN DISCO
# ============================================================================

class GestorEspacio:
    def __init__(self, disco, total_clusters):
        self.disco = disco
        self.total_clusters = total_clusters  # Guardamos el valor real del disco
        self.lock = RLock()
        
    def buscar_espacio_contiguo(self, num_clusters):
        """Busca espacio contiguo para num_clusters"""
        with self.lock:
            inicio = DiscoVirtual.DIR_START_CLUSTER + DiscoVirtual.DIR_CLUSTERS
            total = self.total_clusters 
            
            clusters_libres_consecutivos = 0
            cluster_inicial = None
            
            for c in range(inicio, total):
                data = self.disco.leer_cluster(c)
                if all(b == 0 for b in data):
                    if cluster_inicial is None:
                        cluster_inicial = c
                    clusters_libres_consecutivos += 1
                    
                    if clusters_libres_consecutivos == num_clusters:
                        return cluster_inicial
                else:
                    clusters_libres_consecutivos = 0
                    cluster_inicial = None
                    
            return None
    
    def liberar_clusters(self, cluster_inicial, num_clusters):
        """Libera clusters escribiendo ceros"""
        with self.lock:
            for i in range(num_clusters):
                self.disco.escribir_cluster(cluster_inicial + i, b'\x00' * DiscoVirtual.CLUSTER_SIZE)
    
    def obtener_espacio_disponible(self):
        """Retorna información de espacio disponible"""
        with self.lock:
            inicio = DiscoVirtual.DIR_START_CLUSTER + DiscoVirtual.DIR_CLUSTERS
            total = self.total_clusters
            clusters_libres = 0
            bytes_libres = 0 
            
            for c in range(inicio, total):
                data = self.disco.leer_cluster(c)
                if all(b == 0 for b in data):
                    clusters_libres += 1
                    bytes_libres += DiscoVirtual.CLUSTER_SIZE
            
            return {
                'clusters_libres': clusters_libres,
                'bytes_libres': bytes_libres,
                'clusters_totales': total - inicio,
                'bytes_totales': (total - inicio) * DiscoVirtual.CLUSTER_SIZE
            }

# ============================================================================
# OPERACIONES DEL SISTEMA DE ARCHIVOS
# ============================================================================

class FileSystemOps:
    def __init__(self, disco_path):
        self.disco = DiscoVirtual(disco_path)
        self.sb = Superbloque(self.disco)
        self.directorio = Directorio(self.disco)
        self.gestor_espacio = GestorEspacio(self.disco, self.sb.total_clusters)
        self.lock_ops = RLock()
        self.cambio_notificacion = Condition()

    def listar(self):
        with self.lock_ops:
            self.directorio.recargar()
            return self.directorio.listar_archivos()

    def extraer_archivo(self, nombre_fs, ruta_destino):
        """Extrae archivo del FS a la computadora"""
        with self.lock_ops:
            idx, entrada = self.directorio.buscar_por_nombre(nombre_fs)

            if entrada is None:
                raise FileNotFoundError(f"Archivo '{nombre_fs}' no encontrado")

            clusters_necesarios = math.ceil(entrada.tamano / DiscoVirtual.CLUSTER_SIZE)
            
            data = self.disco.leer_multiples_clusters(
                entrada.cluster_inicial, 
                clusters_necesarios
            )
            
            data = data[:entrada.tamano]

            if os.path.isdir(ruta_destino):
                ruta_destino = os.path.join(ruta_destino, nombre_fs)

            with open(ruta_destino, 'wb') as f:
                f.write(data)

            return ruta_destino

    def agregar_archivo(self, ruta_origen, nombre_fs=None):
        """Agrega archivo al FS"""
        with self.lock_ops:
            if nombre_fs is None:
                nombre_fs = os.path.basename(ruta_origen)
            
            if len(nombre_fs) > 15:
                raise ValueError("Nombre demasiado largo (máx 15 caracteres)")

            idx_existente, _ = self.directorio.buscar_por_nombre(nombre_fs)
            if idx_existente is not None:
                raise ValueError(f"Ya existe un archivo con el nombre '{nombre_fs}'")

            with open(ruta_origen, 'rb') as f:
                contenido = f.read()

            tamano = len(contenido)
            clusters_necesarios = math.ceil(tamano / DiscoVirtual.CLUSTER_SIZE)

            espacio = self.gestor_espacio.obtener_espacio_disponible()
            if espacio['clusters_libres'] < clusters_necesarios:
                raise ValueError(f"Espacio insuficiente")

            idx_libre = self.directorio.encontrar_entrada_libre()
            if idx_libre is None:
                raise ValueError("Directorio lleno")

            cluster_inicial = self.gestor_espacio.buscar_espacio_contiguo(clusters_necesarios)
            if cluster_inicial is None:
                raise ValueError(f"No hay espacio contiguo suficiente")

            self.disco.escribir_multiples_clusters(cluster_inicial, contenido)

            nueva_entrada = EntradaDirectorio()
            nueva_entrada.tipo = '.'
            nueva_entrada.nombre = nombre_fs
            nueva_entrada.cluster_inicial = cluster_inicial
            nueva_entrada.tamano = tamano
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            nueva_entrada.fecha_creacion = timestamp
            nueva_entrada.fecha_modificacion = timestamp

            self.directorio.actualizar_entrada(idx_libre, nueva_entrada)
            
            with self.cambio_notificacion:
                self.cambio_notificacion.notify_all()

    def eliminar_archivo(self, nombre_fs):
        """Elimina archivo del FS"""
        with self.lock_ops:
            idx, entrada = self.directorio.buscar_por_nombre(nombre_fs)

            if entrada is None:
                raise FileNotFoundError(f"Archivo '{nombre_fs}' no encontrado")

            clusters_a_liberar = math.ceil(entrada.tamano / DiscoVirtual.CLUSTER_SIZE)
            
            self.gestor_espacio.liberar_clusters(entrada.cluster_inicial, clusters_a_liberar)

            self.directorio.marcar_como_libre(idx)
            
            with self.cambio_notificacion:
                self.cambio_notificacion.notify_all()

    def obtener_info_superbloque(self):
        return self.sb.obtener_info()
    
    def obtener_info_espacio(self):
        return self.gestor_espacio.obtener_espacio_disponible()