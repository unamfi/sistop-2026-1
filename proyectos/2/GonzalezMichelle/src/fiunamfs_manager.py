#!/usr/bin/env python3
"""
FiUnamFS Manager - Gestor de Sistema de Archivos FiUnamFS

Este programa proporciona una interfaz de línea de comandos para gestionar
archivos en imágenes de filesystem FiUnamFS (Facultad de Ingeniería UNAM).

ARQUITECTURA DE 2 HILOS:

1. Hilo de UI (Main Thread):
   - Maneja la interfaz de usuario mediante argparse
   - Lee comandos del usuario y parámetros
   - Envía comandos al hilo de E/S vía command_queue (producer)
   - Recibe resultados del hilo de E/S vía result_queue (consumer)
   - Muestra resultados formateados al usuario
   - Nunca accede directamente al filesystem

2. Hilo de E/S (I/O Worker Thread):
   - Ejecuta todas las operaciones del filesystem
   - Mantiene el file handle exclusivo del archivo .img
   - Recibe comandos vía command_queue (consumer)
   - Envía resultados vía result_queue (producer)
   - Es el único que puede leer/escribir el filesystem

COMUNICACIÓN THREAD-SAFE:

- Mecanismo: queue.Queue (FIFO thread-safe de Python stdlib)
- command_queue: UI thread → I/O thread (comandos)
- result_queue: I/O thread → UI thread (resultados)
- No se requieren locks manuales (Queue los maneja internamente)

SINCRONIZACIÓN:

- Patrón single-writer: Solo el I/O thread modifica el filesystem
- Previene race conditions sin necesidad de locks explícitos
- Las colas garantizan orden FIFO de operaciones
- I/O thread bloquea en queue.get() cuando no hay comandos (eficiente)
- UI thread bloquea en queue.get() esperando resultados (con timeout)

Autor: PaoGo (pao.gonzma@gmail.com)
Versión: 1.0.0
"""

import argparse
import sys
import os
import queue

# Agregar el directorio src al path para imports
sys.path.insert(0, os.path.dirname(__file__))

from services.io_thread import IOThread
from services.ui_thread import (
    submit_command,
    wait_for_result,
    display_result,
    display_error_result
)


def prompt_confirmation(filename: str, size: int) -> bool:
    """
    Solicita confirmación al usuario antes de eliminar un archivo.

    Args:
        filename: Nombre del archivo a eliminar
        size: Tamaño del archivo en bytes

    Returns:
        True si el usuario confirma, False si cancela
    """
    prompt = f"¿Eliminar '{filename}' ({size:,} bytes)? [s/N]: "
    response = input(prompt).strip().lower()
    return response in ['s', 'si', 'sí', 'y', 'yes']


def cmd_list(args: argparse.Namespace) -> int:
    """
    Ejecuta el comando 'list' usando arquitectura de threading.

    Args:
        args: Argumentos parseados de argparse

    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    # Crear colas de comunicación thread-safe
    command_queue = queue.Queue()  # UI → I/O
    result_queue = queue.Queue()   # I/O → UI

    # Crear e iniciar hilo de E/S
    io_thread = IOThread(args.filesystem, command_queue, result_queue)
    io_thread.start()

    try:
        # Enviar comando 'list' al hilo de E/S (non-blocking put)
        submit_command(command_queue, 'list', None)

        # Esperar resultado del hilo de E/S (blocking get con timeout)
        result = wait_for_result(result_queue, timeout=10.0)

        # Mostrar resultado
        if result['status'] == 'success':
            display_result(result)
            return 0
        else:
            display_error_result(result)
            return 1

    except queue.Empty:
        print("\n❌ Error: Timeout esperando respuesta del filesystem", file=sys.stderr)
        return 1

    finally:
        # Enviar señal de salida al hilo de E/S
        submit_command(command_queue, 'exit', None)
        # Esperar a que el hilo termine (con timeout)
        io_thread.join(timeout=5.0)


def cmd_export(args: argparse.Namespace) -> int:
    """
    Ejecuta el comando 'export' usando arquitectura de threading.

    Args:
        args: Argumentos parseados de argparse

    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    command_queue = queue.Queue()
    result_queue = queue.Queue()

    io_thread = IOThread(args.filesystem, command_queue, result_queue)
    io_thread.start()

    try:
        submit_command(command_queue, 'export', {
            'filename': args.filename,
            'dest_path': args.destination
        })

        result = wait_for_result(result_queue, timeout=10.0)

        if result['status'] == 'success':
            display_result(result)
            return 0
        else:
            display_error_result(result)
            return 1

    except queue.Empty:
        print("\n❌ Error: Timeout esperando respuesta del filesystem", file=sys.stderr)
        return 1

    finally:
        submit_command(command_queue, 'exit', None)
        io_thread.join(timeout=5.0)


def cmd_import(args: argparse.Namespace) -> int:
    """
    Ejecuta el comando 'import' usando arquitectura de threading.

    Args:
        args: Argumentos parseados de argparse

    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    command_queue = queue.Queue()
    result_queue = queue.Queue()

    io_thread = IOThread(args.filesystem, command_queue, result_queue)
    io_thread.start()

    try:
        submit_command(command_queue, 'import', {
            'src_path': args.source,
            'filename': args.name
        })

        result = wait_for_result(result_queue, timeout=10.0)

        if result['status'] == 'success':
            display_result(result)
            return 0
        else:
            display_error_result(result)
            return 1

    except queue.Empty:
        print("\n❌ Error: Timeout esperando respuesta del filesystem", file=sys.stderr)
        return 1

    finally:
        submit_command(command_queue, 'exit', None)
        io_thread.join(timeout=5.0)


def cmd_delete(args: argparse.Namespace) -> int:
    """
    Ejecuta el comando 'delete' usando arquitectura de threading.

    Args:
        args: Argumentos parseados de argparse

    Returns:
        Código de salida (0 = éxito, 1 = error)
    """
    command_queue = queue.Queue()
    result_queue = queue.Queue()

    io_thread = IOThread(args.filesystem, command_queue, result_queue)
    io_thread.start()

    try:
        # Primer comando: solicitar confirmación (sin confirmed flag)
        submit_command(command_queue, 'delete', {
            'filename': args.filename,
            'confirmed': False
        })

        result = wait_for_result(result_queue, timeout=10.0)

        if result['status'] == 'error':
            display_error_result(result)
            return 1

        # Resultado debe ser 'confirm' con info del archivo
        if result['status'] == 'confirm':
            # Pedir confirmación al usuario
            if not prompt_confirmation(result['filename'], result['size']):
                print("\nEliminación cancelada.\n")
                return 0

            # Segundo comando: ejecutar eliminación confirmada
            submit_command(command_queue, 'delete', {
                'filename': args.filename,
                'confirmed': True
            })

            result = wait_for_result(result_queue, timeout=10.0)

            if result['status'] == 'success':
                display_result(result)
                return 0
            else:
                display_error_result(result)
                return 1

    except queue.Empty:
        print("\n❌ Error: Timeout esperando respuesta del filesystem", file=sys.stderr)
        return 1

    finally:
        submit_command(command_queue, 'exit', None)
        io_thread.join(timeout=5.0)


def main():
    """
    Función principal - configura argparse y ejecuta el comando apropiado.
    """
    parser = argparse.ArgumentParser(
        prog='fiunamfs_manager',
        description='Gestor de archivos para filesystem FiUnamFS',
        epilog='Proyecto académico - Sistemas Operativos, FI-UNAM'
    )

    subparsers = parser.add_subparsers(
        title='comandos',
        description='Operaciones disponibles',
        dest='command',
        required=True
    )

    # Comando: list
    parser_list = subparsers.add_parser(
        'list',
        help='Lista todos los archivos del filesystem'
    )
    parser_list.add_argument(
        'filesystem',
        help='Ruta a la imagen del filesystem (.img)'
    )
    parser_list.set_defaults(func=cmd_list)

    # Comando: export
    parser_export = subparsers.add_parser(
        'export',
        help='Exporta un archivo del filesystem al sistema local'
    )
    parser_export.add_argument(
        'filesystem',
        help='Ruta a la imagen del filesystem (.img)'
    )
    parser_export.add_argument(
        'filename',
        help='Nombre del archivo a exportar (dentro del filesystem)'
    )
    parser_export.add_argument(
        'destination',
        help='Ruta destino donde guardar el archivo'
    )
    parser_export.set_defaults(func=cmd_export)

    # Comando: import
    parser_import = subparsers.add_parser(
        'import',
        help='Importa un archivo del sistema local al filesystem'
    )
    parser_import.add_argument(
        'filesystem',
        help='Ruta a la imagen del filesystem (.img)'
    )
    parser_import.add_argument(
        'source',
        help='Ruta del archivo local a importar'
    )
    parser_import.add_argument(
        '--name',
        dest='name',
        default=None,
        help='Nombre para el archivo en FiUnamFS (opcional, usa nombre del archivo fuente por defecto)'
    )
    parser_import.set_defaults(func=cmd_import)

    # Comando: delete
    parser_delete = subparsers.add_parser(
        'delete',
        help='Elimina un archivo del filesystem'
    )
    parser_delete.add_argument(
        'filesystem',
        help='Ruta a la imagen del filesystem (.img)'
    )
    parser_delete.add_argument(
        'filename',
        help='Nombre del archivo a eliminar (dentro del filesystem)'
    )
    parser_delete.set_defaults(func=cmd_delete)

    # Parsear argumentos
    args = parser.parse_args()

    # Ejecutar comando correspondiente
    exit_code = args.func(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
