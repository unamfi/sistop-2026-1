"""
Funciones del hilo de UI para comunicación con IOThread

Este módulo proporciona funciones helper para el hilo principal (UI)
que facilitan la comunicación con el hilo de E/S mediante colas thread-safe.

Arquitectura:
- UI Thread (main): Hilo principal que maneja interfaz de usuario
- Produce comandos en command_queue (non-blocking put)
- Consume resultados de result_queue (blocking get con timeout)
- Nunca accede directamente al filesystem
"""

import queue
from typing import Dict, Optional, Tuple


def submit_command(command_queue: queue.Queue, cmd: str, args: Optional[Dict] = None) -> None:
    """
    Envía un comando al hilo de E/S.

    Esta función es thread-safe y no bloquea. El comando se agrega
    a la cola y el control retorna inmediatamente.

    Args:
        command_queue: Cola de comandos (UI → I/O)
        cmd: Nombre del comando ('list', 'export', 'import', 'delete', 'exit')
        args: Argumentos del comando (dict o None)

    Ejemplo:
        >>> submit_command(cmd_queue, 'list', None)
        >>> submit_command(cmd_queue, 'export', {'filename': 'test.txt', 'dest_path': './out.txt'})
    """
    # queue.Queue.put() es thread-safe y no requiere locks adicionales
    command_queue.put((cmd, args))


def wait_for_result(result_queue: queue.Queue, timeout: float = 10.0) -> Dict:
    """
    Espera por un resultado del hilo de E/S.

    Esta función bloquea hasta que haya un resultado disponible
    o se alcance el timeout.

    Args:
        result_queue: Cola de resultados (I/O → UI)
        timeout: Tiempo máximo de espera en segundos (default: 10.0)

    Returns:
        Diccionario con el resultado de la operación

    Raises:
        queue.Empty: Si se alcanza el timeout sin recibir resultado

    Ejemplo:
        >>> result = wait_for_result(res_queue)
        >>> if result['status'] == 'success':
        ...     print("Operación exitosa")
    """
    # queue.Queue.get() es thread-safe y bloquea hasta recibir dato
    # o hasta alcanzar el timeout
    return result_queue.get(timeout=timeout)


def display_result(result: Dict) -> None:
    """
    Muestra un resultado al usuario.

    Procesa el diccionario de resultado y muestra la información
    apropiada según el tipo de operación y status.

    Args:
        result: Diccionario con 'status' y campos específicos de la operación

    Nota:
        Esta función es llamada desde el UI thread después de recibir
        el resultado del I/O thread.
    """
    status = result.get('status')

    if status == 'success':
        # Determinar tipo de operación por los campos presentes
        if 'files' in result:
            display_list_result(result)
        elif 'dest_path' in result:
            display_export_result(result)
        elif 'start_cluster' in result:
            display_import_result(result)
        elif 'freed_clusters' in result:
            display_delete_result(result)
        else:
            print("\n✓ Operación completada exitosamente\n")

    elif status == 'error':
        display_error_result(result)

    elif status == 'confirm':
        # Este caso se maneja externamente (necesita input del usuario)
        pass


def display_list_result(result: Dict) -> None:
    """Muestra resultado de operación list."""
    files = result['files']
    total_files = result['total_files']
    used_space = result['used_space']
    free_space = result['free_space']

    print(f"\n{'=' * 80}")
    print(f"Contenido del filesystem FiUnamFS")
    print(f"{'=' * 80}")

    if total_files == 0:
        print("\nNo hay archivos en el filesystem.")
    else:
        print(f"\n{'Archivo':<16} {'Tamaño':>10}  {'Creado':<20} {'Modificado':<20} {'Cluster':>7}")
        print(f"{'-' * 16} {'-' * 10}  {'-' * 20} {'-' * 20} {'-' * 7}")

        for file_info in files:
            filename = file_info['filename'][:15]
            size = file_info['size']
            created = file_info['created']
            modified = file_info['modified']
            cluster = file_info['start_cluster']
            print(f"{filename:<16} {size:>10}  {created:<20} {modified:<20} {cluster:>7}")

    print(f"\n{'-' * 80}")
    print(f"Total: {total_files} archivos")
    print(f"Espacio usado: {used_space:,} bytes ({used_space / 1024:.2f} KB)")
    print(f"Espacio libre: {free_space:,} bytes ({free_space / 1024:.2f} KB)")
    print(f"{'=' * 80}\n")


def display_export_result(result: Dict) -> None:
    """Muestra resultado de operación export."""
    print(f"\n✓ Archivo exportado exitosamente")
    print(f"  Archivo: {result['filename']}")
    print(f"  Tamaño: {result['bytes_copied']:,} bytes ({result['bytes_copied'] / 1024:.2f} KB)")
    print(f"  Destino: {result['dest_path']}\n")


def display_import_result(result: Dict) -> None:
    """Muestra resultado de operación import."""
    print(f"\n✓ Archivo importado exitosamente")
    print(f"  Archivo: {result['filename']}")
    print(f"  Tamaño: {result['bytes_copied']:,} bytes ({result['bytes_copied'] / 1024:.2f} KB)")
    print(f"  Cluster inicial: {result['start_cluster']}")
    print(f"  Clusters usados: {result['num_clusters']}\n")


def display_delete_result(result: Dict) -> None:
    """Muestra resultado de operación delete."""
    print(f"\n✓ Archivo eliminado exitosamente")
    print(f"  Archivo: {result['filename']}")
    print(f"  Espacio liberado: {result['freed_bytes']:,} bytes ({result['freed_bytes'] / 1024:.2f} KB)")
    print(f"  Clusters liberados: {result['freed_clusters']}\n")


def display_error_result(result: Dict) -> None:
    """Muestra resultado de error."""
    import sys

    error_type = result.get('error_type', 'Error')
    message = result.get('message', 'Error desconocido')

    print(f"\n❌ Error: {message}", file=sys.stderr)

    # Mostrar información adicional si está disponible
    if 'available_files' in result and result['available_files']:
        print(f"   Archivos disponibles: {', '.join(result['available_files'])}", file=sys.stderr)

    print(file=sys.stderr)
