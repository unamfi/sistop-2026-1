# constantes.py
# Constantes generales del sistema de archivos FiUnamFS.

# Tamaño del cluster 0 (superbloque).
# En FiUnamFS el superbloque ocupa exactamente 1024 bytes.
CLUSTER_SIZE_SUPERBLOQUE = 1024

# Cada entrada de directorio tiene un tamaño fijo de 64 bytes.
# Esto se usa para recorrer el directorio "a pasos" de ENTRY_SIZE.
ENTRY_SIZE = 64

# Cadena mágica que identifica que la imagen pertenece al FS FiUnamFS.
# Se valida al leer el superbloque.
MAGIC = "FiUnamFS"

# Versión de FiUnamFS esperada en la imagen.
# También se valida al leer el superbloque.
VERSION = "26-1"

# En FiUnamFS el directorio comienza en el cluster lógico 1.
# El cluster 0 es el superbloque.
DIR_START_CLUSTER = 1