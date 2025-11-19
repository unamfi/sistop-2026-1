import struct
import os
from datetime import datetime

# Constantes del sistema de archivos
CLUSTER_SIZE = 1024
TOTAL_CLUSTERS = 1440
DIR_CLUSTER_START = 1
DIR_CLUSTER_END = 4
ENTRIES_PER_CLUSTER = CLUSTER_SIZE // 64
ENTRY_SIZE = 64

ENTRY_STRUCT = struct.Struct("<c15sII14s14s12x")


class FiUnamFS:
    """Backend para manejo del sistema de archivos FiUnamFS"""
    
    def __init__(self, disk_path):
        self.disk = disk_path
        self.archivos = None
        
        if not os.path.exists(self.disk):
            raise FileNotFoundError(f"No existe imagen: {self.disk}")
    
    def leer_superbloque(self):
        """Lee y valida el superbloque"""
        with open(self.disk, "rb") as f:
            f.seek(0)
            raw = f.read(54)
            
            if len(raw) < 54:
                raise RuntimeError("Superbloque demasiado corto")
            
            nombre = raw[0:9].decode("ascii", errors="ignore").strip("\x00")
            version = raw[10:15].decode("ascii", errors="ignore").strip("\x00")
            etiqueta = raw[20:36].decode("ascii", errors="ignore").strip("\x00")
            tam_cluster = struct.unpack("<I", raw[40:44])[0]
            dir_clusters = struct.unpack("<I", raw[45:49])[0]
            total_clusters = struct.unpack("<I", raw[50:54])[0]
            
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
    
    def enlistar_directorio(self, mostrar_vacias=False):
        """Enlista todas las entradas del directorio"""
        archivos = []
        
        with open(self.disk, "rb") as f:
            # Recorrer clusters del directorio (1-4)
            for cl in range(DIR_CLUSTER_START, DIR_CLUSTER_END + 1):
                f.seek(cl * CLUSTER_SIZE)
                
                # Cada cluster tiene 16 entradas de 64 bytes
                for entry_index in range(ENTRIES_PER_CLUSTER):
                    entry_pos = cl * CLUSTER_SIZE + entry_index * ENTRY_SIZE
                    f.seek(entry_pos)
                    entry = f.read(ENTRY_SIZE)
                    
                    if len(entry) < ENTRY_SIZE:
                        continue
                    
                    try:
                        tipo_b, nombre_b, cluster, tam, creado_b, modif_b = \
                            ENTRY_STRUCT.unpack(entry)
                    except struct.error:
                        continue
                    
                    # Decodificar campos
                    tipo = tipo_b.decode("ascii", errors="ignore")
                    nombre = nombre_b.decode("ascii", errors="ignore") \
                                   .rstrip("\x00").strip()
                    creado = creado_b.decode("ascii", errors="ignore").strip("\x00")
                    modif = modif_b.decode("ascii", errors="ignore").strip("\x00")
                    
                    # Detectar entrada vacía
                    es_vacia = (tipo == "-" or nombre == "" or 
                               nombre.replace(".", "") == "")
                    
                    if not mostrar_vacias and es_vacia:
                        continue
                    
                    archivos.append({
                        "Nombre": nombre if nombre else "..............",
                        "Tamaño": tam,
                        "Cluster": cluster,
                        "Creado": creado,
                        "Modificado": modif,
                        "entry_pos": entry_pos,
                        "es_vacia": es_vacia,
                    })
        
        # Guardar solo archivos reales en caché
        self.archivos = [a for a in archivos if not a.get("es_vacia", False)]
        return archivos


# Prueba de enlistado
if __name__ == "__main__":
    try:
        fs = FiUnamFS("../fiunamfs.img")
        
        print("=== Superbloque ===")
        info = fs.leer_superbloque()
        for k, v in info.items():
            print(f"{k}: {v}")
        
        print("\n=== Directorio ===")
        archivos = fs.enlistar_directorio()
        
        if not archivos:
            print("(directorio vacío)")
        else:
            print(f"{'Nombre':<15} {'Tamaño':>10} {'Cluster':>8} {'Creado':<20}")
            print("-" * 70)
            for a in archivos:
                # Formatear fechas si es posible
                try:
                    creado = datetime.strptime(a["Creado"], "%Y%m%d%H%M%S") \
                                    .strftime("%Y-%m-%d %H:%M:%S")
                except:
                    creado = a["Creado"]
                
                print(f"{a['Nombre']:<15} {a['Tamaño']:>10} {a['Cluster']:>8} {creado:<20}")
    
    except Exception as e:
        print(f"Error: {e}")