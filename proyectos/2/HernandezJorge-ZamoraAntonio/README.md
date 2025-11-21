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
| Listar archivos del directorio | ✔ |
| Leer contenido de un archivo | ✔ |
| Copiar archivo desde FiUnamFS | ✔ |
| Copiar archivo a FiUnamFS | ✔ |
| Borrado lógico | ✔ |
| Compactación | ✔ |

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
El archivo 'archivo.txt' no se encontró en el FS.

### 📌  Copiar un archivo desde la PC hacia FiUnamFS

En este paso se implementó la funcionalidad para agregar un nuevo archivo al sistema de archivos FiUnamFS. La operación realizada permite tomar un archivo existente en la computadora y almacenarlo dentro de la imagen del sistema.

Para lograrlo, el programa realiza los siguientes procedimientos:

1️⃣ **Lectura del archivo local**  
Se abre el archivo seleccionado desde el sistema operativo anfitrión y se obtiene su tamaño en bytes.

2️⃣ **Búsqueda de una entrada libre en el directorio**  
Se recorre la región del directorio (clusters 1–3) buscando un espacio disponible para registrar el nuevo archivo.

3️⃣ **Asignación de un cluster de datos**  
En esta primera versión se asigna de manera sencilla el primer cluster disponible después de los clusters del directorio.

4️⃣ **Escritura en la imagen del FS**  
- Se copia el contenido del archivo al cluster asignado
- Se actualiza la entrada del directorio con:
  - Nombre del archivo (máximo 15 bytes)
  - Tamaño en bytes
  - Número de cluster inicial

5️⃣ **Validación posterior**  
Se utilizó la funcionalidad del paso 3 para comprobar que el archivo se puede leer correctamente desde el FiUnamFS.

Esta implementación cumple correctamente con el requerimiento de **copiar archivos desde la PC hacia el sistema de archivos**, y sienta las bases para funcionalidades más avanzadas en pasos siguientes como manejo real de clusters libres, archivos mayores a 1 cluster y control de entradas duplicadas.

### 📌  Manejo del espacio libre y asignación real de clusters

En este paso se añadió la capacidad de gestionar de forma correcta qué clusters están en uso dentro del sistema de archivos FiUnamFS. Para ello:

1️⃣ Se recorren las entradas válidas del directorio  
2️⃣ A partir del tamaño de cada archivo se calcula cuántos clusters ocupa  
3️⃣ Todos los clusters utilizados se agregan a un conjunto `ocupados`  
4️⃣ Se recorre la región de datos del FS para localizar el **primer cluster libre**  
5️⃣ Al copiar archivos nuevos se selecciona un cluster disponible, evitando sobrescritura  

Con esto:

- Ya es posible copiar múltiples archivos al FS
- Cada uno obtiene una posición independiente dentro de la imagen
- La lectura de los archivos sigue funcionando correctamente
- Se detecta cuando la unidad se queda sin espacio real

Esta mejora deja listo el sistema para extender la funcionalidad hacia:
- Archivos que ocupen más de un cluster
- Borrado lógico
- Compactación del espacio


### 📌 Exportar archivos desde FiUnamFS hacia la PC

En este paso se implementó la funcionalidad para recuperar archivos almacenados en la imagen de FiUnamFS y copiarlos al sistema anfitrión.

El proceso que realiza el programa es el siguiente:

1️⃣ Usar la función `leer_archivo()` para localizar y leer el contenido del archivo directamente desde los clusters del sistema de archivos.  
2️⃣ Verificar que el archivo exista en el directorio del FS.  
3️⃣ Crear un archivo en la computadora y escribir en él los datos recuperados.  
4️⃣ Confirmar la correcta exportación del archivo.

Esta funcionalidad permite validar completamente la integridad del archivo dentro de FiUnamFS y garantiza que la información almacenada puede ser recuperada por el usuario cuando sea necesario.

Con esto, se cumple el requerimiento del proyecto de copiar archivos del sistema de archivos FiUnamFS hacia el sistema operativo anfitrión.

### 📌 Borrado lógico de archivos en FiUnamFS

En este paso se implementó la capacidad de eliminar archivos del sistema de archivos FiUnamFS mediante un borrado lógico, sin alterar directamente los datos almacenados en los clusters.

El procedimiento consiste en:

1️⃣ Localizar la entrada del directorio correspondiente al archivo a borrar.  
2️⃣ Modificar el primer byte del nombre del archivo, reemplazándolo por un punto `"."`, lo que indica que la entrada queda disponible para reutilización.  
3️⃣ Los datos del archivo no se eliminan, pero el sistema deja de mostrarlo como archivo válido.  
4️⃣ El espacio de almacenamiento ocupado por el archivo queda marcado implícitamente como disponible para futuros archivos.

Esta técnica mantiene la integridad de la estructura del sistema de archivos sin necesidad de reacomodar inmediatamente los datos, y prepara el sistema para la futura funcionalidad de **compactación del espacio libre**.


### 📌 Compactación del espacio en FiUnamFS

Tras el proceso de borrado lógico, los clusters ocupados por archivos eliminados pueden generar fragmentación en la zona de datos del FS. Para evitarlo se implementó un algoritmo de compactación que:

1️⃣ Recopila todas las entradas válidas del directorio  
2️⃣ Ordena los archivos por su cluster actual  
3️⃣ Mueve archivos a los primeros clusters disponibles  
4️⃣ Actualiza en el directorio su nuevo cluster inicial  
5️⃣ Libera clusters al final del FS

Con este mecanismo se garantiza un uso más eficiente del espacio de almacenamiento y se minimizan los huecos entre archivos. Si al ejecutar la compactación no se detectan huecos, la estructura permanece sin cambios, preservando la integridad de los datos del FS.

## Conclusión

Este proyecto permitió comprender de manera práctica el funcionamiento y administración interna de un sistema de archivos. A través del acceso directo al almacenamiento, se analizaron y manipularon las estructuras fundamentales de **FiUnamFS**, logrando implementar operaciones esenciales como lectura, escritura, borrado lógico y compactación.

Además del aprendizaje técnico, este trabajo refuerza conceptos clave de Sistemas Operativos como el manejo de clusters libres, fragmentación, consistencia del directorio y recuperación de datos. La implementación progresiva de cada paso favoreció un enfoque de desarrollo modular y una documentación clara del avance, asegurando la trazabilidad del proceso mediante control de versiones en GitHub.

Con ello, se logró cumplir completamente los requerimientos del proyecto, obteniendo una herramienta funcional que permite gestionar archivos dentro de una imagen del sistema de archivos, simulando operaciones reales que forman parte del núcleo de un sistema operativo moderno.
