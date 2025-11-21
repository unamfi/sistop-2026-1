#!/usr/bin/env python3
"""
fiunamfs_tool.py -- Herramienta para interactuar con FiUnamFS

Autores:
    Escobar Díaz Víctor Manuel
    Hernández Rubio Josue

Soporta versiones 26-1 y 26-2 del sistema de archivos FiUnamFS.

Comandos:
    list    - Listar el contenido del directorio
    extract - Extraer un archivo desde FiUnamFS a tu PC
    import  - Copiar un archivo desde tu PC hacia FiUnamFS
    delete  - Eliminar un archivo dentro de FiUnamFS
    rename  - Renombrar un archivo dentro de FiUnamFS

Uso típico (desde Git Bash en Windows):

    py fiunamfs_tool.py list --img fiunamfs.img

    py fiunamfs_tool.py extract --img fiunamfs.img --file saludo.jpg --dest saludo_extraido.jpg

    py fiunamfs_tool.py import --img fiunamfs.img --src prueba.txt --dest prueba.txt

    py fiunamfs_tool.py delete --img fiunamfs.img --file prueba.txt

    py fiunamfs_tool.py rename --img fiunamfs.img --old prueba.txt --new prueba2.txt
"""

import struct
import os
import argparse
import sys
import datetime
import threading


SECTOR = 512
DEFAULT_CLUSTER_SECTORS = 2  # por si el superbloque trae 0


# ================================================================
#  Read/Write Lock para sincronización entre hilos
# ================================================================

class ReadWriteLock:
    """
    Lock de lectura/escritura muy sencillo:
    - Varios lectores pueden entrar al mismo tiempo.
    - El escritor entra solo, esperando a que no haya lectores.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._read_ready = threading.Condition(self._lock)
        self._readers = 0

    def acquire_read(self):
        with self._lock:
            self._readers += 1

    def release_read(self):
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()

    def acquire_write(self):
        self._lock.acquire()
        while self._readers > 0:
            self._read_ready.wait()

    def release_write(self):
        self._lock.release()


# Lock global que protege el acceso a la imagen FiUnamFS
rw_lock = ReadWriteLock()


# ================================================================
#  Lectura de superbloque y directorio
# ================================================================

def read_superblock(fd):
    """
    Lee el superbloque del cluster 0 (primer sector).
    """
    fd.seek(0)
    data = fd.read(SECTOR)

    magic = data[0:8].decode("ascii", errors="ignore").rstrip("\x00")
    version = data[10:15].decode("ascii", errors="ignore").rstrip("\x00")
    label = data[20:36].decode("ascii", errors="ignore").rstrip("\x00")

    # offsets según especificación (enteros 32-bit little endian)
    cluster_size = struct.unpack_from("<I", data, 40)[0]
    if cluster_size == 0:
        cluster_size = SECTOR * DEFAULT_CLUSTER_SECTORS

    dir_clusters = struct.unpack_from("<I", data, 45)[0]
    total_clusters = struct.unpack_from("<I", data, 50)[0]

    return {
        "magic": magic,
        "version": version,
        "label": label,
        "cluster_size": cluster_size,
        "dir_clusters": dir_clusters,
        "total_clusters": total_clusters,
    }


def validate_fs(sb):
    """
    Valida que el sistema de archivos sea FiUnamFS 26-1 o 26-2.
    """
    if sb["magic"] != "FiUnamFS":
        print("ERROR: Magic inválido. No es FiUnamFS:", sb["magic"])
        return False

    if sb["version"] not in ("26-1", "26-2"):
        print("ERROR: versión no soportada:", sb["version"])
        print("Este programa solo acepta versiones 26-1 y 26-2.")
        return False

    return True


def read_directory(fd, sb):
    """
    Lee el directorio (clusters 1..(1+dir_clusters-1)).

    Cada entrada mide 64 bytes:
      0      : tipo ('A','.', etc.), '-' si está libre
      1–14   : nombre (14 caracteres, ASCII)
      16–19  : cluster inicial (uint32 little endian)
      20–23  : tamaño en bytes (uint32 little endian)
      24–37  : ctime (AAAAMMDDHHMMSS)
      38–51  : mtime (AAAAMMDDHHMMSS)
      52–63  : reservado
    """
    cluster_size = sb["cluster_size"]
    dir_clusters = sb["dir_clusters"]

    dir_offset = cluster_size * 1  # directorio empieza en cluster 1
    dir_size = cluster_size * dir_clusters

    fd.seek(dir_offset)

    entries = []
    n_entries = dir_size // 64

    for i in range(n_entries):
        raw = fd.read(64)
        if len(raw) < 64:
            break

        tipo = chr(raw[0])
        name = raw[1:15].decode("ascii", errors="ignore")
        name = name.rstrip("\x00").rstrip()

        # entradas libres
        if tipo == "-" or name == "" or name == "..............":
            entries.append(
                {
                    "type": "-",
                    "name": "..............",
                    "start_cluster": 0,
                    "size": 0,
                    "ctime": "00000000000000",
                    "mtime": "00000000000000",
                }
            )
            continue

        start_cluster = struct.unpack_from("<I", raw, 16)[0]
        size = struct.unpack_from("<I", raw, 20)[0]
        ctime = raw[24:38].decode("ascii", errors="ignore").strip("\x00")
        mtime = raw[38:52].decode("ascii", errors="ignore").strip("\x00")

        entries.append(
            {
                "type": tipo,
                "name": name,
                "start_cluster": start_cluster,
                "size": size,
                "ctime": ctime,
                "mtime": mtime,
            }
        )

    return entries


# ================================================================
#  Comando LIST
# ================================================================

def cmd_list(path):
    rw_lock.acquire_read()
    try:
        if not os.path.exists(path):
            print("Imagen no encontrada:", path)
            return 1

        with open(path, "rb") as fd:
            sb = read_superblock(fd)
            if not validate_fs(sb):
                return 2

            print("Versión aceptada:", sb["version"])
            print("Etiqueta del volumen:", sb["label"])
            print("Cluster size (bytes):", sb["cluster_size"])
            print("\nDIRECTORIO:\n")

            entries = read_directory(fd, sb)
            if not entries:
                print("  (Directorio vacío)")
                return 0

            print(f"{'Nombre':20} {'Start':6} {'Size':8} {'ctime':14} {'mtime':14}")
            print("-" * 70)
            for e in entries:
                print(
                    f"{e['name']:20} {e['start_cluster']:6} {e['size']:8} "
                    f"{e['ctime']:14} {e['mtime']:14}"
                )

        return 0
    finally:
        rw_lock.release_read()


# ================================================================
#  Comando EXTRACT
# ================================================================

def cmd_extract(img_path, filename, dest_path):
    rw_lock.acquire_read()
    try:
        if not os.path.exists(img_path):
            print("Imagen no encontrada:", img_path)
            return 1

        with open(img_path, "rb") as fd:
            sb = read_superblock(fd)
            if not validate_fs(sb):
                return 2

            entries = read_directory(fd, sb)

            entry = None
            for e in entries:
                if e["name"] == filename:
                    entry = e
                    break

            if entry is None:
                print("No se encontró el archivo:", filename)
                return 3

            cluster_size = sb["cluster_size"]
            start = entry["start_cluster"] * cluster_size
            size = entry["size"]

            fd.seek(start)
            data = fd.read(size)

        with open(dest_path, "wb") as out:
            out.write(data)

        print(f"Archivo extraído correctamente: {dest_path}")
        return 0
    finally:
        rw_lock.release_read()


# ================================================================
#  Comando IMPORT
# ================================================================

def cmd_import(img_path, src_path, dest_name):
    rw_lock.acquire_write()
    try:
        if not os.path.exists(img_path):
            print("Imagen no encontrada:", img_path)
            return 1

        if not os.path.exists(src_path):
            print("No existe el archivo origen:", src_path)
            return 1

        with open(src_path, "rb") as sf:
            data = sf.read()
        size = len(data)

        with open(img_path, "r+b") as fd:
            sb = read_superblock(fd)
            if not validate_fs(sb):
                return 2

            entries = read_directory(fd, sb)

            # 1) buscar entrada libre en el directorio
            free_idx = None
            for i, e in enumerate(entries):
                if e["type"] == "-" or e["name"] == "..............":
                    free_idx = i
                    break

            if free_idx is None:
                print("No hay entradas libres en el directorio.")
                return 3

            # 2) calcular clusters ya usados (asignación contigua muy sencilla)
            cluster_size = sb["cluster_size"]
            dir_clusters = sb["dir_clusters"]

            used_clusters = set()
            for e in entries:
                if e["start_cluster"] > 0 and e["size"] > 0:
                    ncl = (e["size"] + cluster_size - 1) // cluster_size
                    for c in range(e["start_cluster"], e["start_cluster"] + ncl):
                        used_clusters.add(c)

            first_data_cluster = 1 + dir_clusters
            total_clusters = sb["total_clusters"]

            needed_clusters = (size + cluster_size - 1) // cluster_size

            # 3) buscar un rango contiguo de clusters libres
            start_cluster = None
            run = 0
            run_start = None

            for c in range(first_data_cluster, total_clusters):
                if c not in used_clusters:
                    if run == 0:
                        run_start = c
                    run += 1
                    if run >= needed_clusters:
                        start_cluster = run_start
                        break
                else:
                    run = 0
                    run_start = None

            if start_cluster is None:
                print("No hay espacio contiguo suficiente en la imagen.")
                return 4

            # 4) escribir los datos
            fd.seek(start_cluster * cluster_size)
            fd.write(data)

            # 5) escribir entrada de directorio
            dir_offset = cluster_size * 1
            entry_offset = dir_offset + free_idx * 64

            if len(dest_name) > 14:
                print("ERROR: Nombre destino demasiado largo (máx 14).")
                return 5

            name_padded = dest_name.ljust(14)
            now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

            entry = bytearray(64)
            entry[0:1] = b"."  # tipo de archivo "normal"
            entry[1:15] = name_padded.encode("ascii")
            entry[16:20] = struct.pack("<I", start_cluster)
            entry[20:24] = struct.pack("<I", size)
            entry[24:38] = now.encode("ascii")  # ctime
            entry[38:52] = now.encode("ascii")  # mtime
            # el resto (52:64) lo dejamos en cero

            fd.seek(entry_offset)
            fd.write(entry)

        print(
            f"Archivo '{src_path}' importado como '{dest_name}' "
            f"en cluster {start_cluster}"
        )
        return 0
    finally:
        rw_lock.release_write()


# ================================================================
#  Comando DELETE
# ================================================================

def cmd_delete(path, filename):
    rw_lock.acquire_write()
    try:
        if not os.path.exists(path):
            print("Imagen no encontrada:", path)
            return 1

        with open(path, "r+b") as fd:
            sb = read_superblock(fd)
            if not validate_fs(sb):
                return 2

            entries = read_directory(fd, sb)

            pos = -1
            for i, e in enumerate(entries):
                if e["name"] == filename:
                    pos = i
                    break

            if pos == -1:
                print("No se encontró el archivo:", filename)
                return 3

            cluster_size = sb["cluster_size"]
            dir_offset = cluster_size * 1

            fd.seek(dir_offset + pos * 64)
            fd.write(b"\x00" * 64)

        print(f"Archivo '{filename}' eliminado correctamente.")
        return 0
    finally:
        rw_lock.release_write()


# ================================================================
#  Comando RENAME
# ================================================================

def cmd_rename(img_path, old_name, new_name):
    """
    Renombra un archivo dentro de FiUnamFS (solo cambia nombre y mtime).
    """
    rw_lock.acquire_write()
    try:
        if not os.path.exists(img_path):
            print("Imagen no encontrada:", img_path)
            return 1

        if len(new_name) > 14:
            print("ERROR: El nombre nuevo excede 14 caracteres.")
            return 1

        with open(img_path, "r+b") as fd:
            sb = read_superblock(fd)
            if not validate_fs(sb):
                return 2

            entries = read_directory(fd, sb)
            cluster_size = sb["cluster_size"]
            dir_offset = cluster_size * 1

            idx = None
            for i, e in enumerate(entries):
                if e["name"] == old_name:
                    idx = i
                    break

            if idx is None:
                print("Archivo no encontrado:", old_name)
                return 3

            entry_offset = dir_offset + idx * 64

            new_name_padded = new_name.ljust(14)
            now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

            # escribir nombre (bytes 1–15)
            fd.seek(entry_offset + 1)
            fd.write(new_name_padded.encode("ascii"))

            # escribir mtime (bytes 38–51)
            fd.seek(entry_offset + 38)
            fd.write(now.encode("ascii"))

        print(f"Archivo renombrado: {old_name} -> {new_name}")
        return 0
    finally:
        rw_lock.release_write()


# ================================================================
#  main() y parseo de argumentos
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="Herramienta FiUnamFS")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # --- SUBCOMANDO LIST ---
    p_list = subparsers.add_parser("list", help="Listar contenido de la imagen FiUnamFS")
    p_list.add_argument(
        "--img", default="fiunamfs.img", help="Ruta a la imagen FiUnamFS"
    )

    # --- SUBCOMANDO EXTRACT ---
    p_extract = subparsers.add_parser(
        "extract", help="Extraer archivo desde la imagen"
    )
    p_extract.add_argument(
        "--img", default="fiunamfs.img", help="Ruta a la imagen FiUnamFS"
    )
    p_extract.add_argument(
        "--file", required=True, help="Nombre del archivo dentro de FiUnamFS"
    )
    p_extract.add_argument(
        "--dest", required=True, help="Ruta destino para guardar el archivo"
    )

    # --- SUBCOMANDO IMPORT ---
    p_import = subparsers.add_parser(
        "import", help="Copiar archivo desde tu PC hacia FiUnamFS"
    )
    p_import.add_argument(
        "--img", default="fiunamfs.img", help="Imagen FiUnamFS"
    )
    p_import.add_argument(
        "--src", required=True, help="Archivo que quieres copiar desde tu PC"
    )
    p_import.add_argument(
        "--dest", required=True, help="Nombre dentro del FiUnamFS"
    )

    # --- SUBCOMANDO DELETE ---
    p_delete = subparsers.add_parser(
        "delete", help="Eliminar archivo dentro de FiUnamFS"
    )
    p_delete.add_argument(
        "--img", default="fiunamfs.img", help="Imagen FiUnamFS"
    )
    p_delete.add_argument(
        "--file", required=True, help="Archivo que quieres borrar dentro de FiUnamFS"
    )

    # --- SUBCOMANDO RENAME ---
    p_rename = subparsers.add_parser(
        "rename", help="Renombrar archivo dentro de FiUnamFS"
    )
    p_rename.add_argument(
        "--img", default="fiunamfs.img", help="Imagen FiUnamFS"
    )
    p_rename.add_argument(
        "--old", required=True, help="Nombre actual"
    )
    p_rename.add_argument(
        "--new", required=True, help="Nuevo nombre"
    )

    args = parser.parse_args()

    if args.cmd == "list":
        rc = cmd_list(args.img)
        sys.exit(rc)

    elif args.cmd == "extract":
        rc = cmd_extract(args.img, args.file, args.dest)
        sys.exit(rc)

    elif args.cmd == "import":
        rc = cmd_import(args.img, args.src, args.dest)
        sys.exit(rc)

    elif args.cmd == "delete":
        rc = cmd_delete(args.img, args.file)
        sys.exit(rc)

    elif args.cmd == "rename":
        rc = cmd_rename(args.img, args.old, args.new)
        sys.exit(rc)


if __name__ == "__main__":
    main()
