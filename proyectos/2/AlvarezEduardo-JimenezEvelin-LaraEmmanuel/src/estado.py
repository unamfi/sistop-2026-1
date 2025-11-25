# estado.py
# Estado compartido entre hilos para monitorear la actividad del sistema de archivos.

from dataclasses import dataclass


@dataclass
class EstadoFS:
    """
    Estructura simple para llevar estadísticas y último evento del FS.

    Atributos:
    - leidos    : número de operaciones de lectura/copias desde la imagen.
    - escritos  : número de operaciones de escritura/copias hacia la imagen.
    - eliminados: número de archivos marcados como eliminados.
    - ultimo_evento: descripción textual de la última operación relevante
                     (útil para mostrar en monitor o en la GUI).
    """
    
    leidos: int = 0
    escritos: int = 0
    eliminados: int = 0
    ultimo_evento: str = ""