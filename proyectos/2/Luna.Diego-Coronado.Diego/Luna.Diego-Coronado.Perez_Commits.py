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



class OperacionesFS:
    def __init__(self, sistema: SistemaArchivosFiUnamFS):
        self.fs = sistema

    def listar(self):
        try:
            self.fs.leer_superbloque() # Refrescar metadatos
            archivos = self.fs.leer_entradas_directorio()
            CLEAR()
            listarDirectorioImp()
            if not archivos:
                print("\t < Directorio Vacío >")
            else:
                for a in archivos:
                    print(f"\t {a['tipo_show']:<5} {a['Nombre']:<15} | {a['Tamaño']:<10} | {a['Cluster Inicial']:<15} | {a['Fecha Creación']} | {a['Fecha Modificación']}")
            print("\n")
        except Exception as e:
            print(f"\t[Error] No se pudo listar: {e}")

    def copiar_a_pc(self, nombre_fiunam):
        """ Copia un archivo del FS virtual a tu computadora """
        try:
            self.fs.leer_superbloque()
            archivos = self.fs.leer_entradas_directorio()
            archivo_obj = next((a for a in archivos if a['Nombre'] == nombre_fiunam), None)

            if not archivo_obj:
                print(f"\n\t[!] El archivo '{nombre_fiunam}' no existe en FiUnamFS.")
                return

            # Definir ruta destino local
            ruta_local = os.path.join(os.getcwd(), nombre_fiunam)
            # Evitar sobreescritura simple
            if os.path.exists(ruta_local):
                base, ext = os.path.splitext(nombre_fiunam)
                ruta_local = os.path.join(os.getcwd(), f"{base}_copy{ext}")

            # Leer datos
            offset_bytes = archivo_obj['Cluster Inicial'] * self.fs.tamano_cluster
            bytes_a_leer = archivo_obj['Tamaño']

            with archivo_mutex:
                with open(self.fs.imagen_archivo, 'rb') as img:
                    img.seek(offset_bytes)
                    data = img.read(bytes_a_leer)
            
            with open(ruta_local, 'wb') as out:
                out.write(data)
            
            print(f"\n\t[OK] Archivo guardado en: {ruta_local}")

        except Exception as e:
            print(f"\n\t[Error] Falló la copia: {e}")

    def copiar_a_fiunam(self, ruta_origen):
        """ Copia un archivo de tu PC al FS virtual (Asignación Contigua) """
        if not os.path.exists(ruta_origen):
            print("\t[!] Archivo origen no existe.")
            return

        try:
            # Preparar datos
            tamano_archivo = os.path.getsize(ruta_origen)
            nombre_orig = os.path.basename(ruta_origen)
            nombre_base, ext = os.path.splitext(nombre_orig)
            # Ajustar nombre a 14 caracteres ASCII
            nombre_final = (nombre_base + ext)[:14]
            
            try:
                nombre_bytes = nombre_final.encode('ascii')
            except UnicodeEncodeError:
                print("\t[!] Error: El nombre debe contener solo caracteres ASCII.")
                return

            # Calcular clusters necesarios
            self.fs.leer_superbloque()
            clusters_necesarios = (tamano_archivo + self.fs.tamano_cluster - 1) // self.fs.tamano_cluster
            if tamano_archivo == 0: clusters_necesarios = 1 # Al menos 1 si es vacio pero existe

            # Buscar espacio contiguo (Algoritmo First Fit Contiguo)
            mapa = self.fs._obtener_mapa_clusters()
            start_cluster = -1
            contador = 0
            
            # Empezamos a buscar DESPUES del directorio
            inicio_busqueda = self.fs.clusters_directorio + 1
            
            for i in range(inicio_busqueda, self.fs.total_clusters):
                if not mapa[i]:
                    if contador == 0: start_cluster = i
                    contador += 1
                    if contador == clusters_necesarios:
                        break
                else:
                    contador = 0
                    start_cluster = -1
            
            if contador < clusters_necesarios:
                print("\t[!] Error: No hay espacio contiguo suficiente en el disco.")
                return

            # Escribir DATOS
            with open(ruta_origen, 'rb') as f_src:
                datos = f_src.read()

            with archivo_mutex:
                with open(self.fs.imagen_archivo, 'r+b') as img:
                    # 1. Escribir contenido en clusters de datos
                    pos_datos = start_cluster * self.fs.tamano_cluster
                    img.seek(pos_datos)
                    # Rellenar último cluster con ceros si es necesario (padding)
                    datos_padding = datos + b'\x00' * ( (clusters_necesarios * self.fs.tamano_cluster) - len(datos) )
                    img.write(datos_padding)

                    # 2. Crear entrada en directorio
                    # Buscar slot vacío
                    slot_encontrado = False
                    for cl_dir in range(self.fs.clusters_directorio):
                        base_dir = (SUPERBLOQUE_CLUSTER + 1 + cl_dir) * self.fs.tamano_cluster
                        img.seek(base_dir)
                        buff_dir = bytearray(img.read(self.fs.tamano_cluster))
                        
                        for offset in range(0, self.fs.tamano_cluster, TAMANO_ENTRADA):
                            tipo = buff_dir[offset:offset+1]
                            nombre_slot = buff_dir[offset+1:offset+15]
                            
                            if tipo == EMPTY_MARK or nombre_slot == EMPTY_NAME_MARKER:
                                # Construir entrada de 64 bytes
                                nueva_entrada = bytearray(64)
                                nueva_entrada[0:1] = FILE_MARK
                                nueva_entrada[1:15] = nombre_bytes.ljust(14, b'\x00')
                                nueva_entrada[16:20] = struct.pack('<I', start_cluster)
                                nueva_entrada[20:24] = struct.pack('<I', tamano_archivo)
                                
                                fecha_str = datetime.now().strftime("%Y%m%d%H%M%S").encode('ascii')
                                nueva_entrada[24:38] = fecha_str
                                nueva_entrada[38:52] = fecha_str
                                # 52-64 padding vacio
                                
                                # Escribir en buffer y luego a disco
                                buff_dir[offset:offset+64] = nueva_entrada
                                img.seek(base_dir)
                                img.write(buff_dir)
                                slot_encontrado = True
                                break
                        if slot_encontrado: break
            
            if not slot_encontrado:
                print("\t[!] Error: Directorio lleno (no hay slots libres).")
            else:
                print(f"\n\t[OK] Archivo '{nombre_final}' escrito exitosamente.")
                print(f"\t    Cluster inicio: {start_cluster}, Clusters usados: {clusters_necesarios}")

        except Exception as e:
            print(f"\t[Error] {e}")

    def eliminar(self, nombre_fiunam):
        """ Marca un archivo como eliminado en el directorio """
        try:
            self.fs.leer_superbloque()
            encontrado = False
            
            with archivo_mutex:
                with open(self.fs.imagen_archivo, 'r+b') as img:
                    # Recorrer directorio buscando el nombre
                    for cl_dir in range(self.fs.clusters_directorio):
                        base_dir = (SUPERBLOQUE_CLUSTER + 1 + cl_dir) * self.fs.tamano_cluster
                        img.seek(base_dir)
                        buff_dir = bytearray(img.read(self.fs.tamano_cluster))
                        modificado = False

                        for offset in range(0, self.fs.tamano_cluster, TAMANO_ENTRADA):
                            # Comprobamos el nombre (bytes 1-15)
                            nombre_slot = buff_dir[offset+1:offset+15].decode('ascii', errors='ignore').rstrip('\x00').strip()
                            tipo_slot = buff_dir[offset:offset+1]

                            if tipo_slot != EMPTY_MARK and nombre_slot == nombre_fiunam:
                                # BORRAR: Marcar byte 0 con EMPTY_MARK y llenar nombre con '.'
                                buff_dir[offset:offset+1] = EMPTY_MARK
                                buff_dir[offset+1:offset+15] = EMPTY_NAME_MARKER
                                # Opcional: Limpiar metadata a 0
                                buff_dir[offset+16:offset+64] = b'\x00' * 48
                                
                                modificado = True
                                encontrado = True
                                break # Salir del cluster actual
                        
                        if modificado:
                            img.seek(base_dir)
                            img.write(buff_dir)
                            break # Salir de busqueda de clusters
            
            if encontrado:
                print(f"\n\t[OK] Archivo '{nombre_fiunam}' eliminado.")
            else:
                print(f"\n\t[!] Archivo '{nombre_fiunam}' no encontrado.")

        except Exception as e:
            print(f"\t[Error] {e}")

