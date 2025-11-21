import struct
import os
import sys

# PRIMERA SECCION DEL PROYECTO

def leer_superbloque(ruta_archivo):

    #Lee el superbloque del sistema de archivos FiUnamFS.
    #Valida que sea el sistema correcto y muestra sus metadatos.
    
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
            
            # struct.unpack con <I para los enteros
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
            
            # Validacion: Aceptamos 26-2 o 26-1 (hay una diferencia con respecto a lo que venía en la asignación)
            if nombre_fs == "FiUnamFS" and (version_fs == "26-2" or version_fs == "26-1"):
                print("\n[Correcto] El sistema de archivos es VALIDO")
            else:
                print("\n[Error] Sistema de archivos no reconocido (o versión incorrecta)")

    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo '{ruta_archivo}'")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    #Se ejecuta la funcion principal
    leer_superbloque("fiunamfs.img")
