# Proyecto: (Micro) sistema de archivos FiUnamFS
**Alumno:** B. Alejandro Chávez López
**Materia:** Sistemas Operativos

## Descripción
Este proyecto implementa un manipulador para el sistema de archivos FiUnamFS.
El sistema debe permitir listar, copiar y eliminar archivos de una imagen de disco virtual (que se incluyó en la asignación).

## Entorno y Dependencias
Para ejecutar este proyecto se requiere un entorno con las siguientes características:

* **Lenguaje:** Python 3 (Probado v3.13.9).
* **Sistema Operativo:** Desarrollado en Fedora Linux 42.
* **Bibliotecas:** * **Estándar:** "struct", "os", "sys", "threading", "queue", "datetime", "time".
    * **Interfaz Gráfica:** "tkinter" incluida por defecto (Linux).

### Instrucciones de Ejecución

**Modo Interfaz Gráfica**
1. Asegúrese de que "fiunamfs.img" debe estar en el directorio.
2. Ejecutar: python3 interfaz.py

## Estructura del Proyecto
    -> fiunamfs.img: Imagen del disco virtual (sirve como simulación de hardware).
    -> fiunamfs.py: Script principal que implementa las funciones.
    -> interfaz.py: Programa que lanza la interfaz gráfica (se siguen viendo las operaciones en la terminal)
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

### Fase 5: Eliminación de Archivos
Se implementó la función "eliminar_archivo" que:
1. Encuentra la entrada del archivo en el directorio mediante comparación de nombre.
2. Sobrescribe el byte de tipo con "-" (0x2F) y el nombre con una cadena de puntos.
3. Libera la entrada del directorio para ser reutilizado sin necesidad de borrar "físicamente" los datos del cluster.

### Actualización de la fase 4: Validación de duplicados y longitud de nombre 
Se detectó y corrigió un error que permitía la creación de múltiples archivos con el mismo nombre.
1. Se añadió una seccion de validación en la función "copiar_a_fiunamfs" para evitar duplicados.
2. El sistema ahora verifica si hay un archivo con el mismo nombre en el directorio antes de iniciar la asignación de espacio o los hilos de transferencia.
3. Se añadió una seccion de validación en la función "copiar_a_fiunamfs" para evitar que el nombre del archivo a copiar tenga una longitud >15 caracteres (puede corromper archivos al cortar sus nombres a <15 caracteres).

### Fase Final: Interfaz de Usuario (CLI)
Se integró un menú interactivo en bucle infinito que permite al usuario seleccionar las operaciones a realizar.
1. Menú numérico para acceder a las funciones.
2. En operaciones de escritura (copiar hacia el img) o borrado, el sistema muestra el estado del directorio "Antes" y "Después" de la operación para confirmar visualmente la acción.

### GUI: Reemplazo de la CLI por una interfaz gráfica
Se reemplazó la implementación de la CLI para interactuar con el programa por una GUI amigable y con colores llamativos
