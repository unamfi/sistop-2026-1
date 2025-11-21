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
4. Valida que el "Magic Number" sea "FiUnamFS" y la versión 26-2 (o 26-1, ya que cambia con respecto a la asignación).
