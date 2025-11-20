# Proyecto 2 – Micro sistema de archivos FiUnamFS

## Autores
- Escobar Díaz Víctor Manuel  
- Hernández Rubio Josue  

---

## Descripción general

Este proyecto implementa una herramienta en Python para manipular el micro–sistema de archivos **FiUnamFS**, almacenado en una imagen de 1.44 MB (formato tipo disquete).

La herramienta soporta:

- list – Listar el contenido del directorio raíz.  
- extract – Extraer archivos desde la imagen.  
- import – Importar archivos desde la computadora hacia la imagen.  
- delete – Eliminar archivos dentro de la imagen.  
- rename – Renombrar archivos dentro de la imagen.  

El sistema está protegido mediante un **Read/Write Lock**, lo cual permite múltiples lectores simultáneos y escritores exclusivos, garantizando consistencia.

---

## Requisitos

- **Lenguaje:** Python 3.x  
- **Probado en:** Windows 10 (Git Bash con `py`)  
- **Dependencias:** Módulos estándar  
  - `struct`, `os`, `argparse`, `sys`, `datetime`, `threading`
- **Imagen FIUNAMFS:**  
  - Compatible con versiones **26-1** y **26-2**

---

## Estructura del proyecto

```
proyectos/2/EscobarVictor_HernandezJosue/proyecto_fs/
│
├── fiunamfs_tool.py      # Implementación de FiUnamFS
├── README.md             # Documentación del proyecto
└── tests/                # Carpeta opcional de pruebas
```

---

## Uso de la herramienta

Todos los comandos siguen la forma:

```
py fiunamfs_tool.py <comando> [opciones]
```

---

## 1. Listar archivos (list)

```
py fiunamfs_tool.py list --img fiunamfs.img
```

---

## 2. Extraer archivos (extract)

```
py fiunamfs_tool.py extract --img fiunamfs.img --file saludo.jpg --dest saludo_extraido.jpg
```

---

## 3. Importar archivos (import)

```
py fiunamfs_tool.py import --img fiunamfs.img --src prueba.txt --dest prueba.txt
```

---

## 4. Eliminar archivos (delete)

```
py fiunamfs_tool.py delete --img fiunamfs.img --file ejemplo.txt
```

---

## 5. Renombrar archivos (rename)

```
py fiunamfs_tool.py rename --img fiunamfs.img --old viejo.txt --new nuevo.txt
```

---

## Detalles de implementación

### Lectura del Superbloque

El programa valida:

- Magic: `FiUnamFS`  
- Versión: `26-1` o `26-2`  
- Label del volumen  
- cluster_size  
- dir_clusters  
- total_clusters  

Si alguno no coincide, la imagen se rechaza.

---

## Estructura del directorio

Cada entrada ocupa 64 bytes y contiene:

- Tipo  
- Nombre (14 bytes)  
- Cluster inicial  
- Tamaño  
- ctime  
- mtime  

Entradas libres aparecen como:

```
..............
```

---

## Asignación contigua de clusters

Para la operación *import*:

1. Se calcula cuántos clusters necesita el archivo.  
2. Se revisa qué clusters están ocupados.  
3. Se buscan clusters contiguos libres.  
4. Se escribe el archivo en la imagen.  
5. Se crea la entrada válida en el directorio.  

---

## Manejo de hilos y sincronización

Se implementó un **Read/Write Lock**:

- Lectores simultáneos:
  - list  
  - extract  

- Escritores exclusivos:
  - import  
  - delete  
  - rename  

Esto evita condiciones de carrera y mantiene la consistencia del sistema de archivos.

---

## Pruebas realizadas

| Operación              | Estado   |
|------------------------|----------|
| Listar                 | Correcto |
| Extraer                | Correcto |
| Importar               | Correcto |
| Renombrar              | Correcto |
| Eliminar               | Correcto |
| Sincronización (hilos) | Correcto |

Todas las pruebas se realizaron en Windows 10 usando Git Bash con:

```
py fiunamfs_tool.py ...
```

---

## Comentarios finales

El proyecto implementa correctamente todas las operaciones requeridas, maneja sincronización con hilos y soporta imágenes FiUnamFS versión 26-1 y 26-2.  
Las pruebas realizadas confirmaron el funcionamiento correcto del sistema.