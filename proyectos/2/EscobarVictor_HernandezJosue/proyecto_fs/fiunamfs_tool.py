#!/usr/bin/env python3
"""
fiunamfs_tool.py
Implementación básica: leer superbloque y listar directorio.
Autores: Escobar Diaz Victor Manuel, Hernandez Rubio Josue
"""

import struct
import threading
import queue
import argparse
import os
import sys

# constantes
DISK_IMG_DEFAULT = "tests/sample.img"
SECTOR = 512
DEFAULT_CLUSTER_SECTORS = 2

# sincronización
disk_lock = threading.Lock()

def read_superblock(fd):
    fd.seek(0)
    data = fd.read(SECTOR)  # primer cluster = superbloque
    magic = data[0:8].decode('ascii', errors='ignore').rstrip('\x00')
    version = data[10:15].decode('ascii', errors='ignore').rstrip('\x00')
    # leer valores little-endian (offsets según especificación)
    cluster_size = struct.unpack_from('<I', data, 40)[0]
    dir_clusters = struct.unpack_from('<I', data, 45)[0]
    total_clusters = struct.unpack_from('<I', data, 50)[0]
    label = data[20:36].decode('ascii', errors='ignore').rstrip('\x00')
    return {
        'magic': magic,
        'version': version,
        'cluster_size': cluster_size or (SECTOR * DEFAULT_CLUSTER_SECTORS),
        'dir_clusters': dir_clusters,
        'total_clusters': total_clusters,
        'label': label
    }

def read_directory(fd, sb):
    cluster_size = sb['cluster_size']
    # directorio comienza en cluster 1; ocupemos tres clusters (1..3) según spec
    dir_offset = cluster_size * 1
    dir_size = cluster_size * 3
    fd.seek(dir_offset)
    entries = []
    n_entries = dir_size // 64
    for i in range(n_entries):
        raw = fd.read(64)
        tipo = raw[0]
        name = raw[1:15].decode('ascii', errors='ignore').rstrip('\x00').rstrip('.')
        start_cluster = struct.unpack_from('<I', raw, 16)[0]
        size = struct.unpack_from('<I', raw, 20)[0]
        ctime = raw[24:38].decode('ascii', errors='ignore').rstrip('\x00')
        mtime = raw[38:52].decode('ascii', errors='ignore').rstrip('\x00')
        entries.append({
            'index': i,
            'tipo': tipo,
            'name': name,
            'start_cluster': start_cluster,
            'size': size,
            'ctime': ctime,
            'mtime': mtime
        })
    return entries

def cmd_list(path):
    if not os.path.exists(path):
        print("Archivo de imagen no encontrado:", path); return
    with open(path, 'rb') as fd:
        sb = read_superblock(fd)
        if sb['magic'] != 'FiUnamFS' or sb['version'] != '26-2':
            print("ERROR: imagen no es FiUnamFS v26-2 (magic/version):", sb['magic'], sb['version'])
            return
        entries = read_directory(fd, sb)
        print("Label:", sb['label'])
        print("Cluster size:", sb['cluster_size'])
        print("Directorios:")
        for e in entries:
            if e['name'] == '' or e['name'].startswith('.'):
                continue
            print(f" - {e['name']:14} start {e['start_cluster']:5} size {e['size']:8} ctime {e['ctime']} mtime {e['mtime']}")

def main():
    parser = argparse.ArgumentParser(description="Herramienta FiUnamFS (lista básica)")
    parser.add_argument('cmd', choices=['list'], help='comando')
    parser.add_argument('--img', default=DISK_IMG_DEFAULT, help='imagen fiunamfs')
    args = parser.parse_args()
    if args.cmd == 'list':
        cmd_list(args.img)

if __name__ == "__main__":
    main()
