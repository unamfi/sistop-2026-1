import os
import struct

# Constantes globales
nombreImagen = "fiunamfs.img"
clusterSize = 1024 
entradaSize = 64
inicioDirectorio = clusterSize      
directorioSize = 4 * clusterSize  

def validar_superbloque(f):
    # Valida la version 26-1
    f.seek(0)
    nombre_fs = f.read(8).decode('ascii', errors='ignore').replace('\x00', '').strip()
    f.seek(10)
    version = f.read(5).decode('ascii', errors='ignore').replace('\x00', '').strip() 
    
    if nombre_fs == "FiUnamFS" and version == "26-1":
        return True, f"Sistema detectado: {nombre_fs} Versión {version}"
    else:
        return False, f"Error: Se esperaba 'FiUnamFS' v'26-1', se encontró '{nombre_fs}' v'{version}'"

if __name__ == "__main__":
    if os.path.exists(nombreImagen):
        with open(nombreImagen, 'r+b') as f:
            valido, msg = validar_superbloque(f)
            print(msg)
    else:
        print(f"No se encuentra {nombreImagen}")
