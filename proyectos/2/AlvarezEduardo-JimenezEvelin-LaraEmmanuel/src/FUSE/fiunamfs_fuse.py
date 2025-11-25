#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fiunamfs_fuse.py
# Adaptador FUSE para FiUnamFS (lectura, escritura, creación y eliminación)

import os
import sys
import time
import stat
from errno import ENOENT

from fuse import FUSE, Operations, FuseOSError

from estado import EstadoFS       # Estadísticas de uso del FS
from fiunamfs import FiUnamFS     # Implementación principal del sistema


class FiUnamFSFuse(Operations):
    # Adaptador que traduce operaciones FUSE a operaciones FiUnamFS

    def __init__(self, fs: FiUnamFS):
        self.fs = fs                    # Instancia del sistema de archivos
        self.open_files = {}            # Buffers temporales para escritura

    def _find_entry(self, path):
        # Busca una entrada en el directorio por nombre
        name = path.lstrip("/")
        with self.fs.lock:
            for e in self.fs.leer_directorio():
                if not e.is_empty() and e.name == name:
                    return e
        return None

    def getattr(self, path, fh=None):
        # Atributos del directorio raíz
        if path == "/" or path == "":
            return dict(
                st_mode=stat.S_IFDIR | 0o755,
                st_nlink=2,
                st_size=0,
                st_ctime=time.time(),
                st_mtime=time.time(),
                st_atime=time.time()
            )

        # Atributos de archivo
        entry = self._find_entry(path)
        if entry is None:
            raise FuseOSError(ENOENT)

        info = dict(
            st_mode=stat.S_IFREG | 0o644,
            st_nlink=1,
            st_size=entry.size
        )

        # Conversión de fechas almacenadas
        try:
            info["st_mtime"] = time.mktime(time.strptime(entry.modified, "%Y%m%d%H%M%S"))
            info["st_ctime"] = time.mktime(time.strptime(entry.created, "%Y%m%d%H%M%S"))
            info["st_atime"] = info["st_mtime"]
        except:
            now = time.time()
            info["st_mtime"] = info["st_ctime"] = info["st_atime"] = now

        return info

    def readdir(self, path, fh):
        # Lista todos los archivos del directorio raíz
        if path != "/":
            raise FuseOSError(ENOENT)

        with self.fs.lock:
            nombres = [e.name for e in self.fs.leer_directorio() if not e.is_empty()]

        return [".", ".."] + nombres

    def open(self, path, flags):
        # Verifica existencia del archivo
        if self._find_entry(path) is None:
            raise FuseOSError(ENOENT)
        return 0

    def read(self, path, size, offset, fh):
        # Lectura parcial de archivo
        entry = self._find_entry(path)
        if entry is None:
            raise FuseOSError(ENOENT)

        if offset >= entry.size:
            return b""

        size = min(size, entry.size - offset)

        with self.fs.lock:
            pos = entry.start * self.fs.cluster_size + offset
            self.fs.f.seek(pos)
            data = self.fs.f.read(size)
            self.fs.estado.leidos += 1
            self.fs.estado.ultimo_evento = f"Leído '{entry.name}'"

        return data

    def create(self, path, mode, fi=None):
        # Crear archivo vacío mediante copiar_hacia
        name = path.lstrip("/")
        temp = f"/tmp/{name}.fuse_tmp"
        with open(temp, "wb"):
            pass
        self.fs.copiar_hacia(temp, name)
        return 0

    def write(self, path, data, offset, fh):
        # Escritura acumulativa en buffer temporal
        name = path.lstrip("/")
        entry = self._find_entry(path)
        if entry is None:
            raise FuseOSError(ENOENT)

        # Cargar contenido actual en buffer si es primera escritura
        if name not in self.open_files:
            with self.fs.lock:
                self.fs.f.seek(entry.start * self.fs.cluster_size)
                contenido = self.fs.f.read(entry.size)
            self.open_files[name] = bytearray(contenido)

        buf = self.open_files[name]
        end = offset + len(data)

        # Expandir buffer si es necesario
        if end > len(buf):
            buf.extend(b"\x00" * (end - len(buf)))

        buf[offset:end] = data
        return len(data)

    def release(self, path, fh):
        # Guardar archivo completo al cerrar
        name = path.lstrip("/")
        if name in self.open_files:
            temp = f"/tmp/{name}.fuse_tmp2"
            with open(temp, "wb") as out:
                out.write(self.open_files[name])
            self.fs.copiar_hacia(temp, name)
            del self.open_files[name]
        return 0

    def unlink(self, path):
        # Eliminar archivo de FiUnamFS
        name = path.lstrip("/")
        self.fs.eliminar(name)
        return 0


def main():
    # Validación de argumentos de entrada
    if len(sys.argv) != 3:
        print("Uso: python3 fiunamfs_fuse.py <imagen.img> <mountpoint>")
        sys.exit(1)

    imagen = sys.argv[1]
    mountpoint = sys.argv[2]

    estado = EstadoFS()                # Estadísticas del FS
    fs = FiUnamFS(imagen, estado)      # Cargar sistema de archivos

    print("[INFO] Montando FUSE con soporte de lectura, escritura y eliminación.")
    FUSE(FiUnamFSFuse(fs), mountpoint, foreground=True, allow_other=True)


if __name__ == "__main__":
    main()