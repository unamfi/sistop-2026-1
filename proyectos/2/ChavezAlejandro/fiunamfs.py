import struct
import os
import sys

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
            print(f"Tamanio de Cluster: {tam_cluster} bytes")
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

    print(f"\nLISTADO DE ARCHIVOS")
    print(f"{'NOMBRE':<16} {'TAMANIO':<10} {'CLUSTER INICIAL'}")
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
                    #Bytes 1-15: Nombre del archivo (ASCII).
                    #Bytes 16-19: Cluster inicial (Little Endian).
                    #Bytes 20-23: Tamanio del archivo (Little Endian).
                    
                    raw_nombre = entrada[1:16]
                    
                    #Se decodifica y se limpian caracteres nulos o espacios para obtener el nombre "real".
                    nombre = raw_nombre.decode('ascii', errors='ignore').strip().replace('\x00', '')
                    
                    cluster_inicial = struct.unpack('<I', entrada[16:20])[0]
                    tamanio = struct.unpack('<I', entrada[20:24])[0]
                    
                    print(f"{nombre:<16} {tamanio:<10} {cluster_inicial}")
                    
                elif tipo_archivo == '-':
                    #La entrada esta vacia/disponible (se ignora)
                    pass
                else:
                    #Se ignoran entradas con datos no reconocidos
                    pass

    except Exception as e:
        print(f"Error al listar directorio: {e}")

if __name__ == "__main__":
    #Se ejecuta la funcion principal
    leer_superbloque("fiunamfs.img")
    listar_contenido("fiunamfs.img")
