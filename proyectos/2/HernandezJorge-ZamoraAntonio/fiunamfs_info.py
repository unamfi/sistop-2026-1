import sys
import struct
import math
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

def leer_directorio(ruta_imagen, cluster_size, dir_clusters):
    entradas = []

    with open(ruta_imagen, "rb") as f:
        # El directorio comienza en el cluster 1
        inicio_directorio = cluster_size  # 1 * cluster_size
        f.seek(inicio_directorio)

        total_entradas = (cluster_size * dir_clusters) // 64

        for i in range(total_entradas):
            entrada = f.read(64)

            nombre = entrada[0:15].decode("ascii", errors="ignore").strip()

            # Ignorar entradas vacías
            if nombre == "" or nombre.startswith("."):
                continue

            # Tamaño del archivo (bytes) → offset 16-23
            tam = struct.unpack("<I", entrada[16:20])[0]

            # Cluster inicial → offset 24-27
            cluster_ini = struct.unpack("<I", entrada[24:28])[0]

            entradas.append((nombre, tam, cluster_ini))

    return entradas
#Leer entradas sin filtrar
def leer_directorio_raw(ruta_imagen, cluster_size, dir_clusters):
    entradas = []
    
    with open(ruta_imagen, "rb") as f:
        inicio_directorio = cluster_size
        total_entradas = (cluster_size * dir_clusters) // 64
        
        for i in range(total_entradas):
            f.seek(inicio_directorio + i * 64)
            entrada = f.read(64)
            
            nombre = entrada[0:15].decode("ascii", errors="ignore")
            tam = struct.unpack("<I", entrada[16:20])[0]
            cluster_ini = struct.unpack("<I", entrada[24:28])[0]
            
            #entradas.append((nombre.strip(), tam, cluster_ini))
            entradas.append((nombre.strip("\x00 ").rstrip(), tam, cluster_ini))
    
    return entradas

def leer_archivo(ruta_imagen, info, nombre_buscado):
    cluster_size = info["cluster_size"]

    # Primero buscamos la entrada del archivo en el directorio
    entradas = leer_directorio(ruta_imagen, cluster_size, info["dir_clusters"])

    for nombre, tam, cluster_ini in entradas:
        #if nombre == nombre_buscado:
        if nombre.startswith(nombre_buscado):
            with open(ruta_imagen, "rb") as f:
                # Posición física del archivo dentro de la imagen
                pos = cluster_ini * cluster_size
                f.seek(pos)

                contenido = f.read(tam)
                return contenido

    return None

def buscar_entrada_libre(ruta_imagen, cluster_size, dir_clusters):
    with open(ruta_imagen, "rb") as f:
        inicio_directorio = cluster_size
        f.seek(inicio_directorio)

        total_entradas = (cluster_size * dir_clusters) // 64

        for i in range(total_entradas):
            pos = inicio_directorio + (i * 64)
            f.seek(pos)
            nombre = f.read(15).decode("ascii", errors="ignore")

            if nombre.startswith(".") or nombre.strip() == "":
                return i  # índice de entrada libre

    return -1  # No hay espacio

def copiar_a_fiunamfs(ruta_imagen, info, archivo_local, nombre_destino):

    cluster_size = info['cluster_size']

    # Obtener clusters ocupados
    entradas = leer_directorio(ruta_imagen, cluster_size, info['dir_clusters'])
    ocupados = obtener_clusters_ocupados(entradas, cluster_size)

    # Buscar cluster libre
    cluster_ini = buscar_cluster_libre(info, ocupados)

    if cluster_ini == -1:
        print("ERROR: No hay clusters libres para almacenar el archivo.")
        return False

    # Leer archivo desde la PC
    try:
        with open(archivo_local, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo local '{archivo_local}'.")
        return False

    tam = len(data)

    if tam > cluster_size:
        print("ERROR: El archivo es demasiado grande (solo soporta <=1 cluster por ahora).")
        return False

    # Buscar entrada de directorio libre
    entrada_idx = buscar_entrada_libre(ruta_imagen, cluster_size, info['dir_clusters'])
    if entrada_idx == -1:
        print("ERROR: No hay espacio en el directorio.")
        return False

    with open(ruta_imagen, "r+b") as img:
        # Escribir contenido
        img.seek(cluster_ini * cluster_size)
        img.write(data)

        # Actualizar entrada del directorio
        inicio_directorio = cluster_size
        pos_entrada = inicio_directorio + (entrada_idx * 64)

        img.seek(pos_entrada)
        nombre_bytes = nombre_destino.ljust(15, "\x00").encode("ascii")
        img.write(nombre_bytes)

        img.seek(pos_entrada + 16)
        img.write(struct.pack("<I", tam))

        img.seek(pos_entrada + 24)
        img.write(struct.pack("<I", cluster_ini))

    print(f"Archivo '{nombre_destino}' copiado exitosamente al FS (cluster {cluster_ini}).")
    return True


def obtener_clusters_ocupados(entradas, cluster_size):
    ocupados = set()

    for _, tam, cluster_ini in entradas:
        if cluster_ini > 0:
            usados = math.ceil(tam / cluster_size)
            for c in range(cluster_ini, cluster_ini + usados):
                ocupados.add(c)

    return ocupados

def buscar_cluster_libre(info, ocupados):
    primer_data_cluster = 1 + info["dir_clusters"]
    total_clusters = info["total_clusters"]

    for c in range(primer_data_cluster, total_clusters):
        if c not in ocupados:
            return c

    return -1  # No hay espacio disponible

def copiar_de_fiunamfs(ruta_imagen, info, nombre_archivo_fs, nombre_destino_pc):
    contenido = leer_archivo(ruta_imagen, info, nombre_archivo_fs)

    if contenido is None:
        print(f"ERROR: El archivo '{nombre_archivo_fs}' no se encontró en el FS.")
        return False

    # Guardar en PC
    with open(nombre_destino_pc, "wb") as f:
        f.write(contenido)

    print(f"Archivo '{nombre_archivo_fs}' exportado correctamente como '{nombre_destino_pc}'.")
    return True

def borrar_archivo(ruta_imagen, info, nombre_buscado):
    cluster_size = info['cluster_size']
    dir_clusters = info['dir_clusters']

    entradas_raw = leer_directorio_raw(ruta_imagen, cluster_size, dir_clusters)

    # Buscar posición real exacta en el directorio
    for i, (nombre, tam, cluster_ini) in enumerate(entradas_raw):
        #if nombre == nombre_buscado:
        if nombre.strip("\x00 ").rstrip() == nombre_buscado:
            # Encontramos la entrada válida en el directorio
            pos = cluster_size + (i * 64)

            with open(ruta_imagen, "r+b") as img:
                img.seek(pos)
                img.write(b"." + b"\x00" * 14)
            
            print(f"Archivo '{nombre_buscado}' borrado lógicamente.")
            return True

    print(f"ERROR: El archivo '{nombre_buscado}' no existe en el FS.")
    return False

def compactar(ruta_imagen, info):
    cluster_size = info["cluster_size"]
    dir_clusters = info["dir_clusters"]
    
    # Leer entradas válidas y ordenar por cluster
    entradas = leer_directorio(ruta_imagen, cluster_size, dir_clusters)
    entradas.sort(key=lambda x: x[2])  # ordenar por cluster inicial

    primer_cluster_libre = 1 + dir_clusters

    with open(ruta_imagen, "r+b") as img:
        for nombre, tam, cluster_ini in entradas:
            if cluster_ini > primer_cluster_libre:
                # Leer contenido del archivo
                img.seek(cluster_ini * cluster_size)
                data = img.read(tam)

                # Moverlo al primer cluster libre
                img.seek(primer_cluster_libre * cluster_size)
                img.write(data)

                # Limpiar cluster viejo
                img.seek(cluster_ini * cluster_size)
                img.write(b"\x00" * tam)

                # Actualizar el directorio
                actualizar_cluster_directorio(img, nombre, primer_cluster_libre, info)

            primer_cluster_libre += math.ceil(tam / cluster_size)

    print("Compactación completada.")

#funcion auxiliar para actualizar el directorio
def actualizar_cluster_directorio(img, nombre_buscado, nuevo_cluster, info):
    cluster_size = info["cluster_size"]
    dir_clusters = info["dir_clusters"]

    inicio_directorio = cluster_size
    total_entradas = (cluster_size * dir_clusters) // 64

    for i in range(total_entradas):
        pos = inicio_directorio + i * 64
        img.seek(pos)
        nombre = img.read(15).decode("ascii", errors="ignore").strip("\x00 ").rstrip()
        
        if nombre == nombre_buscado:
            img.seek(pos + 24)
            img.write(struct.pack("<I", nuevo_cluster))
            return 

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

    # Leer y listar directorio
    print("\n=== Archivos en el directorio ===")
    entradas = leer_directorio(ruta_imagen,
                               info['cluster_size'],
                               info['dir_clusters'])

    if not entradas:
        print("No hay archivos en el sistema de archivos.")
    else:
        for nombre, tam, cluster in entradas:
            print(f"{nombre:20}  {tam:10} bytes  Cluster: {cluster}")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # ===== Prueba de lectura de archivo =====
    nombre_prueba = "hola.txt"
    contenido = leer_archivo(ruta_imagen, info, nombre_prueba)

    print("\n=== Lectura de archivo de prueba ===")
    if contenido is None:
        print(f"El archivo '{nombre_prueba}' no se encontró en el FS.")
    else:
        print(f"Contenido de '{nombre_prueba}':\n")
        try:
            print(contenido.decode("ascii", errors="ignore"))
        except:
            print("No se pudo mostrar como texto.")

    #Las siguientes partes de código se activaran o desactivaron según la accion que se desea hacer
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><
    # ===== Copiar archivo de prueba al FS =====
    print("\n=== Copiar archivo de prueba ===")
    archivo_local = "hola.txt"
    nombre_dest = "hola.txt"

    if copiar_a_fiunamfs(ruta_imagen, info, archivo_local, nombre_dest):
        print("Verifique con el listado del directorio.")
    else:
        print("No se pudo copiar el archivo.")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><>>>>>>>>>>>>>>>>>>
    # ===== Exportar archivo a PC =====
    print("\n=== Exportar archivo desde el FS ===")
    
    archivo_fs = "datos1.txt"   # archivo dentro del FS
    archivo_pc = "copia_datos1.txt"  # nombre de salida en la PC

    if copiar_de_fiunamfs(ruta_imagen, info, archivo_fs, archivo_pc):
        print("Exportación completada.")
    else:
        print("No se pudo exportar el archivo.")

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #BORRADO DE ARCHIVO DESEADO
    print("\n=== Borrar archivo ===")
    archivo_a_borrar = "datos2.txt"

    if borrar_archivo(ruta_imagen, info, archivo_a_borrar):
        print("Borrado realizado, verificar nuevamente con listado.")
    else:
        print("No se pudo borrar el archivo.")
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    #COMPACTACION
    print("\n=== Compactando FS ===")
    compactar(ruta_imagen, info)

    print("\n=== Directorio tras compactación ===")
    entradas = leer_directorio(ruta_imagen, info["cluster_size"], info["dir_clusters"])
    for nombre, tam, cluster in entradas:
        print(f"{nombre:20} {tam:10} bytes Cluster: {cluster}")

if __name__ == "__main__":
    main()
