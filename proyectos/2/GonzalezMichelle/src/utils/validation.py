"""
Funciones de validación para FiUnamFS

Valida nombres de archivos, tamaños, números de cluster y otros
parámetros según la especificación de FiUnamFS.
"""


def validar_nombre_archivo(nombre: str) -> None:
    """
    Valida que un nombre de archivo cumpla con los requisitos de FiUnamFS.

    Requisitos:
    - Longitud máxima: 14 caracteres
    - Solo caracteres US-ASCII (0-127)
    - No puede contener separadores de ruta (/ o \\)
    - No puede estar vacío

    Args:
        nombre: Nombre de archivo a validar

    Raises:
        ValueError: Si el nombre no cumple algún requisito
    """
    if not nombre or len(nombre) == 0:
        raise ValueError("El nombre de archivo no puede estar vacío")

    if len(nombre) > 14:
        raise ValueError(
            f"El nombre de archivo '{nombre}' excede el límite de 14 caracteres "
            f"(tiene {len(nombre)} caracteres)"
        )

    # Verificar que todos los caracteres sean US-ASCII
    if not all(ord(c) < 128 for c in nombre):
        raise ValueError(
            f"El nombre de archivo '{nombre}' contiene caracteres no-ASCII. "
            "Solo se permiten caracteres US-ASCII (a-z, A-Z, 0-9, _, -, .)"
        )

    # Verificar que no contenga separadores de ruta
    if '/' in nombre or '\\' in nombre:
        raise ValueError(
            f"El nombre de archivo '{nombre}' no puede contener separadores "
            "de ruta (/ o \\). FiUnamFS usa estructura plana de directorios"
        )


def validar_cluster(numero_cluster: int, es_dato: bool = True) -> None:
    """
    Valida que un número de cluster esté en el rango válido.

    Args:
        numero_cluster: Número de cluster a validar
        es_dato: True si el cluster debe ser de datos (5-1439),
                False si puede ser cualquier cluster (0-1439)

    Raises:
        ValueError: Si el número de cluster está fuera de rango
    """
    if es_dato:
        # Clusters de datos: 5 a 1439 (0-4 están reservados)
        if numero_cluster < 5 or numero_cluster >= 1440:
            raise ValueError(
                f"Número de cluster {numero_cluster} fuera de rango. "
                "Los clusters de datos deben estar entre 5 y 1439"
            )
    else:
        # Cualquier cluster válido: 0 a 1439
        if numero_cluster < 0 or numero_cluster >= 1440:
            raise ValueError(
                f"Número de cluster {numero_cluster} fuera de rango. "
                "Los clusters válidos están entre 0 y 1439"
            )


def validar_tamanio_archivo(tamanio: int) -> None:
    """
    Valida que el tamaño de un archivo sea válido para FiUnamFS.

    Args:
        tamanio: Tamaño en bytes

    Raises:
        ValueError: Si el tamaño es negativo o excede la capacidad del filesystem
    """
    if tamanio < 0:
        raise ValueError(f"El tamaño de archivo no puede ser negativo: {tamanio}")

    # Capacidad máxima: 1435 clusters × 1024 bytes = 1,469,440 bytes
    # (clusters 5-1439, ya que 0-4 están reservados)
    capacidad_maxima = 1435 * 1024

    if tamanio > capacidad_maxima:
        raise ValueError(
            f"El tamaño de archivo {tamanio} bytes excede la capacidad "
            f"máxima del filesystem ({capacidad_maxima} bytes)"
        )


def calcular_clusters_necesarios(tamanio: int) -> int:
    """
    Calcula cuántos clusters se necesitan para almacenar un archivo.

    Args:
        tamanio: Tamaño del archivo en bytes

    Returns:
        Número de clusters necesarios (división con techo)

    Ejemplo:
        >>> calcular_clusters_necesarios(100)
        1
        >>> calcular_clusters_necesarios(1024)
        1
        >>> calcular_clusters_necesarios(1025)
        2
        >>> calcular_clusters_necesarios(0)
        1
    """
    # Incluso archivos vacíos necesitan al menos 1 cluster
    # para tener un espacio válido asignado en el filesystem
    if tamanio == 0:
        return 1

    # División con techo: (tamanio + 1023) // 1024
    # Equivale a math.ceil(tamanio / 1024)
    return (tamanio + 1023) // 1024


def validar_rango_clusters(inicio: int, cantidad: int) -> None:
    """
    Valida que un rango de clusters sea válido.

    Args:
        inicio: Cluster de inicio
        cantidad: Cantidad de clusters

    Raises:
        ValueError: Si el rango no es válido
    """
    validar_cluster(inicio, es_dato=True)

    if cantidad < 0:
        raise ValueError(f"La cantidad de clusters no puede ser negativa: {cantidad}")

    # Verificar que el rango no exceda el límite
    ultimo_cluster = inicio + cantidad - 1
    if ultimo_cluster >= 1440:
        raise ValueError(
            f"El rango de clusters {inicio}-{ultimo_cluster} excede el límite. "
            "El último cluster de datos es 1439"
        )
