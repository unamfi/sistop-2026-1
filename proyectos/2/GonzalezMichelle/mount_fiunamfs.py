#!/usr/bin/env python3
"""
Script de montaje para FiUnamFS usando FUSE

Este script monta un filesystem FiUnamFS como un directorio nativo del sistema
operativo, permitiendo usar comandos estándar de Linux/macOS.

Uso:
    python3 mount_fiunamfs.py <filesystem.img> <mountpoint> [opciones]

Ejemplos:
    # Montar en segundo plano
    python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs

    # Montar en primer plano (foreground) para ver logs
    python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs -f

    # Montar con debug habilitado
    python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs -f -d

Desmontar:
    fusermount -u /mnt/fiunamfs        # Linux
    umount /mnt/fiunamfs               # macOS

Autor: PaoGo (pao.gonzma@gmail.com)
"""

import sys
import os
import argparse

# Agregar src/ al path para poder importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from fusepy import FUSE
except ImportError:
    print("Error: fusepy no está instalado.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Para instalarlo:", file=sys.stderr)
    print("  pip3 install fusepy", file=sys.stderr)
    print("", file=sys.stderr)
    print("También necesitas libfuse instalado en el sistema:", file=sys.stderr)
    print("  Ubuntu/Debian: sudo apt-get install fuse3 libfuse3-dev", file=sys.stderr)
    print("  Fedora/RHEL:   sudo dnf install fuse3 fuse3-devel", file=sys.stderr)
    print("  macOS:         brew install macfuse", file=sys.stderr)
    sys.exit(1)

from fuse_mount import FiUnamFSMount


def main():
    """
    Función principal - parsea argumentos y monta el filesystem.
    """
    parser = argparse.ArgumentParser(
        prog='mount_fiunamfs',
        description='Monta un filesystem FiUnamFS usando FUSE',
        epilog='Proyecto académico - Sistemas Operativos, FI-UNAM'
    )

    parser.add_argument(
        'filesystem',
        help='Ruta al archivo .img del filesystem FiUnamFS'
    )

    parser.add_argument(
        'mountpoint',
        help='Directorio donde montar el filesystem'
    )

    parser.add_argument(
        '-f', '--foreground',
        action='store_true',
        help='Ejecutar en primer plano (foreground) en lugar de segundo plano'
    )

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Habilitar mensajes de debug de FUSE'
    )

    parser.add_argument(
        '-o',
        dest='mount_options',
        default='',
        help='Opciones de montaje adicionales (ej: -o allow_other,ro)'
    )

    args = parser.parse_args()

    # Validar que el filesystem existe
    if not os.path.exists(args.filesystem):
        print(f"Error: El archivo '{args.filesystem}' no existe.", file=sys.stderr)
        sys.exit(1)

    # Validar que el mountpoint existe
    if not os.path.exists(args.mountpoint):
        print(f"Error: El directorio '{args.mountpoint}' no existe.", file=sys.stderr)
        print(f"Créalo con: mkdir -p {args.mountpoint}", file=sys.stderr)
        sys.exit(1)

    # Validar que el mountpoint es un directorio
    if not os.path.isdir(args.mountpoint):
        print(f"Error: '{args.mountpoint}' no es un directorio.", file=sys.stderr)
        sys.exit(1)

    # Validar que el mountpoint está vacío
    if os.listdir(args.mountpoint):
        print(f"Advertencia: El directorio '{args.mountpoint}' no está vacío.", file=sys.stderr)
        response = input("¿Continuar de todas formas? [s/N]: ").strip().lower()
        if response not in ['s', 'si', 'sí', 'y', 'yes']:
            print("Montaje cancelado.")
            sys.exit(0)

    # Crear instancia de FiUnamFSMount
    try:
        fs_operations = FiUnamFSMount(args.filesystem)
    except Exception as e:
        print(f"Error al abrir el filesystem: {e}", file=sys.stderr)
        sys.exit(1)

    # Preparar opciones de montaje
    fuse_options = {
        'foreground': args.foreground,
        'debug': args.debug,
        'nothreads': True,  # FiUnamFS no es thread-safe para múltiples operaciones simultáneas
    }

    # Agregar opciones adicionales si se especificaron
    if args.mount_options:
        for option in args.mount_options.split(','):
            key_val = option.split('=', 1)
            if len(key_val) == 2:
                fuse_options[key_val[0]] = key_val[1]
            else:
                fuse_options[key_val[0]] = True

    # Mensaje informativo
    print(f"Montando '{args.filesystem}' en '{args.mountpoint}'...")
    if args.foreground:
        print("Ejecutando en primer plano. Presiona Ctrl+C para desmontar.")
    else:
        print(f"Filesystem montado. Para desmontar:")
        print(f"  fusermount -u {args.mountpoint}")

    # Montar el filesystem
    try:
        FUSE(
            fs_operations,
            args.mountpoint,
            **fuse_options
        )
    except RuntimeError as e:
        print(f"\nError de FUSE: {e}", file=sys.stderr)
        print("\nPosibles causas:", file=sys.stderr)
        print("  - El directorio ya está montado (desmonta primero)", file=sys.stderr)
        print("  - No tienes permisos (tal vez necesites sudo)", file=sys.stderr)
        print("  - FUSE no está instalado correctamente", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nDesmontando filesystem...")
        sys.exit(0)


if __name__ == '__main__':
    main()
