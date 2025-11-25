"""
Hilo de E/S para operaciones del filesystem FiUnamFS

Este módulo implementa el hilo worker que ejecuta todas las operaciones
sobre el filesystem. Se comunica con el hilo de UI mediante colas thread-safe.

Arquitectura:
- IOThread: Hilo dedicado que mantiene el file handle del filesystem
- Consume comandos de command_queue (blocking get)
- Produce resultados en result_queue (non-blocking put)
- Maneja todas las excepciones y las convierte a dicts de error
- Ejecuta en loop hasta recibir comando 'exit'
"""

import threading
import queue
from typing import Dict, Tuple, Optional

from models.filesystem import Filesystem
from utils.exceptions import (
    FiUnamFSError,
    InvalidFilesystemError,
    FileNotFoundInFilesystemError,
    FilenameConflictError,
    NoSpaceError,
    DirectoryFullError,
    InvalidFilenameError
)


class IOThread(threading.Thread):
    """
    Hilo de E/S que ejecuta operaciones del filesystem.

    Este hilo mantiene acceso exclusivo al filesystem y ejecuta todas
    las operaciones de lectura/escritura. Es el único que puede modificar
    el archivo .img, implementando el patrón single-writer.

    Atributos:
        fs_path: Ruta al archivo del filesystem
        command_queue: Cola de comandos (UI → I/O)
        result_queue: Cola de resultados (I/O → UI)
        filesystem: Instancia de Filesystem (exclusiva de este hilo)
    """

    def __init__(self, fs_path: str, command_queue: queue.Queue, result_queue: queue.Queue):
        """
        Inicializa el hilo de E/S.

        Args:
            fs_path: Ruta al archivo .img del filesystem
            command_queue: Cola para recibir comandos del UI thread
            result_queue: Cola para enviar resultados al UI thread
        """
        super().__init__(name='IOThread')
        self.fs_path = fs_path
        self.command_queue = command_queue
        self.result_queue = result_queue
        self.filesystem = None

    def run(self):
        """
        Loop principal del hilo de E/S.

        Este método se ejecuta en el hilo separado. Abre el filesystem,
        procesa comandos en loop, y cierra el filesystem al terminar.
        """
        try:
            # Abrir filesystem (exclusivo de este hilo)
            self.filesystem = Filesystem(self.fs_path)

            # Loop de procesamiento de comandos
            while True:
                # Esperar comando de la cola (blocking get)
                # El hilo se bloquea aquí cuando no hay comandos
                cmd, args = self.command_queue.get()

                # Verificar comando de salida
                if cmd == 'exit':
                    break

                # Ejecutar comando y enviar resultado
                try:
                    result = self.execute_command(cmd, args)
                    self.result_queue.put(result)
                except Exception as e:
                    # Convertir excepción a dict de error
                    error_result = self._exception_to_dict(e)
                    self.result_queue.put(error_result)

        except Exception as e:
            # Error fatal al abrir filesystem
            error_result = self._exception_to_dict(e)
            self.result_queue.put(error_result)

        finally:
            # Siempre cerrar filesystem
            if self.filesystem:
                self.filesystem.close()

    def execute_command(self, cmd: str, args: Optional[Dict]) -> Dict:
        """
        Ejecuta un comando del filesystem.

        Args:
            cmd: Nombre del comando ('list', 'export', 'import', 'delete')
            args: Argumentos del comando (dict o None)

        Returns:
            Diccionario con resultado de la operación

        Raises:
            ValueError: Si el comando no es reconocido
            FiUnamFSError: Si hay error en la operación del filesystem
        """
        if cmd == 'list':
            result = self.filesystem.list_files()
            result['status'] = 'success'
            return result

        elif cmd == 'export':
            result = self.filesystem.export_file(
                args['filename'],
                args['dest_path']
            )
            result['status'] = 'success'
            return result

        elif cmd == 'import':
            result = self.filesystem.import_file(
                args['src_path'],
                args.get('filename')
            )
            result['status'] = 'success'
            return result

        elif cmd == 'delete':
            # Para delete, primero verificar si necesitamos confirmación
            if not args.get('confirmed', False):
                # Buscar archivo para obtener info
                entry = self.filesystem._find_file(args['filename'])
                return {
                    'status': 'confirm',
                    'filename': args['filename'],
                    'size': entry.file_size
                }
            else:
                # Ejecutar eliminación confirmada
                result = self.filesystem.delete_file(args['filename'])
                result['status'] = 'success'
                return result

        else:
            raise ValueError(f"Comando no reconocido: {cmd}")

    def _exception_to_dict(self, exc: Exception) -> Dict:
        """
        Convierte una excepción a un diccionario de error.

        Args:
            exc: Excepción a convertir

        Returns:
            Diccionario con 'status': 'error', 'error_type', 'message', etc.
        """
        result = {
            'status': 'error',
            'error_type': type(exc).__name__,
            'message': str(exc)
        }

        # Agregar información adicional según el tipo de excepción
        if isinstance(exc, FileNotFoundInFilesystemError):
            result['available_files'] = exc.archivos_disponibles

        elif isinstance(exc, NoSpaceError):
            result['bytes_needed'] = exc.bytes_necesarios
            result['bytes_available'] = exc.bytes_disponibles

        return result
