import os
import struct

nombreImagen = "fiunamfs.img"
clusterSize = 1024 
entradaSize = 64
inicioDirectorio = clusterSize      
directorioSize = 4 * clusterSize  

def validar_superbloque(f):
    f.seek(0)
    nombre_fs = f.read(8).decode('ascii', errors='ignore').replace('\x00', '').strip()
    f.seek(10)
    version = f.read(5).decode('ascii', errors='ignore').replace('\x00', '').strip() 
    return nombre_fs == "FiUnamFS" and version == "26-1"

def listar_archivos():
    with open(nombreImagen, 'rb') as f:
        if not validar_superbloque(f): return
        print("\n--- Listado ---")
        f.seek(inicioDirectorio)
        for _ in range(directorioSize // entradaSize):
            entrada = f.read(entradaSize)
            if entrada[0:1] == b'.': 
                nombre = entrada[1:15].decode('ascii', errors='ignore').strip()
                cluster_ini = struct.unpack('<I', entrada[16:20])[0]
                tamano = struct.unpack('<I', entrada[20:24])[0]
                print(f"{nombre.ljust(15)} | {tamano} bytes | Cluster {cluster_ini}")

def copiar_a_pc(nombre_buscado, destino):
    with open(nombreImagen, 'rb') as f:
        f.seek(inicioDirectorio)
        for _ in range(directorioSize // entradaSize):
            entrada = f.read(entradaSize)
            if entrada[0:1] == b'.':
                nombre = entrada[1:15].decode('ascii', errors='ignore').strip()
                if nombre == nombre_buscado:
                    cluster = struct.unpack('<I', entrada[16:20])[0]
                    tam = struct.unpack('<I', entrada[20:24])[0]
                    f.seek(cluster * clusterSize)
                    datos = f.read(tam)
                    with open(destino, 'wb') as out:
                        out.write(datos)
                    print("Archivo copiado.")
                    return
    print("Archivo no encontrado.")

if __name__ == "__main__":
    # Menu simple temporal
    listar_archivos()
