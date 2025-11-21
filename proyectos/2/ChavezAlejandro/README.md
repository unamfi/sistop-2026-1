# Proyecto: (Micro) sistema de archivos FiUnamFS
**Alumno:** B. Alejandro Chávez López

## Descripción
Este proyecto implementa un manipulador para el sistema de archivos FiUnamFS.
El sistema debe permitir listar, copiar y eliminar archivos de una imagen de disco virtual (que se incluyó en la asignación).

## Estructura del Proyecto
    -> fiunamfs.img: Imagen del disco virtual (sirve como simulación de hardware).
    -> fiunamfs.py: Script principal que implementa las funciones.
    -> README.md: Este readme en markdown

## Avance
### Fase 1: Lectura del Superbloque
Se implementó la función "leer_superbloque" que:
1. Abre el archivo ".img" en modo binario.
2. Lee los primeros 54 bytes.
3. Decodifica los valores ASCII y Little Endian (como se muestra en la asignación).
4. Valida que el "Magic Number" sea "FiUnamFS" y la versión 26-2 (o 26-1, ya que cambia con respecto a la asignación

### Fase 2: Listado del Directorio
Se implementó la función "listar_contenido" que:
1. Calcula la ubicación del directorio (cluster 1, byte 1024).
2. Itera byte a byte en bloques de 64 bytes (tamaño de entrada de directorio).
3. Identifica archivos válidos verificando si el primer byte es un punto "." .
4. Decodifica y limpia el nombre del archivo y extrae su tamaño y cluster inicial.

### Fase 3: Copiado desde FiUnamFS hacia PC
Se implementó la función "copiar_de_fiunamfs" que:
1. Recorre el directorio buscando algún archivo con la entrada del usuario.
2. Hace una limpieza de caracteres nulos y espacios en blanco del nombre almacenado para evitar problemas de reconocimiento (esto pasaba, ya que el nombre del archivo en el FS contenía espacios que conlfictuaban con la entrada del usuario).
3. Obtiene el cluster inicial y el tamaño del archivo desde la entrada de directorio.
4. Calcula el offset y genera un archivo local con el contenido extraído ()byte a byte).

### Fase 4: Copiado hacia FiUnamFS (Multihilo)
Se implementó la función "copiar_a_fiunamfs" que:
1. Revisa el directorio existente para mapear clusters ocupados y encontrar un bloque libre contiguo.
2. Usa el patrón productor-consumidor con dos hilos y una cola sincronizada para transferir los datos del archivo local al img.
3. Genera una nueva entrada de directorio con los metadatos (nombre, tamaño, clusters, fechas).
