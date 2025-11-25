# 🗂️ FiUnamFS FUSE – Adaptador del Sistema de Archivos FiUnamFS

## 📖 Descripción General

Este módulo implementa un adaptador **FUSE (Filesystem in Userspace)** que permite montar una imagen de **FiUnamFS** como un sistema de archivos real dentro de Linux.  
Gracias a este adaptador, el sistema operativo puede interactuar con la imagen como si fuera un disco propio, permitiendo:

- Navegar el contenido de la imagen con comandos estándar (`ls`, `rm`, `cat`, `echo`, etc.)
- Crear archivos desde el sistema operativo
- Escribir archivos con sobrescritura completa
- Eliminar entradas del directorio
- Leer archivos parcialmente
- Hacer que cualquier aplicación de usuario (editores, compiladores, scripts) acceda a FiUnamFS de forma natural

Este módulo cumple completamente los requisitos del proyecto:
✔ Lectura  
✔ Escritura  
✔ Creación  
✔ Eliminación  
✔ Integración con el kernel mediante FUSE  

---

## 🧠 ¿Qué es FiUnamFS FUSE?

El archivo **fiunamfs_fuse.py** actúa como un *puente* entre:

- el kernel de Linux, que realiza llamadas estándar de sistema (POSIX), y  
- la implementación del sistema de archivos `fiunamfs.py`, que sabe cómo interpretar la estructura interna de la imagen.

Cada vez que Linux quiere hacer algo con un archivo dentro del punto de montaje, FUSE llama a una función definida en este adaptador, y esta función ejecuta la operación correspondiente en la imagen FiUnamFS.

---

# ⚙️ Funciones Principales Implementadas

## ✔ Lectura de atributos (`getattr`)
Obtiene información esencial de un archivo:

- tamaño  
- fechas  
- permisos  
- si es archivo o directorio  

Esto permite que `ls -l` y otros comandos funcionen correctamente.

---

## ✔ Listado del directorio (`readdir`)
Devuelve todos los archivos almacenados en el directorio raíz de FiUnamFS.  
Soporta:

- `.`
- `..`
- todos los nombres válidos encontrados en las entradas del directorio

Es lo que permite:

```
ls mount/
```

---

## ✔ Apertura de archivos (`open`)
Verifica únicamente que el archivo exista.  
FiUnamFS no soporta manejadores complejos, por lo que FUSE solo confirma la entrada.

---

## ✔ Lectura parcial de archivos (`read`)
Convierte una llamada de lectura del kernel en una lectura real dentro de la imagen:

- Localiza el archivo en el directorio  
- Calcula el offset exacto dentro del cluster  
- Extrae los bytes solicitados  
- Actualiza estadísticas del estado  

---

## ✔ Creación de archivos (`create`)
Como FiUnamFS no soporta creación directa, el adaptador:

1. genera un archivo temporal vacío en `/tmp`  
2. lo inserta en la imagen usando `copiar_hacia()`  

Esto permite:

```
touch mount/nuevo.txt
```

---

## ✔ Escritura con sobrescritura total (`write`)
FiUnamFS no permite escritura parcial.  
Para resolverlo, el adaptador:

- carga el archivo completo a un buffer  
- permite modificaciones parciales sobre el buffer  
- no escribe nada inmediatamente  
- guarda todo al cerrar el archivo  

Esto permite:

```
nano mount/notas.txt
echo "mensaje" > mount/texto.txt
```

---

## ✔ Confirmación de escritura (`release`)
Cuando el archivo se cierra:

- el buffer se guarda como archivo temporal  
- se sobrescribe la entrada en la imagen usando `copiar_hacia()`  
- se actualizan los registros del estado  

---

## ✔ Eliminación de archivos (`unlink`)
Llama directamente a `eliminar()` en `fiunamfs.py` y marca la entrada como libre.  
Permite:

```
rm mount/archivo.txt
```

---

# 📌 ¿Cómo funciona internamente?

FiUnamFS FUSE:

- lee el directorio real desde la imagen  
- interpreta cada entrada con su nombre, tamaño y fechas  
- calcula posiciones en clusters  
- traduce operaciones POSIX a funciones propias del sistema  
- utiliza locks para evitar corrupción con accesos simultáneos  
- mantiene buffers de escritura para simular escritura por partes  

Aunque para el usuario parece un filesystem normal, cada operación es traducida hacia la estructura rígida y simple de FiUnamFS.

---

# 🖥️ Uso del Adaptador

### 1. Crear punto de montaje
```
mkdir mount
```

### 2. Montar la imagen
```
python3 fiunamfs_fuse.py fiunamfs.img mount
```

### 3. Interactuar libremente
```
ls mount/
echo "hola" > mount/hola.txt
cat mount/hola.txt
rm mount/hola.txt
```

### 4. Desmontar
```
fusermount -u mount
```

---

# 📚 Archivo Principal: fiunamfs_fuse.py

Contiene:

- clase `FiUnamFSFuse`  
- implementación de operaciones FUSE:  
  `getattr`, `readdir`, `read`, `write`, `create`, `unlink`, `release`  
- integración directa con `fiunamfs.py`  
- buffers de escritura para simular edición parcial  
- manejo de errores `ENOENT`  
- uso de locks para proteger operaciones críticas  

Es la pieza clave que transforma la imagen FiUnamFS en un sistema montable.

---

# 🛠️ Requisitos

### Python 3.x  
### fusepy  
### FUSE instalado en el sistema

Instalación:

```
sudo apt install fuse
pip install fusepy
```

