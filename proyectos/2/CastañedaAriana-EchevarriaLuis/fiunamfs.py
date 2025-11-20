import argparse
import struct
import os
import datetime
import sys
import shutil
from threading import Thread, Lock
from queue import Queue

SUPERBLOCK_CLUSTER = 0
SUPERBLOCK_SIZE = 512
EXPECTED_IDENT = b'FiUnamFS'
EXPECTED_VERSION = b'26-2'

OFF_IDENT = 0; LEN_IDENT = 9
OFF_VERSION = 10; LEN_VERSION = 5
OFF_LABEL = 20; LEN_LABEL = 16
OFF_CLUSTER_SIZE = 40
OFF_DIR_CLUSTERS = 45
OFF_TOTAL_CLUSTERS = 50

ENTRY_SIZE = 64
NAME_LEN = 15

disk_lock = Lock()
work_queue = Queue()

def safe_backup(filepath):
    backup_path = filepath + ".bak"
    try:
        shutil.copy2(filepath, backup_path)
        print(f"Respaldo creado: {backup_path}")
    except IOError as e:
        print(f"No se pudo crear respaldo: {e}")

def read_superblock_from(f):
    f.seek(SUPERBLOCK_CLUSTER * SUPERBLOCK_SIZE)
    sb = f.read(SUPERBLOCK_SIZE)
    ident = sb[OFF_IDENT:OFF_IDENT+LEN_IDENT].split(b"\x00", 1)[0]
    version = sb[OFF_VERSION:OFF_VERSION+LEN_VERSION].split(b"\x00", 1)[0]
    label = sb[OFF_LABEL:OFF_LABEL+LEN_LABEL].split(b"\x00", 1)[0]
    def read_u32(offset):
        try: return struct.unpack_from('<I', sb, offset)[0]
        except: return None
    return {
        'ident': ident,
        'version': version,
        'label': label,
        'cluster_size': read_u32(OFF_CLUSTER_SIZE) or 1024,
        'dir_clusters': read_u32(OFF_DIR_CLUSTERS) or 3,
        'total_clusters': read_u32(OFF_TOTAL_CLUSTERS) or 1440
    }

def parse_directory(f, cluster_size, dir_clusters, start_cluster=1):
    dir_offset = start_cluster * cluster_size
    dir_size = dir_clusters * cluster_size
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
        
        is_unused = (name == '' or name_raw == b'\x00'*NAME_LEN or name_raw.startswith(b'.') or name_raw.startswith(b'-'))
        
        try: cluster_init = struct.unpack_from('<I', entry, 16)[0]
        except: cluster_init = 0
        try: size = struct.unpack_from('<I', entry, 20)[0]
        except: size = 0
        
        c_raw = entry[24:38].decode('ascii', errors='ignore')
        m_raw = entry[38:52].decode('ascii', errors='ignore')

        entries.append({
            'index': i,
            'name': name,
            'is_unused': is_unused,
            'cluster_init': cluster_init,
            'size': size,
            'created': c_raw,
            'modified': m_raw
        })
    return entries

def worker(img_path, cluster_size, dir_clusters, total_clusters):
    while True:
        task = work_queue.get()
        if task is None: break
        
        op = task.get('op')
        try:
            with disk_lock:
                mode = 'r+b' if os.path.exists(img_path) else 'wb'
                with open(img_path, mode) as f:
                    if op == 'copyout':
                        _logic_copyout(f, task, cluster_size, dir_clusters)
                    elif op == 'copyin':
                        _logic_copyin(f, task, cluster_size, dir_clusters, total_clusters)
                    elif op == 'delete':
                        _logic_delete(f, task, cluster_size, dir_clusters)
        except Exception as e:
            print(f"Error en tarea {op}: {e}")
        finally:
            work_queue.task_done()

def _logic_copyout(f, task, cluster_size, dir_clusters):
    entries = parse_directory(f, cluster_size, dir_clusters)
    target = task['name']
    out = task['out']
    
    found = next((e for e in entries if not e['is_unused'] and e['name'] == target), None)
    if not found:
        print(f"Archivo {target} no encontrado")
        return

    f.seek(found['cluster_init'] * cluster_size)
    data = f.read(found['size'])
    with open(out, 'wb') as fout:
        fout.write(data)
    print(f"Copiado a {out}")

def _logic_copyin(f, task, cluster_size, dir_clusters, total_clusters):
    src_path = task['src']
    dest_name = task['dest']
    
    if not os.path.exists(src_path):
        print(f"Origen {src_path} no existe")
        return
    file_size = os.path.getsize(src_path)
    
    if len(dest_name) > NAME_LEN:
        print("Nombre destino muy largo")
        return
        
    entries = parse_directory(f, cluster_size, dir_clusters)
    if any(not e['is_unused'] and e['name'] == dest_name for e in entries):
        print(f"Ya existe {dest_name}")
        return

    free_entry_idx = next((e['index'] for e in entries if e['is_unused']), None)
    if free_entry_idx is None:
        print("Directorio lleno")
        return

    max_cluster = dir_clusters
    for e in entries:
        if not e['is_unused'] and e['size'] > 0:
            c_needed = (e['size'] + cluster_size - 1) // cluster_size
            end_c = e['cluster_init'] + c_needed
            if end_c > max_cluster: max_cluster = end_c
    
    start_cluster = max_cluster + 1
    needed_clusters = (file_size + cluster_size - 1) // cluster_size
    
    if start_cluster + needed_clusters > total_clusters:
        print("Espacio insuficiente")
        return

    with open(src_path, 'rb') as fsrc:
        raw_data = fsrc.read()
    
    f.seek(start_cluster * cluster_size)
    f.write(raw_data)
    
    entry_bytes = bytearray(ENTRY_SIZE)
    entry_bytes[0] = 0x2d
    
    name_bytes = dest_name.encode('ascii').ljust(15, b'\x00')
    entry_bytes[1:16] = name_bytes
    
    struct.pack_into('<I', entry_bytes, 16, start_cluster)
    struct.pack_into('<I', entry_bytes, 20, file_size)
    
    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S').encode('ascii')
    entry_bytes[24:38] = now
    entry_bytes[38:52] = now
    
    dir_start_offset = 1 * cluster_size
    entry_offset = dir_start_offset + (free_entry_idx * ENTRY_SIZE)
    f.seek(entry_offset)
    f.write(entry_bytes)
    print(f"Importado {dest_name}")

def _logic_delete(f, task, cluster_size, dir_clusters):
    target = task['name']
    entries = parse_directory(f, cluster_size, dir_clusters)
    found = next((e for e in entries if not e['is_unused'] and e['name'] == target), None)
    
    if not found:
        print(f"No encontrado {target}")
        return
        
    dir_start_offset = 1 * cluster_size
    entry_offset = dir_start_offset + (found['index'] * ENTRY_SIZE)
    
    f.seek(entry_offset)
    empty_entry = bytearray(ENTRY_SIZE)
    empty_entry[0] = 0x2f
    empty_entry[1:16] = b'.' * 15
    f.write(empty_entry)
    print(f"Eliminado {target}")

def cmd_info(args):
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
    print(f"Ident: {sb['ident']}, Version: {sb['version']}, Label: {sb['label']}")
    print(f"Cluster size: {sb['cluster_size']}, Total clusters: {sb['total_clusters']}")

def cmd_list(args):
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
        entries = parse_directory(f, sb['cluster_size'], sb['dir_clusters'])
    print('Entradas del directorio:')
    for e in entries:
       # if not e['is_unused']:
            print(f"- {e['name']} | size={e['size']} | cluster={e['cluster_init']}")

def cmd_makecopy26(args):
    src = args.src
    dst = args.dst
    if os.path.exists(dst):
        print(f"El archivo destino {dst} ya existe.")
        return
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        fdst.write(fsrc.read())
    with open(dst, 'r+b') as f:
        f.seek(OFF_VERSION)
        f.write(EXPECTED_VERSION.ljust(LEN_VERSION, b'\x00'))
        f.flush(); os.fsync(f.fileno())
    print(f"Imagen {dst} creada con versión 26-2 correctamente.")

def init_worker(image_path):
    if not os.path.exists(image_path):
        print("La imagen no existe")
        sys.exit(1)
    with open(image_path, 'rb') as f:
        sb = read_superblock_from(f)
    t = Thread(target=worker, args=(image_path, sb['cluster_size'], sb['dir_clusters'], sb['total_clusters']), daemon=True)
    t.start()
    return t

def cmd_copyout(args):
    init_worker(args.image)
    work_queue.put({'op': 'copyout', 'name': args.name, 'out': args.out})
    work_queue.join()

def cmd_copyin(args):
    safe_backup(args.image)
    init_worker(args.image)
    work_queue.put({'op': 'copyin', 'src': args.src, 'dest': args.dest})
    work_queue.join()

def cmd_delete(args):
    safe_backup(args.image)
    init_worker(args.image)
    work_queue.put({'op': 'delete', 'name': args.name})
    work_queue.join()

def main():
    parser = argparse.ArgumentParser(description='FiUnamFS tool')
    sub = parser.add_subparsers(dest='cmd')
    
    sub.add_parser('info').add_argument('image')
    sub.add_parser('list').add_argument('image')
    
    p_out = sub.add_parser('copyout')
    p_out.add_argument('image'); p_out.add_argument('name'); p_out.add_argument('out')
    
    p_in = sub.add_parser('copyin')
    p_in.add_argument('image'); p_in.add_argument('src'); p_in.add_argument('dest')
    
    p_del = sub.add_parser('delete')
    p_del.add_argument('image'); p_del.add_argument('name')
    
    p_make = sub.add_parser('makecopy26')
    p_make.add_argument('src'); p_make.add_argument('dst')
    
    args = parser.parse_args()
    
    if args.cmd == 'info': cmd_info(args)
    elif args.cmd == 'list': cmd_list(args)
    elif args.cmd == 'copyout': cmd_copyout(args)
    elif args.cmd == 'copyin': cmd_copyin(args)
    elif args.cmd == 'delete': cmd_delete(args)
    elif args.cmd == 'makecopy26': cmd_makecopy26(args)
    else: parser.print_help()

if __name__ == '__main__':
    main()
