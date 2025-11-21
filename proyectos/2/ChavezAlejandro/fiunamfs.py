import struct
import os
import sys
import threading
import queue
import datetime
import time

# PRIMERA SECCION DEL PROYECTO

def leer_superbloque(ruta_archivo):

    #Lee el superbloque del sistema de archivos FiUnamFS
    #Valida que sea el sistema correcto y muestra sus metadatos
    
    try:
        with open(ruta_archivo, 'rb') as f:
            #Para aseguramos de estar al inicio del archivo
            f.seek(0)
            
            #Se leen los primeros 54 bytes 
            superbloque_data = f.read(54)
            
            if not superbloque_data:
                print("Error: El archivo esta vacio o no se pudo leer")
                return

            nombre_fs = superbloque_data[0:8].decode('ascii').strip()
            version_fs = superbloque_data[10:14].decode('ascii').strip()
            etiqueta_vol = superbloque_data[20:36].decode('ascii').strip()
            
            #struct.unpack con <I para los enteros
            tam_cluster = struct.unpack('<I', superbloque_data[40:44])[0]
            num_cluster_dir = struct.unpack('<I', superbloque_data[45:49])[0]
            num_cluster_total = struct.unpack('<I', superbloque_data[50:54])[0]

            print(f" SISTEMA DE ARCHIVOS DETECTADO")
            print(f"Nombre: {nombre_fs}")
            print(f"Versión: {version_fs}")
            print(f"Etiqueta: {etiqueta_vol}")
            print(f"Tamanioo de Cluster: {tam_cluster} bytes")
            print(f"Clusters de Directorio: {num_cluster_dir}")
            print(f"Clusters Totales: {num_cluster_total}")
            
            #Validacion: Aceptamos 26-2 o 26-1 (hay una diferencia con respecto a lo que venía en la asignación)
            if nombre_fs == "FiUnamFS" and (version_fs == "26-2" or version_fs == "26-1"):
                print("\n[Correcto] El sistema de archivos es VALIDO")
            else:
                print("\n[Error] Sistema de archivos no reconocido (o versión incorrecta)")

    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo '{ruta_archivo}'")
    except Exception as e:
        print(f"Error inesperado: {e}")


# SEGUNDA SECCION

def listar_contenido(ruta_archivo):
    #Recorre el directorio y muestra los archivos existentes en el sistema de archivos
    
    #Se definen las constantes
    #El directorio comienza en el cluster 1
    #Tamanio de cluster: 1024 bytes (2 sectores de 512 bytes)
    tam_cluster = 1024
    inicio_directorio = tam_cluster * 1
    
    #El directorio ocupa 4 clusters consecutivos(1, 2, 3 y 4)
    fin_directorio = inicio_directorio + (tam_cluster * 4)
    
    #Cada entrada del directorio tiene una longitud fija de 64 bytes
    tam_entrada = 64

    print(f"\n LISTADO DE ARCHIVOS ")
    print(f"{'NOMBRE':<16} {'TAMAÑO':<10} {'CLUSTER INICIAL'}")
    print("-" * 40)

    try:
        with open(ruta_archivo, 'rb') as f:
            #Se posiciona el puntero de lectura al inicio de la zona de directorio
            f.seek(inicio_directorio)
            
            #Se itera sobre el espacio reservado para el directorio hasta el final
            while f.tell() < fin_directorio:
                entrada = f.read(tam_entrada)
                
                #Se valida que se haya leído un bloque completo de 64 bytes.
                if len(entrada) < tam_entrada:
                    break
                
                #El primer byte indica el estado de la entrada.
                tipo_archivo = chr(entrada[0])

                #Se verifica si la entrada corresponde a un archivo valido
                if tipo_archivo == '.':
                    #Decodificación de la entrada:
                    #Bytes 1-15: Nombre del archivo (ASCII)
                    #Bytes 16-19: Cluster inicial (Little Endian)
                    #Bytes 20-23: Tamanio del archivo (Little Endian)
                    
                    raw_nombre = entrada[1:16]
                    
                    #Se decodifica y se limpian caracteres nulos o espacios para obtener el nombre "real"
                    nombre = raw_nombre.decode('ascii', errors='ignore').strip().replace('\x00', '')
                    
                    cluster_inicial = struct.unpack('<I', entrada[16:20])[0]
                    tamano = struct.unpack('<I', entrada[20:24])[0]
                    
                    print(f"{nombre:<16} {tamano:<10} {cluster_inicial}")
                    
                elif tipo_archivo == '-':
                    #La entrada esta vacia/disponible (se ignora)
                    pass
                else:
                    #Se ignoran entradas con datos no reconocidos
                    pass

    except Exception as e:
        print(f"Error al listar directorio: {e}")

# TERCERA SECCION

def copiar_de_fiunamfs(ruta_fs, nombre_objetivo):
    #Se busca un archivo por nombre en el FS y se copia al directorio actual
    
    tam_cluster = 1024
    inicio_directorio = tam_cluster * 1
    fin_directorio = inicio_directorio + (tam_cluster * 4)
    tam_entrada = 64
    
    #Se asegura que el nombre buscado no tenga espacios extra
    nombre_objetivo = nombre_objetivo.strip()

    print(f"\n INTENTANDO COPIAR: '{nombre_objetivo}' ")

    try:
        with open(ruta_fs, 'rb') as f:
            f.seek(inicio_directorio)
            
            archivo_encontrado = False
            
            while f.tell() < fin_directorio:
                entrada = f.read(tam_entrada)
                if len(entrada) < tam_entrada:
                    break
                
                tipo = chr(entrada[0])
                
                if tipo == '.':
                    raw_nombre = entrada[1:16]
                    
                    #Se agrega esto ya que inicialmente los archivos tienen espacios al final de los nombres que hacen
                    #que no coincidan con el input del usuario
                    #Primero se eliminan los nulos, luego se quitan los espacios.
                    nombre_limpio = raw_nombre.decode('ascii', errors='ignore').replace('\x00', '').strip()
                    
                    #para debug
                    #print(f"Comparando: '{nombre_limpio}' vs '{nombre_objetivo}'") 

                    if nombre_limpio == nombre_objetivo:
                        #Se encuentra el archivo con el nombre que se lee
                        cluster_init = struct.unpack('<I', entrada[16:20])[0]
                        tamano_archivo = struct.unpack('<I', entrada[20:24])[0]
                        
                        print(f"Archivo encontrado en cluster {cluster_init} con tamanio {tamano_archivo}")
                        
                        #Se guarda la posicion actual del directorio para no perderla
                        posicion_dir = f.tell()
                        
                        #Se calcula la ubicacion absoluta de los datos
                        offset_datos = cluster_init * tam_cluster
                        
                        #Se mueve el puntero a la ubicacion de los datos
                        f.seek(offset_datos)
                        datos = f.read(tamano_archivo)
                        
                        #Se escribe el archivo en la maquina local
                        with open(nombre_objetivo, 'wb') as salida:
                            salida.write(datos)
                            
                        print(f"[Exito] Archivo '{nombre_objetivo}' copiado a la maquina local")
                        archivo_encontrado = True
                        break
            
            if not archivo_encontrado:
                print(f"[Error] El archivo '{nombre_objetivo}' no existe en el sistema FiUnamFS")

    except Exception as e:
        print(f"Error al copiar archivo: {e}")


# SECCION 4: ESCRITURA Y CONCURRENCIA

#  AUXILIARES 

def encontrar_hueco_libre(ruta_fs, clusters_necesarios):
    #Analiza el disco para encontrar una secuencia de clusters libres contiguos
    #Retorna el numero del primer cluster libre o -1 si no hay espacio
    
    tam_cluster = 1024
    #Clusters 0 (SB) y del 1 al 4 (Dir) estan reservados
    #Datos inician en el 5
    inicio_datos = 5
    
    total_clusters = 1440 
    
    #Mapa de ocupacion
    #false = libre
    #true = ocupado
    mapa_clusters = [False] * total_clusters
    
    #Se marcan del 1 al 4 como ocupados
    for i in range(0, 5):
        mapa_clusters[i] = True
        
    #Se lee el directorio para ver cuales clusters estan ocupados por archivos existentes
    tam_entrada = 64
    inicio_dir = 1024
    fin_dir = inicio_dir + (tam_cluster * 4)
    
    try:
        with open(ruta_fs, 'rb') as f:
            f.seek(inicio_dir)
            while f.tell() < fin_dir:
                entrada = f.read(tam_entrada)
                if len(entrada) < tam_entrada: break
                
                tipo = chr(entrada[0])
                if tipo == '.':
                    #(Archivo valido) se lee donde empieza y cuanto mide
                    cluster_init = struct.unpack('<I', entrada[16:20])[0]
                    tamano = struct.unpack('<I', entrada[20:24])[0]
                    
                    #Se calculan cuantos clusters ocupa este archivo
                    num_clusters = (tamano // tam_cluster) + (1 if tamano % tam_cluster > 0 else 0)
                    
                    #Se marcan esos clusters como ocupados en el mapa
                    for i in range(cluster_init, cluster_init + num_clusters):
                        if i < total_clusters:
                            mapa_clusters[i] = True
                            
    except Exception as e:
        print(f"Error al mapear espacio: {e}")
        return -1
        
    #Se busca el espacio vaio (secuencia false del tamanio necesario)
    contador_libres = 0
    inicio_hueco = -1
    
    for i in range(inicio_datos, total_clusters):
        if mapa_clusters[i] == False:
            if contador_libres == 0:
                inicio_hueco = i
            contador_libres += 1
            
            if contador_libres == clusters_necesarios:
                return inicio_hueco #Se encontro lugar
        else:
            #Se se rompe la cadena (se reinicia contador)
            contador_libres = 0
            inicio_hueco = -1
            
    return -1 #Si no hay espacio suficiente

#  HILOS 

def hilo_productor(ruta_origen, cola_buffer):

    #Lee el archivo local y pone datos en la cola
    try:
        with open(ruta_origen, 'rb') as f:
            while True:
                bloque = f.read(1024) #Se lee de 1KB en 1KB
                if not bloque:
                    break
                cola_buffer.put(bloque)
        
        #Senial de fin
        cola_buffer.put(None)
    except Exception as e:
        print(f"Error en hilo productor: {e}")

def hilo_consumidor(ruta_destino, cola_buffer, offset_inicial):
    #Lee de la cola y escribe en la img
    try:
        with open(ruta_destino, 'r+b') as f: #r+b permite lectura y escritura sin borrar
            f.seek(offset_inicial)
            while True:
                datos = cola_buffer.get()
                if datos is None: #Senial de fin
                    break
                f.write(datos)
                cola_buffer.task_done()
    except Exception as e:
        print(f"Error en hilo consumidor: {e}")

#  FUNCION DE COPIADO 

def copiar_a_fiunamfs(ruta_fs, ruta_archivo_local):
    #Copia un archivo de la PC hacia el fiunamfs 
    
    #Validaciones iniciales que existe localmente
    if not os.path.exists(ruta_archivo_local):
        print(f"[Error] El archivo '{ruta_archivo_local}' no existe")
        return

    #Se obtiene el nombre y tamanio
    nombre_archivo = os.path.basename(ruta_archivo_local)
    tamano_archivo = os.path.getsize(ruta_archivo_local)
    
    #Calculo de clusters necesarios
    tam_cluster = 1024
    clusters_necesarios = (tamano_archivo // tam_cluster) + (1 if tamano_archivo % tam_cluster > 0 else 0)
    
    #Se busca que haya espacio suficiente
    cluster_inicio = encontrar_hueco_libre(ruta_fs, clusters_necesarios)
    
    if cluster_inicio == -1:
        print("[Error] No hay espacio contiguo suficiente en el disco")
        return
        
    print(f"Espacio encontrado iniciando en cluster {cluster_inicio}")

    #Se busca que haya un espacio libre en el directorio
    #Hueco vacio en los clusters 1 a 4
    offset_entrada_dir = -1
    inicio_dir = 1024
    fin_dir = inicio_dir + (tam_cluster * 4)
    tam_entrada = 64
    
    try:
        with open(ruta_fs, 'r+b') as f:
            f.seek(inicio_dir)
            while f.tell() < fin_dir:
                pos_actual = f.tell()
                entrada = f.read(tam_entrada)
                
                #Se verifica si el espacio esta disponible (nulo o con marca de borrado)
                if len(entrada) == 0 or entrada[0] == 0 or chr(entrada[0]) == '-':
                    offset_entrada_dir = pos_actual
                    break
                    
        if offset_entrada_dir == -1:
            print("[Error] El directorio esta lleno (no hay entradas libres)")
            return
            
        #Se inicia la transferencia
        #Cola de sincronizacion (max 10 bloques)
        cola = queue.Queue(maxsize=10)
        
        #Se calcula donde escribir los datos
        offset_datos = cluster_inicio * tam_cluster
        
        hilo_leer = threading.Thread(target=hilo_productor, args=(ruta_archivo_local, cola))
        hilo_escribir = threading.Thread(target=hilo_consumidor, args=(ruta_fs, cola, offset_datos))
        
        print("Iniciando transferencia asincrona...")
        hilo_leer.start()
        hilo_escribir.start()
        
        hilo_leer.join()
        hilo_escribir.join()
        
        #Se actualiza el directorio
        #Se preparan los datos de la entrada de 64 bytes
        
        #Tipo de archivo (.)
        byte_tipo = b'.'
        
        #Nombre (15 bytes)
        #Se rellenan los espacios vacios para completar los 15 bytes
        byte_nombre = nombre_archivo.encode('ascii')
        byte_nombre = byte_nombre.ljust(15, b'\x00')
        
        #Fechas (formato AAAAMMDDHHMMSS)
        ahora = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        byte_fecha_creacion = ahora.encode('ascii')
        byte_fecha_mod = ahora.encode('ascii')
        
        #Se ensambla (se usa pack para garantizar los bytes exactos)
        nueva_entrada = struct.pack('<c15sII14s14s12x', 
                                    byte_tipo, 
                                    byte_nombre, 
                                    cluster_inicio, 
                                    tamano_archivo, 
                                    byte_fecha_creacion, 
                                    byte_fecha_mod)
        
        #Se escribe la entrada en el directorio
        with open(ruta_fs, 'r+b') as f:
            f.seek(offset_entrada_dir)
            f.write(nueva_entrada)
            
        print(f"[Exito] Archivo guardado correctamente en cluster {cluster_inicio}")
            
    except Exception as e:
        print(f"Error al escribir en disco: {e}")


if __name__ == "__main__":
    leer_superbloque("fiunamfs.img")

    #Listado inicial
    listar_contenido("fiunamfs.img")

    #Copiar algo de la PC al fiunamfs
    archivo_local = input("\nNombre de archivo local para copiar: ")
    copiar_a_fiunamfs("fiunamfs.img", archivo_local)

    #Se lista de nuevo para ver si aparecio
    print("\n VERIFICACION ")
    listar_contenido("fiunamfs.img")
