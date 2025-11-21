import os
import struct

# constantes globales
nombreImagen = "fiunamfs.img"
clusterSize = 1024 #dos sectores de 512 bytes
entradaSize = 64
inicioDirectorio = clusterSize      
directorioSize = 4 * clusterSize  

def validar_superbloque(f):
    # valida la version 26-1
    f.seek(0)
    # Limpiamos nulos y espacios del nombre
    nombre_fs = f.read(8).decode('ascii', errors='ignore').replace('\x00', '').strip()
    f.seek(10)
    version = f.read(5).decode('ascii', errors='ignore').replace('\x00', '').strip() 
    
    # Validación 
    return nombre_fs == "FiUnamFS" and version == "26-1"

def listar_archivos():
    if not os.path.exists(nombreImagen):
        print("No se encuentra el archivo.")
        return

    with open(nombreImagen, 'rb') as f:
        if not validar_superbloque(f):
            print("Sistema de archivos inválido.")
            return
            
        print("\n--- Listado de Archivos ---")
        f.seek(inicioDirectorio)
        for _ in range(directorioSize // entradaSize):
            entrada = f.read(entradaSize)
            if entrada[0:1] == b'.': 
                nombre = entrada[1:15].decode('ascii', errors='ignore').strip()
                
                cluster_ini = struct.unpack('<I', entrada[16:20])[0]
                tamano = struct.unpack('<I', entrada[20:24])[0]
                print(f"{nombre.ljust(15)} | {tamano} bytes | Cluster {cluster_ini}")

def copiar_a_pc(nombre_buscado, destino):
    if not os.path.exists(nombreImagen): return

    with open(nombreImagen, 'rb') as f:
        f.seek(inicioDirectorio)
        for _ in range(directorioSize // entradaSize):
            entrada = f.read(entradaSize)
            if entrada[0:1] == b'.':
                nombre = entrada[1:15].decode('ascii', errors='ignore').strip()
                if nombre == nombre_buscado:
                    cluster_ini = struct.unpack('<I', entrada[16:20])[0]
                    tamano = struct.unpack('<I', entrada[20:24])[0]
                    
                    # Leer datos
                    f.seek(cluster_ini * clusterSize)
                    datos = f.read(tamano)
                    
                    # Escribir en disco local
                    with open(destino, 'wb') as out:
                        out.write(datos)
                    print(f"Archivo {nombre_buscado} extraído exitosamente.")
                    return
    print("Archivo no encontrado.")

def copiar_a_fiunamfs(ruta_origen, nombre_destino):
    if not os.path.exists(ruta_origen):
        print("El archivo origen no existe.")
        return

    tam_archivo = os.path.getsize(ruta_origen)
    
    with open(nombreImagen, 'r+b') as f:
        max_cluster_usado = 4 
        pos_directorio_libre = None
        
        f.seek(inicioDirectorio)
        
        # Barrido para buscar espacio en directorio y último cluster
        for _ in range(directorioSize // entradaSize):
            pos = f.tell()
            entrada = f.read(entradaSize)
            
            if entrada[0:1] == b'.':
                c_ini = struct.unpack('<I', entrada[16:20])[0]
                size = struct.unpack('<I', entrada[20:24])[0]
                clusters_ocupados = (size + clusterSize - 1) // clusterSize
                if (c_ini + clusters_ocupados) > max_cluster_usado:
                    max_cluster_usado = c_ini + clusters_ocupados - 1
            
            # Marco entrada vacía
            elif (entrada[0:1] == b'-' or entrada[0:1] == b'/') and pos_directorio_libre is None:
                pos_directorio_libre = pos 

        if pos_directorio_libre is None:
            print("Directorio lleno.")
            return

        nuevo_cluster_inicio = max_cluster_usado + 1
        
        # Escribir datos
        with open(ruta_origen, 'rb') as src:
            f.seek(nuevo_cluster_inicio * clusterSize)
            f.write(src.read())

        # Actualizar directorio 
        f.seek(pos_directorio_libre)
        
        nombre_fmt = nombre_destino[:14].ljust(14, ' ').encode('ascii')
        f.write(b'.') 
        f.write(nombre_fmt)
        f.write(b'\x00') 
        f.write(struct.pack('<I', nuevo_cluster_inicio)) 
        f.write(struct.pack('<I', tam_archivo)) 
        f.write(b'20260101000000') 
        f.write(b'20260101000000') 
        f.write(b'\x00' * 12)   
        
        print(f"Guardado en Cluster {nuevo_cluster_inicio}")

def eliminar(nombre_borrar):
    
    if not os.path.exists(nombreImagen): return

    with open(nombreImagen, 'r+b') as f:
        f.seek(inicioDirectorio)
        for _ in range(directorioSize // entradaSize):
            pos = f.tell()
            entrada = f.read(entradaSize)
            if entrada[0:1] == b'.':
                nombre = entrada[1:15].decode('ascii', errors='ignore').strip()
                if nombre == nombre_borrar:
                    
                    f.seek(pos)
                    f.write(b'-') 
                    f.write(b'.' * 14) 
                    print(f"Archivo {nombre} eliminado.")
                    return
    print("Archivo no encontrado.")
#menu
if __name__ == "__main__":
    if not os.path.exists(nombreImagen):
        print(f"AVISO: No se detectó {nombreImagen}.")
    
    while True:
        print("\n=== FiUnamFS 2026 (Modo Secuencial) ===")
        print("1. Listar")
        print("2. Copiar a PC (GET)")
        print("3. Copiar a FiUnamFS (PUT)")
        print("4. Eliminar (RM)")
        print("5. Salir")
        op = input("Selecciona una opcion: ")
        
        if op == '1': listar_archivos()
        elif op == '2': 
            n = input("Nombre archivo en FiUnamFS: ")
            d = input("Nombre destino en tu PC: ")
            copiar_a_pc(n, d)
        elif op == '3':
            o = input("Ruta archivo en tu PC: ")
            d = input("Nombre para guardar en FiUnamFS: ")
            copiar_a_fiunamfs(o, d)
        elif op == '4':
            n = input("Nombre archivo a borrar: ")
            eliminar(n)
        elif op == '5': break
        else: print("Opción inválida")
    print("Archivo no encontrado.")

if __name__ == "__main__":
    # Menu simple temporal
    listar_archivos()
