import argparse
import struct
import os
import math
import datetime
from threading import Thread, Lock
from queue import Queue
import sys
import tempfile
from types import SimpleNamespace

# Constantes
SUPERBLOCK_CLUSTER = 0
DEFAULT_CLUSTER_SIZE = 1024  # fallback
EXPECTED_IDENT = b'FiUnamFS'
EXPECTED_VERSION = b'26-2'  # exigido por la especificacion

# Offsets in superbloque (based on spec)
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

# Threading globals
disk_lock = Lock()
work_queue = Queue()

# Utilities

def read_superblock_from(f):
    # f: file object opened in binary mode
    f.seek(SUPERBLOCK_CLUSTER * 512)
    sb = f.read(512)
    ident = sb[OFF_IDENT:OFF_IDENT+LEN_IDENT].split(b"\x00",1)[0]
    version = sb[OFF_VERSION:OFF_VERSION+LEN_VERSION].split(b"\x00",1)[0]
    label = sb[OFF_LABEL:OFF_LABEL+LEN_LABEL].split(b"\x00",1)[0]
    def read_u32(offset):
        try:
            return struct.unpack_from('<I', sb, offset)[0]
        except struct.error:
            return None
    cluster_size = read_u32(OFF_CLUSTER_SIZE) or DEFAULT_CLUSTER_SIZE
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


def parse_directory(f, cluster_size, dir_clusters, start_cluster=1):
    dir_offset = start_cluster * cluster_size
    dir_size = dir_clusters * cluster_size
    f.seek(dir_offset)
    ddata = f.read(dir_size)
    entries = []
    num_entries = len(ddata) // ENTRY_SIZE
    for i in range(num_entries):
        off = i * ENTRY_SIZE
        entry = ddata[off:off+ENTRY_SIZE]
        if len(entry) < ENTRY_SIZE:
            continue
        tipo = entry[0]
        name = entry[1:15].decode('ascii', errors='ignore').rstrip('\x00').strip()
        is_unused = (name == '' or set(name) == {'.'} or entry[1:15] == b'.'*14)
        try:
            cluster_init = struct.unpack_from('<I', entry, 16)[0]
        except Exception:
            cluster_init = 0
        try:
            size = struct.unpack_from('<I', entry, 20)[0]
        except Exception:
            size = 0
        created_raw = entry[24:38].decode('ascii', errors='ignore').rstrip('\x00').strip()
        modified_raw = entry[38:52].decode('ascii', errors='ignore').rstrip('\x00').strip()
        def parse_ts(s):
            if isinstance(s, str) and len(s) >= 14 and s.isdigit():
                try:
                    return datetime.datetime.strptime(s[:14], "%Y%m%d%H%M%S")
                except Exception:
                    return s
            return s or None
        created = parse_ts(created_raw)
        modified = parse_ts(modified_raw)
        entries.append({
            'index': i,
            'tipo': tipo,
            'name': name,
            'is_unused': is_unused,
            'cluster_init': cluster_init,
            'size': size,
            'created': created,
            'modified': modified,
            'raw': entry
        })
    return entries


def find_free_directory_entry(entries):
    for e in entries:
        if e['is_unused']:
            return e['index']
    return None


def used_ranges_from_entries(entries, cluster_size):
    ranges = []  # list of (start_cluster, end_cluster_exclusive)
    for e in entries:
        if not e['is_unused'] and e['size'] > 0 and e['cluster_init'] > 0:
            start = e['cluster_init']
            needed = math.ceil(e['size'] / cluster_size)
            ranges.append((start, start + needed))
    ranges.sort()
    return ranges


def find_contiguous_gap(ranges, data_start, total_clusters, needed):
    # search from data_start to total_clusters
    cur = data_start
    for (s,e) in ranges:
        if cur + needed <= s:
            return cur
        cur = max(cur, e)
    if cur + needed <= total_clusters:
        return cur
    return None


# Disk operations (thread-safe)

def safe_backup(path):
    bak = path + '.bak'
    if not os.path.exists(bak):
        with disk_lock:
            with open(path, 'rb') as src, open(bak, 'wb') as dst:
                dst.write(src.read())
    return bak


def read_file_from_image(path, cluster_init, size, cluster_size):
    with disk_lock:
        with open(path, 'rb') as f:
            f.seek(cluster_init * cluster_size)
            return f.read(size)


def write_file_to_image(path, cluster_init, data, cluster_size):
    with disk_lock:
        with open(path, 'r+b') as f:
            f.seek(cluster_init * cluster_size)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())


def update_directory_entry(path, entry_index, new_entry_bytes, cluster_size, dir_start_cluster=1):
    dir_offset = dir_start_cluster * cluster_size
    entry_offset = dir_offset + entry_index * ENTRY_SIZE
    with disk_lock:
        with open(path, 'r+b') as f:
            f.seek(entry_offset)
            f.write(new_entry_bytes)
            f.flush(); os.fsync(f.fileno())


# Task workers

def worker(path, cluster_size, dir_clusters, total_clusters):
    while True:
        task = work_queue.get()
        if task is None:
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
            print(f"Error en tarea {op}: {e}")
        work_queue.task_done()


def _task_copyout(path, cluster_size, task):
    filename = task['name']
    outpath = task['outpath']
    with open(path, 'rb') as f:
        sb = read_superblock_from(f)
        entries = parse_directory(f, cluster_size, sb['dir_clusters'])
        # find file
        found = [e for e in entries if (not e['is_unused']) and e['name'] == filename]
        if not found:
            print(f"Archivo {filename} no encontrado en imagen.")
            return
        e = found[0]
        data = read_file_from_image(path, e['cluster_init'], e['size'], cluster_size)
        with open(outpath, 'wb') as out:
            out.write(data)
        print(f"Extracted {filename} -> {outpath} ({len(data)} bytes)")


def _task_copyin(path, cluster_size, dir_clusters, total_clusters, task):
    src = task['src']
    dest_name = task['dest_name']
    # read file
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
            print("No hay espacio contiguo suficiente en la imagen.")
            return
        # write data
        write_file_to_image(path, target_cluster, data + b'\x00' * (needed_clusters*cluster_size - size), cluster_size)
        # build directory entry bytes
        tipo = b'\x2d'  # '-'
        name_field = dest_name.encode('ascii', errors='ignore')[:14].ljust(14, b'\x00')
        cluster_bytes = struct.pack('<I', target_cluster)
        size_bytes = struct.pack('<I', size)
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S').encode('ascii')
        created = now.ljust(14, b'0')[:14]
        modified = now.ljust(14, b'0')[:14]
        reserved = b'\x00' * (ENTRY_SIZE - 1 - 14 - 4 - 4 - 14 - 14)
        new_entry = tipo + name_field + cluster_bytes + size_bytes + created + modified + reserved
        update_directory_entry(path, dir_index, new_entry, cluster_size)
        print(f"Wrote {src} as {dest_name} at cluster {target_cluster} ({size} bytes)")


def _task_delete(path, cluster_size, dir_clusters, task):
    name = task['name']
    with open(path, 'r+b') as f:
        sb = read_superblock_from(f)
        entries = parse_directory(f, cluster_size, sb['dir_clusters'])
        found = [e for e in entries if (not e['is_unused']) and e['name'] == name]
        if not found:
            print(f"Archivo {name} no encontrado.")
            return
        e = found[0]
        # mark entry as unused: tipo = 0x2f ('/') and name set to dots
        tipo = b'\x2f'
        name_field = b'.' * 14
        cluster_bytes = struct.pack('<I', 0)
        size_bytes = struct.pack('<I', 0)
        created = b'0'*14
        modified = b'0'*14
        reserved = b'\x00' * (ENTRY_SIZE - 1 - 14 - 4 - 4 - 14 - 14)
        new_entry = tipo + name_field + cluster_bytes + size_bytes + created + modified + reserved
        update_directory_entry(path, e['index'], new_entry, cluster_size)
        print(f"Deleted {name}")


# CLI

def cmd_info(args):
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
    print('Ident:', sb['ident'])
    print('Version:', sb['version'])
    print('Label:', sb['label'])
    print('Cluster size:', sb['cluster_size'])
    print('Dir clusters:', sb['dir_clusters'])
    print('Total clusters:', sb['total_clusters'])


def cmd_list(args):
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
        entries = parse_directory(f, sb['cluster_size'], sb['dir_clusters'])
    print('Directory entries:')
    for e in entries:
        if e['is_unused']:
            continue
        print(f"- {e['name']} | size={e['size']} | cluster={e['cluster_init']} | modified={e['modified']}")


def cmd_copyout(args):
    # queue a copyout task
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
    if sb['version'] != EXPECTED_VERSION:
        print(f"ERROR: La imagen no tiene versi\u00f3n {EXPECTED_VERSION.decode()} en superbloque. Ejecuta makecopy26 o verifica la imagen.")
        return
    # start worker
    t = Thread(target=worker, args=(args.image, sb['cluster_size'], sb['dir_clusters'], sb['total_clusters']), daemon=True)
    t.start()
    work_queue.put({'op':'copyout', 'name': args.name, 'outpath': args.out})
    work_queue.join()
    work_queue.put(None); t.join()


def cmd_copyin(args):
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
    if sb['version'] != EXPECTED_VERSION:
        print(f"ERROR: La imagen no tiene versi\u00f3n {EXPECTED_VERSION.decode()} en superbloque. Ejecuta makecopy26 o verifica la imagen.")
        return
    safe_backup(args.image)
    t = Thread(target=worker, args=(args.image, sb['cluster_size'], sb['dir_clusters'], sb['total_clusters']), daemon=True)
    t.start()
    work_queue.put({'op':'copyin', 'src': args.src, 'dest_name': args.dest_name})
    work_queue.join(); work_queue.put(None); t.join()


def cmd_delete(args):
    with open(args.image, 'rb') as f:
        sb = read_superblock_from(f)
    if sb['version'] != EXPECTED_VERSION:
        print(f"ERROR: La imagen no tiene versi\u00f3n {EXPECTED_VERSION.decode()} en superbloque. Ejecuta makecopy26 o verifica la imagen.")
        return
    safe_backup(args.image)
    t = Thread(target=worker, args=(args.image, sb['cluster_size'], sb['dir_clusters'], sb['total_clusters']), daemon=True)
    t.start()
    work_queue.put({'op':'delete', 'name': args.name})
    work_queue.join(); work_queue.put(None); t.join()


def cmd_makecopy26(args):
    # Create a copy and write version bytes at OFF_VERSION
    src = args.src
    dst = args.dst
    if os.path.exists(dst):
        print(f"Destination {dst} already exists; aborting.")
        return
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        data = fsrc.read()
        fdst.write(data)
    # patch version
    with open(dst, 'r+b') as f:
        f.seek(OFF_VERSION)
        f.write(EXPECTED_VERSION.ljust(LEN_VERSION, b'\x00'))
        f.flush(); os.fsync(f.fileno())
    print(f"Created copy {dst} with version set to {EXPECTED_VERSION.decode()}")


def create_test_image(path):
    """Crea una imagen de prueba pequeña compatible con la especificación.
    La imagen es del tamaño real (1440 KiB) para mantener consistencia.
    """
    total_size = 1440 * 1024
    cluster_size = DEFAULT_CLUSTER_SIZE
    dir_clusters = 3
    total_clusters = total_size // cluster_size
    # create zero-filled image
    with open(path, 'wb') as f:
        f.truncate(total_size)
    # write superbloque
    with open(path, 'r+b') as f:
        sb = bytearray(512)
        sb[OFF_IDENT:OFF_IDENT+LEN_IDENT] = EXPECTED_IDENT.ljust(LEN_IDENT, b'\x00')
        sb[OFF_VERSION:OFF_VERSION+LEN_VERSION] = EXPECTED_VERSION.ljust(LEN_VERSION, b'\x00')
        sb[OFF_LABEL:OFF_LABEL+LEN_LABEL] = b'TestImage'.ljust(LEN_LABEL, b'\x00')
        struct.pack_into('<I', sb, OFF_CLUSTER_SIZE, cluster_size)
        struct.pack_into('<I', sb, OFF_DIR_CLUSTERS, dir_clusters)
        struct.pack_into('<I', sb, OFF_TOTAL_CLUSTERS, total_clusters)
        f.seek(0)
        f.write(sb)
    # create a small directory with two files and write their data
    # prepare entries
    with open(path, 'r+b') as f:
        # directory offset
        dir_offset = cluster_size * 1
        # create README entry
        readme_data = b'Hello FiUnamFS README\n' * 100
        logo_data = b'\x89PNG' + b'LOGODATA' * 100
        # start data at cluster (1 + dir_clusters)
        data_cluster = 1 + dir_clusters
        # write README
        f.seek(data_cluster * cluster_size)
        f.write(readme_data)
        readme_clusters = math.ceil(len(readme_data) / cluster_size)
        # write logo after README
        f.seek((data_cluster + readme_clusters) * cluster_size)
        f.write(logo_data)
        logo_clusters = math.ceil(len(logo_data) / cluster_size)
        # build directory entries
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S').encode('ascii')[:14]
        # entry 0: README
        tipo = b'\x2d'
        name_field = b'README.org'[:14].ljust(14, b'\x00')
        cluster_bytes = struct.pack('<I', data_cluster)
        size_bytes = struct.pack('<I', len(readme_data))
        entry0 = tipo + name_field + cluster_bytes + size_bytes + now + now + b'\x00' * (ENTRY_SIZE - 1 - 14 - 4 - 4 - 14 - 14)
        # entry 1: logo.png
        tipo = b'\x2d'
        name_field = b'logo.png'[:14].ljust(14, b'\x00')
        cluster_bytes = struct.pack('<I', data_cluster + readme_clusters)
        size_bytes = struct.pack('<I', len(logo_data))
        entry1 = tipo + name_field + cluster_bytes + size_bytes + now + now + b'\x00' * (ENTRY_SIZE - 1 - 14 - 4 - 4 - 14 - 14)
        # rest entries filled with dots
        f.seek(dir_offset)
        f.write(entry0)
        f.write(entry1)
        remaining = dir_clusters * cluster_size - 2 * ENTRY_SIZE
        f.write(b'.' * remaining)


def run_selftest():
    tmpdir = tempfile.mkdtemp(prefix='fiunamfs_test_')
    img = os.path.join(tmpdir, 'fiunamfs_test.img')
    create_test_image(img)
    print('Created test image at', img)
    # test info
    args = SimpleNamespace(image=img)
    print('\n--- TEST: info ---')
    cmd_info(args)
    print('\n--- TEST: list ---')
    cmd_list(args)
    # test copyout
    out1 = os.path.join(tmpdir, 'README.org')
    cargs = SimpleNamespace(image=img, name='README.org', out=out1)
    print('\n--- TEST: copyout README.org ---')
    cmd_copyout(cargs)
    if os.path.exists(out1):
        print('copyout succeeded:', out1, 'size=', os.path.getsize(out1))
    else:
        print('copyout failed: file not created')
    print('\nSelftest finished. Temporary directory:', tmpdir)


def main():
    parser = argparse.ArgumentParser(description='FiUnamFS tool (expects version 26-2)')
    sub = parser.add_subparsers(dest='cmd')
    p_info = sub.add_parser('info')
    p_info.add_argument('image')
    p_list = sub.add_parser('list')
    p_list.add_argument('image')
    p_copyout = sub.add_parser('copyout')
    p_copyout.add_argument('image')
    p_copyout.add_argument('name')
    p_copyout.add_argument('out')
    p_copyin = sub.add_parser('copyin')
    p_copyin.add_argument('image')
    p_copyin.add_argument('src')
    p_copyin.add_argument('dest_name')
    p_delete = sub.add_parser('delete')
    p_delete.add_argument('image')
    p_delete.add_argument('name')
    p_make = sub.add_parser('makecopy26')
    p_make.add_argument('src')
    p_make.add_argument('dst')
    p_self = sub.add_parser('selftest')

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        # salir con 0 para indicar que no es un error ejecutar sin args
        sys.exit(0)

    if args.cmd == 'info':
        cmd_info(args)
    elif args.cmd == 'list':
        cmd_list(args)
    elif args.cmd == 'copyout':
        cmd_copyout(args)
    elif args.cmd == 'copyin':
        cmd_copyin(args)
    elif args.cmd == 'delete':
        cmd_delete(args)
    elif args.cmd == 'makecopy26':
        cmd_makecopy26(args)
    elif args.cmd == 'selftest':
        run_selftest()

if __name__ == '__main__':
    main()
