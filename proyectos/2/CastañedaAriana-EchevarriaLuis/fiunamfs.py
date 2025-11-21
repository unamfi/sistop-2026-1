"""
Módulo Backend para el sistema de archivos FiUnamFS (v26-1).

Este script implementa la lógica de bajo nivel para manipular imágenes de disco
que siguen la especificación FiUnamFS. Incluye una clase controladora (FiUnamFS)
que encapsula el estado del sistema, validaciones de versión y operaciones
atómicas (lectura/escritura) protegidas por hilos.

Autor: Castañeda Ariana, Echevarria Luis
Materia: Sistemas Operativos
"""

import argparse  
import struct    
import os
import math
import datetime
from threading import Thread, Lock  
from queue import Queue
import sys
import tempfile
import shutil
from types import SimpleNamespace

# -------------------- Constantes Globales --------------------
SUPERBLOCK_CLUSTER = 0   
SUPERBLOCK_SIZE = 512   
EXPECTED_IDENT = b'FiUnamFS'
EXPECTED_VERSION = b'26-1' 
FREE_ENTRY_NAME = b'.' * 15

# Offsets (posiciones de bytes) dentro del Superbloque
OFF_IDENT = 0; LEN_IDENT = 9
OFF_VERSION = 10; LEN_VERSION = 5
OFF_LABEL = 20; LEN_LABEL = 16
OFF_CLUSTER_SIZE = 40
OFF_DIR_CLUSTERS = 45
OFF_TOTAL_CLUSTERS = 50

ENTRY_SIZE = 64   
NAME_LEN = 15     

# Cola de trabajo global 
work_queue = Queue()

# -------------------- CLASE PRINCIPAL DEL SISTEMA DE ARCHIVOS --------------------

class FiUnamFS:
    """
    Controlador del sistema de archivos. 
    
    Esta clase encapsula el acceso a la imagen de disco, garantizando que todas
    las operaciones sean seguras (thread-safe) y consistentes.
    """
    def __init__(self, img_path):
        """
        Inicializa el controlador montando la imagen especificada.
        
        Argumentos:
            img_path (str): Ruta al archivo .img
            
        Lanza:
            FileNotFoundError: Si la imagen no existe.
            ValueError: Si la versión o identificador del FS son incorrectos.
        """
        self.img_path = img_path
        self.lock = Lock()
        self.valid = False
        
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"La imagen {img_path} no existe.")
            
        # Cargar metadatos iniciales
        with open(self.img_path, 'rb') as f:
            self.sb = self._read_superblock(f)
            
        self._validate_version()
        
        # Cachear valores frecuentes para no leerlos del sb cada vez
        self.cluster_size = self.sb['cluster_size']
        self.dir_clusters = self.sb['dir_clusters']
        self.total_clusters = self.sb['total_clusters']
        self.valid = True

    def _read_superblock(self, f):
        """
        Lee los 512 bytes del superbloque y decodifica sus campos.
        """
        f.seek(SUPERBLOCK_CLUSTER * SUPERBLOCK_SIZE)
        data = f.read(SUPERBLOCK_SIZE)
        
        def read_u32(offset):
            """
            Helper para leer enteros de 32 bits Little Endian (<I).
            """
            return struct.unpack_from('<I', data, offset)[0]

        return {
            'ident': data[OFF_IDENT:OFF_IDENT+LEN_IDENT].split(b"\x00", 1)[0],
            'version': data[OFF_VERSION:OFF_VERSION+LEN_VERSION].split(b"\x00", 1)[0],
            'label': data[OFF_LABEL:OFF_LABEL+LEN_LABEL].split(b"\x00", 1)[0],
            'cluster_size': read_u32(OFF_CLUSTER_SIZE) or 1024,
            'dir_clusters': read_u32(OFF_DIR_CLUSTERS) or 3,
            'total_clusters': read_u32(OFF_TOTAL_CLUSTERS) or 1440
        }

    def _validate_version(self):
        """
        Verifica que la imagen sea versión 26-1 para evitar corrupción.
        """
        if self.sb['ident'] != EXPECTED_IDENT:
            raise ValueError(f"Identificador inválido: {self.sb['ident']}")
        if self.sb['version'] != EXPECTED_VERSION:
            raise ValueError(f"Versión inválida: {self.sb['version'].decode()}. Se requiere {EXPECTED_VERSION.decode()}.")

    def _parse_directory(self, f):
        """
        Escanea el área de directorio y parsea cada entrada de 64 bytes.
        Retorna una lista de diccionarios con la metadata de cada archivo.
        """
        dir_offset = 1 * self.cluster_size
        dir_size = self.dir_clusters * self.cluster_size
        f.seek(dir_offset)
        data = f.read(dir_size)
        
        entries = []
        num_entries = len(data) // ENTRY_SIZE
        
        for i in range(num_entries):
            off = i * ENTRY_SIZE
            entry = data[off:off+ENTRY_SIZE]
            if len(entry) < ENTRY_SIZE: break
            
            name_raw = entry[1:1+NAME_LEN]
            try: name = name_raw.decode('ascii', errors='ignore').rstrip('\x00').strip()
            except: name = ''
            
            try: cluster_init = struct.unpack_from('<I', entry, 16)[0]
            except: cluster_init = 0
            try: size = struct.unpack_from('<I', entry, 20)[0]
            except: size = 0
            
            # Determinación de vacío
            is_unused = (name_raw == FREE_ENTRY_NAME) or \
                        (name_raw == b'\x00'*NAME_LEN) or \
                        (name == '' and cluster_init == 0 and size == 0)
            
            # Parsear fechas
            c_str = entry[24:38].decode('ascii', errors='ignore')
            m_str = entry[38:52].decode('ascii', errors='ignore')
            
            entries.append({
                'index': i, 'name': name, 'is_unused': is_unused,
                'cluster_init': cluster_init, 'size': size,
                'created': self._parse_ts(c_str), 'modified': self._parse_ts(m_str)
            })
        return entries

    def _parse_ts(self, s):
        """
        Convierte cadena AAAAMMDDHHMMSS a objeto datetime para fechas.
        """
        if len(s) >= 14 and s.isdigit():
            try: return datetime.datetime.strptime(s[:14], '%Y%m%d%H%M%S')
            except: pass
        return s

    def _format_ts(self, dt):
        """
        Convierte objeto datetime a cadena de bytes para escritura.
        """
        return dt.strftime('%Y%m%d%H%M%S').encode('ascii')[:14]

    def create_backup(self):
        """
        Genera una copia de seguridad .bak antes de operaciones destructivas.
        """
        bak = self.img_path + '.bak'
        with self.lock:
            try:
                shutil.copy2(self.img_path, bak)
                print(f"[Backup] Respaldo generado: {bak}")
            except Exception as e:
                print(f"[Backup Error] {e}")

    # --- MÉTODOS PÚBLICOS (Interfaz para el exterior) ---

    def list_files(self):
        """
        Retorna la lista de archivos activos en el directorio.
        Filtra entradas vacías o marcadas como borradas.
        """
        with self.lock:
            with open(self.img_path, 'rb') as f:
                entries = self._parse_directory(f)
        
        return [e for e in entries 
                if not e['is_unused'] and e['name'] != '--------------' and e['name'] != '...............']

    def read_file(self, filename, out_path):
        """
        Busca un archivo por nombre y extrae su contenido al sistema local.
        """
        with self.lock:
            with open(self.img_path, 'rb') as f:
                entries = self._parse_directory(f)
                found = next((e for e in entries if not e['is_unused'] and e['name'] == filename), None)
                
                if not found:
                    raise FileNotFoundError(f"Archivo '{filename}' no encontrado en FiUnamFS.")
                
                f.seek(found['cluster_init'] * self.cluster_size)
                data = f.read(found['size'])
                
            with open(out_path, 'wb') as fout:
                fout.write(data)
            print(f"Archivo {filename} extraído correctamente → {out_path}")

    def write_file(self, src_path, dest_name):
        """
        Importa un archivo local al sistema FiUnamFS.
        Maneja la búsqueda de espacio contiguo y actualización del directorio.
        """
        if len(dest_name) > NAME_LEN:
            raise ValueError(f"El nombre de destino '{dest_name}' excede {NAME_LEN - 1} caracteres.")
            
        file_size = os.path.getsize(src_path)
        with open(src_path, 'rb') as f:
            data = f.read()

        self.create_backup()

        with self.lock:
            with open(self.img_path, 'r+b') as f:
                entries = self._parse_directory(f)
                
                if any(not e['is_unused'] and e['name'] == dest_name for e in entries):
                    raise FileExistsError(f"El archivo '{dest_name}' ya existe.")
                
                free_idx = next((e['index'] for e in entries if e['is_unused']), None)
                if free_idx is None:
                    raise OSError("Directorio lleno.")

                # Buscar espacio (Hueco o Final)
                needed_clusters = math.ceil(file_size / self.cluster_size)
                ranges = []
                for e in entries:
                    if not e['is_unused'] and e['cluster_init'] > 0:
                        s = e['cluster_init']
                        n = math.ceil(e['size'] / self.cluster_size)
                        ranges.append((s, s+n))
                ranges.sort()
                
                data_start = 1 + self.dir_clusters
                target_cluster = data_start
                for s, e in ranges:
                    if target_cluster + needed_clusters <= s: break
                    target_cluster = max(target_cluster, e)
                
                if target_cluster + needed_clusters > self.total_clusters:
                    raise OSError("Espacio insuficiente en disco.")

                f.seek(target_cluster * self.cluster_size)
                # Padding con ceros al final del cluster
                padding = (needed_clusters * self.cluster_size) - len(data)
                f.write(data + b'\x00' * padding)
                
                # Actualizar Directorio
                entry_offset = (1 * self.cluster_size) + (free_idx * ENTRY_SIZE)
                f.seek(entry_offset)
                
                name_bytes = dest_name.encode('ascii').ljust(NAME_LEN, b'\x00')
                now = self._format_ts(datetime.datetime.now())
                
                new_entry = b'-' + name_bytes + \
                            struct.pack('<I', target_cluster) + \
                            struct.pack('<I', file_size) + \
                            now + now + \
                            b'\x00' * (ENTRY_SIZE - 1 - NAME_LEN - 8 - 28)
                f.write(new_entry)
                f.flush(); os.fsync(f.fileno())
        print(f"Archivo {src_path} escrito como {dest_name} en cluster {target_cluster} (tamaño {file_size} bytes).")

    def delete_file(self, filename):
        """
        Marca un archivo como eliminado liberando su entrada en el directorio.
        """
        self.create_backup()
        
        with self.lock:
            with open(self.img_path, 'r+b') as f:
                entries = self._parse_directory(f)
                found = next((e for e in entries if not e['is_unused'] and e['name'] == filename), None)
                
                if not found:
                    raise FileNotFoundError(f"Archivo '{filename}' no encontrado.")
                
                offset = (1 * self.cluster_size) + (found['index'] * ENTRY_SIZE)
                f.seek(offset)
                
                # Patrón de borrado seguro
                empty_entry = b'\x2f' + FREE_ENTRY_NAME + \
                              struct.pack('<I', 0) + struct.pack('<I', 0) + \
                              b'0'*14 + b'0'*14 + \
                              b'\x00' * (ENTRY_SIZE - 1 - NAME_LEN - 8 - 28)
                f.write(empty_entry)
                f.flush(); os.fsync(f.fileno())
        print(f"Archivo {filename} eliminado correctamente (entrada {found['index']} marcada como libre).")

# -------------------- WORKER (Concurrencia) --------------------

def worker_wrapper(fs_instance):
    """
    Hilo consumidor que procesa tareas de la cola.
    Permite que las operaciones pesadas no bloqueen la interfaz principal.
    """
    while True:
        task = work_queue.get()
        if task is None:
            work_queue.task_done(); break
            
        op = task.get('op')
        try:
            if op == 'copyout':
                fs_instance.read_file(task['name'], task['outpath'])
            elif op == 'copyin':
                fs_instance.write_file(task['src'], task['dest_name'])
            elif op == 'delete':
                fs_instance.delete_file(task['name'])
        except Exception as e:
            print(f"[WORKER ERROR] Error en tarea {op}: {e}", file=sys.stderr)
        finally:
            work_queue.task_done()

# -------------------- CLI & UTILS --------------------

def cmd_info(args):
    """
    Comando CLI: Muestra información del superbloque.
    """
    try:
        fs = FiUnamFS(args.image)
        print(f"Ident: {fs.sb['ident'].decode()}")
        print(f"Version: {fs.sb['version'].decode()}")
        print(f"Label: {fs.sb['label'].decode()}")
        print(f"Cluster size: {fs.cluster_size} bytes")
        print(f"Dir clusters: {fs.dir_clusters}")
        print(f"Total clusters: {fs.total_clusters}")
    except ValueError as e:
        print(f"AVISO: {e}")
    except Exception as e:
        print(f"ERROR: {e}")

def cmd_list(args):
    """
    Comando CLI: Lista archivos en consola.
    """
    try:
        fs = FiUnamFS(args.image) # Esto valida 26-1 estrictamente
        files = fs.list_files()
        print(f'Entradas del directorio ({len(files)} archivos activos):')
        for e in files:
            cts = e['created'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(e['created'], datetime.datetime) else e['created']
            print(f"Index={e['index']} | Name={e['name']} | Size={e['size']} bytes | Cluster={e['cluster_init']} | Created={cts}")
    except Exception as e:
        print(f"ERROR: No se pudo listar. {e}", file=sys.stderr)

def _launch_worker(args):
    """
    Inicializa el hilo worker para comandos CLI asíncronos.
    """
    try:
        fs = FiUnamFS(args.image)
        t = Thread(target=worker_wrapper, args=(fs,), daemon=True)
        t.start()
        return t
    except Exception as e:
        print(f"ERROR INICIALIZANDO FS: {e}", file=sys.stderr)
        sys.exit(1)

# Funciones puente para argumentos CLI
def cmd_copyout(args):
    t = _launch_worker(args)
    work_queue.put({'op':'copyout', 'name':args.name, 'outpath':args.out})
    work_queue.join(); work_queue.put(None); t.join()

def cmd_copyin(args):
    if not os.path.exists(args.src):
        print(f"ERROR: Archivo fuente '{args.src}' no encontrado.", file=sys.stderr)
        return
    t = _launch_worker(args)
    work_queue.put({'op':'copyin', 'src':args.src, 'dest_name':args.dest_name})
    work_queue.join(); work_queue.put(None); t.join()

def cmd_delete(args):
    t = _launch_worker(args)
    work_queue.put({'op':'delete', 'name':args.name})
    work_queue.join(); work_queue.put(None); t.join()

def cmd_makecopy26(args):
    """
    Herramienta de reparación: Crea una copia de la imagen y fuerza
    la versión 26-1 en el superbloque.
    """
    src, dst = args.src, args.dst
    if not os.path.exists(src): print(f"ERROR: El archivo fuente {src} no existe.", file=sys.stderr); return
    if os.path.exists(dst): print(f"El archivo destino {dst} ya existe.", file=sys.stderr); return
    
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        fdst.write(fsrc.read())
    with open(dst, 'r+b') as f:
        f.seek(OFF_VERSION)
        f.write(EXPECTED_VERSION.ljust(LEN_VERSION, b'\x00'))
        f.flush(); os.fsync(f.fileno())
    print(f"Imagen {dst} creada con versión oficial {EXPECTED_VERSION.decode()} a partir de {src}.")

# -------------------- SELFTEST --------------------

def create_test_image(path):
    """
    Crea una imagen de disco de prueba con 2 archivos insertados y entradas limpias.
    """
    total_size = 1440 * 1024
    cluster_size = 1024
    dir_clusters = 3
    total_clusters = total_size // cluster_size
    
    # 1. Crear el archivo de imagen y rellenar con ceros
    with open(path, 'wb') as f:
        # Crea el archivo y lo rellena con ceros hasta el tamaño total
        f.write(b'\x00' * total_size)
        
    with open(path, 'r+b') as f:
        # 2. Escribir Superbloque
        sb = bytearray(SUPERBLOCK_SIZE)
        sb[OFF_IDENT:OFF_IDENT+LEN_IDENT] = EXPECTED_IDENT.ljust(LEN_IDENT, b'\x00')
        # Se usa EXPECTED_VERSION (26-1) automáticamente
        sb[OFF_VERSION:OFF_VERSION+LEN_VERSION] = EXPECTED_VERSION.ljust(LEN_VERSION, b'\x00')
        sb[OFF_LABEL:OFF_LABEL+LEN_LABEL] = b'TestImage'.ljust(LEN_LABEL, b'\x00')
        struct.pack_into('<I', sb, OFF_CLUSTER_SIZE, cluster_size)
        struct.pack_into('<I', sb, OFF_DIR_CLUSTERS, dir_clusters)
        struct.pack_into('<I', sb, OFF_TOTAL_CLUSTERS, total_clusters)
        f.seek(0); f.write(sb)
        
        # 3. Escribir Datos de Prueba
        data_cluster = 1 + dir_clusters # Cluster de datos inicial: 1 (directorio) + 3 (clusters) = 4
        readme = b'Hello FiUnamFS\n' * 100 
        logo = b'\x89PNG' + b'LOGODATA' * 100 
        
        f.seek(data_cluster * cluster_size); f.write(readme)
        readme_clusters = math.ceil(len(readme) / cluster_size)
        f.seek((data_cluster + readme_clusters) * cluster_size); f.write(logo)
        
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S').encode('ascii')
        
        # 4. Escribir Entradas de Directorio (Entry 0 y Entry 1)
        tipo = b'-'
        
        # Entry 0: README
        name_field = b'README.org'[:NAME_LEN].ljust(NAME_LEN, b'\x00')
        cluster_bytes = struct.pack('<I', data_cluster)
        size_bytes = struct.pack('<I', len(readme))
        reserved_len = ENTRY_SIZE - (1 + NAME_LEN + 4 + 4 + 14 + 14)
        entry0 = tipo + name_field + cluster_bytes + size_bytes + now + now + b'\x00' * reserved_len
        
        # Entry 1: logo
        name_field2 = b'logo.png'[:NAME_LEN].ljust(NAME_LEN, b'\x00')
        cluster_bytes2 = struct.pack('<I', data_cluster + readme_clusters) # Cluster 4 + 2 = 6
        size_bytes2 = struct.pack('<I', len(logo))
        entry1 = tipo + name_field2 + cluster_bytes2 + size_bytes2 + now + now + b'\x00' * reserved_len
        
        # Escribir entradas en el cluster 1 (inicio del directorio)
        f.seek(cluster_size * 1); 
        f.write(entry0); 
        f.write(entry1)

def run_selftest():
    """
    Ejecuta tests automáticos para verificar el ciclo de vida completo.
    """
    tmpdir = tempfile.mkdtemp(prefix='fiunamfs_test_')
    img = os.path.join(tmpdir, 'fiunamfs_test.img')
    
    try:
        # 1. Creación de imagen base
        create_test_image(img)
        print(f'Imagen de prueba creada en {img}')

        print('\n--- TEST: info ---')
        cmd_info(SimpleNamespace(image=img))

        print('\n--- TEST: list inicial ---')
        cmd_list(SimpleNamespace(image=img))

        # 2. Test copyout de archivo existente (README.org)
        print('\n--- TEST: copyout README.org ---')
        out1 = os.path.join(tmpdir, 'README.org.out')
        cmd_copyout(SimpleNamespace(image=img, name='README.org', out=out1))
        
        if os.path.exists(out1) and os.path.getsize(out1) == 1500:
            print(f"[SUCCESS] README.org ({os.path.getsize(out1)} bytes) extraído correctamente.")
        else:
            print(f"[FAILURE] La extracción no fue exitosa. Tamaño: {os.path.getsize(out1) if os.path.exists(out1) else 'N/A'}")

        # 3. Test copyin de un nuevo archivo
        test_file_path = os.path.join(tmpdir, 'NEWFILE.txt')
        test_data = b'This is a new file being copied in.' * 50
        with open(test_file_path, 'wb') as f:
            f.write(test_data)
            
        print(f'\n--- TEST: copyin {test_file_path} como newfile.txt ---')
        cmd_copyin(SimpleNamespace(image=img, src=test_file_path, dest_name='newfile.txt'))

        print('\n--- TEST: list después de copyin ---')
        cmd_list(SimpleNamespace(image=img))

        # 4. Test delete del archivo existente (logo.png, entrada 1)
        print('\n--- TEST: delete logo.png ---')
        cmd_delete(SimpleNamespace(image=img, name='logo.png'))

        print('\n--- TEST: list después de delete ---')
        cmd_list(SimpleNamespace(image=img))
        
        fs = FiUnamFS(img)
        with open(img, 'rb') as f:
            entries = fs._parse_directory(f)
            
        if entries[1]['is_unused'] and entries[1]['cluster_init'] == 0:
            print("[SUCCESS] La entrada 1 (logo.png) marcada como libre y cluster=0.")
        else:
            print("[FAILURE] La entrada 1 no fue marcada como libre después de delete.")

    except Exception as e:
        print(f"\n[FATAL ERROR] El selftest falló: {e}", file=sys.stderr)
    finally:
        print('\nSelftest terminado. Limpiando archivos temporales.')
        shutil.rmtree(tmpdir, ignore_errors=True)

# -------------------- MAIN --------------------
def main():
    p = argparse.ArgumentParser(description='FiUnamFS Manager (OOP Version)')
    sub = p.add_subparsers(dest='cmd')
    
    sub.add_parser('info').add_argument('image')
    sub.add_parser('list').add_argument('image')
    
    c_out = sub.add_parser('copyout')
    c_out.add_argument('image'); c_out.add_argument('name'); c_out.add_argument('out')
    
    c_in = sub.add_parser('copyin')
    c_in.add_argument('image'); c_in.add_argument('src'); c_in.add_argument('dest_name')
    
    c_del = sub.add_parser('delete')
    c_del.add_argument('image'); c_del.add_argument('name')
    
    mk = sub.add_parser('makecopy26')
    mk.add_argument('src'); mk.add_argument('dst')
    
    sub.add_parser('selftest')
    
    args = p.parse_args()
    if not args.cmd: p.print_help(); sys.exit(0)

    if args.cmd == 'info': cmd_info(args)
    elif args.cmd == 'list': cmd_list(args)
    elif args.cmd == 'copyout': cmd_copyout(args)
    elif args.cmd == 'copyin': cmd_copyin(args)
    elif args.cmd == 'delete': cmd_delete(args)
    elif args.cmd == 'makecopy26': cmd_makecopy26(args)
    elif args.cmd == 'selftest': run_selftest()
    else: p.print_help()

if __name__ == '__main__':
    main()