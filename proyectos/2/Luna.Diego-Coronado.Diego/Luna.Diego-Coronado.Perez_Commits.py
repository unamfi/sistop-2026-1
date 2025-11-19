import os
import struct
import threading
import time
from datetime import datetime


TAMANO_DISQUETE = 1440 * 1024
TAMANO_SECTOR = 512
TAMANO_CLUSTER_DEFECTO = 1024  
TAMANO_ENTRADA = 64
SUPERBLOQUE_CLUSTER = 0

CLUSTERS_DIRECTORIO_DEFECTO = 4 
NOMBRE_SISTEMA_ARCHIVOS = 'FiUnamFS'

VERSION_SISTEMA = '26-1'  
ARCHIVO_IMAGEN = 'fiunamfs.img'


archivo_mutex = threading.Lock() 

FILE_MARK = b'\x2d'             

EMPTY_MARK = b'\x2f'            

EMPTY_NAME_MARKER = b'.' * 14 


def CLEAR():
    os.system('cls' if os.name == 'nt' else 'clear')

def pausa():
    input("\n\tPresione Enter para continuar...")

def menuMainImp():
    print("\n\t----------------------------------------------")
    print(f"\t      Sistema de Archivos {NOMBRE_SISTEMA_ARCHIVOS} v{VERSION_SISTEMA}")
    print("\t----------------------------------------------")
    print("\t1. Listar directorio")
    print("\t2. Copiar archivo desde FiUnamFS al sistema (PC)")
    print("\t3. Copiar archivo desde el sistema (PC) a FiUnamFS")
    print("\t4. Eliminar archivo en FiUnamFS")
    print("\t5. Salir")
    print("\t----------------------------------------------")

def listarDirectorioImp():
    print("\n\t" + "-"*105)
    print("\t {:<5} {:<15} | {:<10} | {:<15} | {:<18} | {:<18}".format(
        "Tipo", "Nombre", "Tamaño", "Cluster Ini", "Fecha Creación", "Fecha Modif"))
    print("\t" + "-"*105)



class SistemaArchivosFiUnamFS:

    def __init__(self, imagen_archivo=ARCHIVO_IMAGEN):
        self.imagen_archivo = imagen_archivo
        self.tamano_cluster = TAMANO_CLUSTER_DEFECTO
        self.clusters_directorio = CLUSTERS_DIRECTORIO_DEFECTO
        self.total_clusters = None
        self.etiqueta_volumen = None

    def verificar_existencia_imagen(self):
        """ Verifica si el archivo .img existe, si no, pide ruta """
        if not os.path.exists(self.imagen_archivo):
            print(f"\n\t[!] El archivo '{self.imagen_archivo}' no está en el directorio.")
            while True:
                ruta = input("\n\tIngrese la ruta completa del archivo 'fiunamfs.img': ").strip()
                if os.path.exists(ruta):
                    self.imagen_archivo = ruta
                    CLEAR()
                    print(f"\t[OK] Archivo cargado: {self.imagen_archivo}")
                    break
                else:
                    print("\n\t[X] Archivo no encontrado.")

    def leer_superbloque(self):
        """
        Lee y valida superbloque. Actualiza configuración del FS.
        Usa Locks para asegurar lectura atómica si hubiera hilos concurrentes leyendo.
        """
        with archivo_mutex:
            with open(self.imagen_archivo, 'rb') as img:
                img.seek(0)
                superbloque = img.read(1024)
                
                # Validaciones de texto (Nombre y Versión)
                nombre = superbloque[0:8].decode('ascii', errors='ignore').rstrip('\x00').strip()
                version = superbloque[10:15].decode('ascii', errors='ignore').rstrip('\x00').strip()
                self.etiqueta_volumen = superbloque[20:36].decode('ascii', errors='ignore').rstrip('\x00').strip()

                if nombre != NOMBRE_SISTEMA_ARCHIVOS:
                    raise ValueError(f"Sistema de archivos desconocido: {nombre}")

                if version != VERSION_SISTEMA:
                    raise ValueError(f"Versión incompatible: {version}. Se esperaba {VERSION_SISTEMA}")

                # Lectura de enteros little-endian (<I)
                try:
                    self.tamano_cluster = struct.unpack('<I', superbloque[40:44])[0]
                    self.clusters_directorio = struct.unpack('<I', superbloque[45:49])[0]
                    self.total_clusters = struct.unpack('<I', superbloque[50:54])[0]
                except Exception:
                    print("\t[!] Advertencia: Datos del superbloque corruptos o incompletos. Usando valores por defecto.")

                # Si total_clusters es 0 o erróneo, calcularlo
                if self.total_clusters == 0:
                    img.seek(0, os.SEEK_END)
                    tam_img = img.tell()
                    self.total_clusters = tam_img // self.tamano_cluster

    def leer_entradas_directorio(self):
        """ Retorna una lista de diccionarios con la metadata de los archivos activos """
        directorio = []
        
        with archivo_mutex:
            with open(self.imagen_archivo, 'rb') as img:
                tam_cluster = self.tamano_cluster
                # Recorremos los clusters dedicados al directorio
                for cluster in range(self.clusters_directorio):
                    posicion_inicial = (SUPERBLOQUE_CLUSTER + 1 + cluster) * tam_cluster
                    img.seek(posicion_inicial)
                    cluster_datos = img.read(tam_cluster)

                    # Recorremos cada entrada de 64 bytes dentro del cluster
                    for offset in range(0, tam_cluster, TAMANO_ENTRADA):
                        entrada_bytes = cluster_datos[offset:offset + TAMANO_ENTRADA]
                        
                        # Byte 0: Tipo de archivo o vacio
                        tipo = entrada_bytes[0:1]
                        
                        # Si es marca de vacío, saltar
                        if tipo == EMPTY_MARK:
                            continue
                        
                        # Parsear nombre
                        nombre_raw = entrada_bytes[1:15]

                        #####################################COMMIT 2
                        if nombre_raw == EMPTY_NAME_MARKER:
                            continue

                        nombre = nombre_raw.decode('ascii', errors='ignore').rstrip('\x00').strip()

                        # DESCARTAR basura común: --------------  o vacíos reales
                        if nombre == "" or nombre.replace("-", "") == "":
                            continue
                        
                        ###################################
                        cluster_ini = struct.unpack('<I', entrada_bytes[16:20])[0]
                        tamano = struct.unpack('<I', entrada_bytes[20:24])[0]
                        
                        creacion = entrada_bytes[24:38].decode('ascii', errors='ignore')
                        modif = entrada_bytes[38:52].decode('ascii', errors='ignore')

                    
                        tipo_str = "DIR" if tipo == b'.' else "FILE" # Ajuste visual

                        try:
                            tipo_char = tipo.decode('ascii')
                        except:
                            tipo_char = '?'

                        directorio.append({
                            'raw_tipo': tipo,
                            'tipo_show': tipo_char,
                            'Nombre': nombre,
                            'Tamaño': tamano,
                            'Cluster Inicial': cluster_ini,
                            'Fecha Creación': creacion,
                            'Fecha Modificación': modif
                        })
        return directorio

    def _obtener_mapa_clusters(self):
        """ Mapa booleano de clusters ocupados """
        ocupados = [False] * self.total_clusters
        
        # Superbloque ocupado
        ocupados[0] = True
        
        # Clusters de directorio ocupados
        for i in range(1, 1 + self.clusters_directorio):
            if i < self.total_clusters:
                ocupados[i] = True

        # Clusters de archivos ocupados
        entradas = self.leer_entradas_directorio()
        for archivo in entradas:
            inicio = archivo['Cluster Inicial']
            if archivo['Tamaño'] > 0:
                num_clusters = (archivo['Tamaño'] + self.tamano_cluster - 1) // self.tamano_cluster
            else:
                num_clusters = 0
            
            for offset in range(num_clusters):
                idx = inicio + offset
                if idx < self.total_clusters:
                    ocupados[idx] = True
        return ocupados