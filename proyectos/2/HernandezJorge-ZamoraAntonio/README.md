# 📂 Proyecto 2 — FiUnamFS

**Materia:** Sistemas Operativos  
 
**Alumno(s):** (Hernández Irineo Jorge Manuel, Zamora Ayala Antonio Manuel)  
**Semestre:** (2026-1)

---

## 📘 Descripción del Proyecto

El objetivo de este proyecto es implementar un sistema de archivos tipo **FiUnamFS**, capaz de:

- Leer y validar el superbloque
- Listar el contenido del directorio
- Leer archivos almacenados en el FiUnamFS
- Copiar archivos desde y hacia la imagen del sistema de archivos
- Realizar borrado lógico
- Manejar y compactar el espacio libre disponible

El proyecto está desarrollado en **Python 3**, haciendo uso del manejo de archivos binarios
para interpretar correctamente la estructura interna de FiUnamFS.

---

## 🛠️ Características Implementadas

| Funcionalidad | Estado |
|--------------|:-----:|
| Lectura del superbloque | ✔ |
| Validación del FS y versión | ✔ |
| Listar archivos del directorio | En proceso |
| Leer contenido de un archivo | ❌ |
| Copiar archivo desde FiUnamFS | ❌ |
| Copiar archivo a FiUnamFS | ❌ |
| Borrado lógico | ❌ |
| Compactación | ❌ |

> Se irá actualizando conforme avance el desarrollo

---

## ▶ Ejecución del programa

Dentro del directorio del proyecto, ejecutar:

```bash
python fiunamfs_info.py fiunamfs.img

### 📌 Lectura y listado de entradas del directorio

En este paso del proyecto se implementó la funcionalidad encargada de leer el área del directorio del sistema de archivos FiUnamFS, la cual se encuentra ubicada a partir del *cluster 1* y abarca *3 clusters*, según lo indicado en el superbloque.

Cada entrada del directorio tiene un tamaño fijo de **64 bytes**, y se obtienen los campos:

- Nombre del archivo (primeros 15 bytes)
- Tamaño del archivo en bytes (offset 16–19)
- Cluster inicial donde se ubica el contenido del archivo (offset 24–27)

Con esta información, el programa ahora es capaz de:

- Recorrer todas las entradas asignadas al directorio
- Identificar entradas ocupadas o vacías
- Mostrar los archivos encontrados en el formato:

### 📌 Lectura de contenido de archivos en FiUnamFS

En esta etapa del proyecto se implementó la funcionalidad necesaria para leer el contenido de un archivo almacenado en el sistema de archivos FiUnamFS. Para lograrlo, se realiza lo siguiente:

1️⃣ Se recorre nuevamente el directorio para localizar una entrada cuyo nombre coincida con el archivo solicitado.  
2️⃣ Si el archivo es encontrado:
- Se toma su cluster inicial y tamaño en bytes
- Se calcula la posición real dentro de la imagen
- Se lee el contenido completo del archivo desde la imagen
- Se muestra como texto al usuario (cuando es posible)

3️⃣ Si el archivo **no** existe en el directorio:
- Se muestra un mensaje indicando que no fue encontrado

Actualmente, la imagen del sistema de archivos contiene únicamente entradas vacías, por lo que se espera la salida:



