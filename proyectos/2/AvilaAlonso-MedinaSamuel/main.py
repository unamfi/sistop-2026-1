from threading import RLock
import math

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