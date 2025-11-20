import argparse
import struct
import os
import datetime
import sys

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
        is_unused = (name == '' or name_raw == b'\x00'*NAME_LEN or name_raw == b'.'*NAME_LEN or name_raw == b'-'*NAME_LEN)
        
        try: cluster_init = struct.unpack_from('<I', entry, 16)[0]
        except: cluster_init = 0
        try: size = struct.unpack_from('<I', entry, 20)[0]
        except: size = 0
        
        c_raw = entry[24:38].decode('ascii', errors='ignore')
        m_raw = entry[38:52].decode('ascii', errors='ignore')

        entries.append({
            'name': name,
            'is_unused': is_unused,
            'cluster_init': cluster_init,
            'size': size,
            'created': c_raw,
            'modified': m_raw
        })
    return entries

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
        if not e['is_unused']:
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

def main():
    parser = argparse.ArgumentParser(description='FiUnamFS tool')
    sub = parser.add_subparsers(dest='cmd')
    
    sub.add_parser('info').add_argument('image')
    sub.add_parser('list').add_argument('image')
    
    p_make = sub.add_parser('makecopy26')
    p_make.add_argument('src')
    p_make.add_argument('dst')
    
    args = parser.parse_args()
    if args.cmd == 'info': cmd_info(args)
    elif args.cmd == 'list': cmd_list(args)
    elif args.cmd == 'makecopy26': cmd_makecopy26(args)
    else: parser.print_help()

if __name__ == '__main__':
    main()
