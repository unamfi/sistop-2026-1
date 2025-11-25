# entradas.py
# Definición de la estructura de una entrada de directorio.

from constantes import ENTRY_SIZE


class DirEntry:
    """
    Representa una entrada de 64 bytes en el directorio de FiUnamFS.

    El formato (offsets dentro de los 64 bytes) es:
    - [0:1]   : tipo de archivo (un carácter ASCII)
    - [1:15]  : nombre del archivo en ASCII, relleno con espacios
    - [16:20] : número de cluster de inicio (little-endian, entero sin signo)
    - [20:24] : tamaño del archivo en bytes (little-endian, entero sin signo)
    - [24:38] : fecha/hora de creación en formato ASCII (YYYYMMDDhhmmss)
    - [38:52] : fecha/hora de modificación en formato ASCII (YYYYMMDDhhmmss)

    El resto de los bytes de la entrada pueden estar reservados o no usados.
    """

    def __init__(self, raw: bytes):
        # Validamos estrictamente que los datos crudos midan exactamente
        # ENTRY_SIZE bytes; si no, algo se leyó mal del directorio.
        if len(raw) != ENTRY_SIZE:
            raise ValueError("Entrada de directorio inválida (tamaño incorrecto).")

        # Guardamos la vista cruda por si se necesita depuración futura.
        self.raw = raw
        
        # Tipo de entrada (archivo, directorio, etc.). En FiUnamFS se usa
        # típicamente un punto ('.') para archivos normales.
        self.type = raw[0:1].decode("ascii")
        
        # Nombre del archivo, en ASCII, rellenado a 14 caracteres.
        # Se hace strip() para quitar espacios a la derecha.
        self.name = raw[1:15].decode("ascii").strip()
        
        # Cluster lógico de inicio del archivo.
        self.start = int.from_bytes(raw[16:20], "little")
        
        # Tamaño en bytes del archivo.
        self.size = int.from_bytes(raw[20:24], "little")
        
        # Marca de tiempo de creación como cadena ASCII.
        self.created = raw[24:38].decode("ascii")
        
        # Marca de tiempo de última modificación como cadena ASCII.
        self.modified = raw[38:52].decode("ascii")

    def is_empty(self) -> bool:
        """
        Determina si la entrada está libre.

        En FiUnamFS las entradas libres se marcan llenando el nombre
        con puntos (por ejemplo ".............").
        """
        return self.name.startswith(".............")