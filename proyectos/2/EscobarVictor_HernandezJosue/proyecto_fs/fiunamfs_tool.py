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

def extract_file(fd, sb, filename, dest):
    entries = read_directory(fd, sb)
    for e in entries:
        if e['name'] == filename:
            if e['start_cluster'] == 0 or e['size'] == 0:
                print("Archivo vacío o con start 0")
                return False
            start_byte = e['start_cluster'] * sb['cluster_size']
            fd.seek(start_byte)
            data = fd.read(e['size'])
            with open(dest, 'wb') as out:
                out.write(data)
            print(f"Archivo {filename} extraído a {dest}")
            return True
    print("No se encontró el archivo:", filename)
    return False

def cmd_extract(img_path, filename, dest):
    if not os.path.exists(img_path):
        print("Imagen no encontrada:", img_path)
        return 1

    with open(img_path, "rb") as fd:
        sb = read_superblock(fd)

        # Validar versión
        if sb['magic'] != 'FiUnamFS' or sb['version'] not in ['26-1', '26-2']:
            print("ERROR: versión no soportada:", sb['version'])
            return 2

        # Leer directorio
        entries = read_directory(fd, sb)

        # Normalizar nombre buscado
        filename_norm = filename.strip().lower()

        # Buscar
        found = None
        for e in entries:
            name_norm = e['name'].strip().lower()
            if name_norm == filename_norm:
                found = e
                break

        if not found:
            print("No se encontró el archivo dentro del sistema:", filename)
            return 3

        # Calcular offset de datos
        cluster_size = sb['cluster_size']
        start = found['start_cluster'] * cluster_size
        size = found['size']

        fd.seek(start)
        data = fd.read(size)

        # Guardar en destino
        with open(dest, "wb") as out:
            out.write(data)

        print(f"Archivo extraído correctamente: {dest}")
        return 0


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
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    #
    # --- SUBCOMANDO LIST ---
    #
    p_list = subparsers.add_parser("list", help="Listar contenido de la imagen FiUnamFS")
    p_list.add_argument("--img", default="fiunamfs.img", help="Ruta a la imagen FiUnamFS")

    #
    # --- SUBCOMANDO EXTRACT ---
    #
    p_extract = subparsers.add_parser("extract", help="Extraer archivo desde la imagen")
    p_extract.add_argument("--img", default="fiunamfs.img", help="Ruta a la imagen FiUnamFS")
    p_extract.add_argument("--file", required=True, help="Nombre del archivo dentro de FiUnamFS")
    p_extract.add_argument("--dest", required=True, help="Ruta destino para guardar el archivo")

    #
    # --- PARSEAR ---
    #
    args = parser.parse_args()

    #
    # --- EJECUTAR COMANDOS ---
    #
    if args.cmd == "list":
        rc = cmd_list(args.img)
        sys.exit(rc)

    elif args.cmd == "extract":
        rc = cmd_extract(args.img, args.file, args.dest)
        sys.exit(rc)


if __name__ == "__main__":
    main()

