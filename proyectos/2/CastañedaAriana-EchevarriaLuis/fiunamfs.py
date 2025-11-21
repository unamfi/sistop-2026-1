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

# -------------------- Constantes --------------------
SUPERBLOCK_CLUSTER = 0   
SUPERBLOCK_SIZE = 512   
EXPECTED_IDENT = b'FiUnamFS'
# [CORRECCIÓN] Versión oficial ajustada a 26-1 por instrucción del profesor
EXPECTED_VERSION = b'26-1' 
# Patrón estricto para entrada libre: 15 puntos ASCII
FREE_ENTRY_NAME = b'.' * 15

# Offsets en superbloque
OFF_IDENT = 0
LEN_IDENT = 9
OFF_VERSION = 10
LEN_VERSION = 5
OFF_LABEL = 20
LEN_LABEL = 16
OFF_CLUSTER_SIZE = 40
OFF_DIR_CLUSTERS = 45
OFF_TOTAL_CLUSTERS = 50

ENTRY_SIZE = 64   
NAME_LEN = 15     

# Concurrencia
disk_lock = Lock()  
work_queue = Queue()  

# -------------------- Funciones de Bajo Nivel --------------------

def read_superblock_from(f):
    """
    Lee el superbloque (primer cluster) y extrae la información esencial.
    """
    f.seek(SUPERBLOCK_CLUSTER * SUPERBLOCK_SIZE)
    sb = f.read(SUPERBLOCK_SIZE)
    ident = sb[OFF_IDENT:OFF_IDENT+LEN_IDENT].split(b"\x00", 1)[0]
    version = sb[OFF_VERSION:OFF_VERSION+LEN_VERSION].split(b"\x00", 1)[0]
    label = sb[OFF_LABEL:OFF_LABEL+LEN_LABEL].split(b"\x00", 1)[0]
    
    def read_u32(offset):
        try:
            return struct.unpack_from('<I', sb, offset)[0]
        except struct.error:
            return None
            
    cluster_size = read_u32(OFF_CLUSTER_SIZE) or 1024
    dir_clusters = read_u32(OFF_DIR_CLUSTERS) or 3
    total_clusters = read_u32(OFF_TOTAL_CLUSTERS) or (1440 * 1024) // cluster_size
    
    return {
        'ident': ident,
        'version': version,
        'label': label,
        'cluster_size': cluster_size,
        'dir_clusters': dir_clusters,
        'total_clusters': total_clusters,
        'raw': sb
    }

def format_ts(dt):
    """Convierte objeto datetime a formato AAAAMMDDHHMMSS como bytes ASCII."""
    return dt.strftime('%Y%m%d%H%M%S').encode('ascii')[:14]

def parse_directory(f, cluster_size, dir_clusters, start_cluster=1):
    """
    Parsea la región del directorio, extrayendo las entradas de archivo.
    """
    dir_offset = start_cluster * cluster_size
    dir_size = dir_clusters * cluster_size
    f.seek(dir_offset)
    data = f.read(dir_size)
    entries = []
    num_entries = len(data) // ENTRY_SIZE
    
    for i in range(num_entries):
        off = i * ENTRY_SIZE
        entry = data[off:off+ENTRY_SIZE]
        if len(entry) < ENTRY_SIZE:
            break
            
        tipo = entry[0]
        name_raw = entry[1:1+NAME_LEN]
        
        try:
            name = name_raw.decode('ascii', errors='ignore').rstrip('\x00').strip()
        except Exception:
            name = ''

        # [BUG FIX] Leer cluster_init y size ANTES de verificar is_unused
        try:
            cluster_init = struct.unpack_from('<I', entry, 16)[0]
        except Exception:
            cluster_init = 0
            
        try:
            size = struct.unpack_from('<I', entry, 20)[0]
        except Exception:
            size = 0

        # [VERIFICACIÓN] La entrada es libre si el nombre es el patrón de puntos,
        # todo nulo, o si está vacío con tamaño cero.
        is_unused = (name_raw == FREE_ENTRY_NAME) or \
                    (name_raw == b'\x00'*NAME_LEN) or \
                    (name == '' and cluster_init == 0 and size == 0)
            
        created_raw = entry[24:38].decode('ascii', errors='ignore').rstrip('\x00').strip()
        modified_raw = entry[38:52].decode('ascii', errors='ignore').rstrip('\x00').strip()
        
        def parse_ts(s):
            """Intenta parsear la marca de tiempo AAAAMMDDHHMMSS."""
            if isinstance(s, str) and len(s) >= 14 and s.isdigit():
                try:
                    return datetime.datetime.strptime(s[:14], '%Y%m%d%H%M%S')
                except Exception:
                    pass
            return s or None
            
        entries.append({
            'index': i,
            'tipo': tipo,
            'name': name,
            'name_raw': name_raw,
            'is_unused': is_unused,
            'cluster_init': cluster_init,
            'size': size,
            'created': parse_ts(created_raw),
            'modified': parse_ts(modified_raw),
            'raw': entry
        })
    return entries

def find_free_directory_entry(entries):
    """Devuelve índice de primera entrada libre/no utilizada."""
    for e in entries:
        if e['is_unused']:
            return e['index']
    return None

def used_ranges_from_entries(entries, cluster_size):
    """Calcula los rangos de clusters ocupados por los archivos activos."""
    ranges = []
    for e in entries:
        if not e['is_unused'] and e['size'] > 0 and e['cluster_init'] > 0:
            start = e['cluster_init']
            needed = math.ceil(e['size'] / cluster_size)
            ranges.append((start, start + needed))
    ranges.sort()
    return ranges

def find_contiguous_gap(ranges, data_start, total_clusters, needed):
    """Busca el primer espacio contiguo libre para el nuevo archivo."""
    cur = data_start
    for (s, e) in ranges:
        if cur + needed <= s:
            return cur
        cur = max(cur, e)
    if cur + needed <= total_clusters:
        return cur
    return None


def safe_backup(path):
    """Crea una copia de seguridad segura del archivo de imagen antes de modificarlo."""
    bak = path + '.bak'
    if not os.path.exists(bak):
        with disk_lock:
            try:
                with open(path, 'rb') as src, open(bak, 'wb') as dst:
                    dst.write(src.read())
            except Exception as e:
                print(f"Error creando backup: {e}")
                return None
    return bak

def read_file_from_image(path, cluster_init, size, cluster_size):
    """Lee el contenido de un archivo desde la imagen de disco de forma segura."""
    with disk_lock:
        with open(path, 'rb') as f:
            f.seek(cluster_init * cluster_size)
            return f.read(size)

def write_file_to_image(path, cluster_init, data, cluster_size):
    """Escribe los datos de un archivo en la imagen de disco de forma segura."""
    with disk_lock:
        with open(path, 'r+b') as f:
            f.seek(cluster_init * cluster_size)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

def update_directory_entry(path, entry_index, new_entry_bytes, cluster_size, dir_start_cluster=1):
    """Actualiza una entrada de directorio específica en el disco."""
    dir_offset = dir_start_cluster * cluster_size
    entry_offset = dir_offset + entry_index * ENTRY_SIZE
    with disk_lock:
        with open(path, 'r+b') as f:
            f.seek(entry_offset)
            f.write(new_entry_bytes)
            f.flush(); os.fsync(f.fileno())


# -------------------- Hilo Worker (Productor/Consumidor) --------------------

def worker(path, cluster_size, dir_clusters, total_clusters):
    """Hilo trabajador que procesa tareas de copyin, copyout y delete de la cola."""
    while True:
        task = work_queue.get()
        if task is None:
            # Señal de terminación recibida
            work_queue.task_done()
            break
            
        op = task.get('op')
        try:
            if op == 'copyout':
                _task_copyout(path, cluster_size, task)
            elif op == 'copyin':
                _task_copyin(path, cluster_size, dir_clusters, total_clusters, task)
            elif op == 'delete':
                _task_delete(path, cluster_size, dir_clusters, task)
        except Exception as e:
            # Si hay un error, lo registramos. El hilo principal debe manejar la detención.
            print(f"[WORKER ERROR] Error en tarea {op}: {e}", file=sys.stderr)
        
        # Indica que la tarea actual ha terminado, permitiendo al hilo principal avanzar
        work_queue.task_done()


def _task_copyout(path, cluster_size, task):
    """Tarea para extraer un archivo de la imagen al sistema de archivos local."""
    filename = task['name']
    outpath = task['outpath']
    with open(path, 'rb') as f:
        sb = read_superblock_from(f)
        entries = parse_directory(f, cluster_size, sb['dir_clusters'])
        
        found = [e for e in entries if (not e['is_unused']) and e['name'] == filename]
        if not found:
            print(f"Archivo {filename} no encontrado en imagen.")
            return
            
        e = found[0]
        data = read_file_from_image(path, e['cluster_init'], e['size'], cluster_size)
        
        with open(outpath, 'wb') as out:
            out.write(data)
        print(f"Archivo {filename} extraído correctamente → {outpath}")

def _task_copyin(path, cluster_size, dir_clusters, total_clusters, task):
    """Tarea para insertar un archivo en la imagen de disco."""
    src = task['src']
    dest_name = task['dest_name']
    
    with open(src, 'rb') as s:
        data = s.read()
        
    size = len(data)
    needed_clusters = math.ceil(size / cluster_size)
    
    with open(path, 'r+b') as f:
        sb = read_superblock_from(f)
        entries = parse_directory(f, cluster_size, sb['dir_clusters'])
        
        dir_index = find_free_directory_entry(entries)
        if dir_index is None:
            print("No hay entradas libres en el directorio.")
            return
            
        ranges = used_ranges_from_entries(entries, cluster_size)
        data_start = (1 + sb['dir_clusters'])
        target_cluster = find_contiguous_gap(ranges, data_start, sb['total_clusters'], needed_clusters)
        
        if target_cluster is None:
            print("No hay espacio contiguo suficiente en el disco.")
            return
            
        write_file_to_image(path, target_cluster, 
                            data + b'\x00' * (needed_clusters*cluster_size - size), 
                            cluster_size)
                            
        # Construir y actualizar entrada de directorio
        tipo = b'-' # Tipo de archivo normal (ej. '\x2d')
        name_field = dest_name.encode('ascii', errors='ignore')[:NAME_LEN].ljust(NAME_LEN, b'\x00')
        cluster_bytes = struct.pack('<I', target_cluster)
        size_bytes = struct.pack('<I', size)
        now = format_ts(datetime.datetime.now())
        created = now
        modified = now
        reserved_len = ENTRY_SIZE - (1 + NAME_LEN + 4 + 4 + 14 + 14)
        reserved = b'\x00' * reserved_len
        new_entry = tipo + name_field + cluster_bytes + size_bytes + created + modified + reserved
        
        update_directory_entry(path, dir_index, new_entry, cluster_size)
        print(f"Archivo {src} escrito como {dest_name} en cluster {target_cluster} (tamaño {size} bytes).")

def _task_delete(path, cluster_size, dir_clusters, task):
    """Tarea para marcar un archivo como eliminado (entrada de directorio libre)."""
    name = task['name']
    
    with open(path, 'r+b') as f:
        sb = read_superblock_from(f)
        entries = parse_directory(f, cluster_size, sb['dir_clusters'])
        
        found = [e for e in entries if (not e['is_unused']) and e['name'] == name]
        if not found:
            print(f"Archivo {name} no encontrado en el directorio.")
            return
            
        e = found[0]
        
        # Construir entrada de directorio 'eliminada/libre'
        tipo = b'\x2f' # Tipo de archivo eliminado (ej. '/')
        # Marcar como libre con el patrón de puntos
        name_field = FREE_ENTRY_NAME 
        cluster_bytes = struct.pack('<I', 0) # Cluster inicial a 0
        size_bytes = struct.pack('<I', 0)    # Tamaño a 0
        created = b'0'*14
        modified = b'0'*14
        
        reserved_len = ENTRY_SIZE - (1 + NAME_LEN + 4 + 4 + 14 + 14)
        reserved = b'\x00' * reserved_len
        
        new_entry = tipo + name_field + cluster_bytes + size_bytes + created + modified + reserved
        
        update_directory_entry(path, e['index'], new_entry, cluster_size)
        print(f"Archivo {name} eliminado correctamente (entrada {e['index']} marcada como libre).")

# -------------------- CLI Comandos --------------------

def _check_fs_validity(sb):
    """Valida el identificador y la versión del superbloque."""
    if sb['ident'] != EXPECTED_IDENT:
        print(f"ERROR: Identificador esperado '{EXPECTED_IDENT.decode()}', encontrado '{sb['ident'].decode()}'.", file=sys.stderr)
        return False
    if sb['version'] != EXPECTED_VERSION:
        print(f"ERROR: La versión no es {EXPECTED_VERSION.decode()}. Ejecuta makecopy26 para convertir/reparar la imagen.", file=sys.stderr)
        return False
    return True

def cmd_info(args):
    """Muestra información del superbloque del sistema de archivos."""
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
    print('Ident:', sb['ident'].decode('ascii'))
    print('Version:', sb['version'].decode('ascii'))
    print('Label:', sb['label'].decode('ascii'))
    print('Cluster size:', sb['cluster_size'], 'bytes')
    print('Dir clusters:', sb['dir_clusters'])
    print('Total clusters:', sb['total_clusters'])
    
    if not _check_fs_validity(sb):
        print(f"AVISO: La imagen puede no ser un FiUnamFS {EXPECTED_VERSION.decode()} válido.")

def cmd_list(args):
    """
    Lista SOLO los archivos activos en el directorio, ocultando entradas vacías
    o marcadores de borrado para mejorar la experiencia de usuario.
    """
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
        
    if not _check_fs_validity(sb):
        return

    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
        entries = parse_directory(f, sb['cluster_size'], sb['dir_clusters'])
        
    archivos_activos = [
        e for e in entries 
        if not e['is_unused'] and e['name'] != '--------------' and e['name'] != '...............'
    ]
        
    print(f'Entradas del directorio ({len(archivos_activos)} archivos activos):')
    
    for e in archivos_activos:
        created = e['created']
        if isinstance(created, datetime.datetime):
            created = created.strftime('%Y-%m-%d %H:%M:%S')

        print(f"Index={e['index']} | Name={e['name']} | Size={e['size']} bytes | Cluster={e['cluster_init']} | Created={created}")

def cmd_copyout(args):
    """Extrae archivo de imagen usando el worker (productor/consumidor)."""
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
        
    if not _check_fs_validity(sb): return
        
    t = Thread(target=worker, args=(args.image, sb['cluster_size'], sb['dir_clusters'], sb['total_clusters']), daemon=True)
    t.start()
    
    work_queue.put({'op':'copyout', 'name': args.name, 'outpath': args.out})
    work_queue.join()
    
    work_queue.put(None)
    t.join()

def cmd_copyin(args):
    """Inserta archivo en imagen usando el worker y realiza backup previo."""
    
    if len(args.dest_name) >= NAME_LEN:
        print(f"ERROR: El nombre de destino '{args.dest_name}' excede {NAME_LEN - 1} caracteres.", file=sys.stderr)
        return
        
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
        
    if not _check_fs_validity(sb): return
        
    if not os.path.exists(args.src):
        print(f"ERROR: Archivo fuente '{args.src}' no encontrado.", file=sys.stderr)
        return
        
    safe_backup(args.image)
    t = Thread(target=worker, args=(args.image, sb['cluster_size'], sb['dir_clusters'], sb['total_clusters']), daemon=True)
    t.start()
    
    work_queue.put({'op':'copyin', 'src': args.src, 'dest_name': args.dest_name})
    work_queue.join()
    
    work_queue.put(None)
    t.join()

def cmd_delete(args):
    """Elimina archivo usando el worker (marca como libre) y realiza backup previo."""
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
        
    if not _check_fs_validity(sb): return
        
    safe_backup(args.image)
    t = Thread(target=worker, args=(args.image, sb['cluster_size'], sb['dir_clusters'], sb['total_clusters']), daemon=True)
    t.start()
    
    work_queue.put({'op':'delete', 'name': args.name})
    work_queue.join()
    
    work_queue.put(None)
    t.join()

def cmd_makecopy26(args):
    """Crea una copia del FS fuente y fuerza la versión oficial (26-1) en el superbloque."""
    src = args.src
    dst = args.dst
    if not os.path.exists(src):
        print(f"ERROR: El archivo fuente {src} no existe.", file=sys.stderr)
        return
    if os.path.exists(dst):
        print(f"El archivo destino {dst} ya existe.", file=sys.stderr)
        return
        
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        fdst.write(fsrc.read())
        
    with open(dst, 'r+b') as f:
        f.seek(OFF_VERSION)
        f.write(EXPECTED_VERSION.ljust(LEN_VERSION, b'\x00'))
        f.flush(); os.fsync(f.fileno())
        
    print(f"Imagen {dst} creada con versión oficial {EXPECTED_VERSION.decode()} a partir de {src}.")

# -------------------- Pruebas y Creación de Imagen --------------------

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
        readme = b'Hello FiUnamFS\n' * 100 # 1600 bytes -> 2 clusters
        logo = b'\x89PNG' + b'LOGODATA' * 100 # 804 bytes -> 1 cluster
        
        f.seek(data_cluster * cluster_size); f.write(readme)
        readme_clusters = math.ceil(len(readme) / cluster_size)
        f.seek((data_cluster + readme_clusters) * cluster_size); f.write(logo)
        
        now = format_ts(datetime.datetime.now())
        
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
        # El resto del directorio ya está en ceros gracias a la inicialización del archivo.

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
        
        # Verificación de que la entrada 1 ha sido marcada como libre/borrada
        with open(img, 'rb') as f:
            sb = read_superblock_from(f)
            entries = parse_directory(f, sb['cluster_size'], sb['dir_clusters'])
            
        if entries[1]['is_unused'] and entries[1]['cluster_init'] == 0:
            print("[SUCCESS] La entrada 1 (logo.png) marcada como libre y cluster=0.")
        else:
            print("[FAILURE] La entrada 1 no fue marcada como libre después de delete.")

    except Exception as e:
        print(f"\n[FATAL ERROR] El selftest falló: {e}", file=sys.stderr)
    finally:
        print('\nSelftest terminado. Limpiando archivos temporales.')
        shutil.rmtree(tmpdir, ignore_errors=True)


# -------------------- CLI--------------------

def main():
    parser = argparse.ArgumentParser(description='FiUnamFS tool (version 26-1)')
    sub = parser.add_subparsers(dest='cmd')
    
    p_info = sub.add_parser('info'); p_info.add_argument('image')
    p_list = sub.add_parser('list'); p_list.add_argument('image')
    
    p_copyout = sub.add_parser('copyout'); 
    p_copyout.add_argument('image'); 
    p_copyout.add_argument('name'); 
    p_copyout.add_argument('out')
    
    p_copyin = sub.add_parser('copyin'); 
    p_copyin.add_argument('image'); 
    p_copyin.add_argument('src'); 
    p_copyin.add_argument('dest_name')
    
    p_delete = sub.add_parser('delete'); 
    p_delete.add_argument('image'); 
    p_delete.add_argument('name')
    
    p_make = sub.add_parser('makecopy26'); 
    p_make.add_argument('src'); 
    p_make.add_argument('dst')
    
    p_self = sub.add_parser('selftest')
    
    args = parser.parse_args()
    
    if not args.cmd:
        parser.print_help(); sys.exit(0)
        
    if args.cmd == 'info': cmd_info(args)
    elif args.cmd == 'list': cmd_list(args)
    elif args.cmd == 'copyout': cmd_copyout(args)
    elif args.cmd == 'copyin': cmd_copyin(args)
    elif args.cmd == 'delete': cmd_delete(args)
    elif args.cmd == 'makecopy26': cmd_makecopy26(args)
    elif args.cmd == 'selftest': run_selftest()

if __name__ == '__main__':
    main()