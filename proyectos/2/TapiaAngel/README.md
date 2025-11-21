# Proyecto: Micro sistema de archivos con arquitectura concurrente 
## Autor: Tapia Ledesma Angel Hazel 

## Estrategia de solucion
El proyecto se abordó utilizando el lenguaje **Python** debido a su capacidad nativa para manejar estructuras de datos binarios (`struct`) y mapeo de memoria (`mmap`).

La arquitectura sigue el patrón de diseño **Productor-Consumidor**:

1.  **Interfaz (Productor):** El hilo principal captura los comandos del usuario y los valida superficialmente. No toca el disco directamente.
2.  **Cola de Mensajes:** Las órdenes válidas se colocan en una `Queue`, que actúa como un buffer seguro entre la interfaz y el sistema de archivos.
3.  **Motor (Consumidor):** Un hilo trabajador (Worker) procesa las órdenes una por una, garantizando que las operaciones complejas no congelen el programa.

## Descripción de la Sincronización

Para cumplir con el requisito de administración de procesos concurrente, se implementaron dos mecanismos clave:

1.  **Cola Sincronizada (`queue.Queue`):**
    * Se utiliza para comunicar el hilo principal (Main) con el hilo trabajador (Worker).
  

2.  **Exclusión Mutua (`threading.Lock`):**
    * **Recurso Crítico:** El archivo mapeado en memoria (`self.mm`).
    * **Mecanismo:** Se utiliza un objeto `Lock` global. Antes de que el hilo trabajador lea o escriba en el disco, adquiere el candado (`lock.acquire()`). Al terminar, lo libera (`lock.release()`).
    * **Objetivo:** Esto previene condiciones de carrera, asegurando que no se intenten escribir dos archivos al mismo tiempo o leer mientras se está borrando, lo cual corrompería el sistema de archivos.

## Requisitos 
### Requisitos del Sistema

  * **Python 3.6** o superior.
  * No requiere instalación de librerías externas (utiliza solo la biblioteca estándar).
  * Sistema Operativo: Windows, Linux o macOS.
  * Imagen del sistema de archivos (fiunamfs.img)

## Instrucciones de ejecución 
Para ejecutar el programa, primero nos tendremos que posicionar sobre el directorio en el cual se encuentra tanto el archivo del proyecto, cómo la imágen del sistemas de archivos, una vez en esta zona, escribiremos el siguiente comando para ejecutar el programa

``` 
python3 Proyecto.py
```
Verás un prompt `FiUnamFS>`. Ingresa los comandos deseados.

## Guía de uso y comandos
El programa cuenta con los siguientes comandos
| Comando | Argumentos | Descripción | Ejemplo |
| :--- | :--- | :--- | :--- |
| `ls` | (Ninguno) | Lista los archivos en el disco | `FiUnamFS> ls` |
| `cp in` | `<local> <remoto>` | Copia un archivo de tu PC al FiUnamFS | `cp in foto.jpg imagen.jpg` |
| `cp out` | `<remoto> <local>` | Extrae un archivo del FiUnamFS a tu PC | `cp out tarea.txt copia.txt` |
| `rm` | `<nombre>` | Elimina un archivo del sistema | `rm virus.exe` |
| `exit` | (Ninguno) | Cierra el programa y guarda cambios | `FiUnamFS> exit` |

