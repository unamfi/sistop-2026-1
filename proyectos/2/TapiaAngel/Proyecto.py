#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Elaborado por Tapia Ledesma Angel Hazel 


"""
Implementación del micro sistema de archivos multihilos FiUnamFS

Este script implementa las operaciones básicas (ls, cp in, cp out, rm)
sobre un archivo .img que simula un mini disco, usando mapeo de memoria 
y un modelo de concurrencia Productor-Consumidor
"""

import os
import sys
import mmap
import struct
import threading
import queue
import time
from datetime import datetime

# Constantes del Proyecto
# Identificadores del Superbloque
FS_NAME = b'FiUnamFS'
FS_VERSION = b'26-1' 

FS_NAME_OFFSET = 0
FS_NAME_LEN = 8
FS_VERSION_OFFSET = 10
FS_VERSION_LEN = 4 

# Offsets de metadatos del Superbloque
FS_LABEL_OFFSET = 20
FS_LABEL_LEN = 16
CLUSTER_SIZE_OFFSET = 40
DIR_CLUSTERS_OFFSET = 45
TOTAL_CLUSTERS_OFFSET = 50

# Tamaños para datos del directorio
DIR_ENTRY_SIZE = 64

# Constantes del tipo de entrada de directorio (bytes)
ENTRY_TYPE_FILE = b'.'
ENTRY_TYPE_EMPTY = b'-' 
EMPTY_NAME_MARKER = b'.' * 14

# Tamaño de disco por defecto así como de los clusters y sectores 
DEFAULT_DISK_SIZE = 1440 * 1024 
DEFAULT_SECTOR_SIZE = 512
DEFAULT_CLUSTER_SECTORS = 2
DEFAULT_CLUSTER_SIZE = DEFAULT_SECTOR_SIZE * DEFAULT_CLUSTER_SECTORS 
DEFAULT_DIR_CLUSTERS = 3 

class FiUnamFS:
    
    #Clase principal para interactuar con el sistema de archivos FiUnamFS.
    
    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.mm = None
        
        # Configuración de concurrencia
        self.lock = threading.Lock() 
        self.job_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True 

        # Metadatos del FS
        self.volume_label = "Desconocido"
        self.cluster_size = 0
        self.dir_cluster_start = 1 
        self.dir_clusters_count = 0
        self.total_clusters = 0
        self.data_cluster_start = 0
        self.dir_start_offset = 0
        self.dir_size_bytes = 0
        self.num_dir_entries = 0

    def open(self):
        # Abre el archivo, lo mapea con mmap y lanza el hilo trabajador
        # Tambien se manejan errores en caso de que no se encuentre el archivo de la imagen del sistema de archivos 
        try:
            self.file = open(self.filename, 'r+b')
            self.mm = mmap.mmap(self.file.fileno(), 0)
        except FileNotFoundError:
            print(f"Error: Archivo '{self.filename}' no encontrado", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error al abrir o mapear el archivo: {e}", file=sys.stderr)
            return False

        # Esto checa que el super bloque sea valido, si no regresa false
        if not self._validate_superblock():
            self.close()
            return False
        
        # Si es valido lanza el hilo trabajador 
        self._read_superblock_metadata()
        self.worker_thread.start()
        
        print(f"--- FiUnamFS Montado 😎 ---")
        print(f"Archivo:  {self.filename}")
        print(f"Versión:  {FS_VERSION.decode('ascii')}")
        print(f"Etiqueta: {self.volume_label}") 
        print(f"Tamaño Cluster: {self.cluster_size} bytes")
        return True

    def close(self):
        # Detiene el trabajador y cierra los recursos cuando usamos exit
        if self.worker_thread.is_alive():
            self.job_queue.put(('EXIT',))
            self.worker_thread.join(timeout=2)
        
        # Limpia el mapeo de memoria 
        if self.mm:
            self.mm.flush()
            self.mm.close()
            self.mm = None
        if self.file:
            self.file.close()
            self.file = None

    def __enter__(self):
        if not self.open():
            sys.exit(1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _validate_superblock(self):
        # Comprueba si la imagen es archivo valido con base en el superbolque
        try:
            # Leer nombre y version usando el mapeo de memoria, ademas uso rstrip para limpiar en caso de que no se ocupen los bytes exactos, si no menos
            name = self.mm[FS_NAME_OFFSET : FS_NAME_OFFSET + FS_NAME_LEN].rstrip(b'\x00')
            version_raw = self.mm[FS_VERSION_OFFSET : FS_VERSION_OFFSET + FS_VERSION_LEN]
            version = version_raw.rstrip(b'\x00').strip() 

            # no coincide el nombre con el del FS
            if name != FS_NAME:
                print(f"Error: No es un sistema FiUnamFS. (Leído: {name})", file=sys.stderr)
                return False
            
            # No coincide la version con la del FS
            if version != FS_VERSION:
                print(f"Advertencia: Versión del archivo ({version}) no coincide con la esperada ({FS_VERSION}). Intentando continuar", file=sys.stderr)
                return False 
            return True
        except Exception as e:
            print(f"Error validando superbloque: {e}", file=sys.stderr)
            return False
            
    def _read_superblock_metadata(self):
        # Lee los metadatos del superbloque al iniciar
        
        # Lee la etiqueta del volumen
        label_bytes = self.mm[FS_LABEL_OFFSET : FS_LABEL_OFFSET + FS_LABEL_LEN]
        self.volume_label = label_bytes.decode('ascii', errors='ignore').strip().rstrip('\x00')

        # Lee los enteros usando Little Endian <I, el 4 es porque asi se especifica que cada uno tome 4 bytes
        self.cluster_size = struct.unpack('<I', self.mm[CLUSTER_SIZE_OFFSET : CLUSTER_SIZE_OFFSET + 4])[0]
        self.dir_clusters_count = struct.unpack('<I', self.mm[DIR_CLUSTERS_OFFSET : DIR_CLUSTERS_OFFSET + 4])[0]
        self.total_clusters = struct.unpack('<I', self.mm[TOTAL_CLUSTERS_OFFSET : TOTAL_CLUSTERS_OFFSET + 4])[0]
        
        # Calculos derivados paralos directorios
        self.data_cluster_start = self.dir_cluster_start + self.dir_clusters_count
        self.dir_start_offset = self.dir_cluster_start * self.cluster_size
        self.dir_size_bytes = self.dir_clusters_count * self.cluster_size
        
        # Protección contra division por cero
        if DIR_ENTRY_SIZE > 0:
            self.num_dir_entries = self.dir_size_bytes // DIR_ENTRY_SIZE
        else:
            self.num_dir_entries = 0

    # Solo pone el tiempo en un formato legible
    def _format_timestamp(self, dt=None):
        if dt is None:
            dt = datetime.now()
        return dt.strftime('%Y%m%d%H%M%S').encode('ascii')

    # Funciones para interactuar con la "terminal", las mete a una cola
    def stop(self):
        self.job_queue.put(('EXIT',))

    def list_files(self):
        self.job_queue.put(('LS',))
        
    def copy_to_fs(self, local_path, remote_name):
        self.job_queue.put(('CP_IN', local_path, remote_name))

    def copy_from_fs(self, remote_name, local_path):
        self.job_queue.put(('CP_OUT', remote_name, local_path))
        
    def remove_file(self, remote_name):
        self.job_queue.put(('RM', remote_name))
        
    def wait_for_jobs(self):
        self.job_queue.join()

    # Bucle de trabajador (Consumidor)
    def _worker_loop(self):
        while True:
            job = self.job_queue.get()
            job_type = job[0]
            
            if job_type == 'EXIT':
                self.job_queue.task_done()
                break
            
            # Pongo un candado para que no accedan 2 hilos al mismo dato y se genere inconsistencia 
            self.lock.acquire()
            try:
                if job_type == 'LS':
                    self._do_list_files()
                elif job_type == 'CP_IN':
                    self._do_copy_to_fs(job[1], job[2])
                elif job_type == 'CP_OUT':
                    self._do_copy_from_fs(job[1], job[2])
                elif job_type == 'RM':
                    self._do_remove_file(job[1])
            except Exception as e:
                print(f"[Error] Falló operación {job_type}: {e}", file=sys.stderr)
            finally:
                self.lock.release() # ya liberamos el candado porque ya se llamo a la funcion
                self.job_queue.task_done()

    # un bucle sencillo para encontrar el archivo por nombre
    def _find_entry_by_name(self, remote_name):
        for i in range(self.num_dir_entries):
            offset = self.dir_start_offset + (i * DIR_ENTRY_SIZE)
            entry_type = self.mm[offset : offset + 1]
            
            # Verifica si es . para saber que hay un archivo
            if entry_type == ENTRY_TYPE_FILE:
                name_bytes = self.mm[offset + 1 : offset + 15]
                name = name_bytes.rstrip(b'\x00').decode('ascii', errors='ignore').strip() # Lo mismo de arriba para que no aparezca basura en el nombre 
                if name == remote_name: # Coinciden los nombres 
                    start_cluster = struct.unpack('<I', self.mm[offset + 16 : offset + 20])[0] # En que cluster empieza el archivo
                    file_size = struct.unpack('<I', self.mm[offset + 20 : offset + 24])[0] # El tamaño del archivo
                    return offset, start_cluster, file_size
        return None, None, None

    # Busca que directorio esta libre para poder escribir
    def _find_free_directory_entry(self):
        for i in range(self.num_dir_entries):
            offset = self.dir_start_offset + (i * DIR_ENTRY_SIZE)
            entry_type = self.mm[offset : offset + 1] # Chequea el primer simbolo a ver si está vacio o no (. o -)
            
            if entry_type == ENTRY_TYPE_EMPTY:
                return offset
        return -1

    # ahora busca en que parte del cluster hay espacio disponible para poner los datos de forma contigua
    def _find_free_data_clusters(self, clusters_needed):
        used_clusters = set()
        for i in range(self.num_dir_entries):
            offset = self.dir_start_offset + (i * DIR_ENTRY_SIZE)
            entry_type = self.mm[offset : offset + 1]
            
            if entry_type == ENTRY_TYPE_FILE:
                start = struct.unpack('<I', self.mm[offset + 16 : offset + 20])[0]
                size = struct.unpack('<I', self.mm[offset + 20 : offset + 24])[0]
                
                if self.cluster_size > 0:
                    num_clusters_file = (size + self.cluster_size - 1) // self.cluster_size # Redondea hacia el numero de clusters
                else:
                    num_clusters_file = 0
                
                # Marca donde hay datos, no se puede escribir ahi 
                for c in range(num_clusters_file):
                    used_clusters.add(start + c)
        
        # Variables para buscar si cabe de forma contigua
        current_run_start = -1
        current_run_length = 0
        
        # Recorre los que no fueron marcados para ver si cabe la informacion
        # En caso de que quepa, va a regresar donde inició a contabilizar el espacio disponible
        for cluster_idx in range(self.data_cluster_start, self.total_clusters):
            if cluster_idx not in used_clusters:
                if current_run_start == -1:
                    current_run_start = cluster_idx
                current_run_length += 1
                if current_run_length == clusters_needed:
                    return current_run_start 
            else:
                current_run_start = -1
                current_run_length = 0
        return -1 

    # funcion al usar ls
    def _do_list_files(self):
        print(f"\n--- LISTADO DE ARCHIVOS ({self.volume_label}) ---")
        print(f"{'NOMBRE':<16} {'TAMAÑO':>10}  {'MODIFICADO'}")
        print("-" * 45)
        
        total_files = 0
        
        for i in range(self.num_dir_entries):
            offset = self.dir_start_offset + (i * DIR_ENTRY_SIZE)
            entry_type = self.mm[offset : offset + 1]
            
            if entry_type == ENTRY_TYPE_FILE:
                name_bytes = self.mm[offset + 1 : offset + 15]
                name = name_bytes.rstrip(b'\x00').decode('ascii', errors='ignore').strip()
                
                file_size = struct.unpack('<I', self.mm[offset + 20 : offset + 24])[0]
                modified = self.mm[offset + 38 : offset + 52].decode('ascii', errors='ignore')
                
                # Formato de fecha más legible
                try:
                    dt = datetime.strptime(modified, '%Y%m%d%H%M%S')
                    mod_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    mod_str = modified

                print(f"{name:<16} {file_size:>10}  {mod_str}")
                total_files += 1
                
        print("-" * 45)
        print(f"Total: {total_files} archivos encontrados\n")

    # funcion al usar cp in
    def _do_copy_to_fs(self, local_path, remote_name):
        print(f"Copiando '{local_path}' -> FiUnamFS:'{remote_name}'")
        #No existe
        if not os.path.exists(local_path):
            print(f"Error: Archivo local '{local_path}' no existe")
            return
        # Tiene nombre muy largo
        if len(remote_name) > 14:
            print(f"Error: Nombre '{remote_name}' muy largo (max 14)")
            return
        # Ya existe en el disco
        if self._find_entry_by_name(remote_name)[0] is not None:
            print(f"Error: El archivo '{remote_name}' ya existe en el disco")
            return

        # No hay espacio para guardar en el directorio
        dir_entry_offset = self._find_free_directory_entry()
        if dir_entry_offset == -1:
            print("Error: Directorio lleno.")
            return
            
        with open(local_path, 'rb') as f:
            data = f.read()
        file_size = len(data)
        # Calcula cuantos clusters se necesitan pa cargar el archivo 
        clusters_needed = (file_size + self.cluster_size - 1) // self.cluster_size
        if clusters_needed == 0: clusters_needed = 1
        
        # Ve si hay espacio contiguo
        start_cluster = self._find_free_data_clusters(clusters_needed)
        if start_cluster == -1:
            print(f"Error: No hay espacio contiguo ({clusters_needed} clusters).")
            return

        # Calcula la direccion
        data_offset = start_cluster * self.cluster_size
        # Asegurarse de no escribir más allá del final del disco
        if data_offset + file_size > len(self.mm):
             print("Error crítico: Intento de escritura fuera del disco.")
             return
        
        # pega la informacion binaria de lo que copiamos
        self.mm[data_offset : data_offset + file_size] = data
        
        # Escribir entrada directorio
        b_remote_name = remote_name.encode('ascii').ljust(14, b'\x00') # Rellenar con nulos
        timestamp = self._format_timestamp()
        
        self.mm[dir_entry_offset : dir_entry_offset + 1] = ENTRY_TYPE_FILE
        self.mm[dir_entry_offset + 1 : dir_entry_offset + 15] = b_remote_name
        struct.pack_into('<I', self.mm, dir_entry_offset + 16, start_cluster)
        struct.pack_into('<I', self.mm, dir_entry_offset + 20, file_size)
        self.mm[dir_entry_offset + 24 : dir_entry_offset + 38] = timestamp
        self.mm[dir_entry_offset + 38 : dir_entry_offset + 52] = timestamp
        
        print(f"OK: Archivo copiado")

    # funcion al usar cp out
    def _do_copy_from_fs(self, remote_name, local_path):
        print(f"Copiando FiUnamFS:'{remote_name}' -> '{local_path}'")
        
        # encuentra y devuelve los parametros por nombre de archivo
        offset, start_cluster, file_size = self._find_entry_by_name(remote_name)
        if offset is None:
            print(f"Error: Archivo '{remote_name}' no encontrado")
            return

        data_start_offset = start_cluster * self.cluster_size
        data_end_offset = data_start_offset + file_size
        data = self.mm[data_start_offset : data_end_offset]
        
        try:
            with open(local_path, 'wb') as f:
                f.write(data)
            print(f"OK: Archivo extraído.")
        except Exception as e:
            print(f"Error escribiendo archivo local: {e}")

    # funcion al usar rm 
    def _do_remove_file(self, remote_name):
        print(f"Eliminando '{remote_name}'...")

        # lo busca por nombre
        offset, start_cluster, file_size = self._find_entry_by_name(remote_name)
        if offset is None:
            print(f"Error: Archivo '{remote_name}' no encontrado.")
            return
            
        # Marcar como vacío y limpiar nombre para evitar 
        self.mm[offset : offset + 1] = ENTRY_TYPE_EMPTY
        self.mm[offset + 1 : offset + 15] = EMPTY_NAME_MARKER
        
        print(f"OK: Archivo eliminado.")

def main():
    # Nombre del archivo de prueba dado 
    img_filename = "fiunamfs.img"
    
    if not os.path.exists(img_filename):
        print(f"ERROR: No se encuentra el archivo '{img_filename}' en la carpeta actual")
        print("Por favor sube el archivo .img o verifica el nombre")
        return
            
    with FiUnamFS(img_filename) as fs:
        print("\n--- Sistema de archivos de FiUnamFS ---")
        print("Comandos: ls, cp in/out, rm, exit")
        
        while True:
            try:
                cmd_line = input("\nFiUnamFS> ").strip()
                if not cmd_line: continue
                    
                parts = cmd_line.split()
                cmd = parts[0].lower()
                
                if cmd == 'exit':
                    break 
                    
                elif cmd == 'ls':
                    fs.list_files()
                    
                # Para detectar que se den los parametros adecuados(cp, in/out nombre1 nombre2) y detecta si es in o out
                elif cmd == 'cp' and len(parts) >= 3:
                    direction = parts[1].lower()
                    if direction == 'in' and len(parts) == 4:
                        fs.copy_to_fs(parts[2], parts[3])
                    elif direction == 'out' and len(parts) == 4:
                        fs.copy_from_fs(parts[2], parts[3])
                    else:
                        print("Uso: cp in <local> <remoto>  O  cp out <remoto> <local>")
                
                elif cmd == 'rm' and len(parts) == 2:
                    fs.remove_file(parts[1])
                    
                elif cmd == 'wait':
                    fs.wait_for_jobs()
                    
                else:
                    print(f"Comando no reconocido: {cmd}")
                    
            except (EOFError, KeyboardInterrupt):
                break
    print("\nSaliendo")

if __name__ == "__main__":
    main()