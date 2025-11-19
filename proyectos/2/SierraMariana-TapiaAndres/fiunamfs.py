#!/usr/bin/env python3

import struct
import os

# Constantes del sistema de archivos
CLUSTER_SIZE = 1024
TOTAL_CLUSTERS = 1440
DIR_CLUSTER_START = 1
DIR_CLUSTER_END = 4
ENTRIES_PER_CLUSTER = CLUSTER_SIZE // 64
ENTRY_SIZE = 64

# Estructura de entrada del directorio (64 bytes)
ENTRY_STRUCT = struct.Struct("<c15sII14s14s12x")


class FiUnamFS:
    def __init__(self, disk_path):
        self.disk = disk_path
        self.archivos = None
        if not os.path.exists(self.disk):
            raise FileNotFoundError(f"No existe imagen: {self.disk}")
    
    def leer_superbloque(self):
        with open(self.disk, "rb") as f:
            f.seek(0)
            raw = f.read(54)
            
            # Extraer campos
            nombre = raw[0:9].decode("ascii", errors="ignore").strip("\x00")
            version = raw[10:15].decode("ascii", errors="ignore").strip("\x00")
            etiqueta = raw[20:36].decode("ascii", errors="ignore").strip("\x00")
            tam_cluster = struct.unpack("<I", raw[40:44])[0]
            dir_clusters = struct.unpack("<I", raw[45:49])[0]
            total_clusters = struct.unpack("<I", raw[50:54])[0]
            
            # Validaciones
            if nombre != "FiUnamFS":
                raise ValueError(f"No es FiUnamFS (nombre='{nombre}')")
            
            if version != "26-1":
                print(f"[ADVERTENCIA] Versión: {version} (esperada: 26-1)") 
            
            return {
                "Nombre": nombre,
                "Version": version,
                "Etiqueta": etiqueta,
                "Tamano_Cluster": tam_cluster,
                "Clusters_Directorio": dir_clusters,
                "Total_Clusters": total_clusters,
            }
# Prueba básica
if __name__ == "__main__":
    try:
        fs = FiUnamFS("../fiunamfs.img")
        info = fs.leer_superbloque()
        print("=== Superbloque ===")
        for k, v in info.items():
            print(f"{k}: {v}")
    except Exception as e:
        print(f"Error: {e}")