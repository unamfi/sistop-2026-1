
# Proyecto 2 – Micro sistema de archivos FiUnamFS

## Autores

- Escobar Díaz Víctor Manuel  
- Hernández Rubio Josue  

## Descripción general

Este proyecto implementa una herramienta en Python para manipular el micro–sistema de archivos **FiUnamFS**, almacenado en un archivo de 1.44 MB (imagen de diskette).  

La herramienta permite:

- Listar el contenido del directorio raíz de FiUnamFS. (`list`).
- Copiar archivos **desde** FiUnamFS hacia la computadora (`extract`).
- Copiar archivos **desde la computadora** hacia FiUnamFS (`import`).
- Eliminar archivos dentro de FiUnamFS (`delete`).
- Renombrar archivos dentro de FiUnamFS (`rename`).

Además, el acceso a la imagen está protegido con un **Read/Write Lock** para permitir un uso seguro desde múltiples hilos.

---

## Requisitos

- **Lenguaje:** Python 3.x  
- **Probado en:** Windows 10, usando Git Bash y `py` como lanzador de Python.  
- **Dependencias externas:** Solo módulos estándar de Python:
  - `struct`
  - `os`
  - `argparse`
  - `sys`
  - `datetime`
  - `threading`

- **Archivo de imagen:**  
  - `fiunamfs.img` (o una imagen compatible)  
  - Debe ser una imagen creada con el formato **FiUnamFS** versión `26-1` o `26-2`.  
  - La imagen **no se sube** al repositorio del profesor; se usa únicamente para pruebas locales.

---

## Estructura del proyecto

Dentro de `proyectos/2/EscobarVictor_HernandezJosue/proyecto_fs/` tenemos:

- `fiunamfs_tool.py` – Programa principal, implementación de la herramienta.  
- `tests/` – Directorio reservado para pruebas (por ejemplo, scripts o notas).  
- `fiunamfs.img` – Imagen del sistema de archivos usada para pruebas locales (no incluida en la entrega al profesor).

---

## Uso de la herramienta

Todos los comandos se invocan con la forma:

`bash`
py fiunamfs_tool.py <comando> [opciones]
- Copiar archivos **desde la computadora** hacia FiUnamFS (`import`).
- Eliminar archivos dentro de FiUnamFS (`delete`).
- Renombrar archivos dentro de FiUnamFS (`rename`).

Además, el acceso a la imagen está protegido con un **Read/Write Lock** para permitir un uso seguro desde múltiples hilos.

---

## Requisitos

- **Lenguaje:** Python 3.x
- **Probado en:** Windows 10, usando Git Bash y `py` como lanzador de Python.
- **Dependencias externas:** Solo módulos estándar de Python:
  - `struct`
  - `os`
  - `argparse`
  - `sys`
  - `datetime`
  - `threading`

- **Archivo de imagen:**
  - `fiunamfs.img` (o una imagen compatible)
  - Debe ser una imagen creada con el formato **FiUnamFS** versión `26-1` o `26-2`.
  - La imagen **no se sube** al repositorio del profesor; se usa únicamente para pruebas locales.

---

## Estructura del proyecto

Dentro de `proyectos/2/EscobarVictor_HernandezJosue/proyecto_fs/` tenemos:

- `fiunamfs_tool.py` – Programa principal, implementación de la herramienta.
- `tests/` – Directorio reservado para pruebas (por ejemplo, scripts o notas).
- `fiunamfs.img` – Imagen del sistema de archivos usada para pruebas locales (no incluida en la entrega al profesor).

---

## Uso de la herramienta

Todos los comandos se invocan con la forma:

`bash`
py fiunamfs_tool.py <comando> [opcion]

## Comandos disponibles

### 1. Listar archivos (list)

Muestra todo el contenido del directorio FiUnamFS.

`bash`
py fiunamfs_tool.py list --img fiunamfs.img

###2. Extraer archivos (extract)
Copia un archivo desde la imagen hacia tu computadora.

`bash`
py fiunamfs_tool.py extract --img fiunamfs.img --file saludo.jpg --dest saludo_extraido.jpg

###3. Importar archivos (import)
Copia un archivo desde la computadora hacia la imagen FiUnamFS.

`bash`
py fiunamfs_tool.py import --img fiunamfs.img --src prueba.txt --dest prueba.txt

El sistema busca espacio contiguo libre, asigna clusters y crea la entrada del directorio.

###4. Eliminar archivos (delete)
Marca la entrada como libre dentro del directorio y libera los clusters ocupados.

`bash`
py fiunamfs_tool.py delete --img fiunamfs.img --file ejemplo.txt

###5. Renombrar archivos (rename)
Cambia el nombre de un archivo existente dentro de la imagen.

`bash`
py fiunamfs_tool.py rename --img fiunamfs.img --old viejo.txt --new nuevo.txt

---
###Detalles de Implementación
Lectura del Superbloque
El programa interpreta el primer sector (superbloque) y lee:

Magic: "FiUnamFS"

Version: "26-1" o "26-2"

Label: nombre del volumen

cluster_size

dir_clusters

total_clusters

El programa no continúa si la imagen no cumple con estos requisitos.
---

---
##Estructura del directorio
Cada entrada del directorio mide 64 bytes e incluye:

Tipo

Nombre (14 bytes)

Cluster inicial

Tamaño

ctime

mtime

Las entradas vacías se representan como:

..............

---

---
###Asignación contigua de clusters
Para importar un archivo:

Se calcula el número de clusters necesarios.

Se identifica qué clusters están ocupados.

Se buscan clusters contiguos disponibles.

Se escribe el archivo en la imagen.

Se agrega una entrada válida en el directorio.
---

---
###Manejo de hilos y sincronización
Para cumplir con la sección de hilos y sincronización requerida en el proyecto:

Se implementó un Read/Write Lock con el módulo threading, permitiendo:

-Lectores concurrentes (list y extract).

-Escritores exclusivos (import, delete, rename).

Esto evita condiciones de carrera al modificar la imagen y garantiza consistencia cuando varias operaciones acceden al archivo simultáneamente.
---

---
###Pruebas realizadas
Se validaron todas las operaciones del sistema:

Operación	Estado
Listar	        Correcto
Extraer	        Correcto
Importar	Correcto
Renombrar	Correcto
Eliminar	Correcto
Sincronización con hilos	Correcto

Las pruebas se realizaron en Windows 10 con Git Bash usando el comando py para ejecutar Python.
---
