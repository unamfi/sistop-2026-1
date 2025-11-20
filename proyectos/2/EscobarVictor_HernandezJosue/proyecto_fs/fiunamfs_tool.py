#!/usr/bin/env python3
"""
fiunamfs_tool.py -- herramienta para interactuar con FiUnamFS
Autores: Escobar Diaz Victor Manuel; Hernandez Rubio Josue

Versión inicial: solo implementa LISTAR
Soporta versiones 26-1 y 26-2 del sistema de archivos.
"""

import struct
import os
import argparse
import sys

SECTOR = 512
DEFAULT_CLUSTER_SECTORS = 2  # por si superbloque marca cero


def read_superblock(fd):
    fd.seek(0)
    data = fd.read(SECTOR)

    magic = data[0:8].decode('ascii', errors='ignore').rstrip('\x00')
    version = data[10:15].decode('ascii', errors='ignore').rstrip('\x00')
    label = data[20:36].decode('ascii', errors='ignore').rstrip('\x00')

    cluster_size = struct.unpack_from('<I', data, 40)[0] or (SECTOR * DEFAULT_CLUSTER_SECTORS)
    dir_clusters = struct.unpack_from('<I', data, 45)[0]
    total_clusters = struct.unpack_from('<I', data, 50)[0]

    return {
        'magic': magic,
        'version': version,
        'label': label,
        'cluster_size': cluster_size,
        'dir_clusters': dir_clusters,
        'total_clusters': total_clusters
    }


def read_directory(fd, sb):
    cluster_size = sb['cluster_size']
    dir_offset = cluster_size * 1
    dir_size = cluster_size * 3

    fd.seek(dir_offset)
    entries = []

    num_entries = dir_size // 64

    for i in range(num_entries):
        raw = fd.read(64)
        if len(raw) < 64:
            break

        tipo = raw[0]
        name = raw[1:15].decode('ascii', errors='ignore').rstrip('\x00').rstrip('.')
        start_cluster = struct.unpack_from('<I', raw, 16)[0]
        size = struct.unpack_from('<I', raw, 20)[0]
        ctime = raw[24:38].decode('ascii', errors='ignore').rstrip('\x00')
        mtime = raw[38:52].decode('ascii', errors='ignore').rstrip('\x00')

        if not name or set(name) == {'.'}:
            continue

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
        print("Imagen no encontrada:", path)
        return 1

    with open(path, 'rb') as fd:
        sb = read_superblock(fd)

        # Validar magic y versión
        if sb['magic'] != 'FiUnamFS':
            print("ERROR: Magic inválido. No es FiUnamFS:", sb['magic'])
            return 2

        if sb['version'] not in ('26-1', '26-2'):
            print("ERROR: Versión no soportada:", sb['version'])
            print("Este programa solo soporta 26-1 y 26-2.")
            return 3

        print(f"Versión aceptada: {sb['version']}")
        print("Etiqueta del volumen:", sb['label'])
        print("Cluster size (bytes):", sb['cluster_size'])
        print("\nDIRECTORIO:\n")

        entries = read_directory(fd, sb)

        if not entries:
            print("(No hay archivos en el directorio)")
            return 0

        print(f"{'Nombre':20} {'Start':6} {'Size':8} {'ctime':14} {'mtime':14}")
        print("-" * 70)

        for e in entries:
            print(
                f"{e['name']:20} "
                f"{e['start_cluster']:6} "
                f"{e['size']:8} "
                f"{e['ctime']:14} "
                f"{e['mtime']:14}"
            )

    return 0


def main():
    parser = argparse.ArgumentParser(description="Herramienta FiUnamFS")
    parser.add_argument('cmd', choices=['list'], help='Comando')
    parser.add_argument('--img', default='fiunamfs.img', help='Ruta de la imagen FiUnamFS')

    args = parser.parse_args()

    if args.cmd == 'list':
        rc = cmd_list(args.img)
        sys.exit(rc)


if __name__ == "__main__":
    main()
