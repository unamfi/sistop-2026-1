import sys
import struct
#Sistemas Operativos: Proyecto 2
# ---------------------------------------------------------------------
# Hernández Irineo Jorge Manuel
# Zamora Ayala Antonio Manuel
# ---------------------------------------------------------------------
# Lectura y validación del superbloque de FiUnamFS
# ---------------------------------------------------------------------

def leer_superbloque(ruta_imagen):
    with open(ruta_imagen, "rb") as f:
        # Cluster 0 completo: 1 cluster = 2 sectores * 512 bytes = 1024 bytes
        superbloque = f.read(1024)

    # Campos según especificación
    # 0–8  : nombre del sistema de archivos (esperamos "FiUnamFS")
    # 10–14: versión (esperamos "26-2")
    # 20–35: etiqueta del volumen (16 bytes)
    # 40–44: tamaño del cluster en bytes (entero 32 bits, little endian)
    # 45–49: número de clusters reservados para el directorio (entero 32 bits)
    # 50–54: número de clusters que mide la unidad completa (entero 32 bits)

    # Nombre del sistema de archivos
    fs_name = superbloque[0:8].decode("ascii", errors="ignore").strip("\x00 ").strip()
    # Versión
    version = superbloque[10:15].decode("ascii", errors="ignore").strip("\x00 ").strip()
    # Etiqueta del volumen
    volume_label = superbloque[20:36].decode("ascii", errors="ignore").strip("\x00 ")

    # Enteros de 32 bits en little endian:
    # Tomamos 4 bytes para cada entero (aunque el rango diga 5, la especificación
    # marca que los enteros son de 32 bits)
    cluster_size_bytes = struct.unpack("<I", superbloque[40:44])[0]
    dir_clusters      = struct.unpack("<I", superbloque[45:49])[0]
    total_clusters    = struct.unpack("<I", superbloque[50:54])[0]

    return {
        "fs_name": fs_name,
        "version": version,
        "volume_label": volume_label,
        "cluster_size": cluster_size_bytes,
        "dir_clusters": dir_clusters,
        "total_clusters": total_clusters,
    }

def main():
    if len(sys.argv) != 2:
        print("Uso: python fiunamfs_info.py <imagen_fiunamfs>")
        sys.exit(1)

    ruta_imagen = sys.argv[1]
    info = leer_superbloque(ruta_imagen)

    # Validaciones básicas
    if info["fs_name"] != "FiUnamFS":
        print("ERROR: La imagen no parece ser un sistema de archivos FiUnamFS.")
        print(f"Nombre leído: '{info['fs_name']}'")
        sys.exit(1)

    if info["version"] != "26-1":
        print("ERROR: Versión incorrecta del sistema de archivos.")
        print(f"Versión leída: '{info['version']}' (se esperaba '26-2')")
        sys.exit(1)

    # Si todo está bien, mostramos la información del superbloque
    print("=== SuperbLoque de FiUnamFS ===")
    print(f"Nombre del FS      : {info['fs_name']}")
    print(f"Versión            : {info['version']}")
    print(f"Etiqueta del volumen: {info['volume_label']}")
    print(f"Tamaño de cluster  : {info['cluster_size']} bytes")
    print(f"Clusters de directorio: {info['dir_clusters']}")
    print(f"Total de clusters  : {info['total_clusters']}")

if __name__ == "__main__":
    main()
