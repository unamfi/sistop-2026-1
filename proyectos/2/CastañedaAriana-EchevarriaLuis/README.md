# Micro-sistema de Archivos: FiUnamFS (v26-1)

## Información del Proyecto
* **Autores:** Castañeda González Michelle Ariana y Echevarria Aguilar Luis Angel 
* **Materia:** Sistemas Operativos
* **Semestre:** 2026-1
* **Proyecto:** Manipulador de Sistema de Archivos FIUnamFS

## Descripción
Este proyecto implementa un controlador completo para el sistema de archivos **FiUnamFS** (versión 26-1). El software permite manipular imágenes de disco (`.img`) que simulan un diskette de 1.44 MB, realizando operaciones de lectura, escritura y eliminación de archivos de manera segura y concurrente.  
El objetivo es administrar el almacenamiento simulado respetando la especificación de diseño (Superbloque, Directorio plano, Clusters de 512x2 bytes, formato Little Endian).

El proyecto consta de dos componentes principales:
1.  **Backend CLI (`fiunamfs.py`):** Núcleo lógico robusto basado en Clases (OOP) que maneja la interacción a nivel de bytes con el disco.
2.  **Frontend GUI (`interfaz_fiunamfs.py`):** Una interfaz gráfica moderna desarrollada en Tkinter que facilita la gestión visual del disco.

---

## Entorno y Dependencias
El proyecto fue desarrollado bajo el siguiente entorno. No requiere instalación de bibliotecas de terceros (PyPI/pip), utiliza solo la biblioteca estándar de Python.

* **Lenguaje:** Python 3.x (Probado en 3.10+)
* **Bibliotecas Estándar:** `os`, `struct`, `math`, `datetime`, `threading`, `queue`, `tkinter`.

### Nota para Usuarios de Linux (Fedora/Ubuntu)
La interfaz gráfica requiere el módulo `tkinter`. Si obtienes un error `ModuleNotFoundError`, instálalo con:
* **Fedora:** `sudo dnf install python3-tkinter`
* **Ubuntu/Debian:** `sudo apt-get install python3-tk`

---

## Estrategia de Desarrollo y Arquitectura

### Arquitectura Orientada a Objetos (OOP)
Se refactorizó el código base a una arquitectura de clases para mejorar la modularidad y cumplir con el principio de encapsulamiento:
* **Clase `FiUnamFS`:** Actúa como el "Driver" del sistema de archivos. Mantiene el estado del disco, valida versiones y gestiona el bloqueo de recursos.
* **Separación de Responsabilidades:** La lógica de negocio (Backend) está totalmente desacoplada de la presentación (CLI/GUI).

### Sincronización y Concurrencia
Para garantizar la integridad de los datos y una interfaz fluida, se implementó el patrón **Productor-Consumidor**:

1.  **Hilo Principal (UI):** Recibe la instrucción del usuario y la coloca en una cola (`queue.Queue`). No se bloquea.
2.  **Hilo Trabajador (Worker Daemon):** Un hilo en segundo plano consume las tareas de la cola y ejecuta las operaciones pesadas de E/S.
3.  **Exclusión Mutua (`threading.Lock`):** Se implementó un cerrojo global (`self.lock`) dentro de la clase `FiUnamFS`. Esto asegura que, aunque existan múltiples hilos, solo uno pueda escribir o mover el puntero del archivo `.img` a la vez, previniendo condiciones de carrera y corrupción de datos.

---

## Limitaciones Conocidas: Capacidad y Fragmentación
Es posible que al intentar copiar múltiples archivos (ej. más de 4 o 5), el sistema reporte **"Espacio insuficiente"** o **"No hay espacio contiguo"**, aun cuando parezca haber espacio libre. Esto **no es un error del programa**, sino una restricción del diseño del FiUnamFS simulado:

1.  **Capacidad Real (Diskette):** El sistema simula un Floppy Disk de **1,440 KB** (1.4 MB). Una sola foto moderna de celular (2-3 MB) **no cabe**. Archivos de imagen pequeños (~300 KB) llenarán el disco con solo 4 archivos ($300 \times 4 = 1200$ KB).
2.  **Asignación Contigua:** La especificación exige asignación contigua. Si borras un archivo en medio del disco, se crea un "hueco". Si intentas meter un archivo nuevo que es más grande que ese hueco, no cabrá ahí, y si no hay espacio al final, la operación fallará por **Fragmentación Externa**.

---

## Instrucciones de Ejecución

### 1. Interfaz Gráfica (Recomendado)
Ofrece una experiencia visual completa con tabla de archivos, barra de estado y validación automática.
```bash
python interfaz_fiunamfs.py
```
### 2. Línea de Comandos (CLI)
Para usuarios avanzados o scripts de automatización.

```bash
# Sintaxis General
python fiunamfs.py [COMANDO] [ARGUMENTOS]
```
#### Comandos Disponibles:

* **Información del Disco (`info`):**
  Muestra los metadatos del superbloque (versión, etiqueta, tamaño de clúster y totales).
  ```bash
  python fiunamfs.py info disco.img
  ```
* **Listar Contenido (`list`):**
  Muestra los archivos activos en el directorio, ocultando las entradas vacías o borradas.
  ```bash
  python fiunamfs.py list disco.img
  ```
* **Copiar AL disco (`copyin`):**
  Importa un archivo de tu computadora hacia el sistema FiUnamFS.   
  Sintaxis: `copyin [imagen] [ruta_origen] [nombre_destino]`
  ```bash
  python fiunamfs.py copyin disco.img archivo_local.txt nombre_en_disco.txt
  ```
* **Copiar DEL disco (`copyout`):**
  Extrae un archivo del FiUnamFS y lo guarda en tu computadora.   
  Sintaxis: `copyout [imagen] [nombre_interno] [ruta_salida]`
  ```bash
  python fiunamfs.py copyout disco.img nombre_interno.txt ./archivo_recuperado.txt
  ```
* **Eliminar Archivo (`delete`):**
  Marca un archivo como borrado en el directorio y libera su entrada.  
  Sintaxis: `delete [imagen] [nombre_archivo`
  ```bash
  python fiunamfs.py delete disco.img archivo_a_borrar.txt
  ```
* **Reparar Versión (`makecopy26`):**
  Herramienta de mantenimiento que crea una copia de una imagen (posiblemente dañada o de versión incorrecta) y fuerza la versión 26-1 en el superbloque para hacerla compatible con el sistema.  
  Sintaxis: `makecopy26 [imagen_origen] [imagen_destino]`
  ```bash
  python fiunamfs.py makecopy26 imagen_vieja.img imagen_reparada.img
  ```
* **Auto-Test (`selftest`):**
  Ejecuta una suite de pruebas integral automática: genera un disco temporal, escribe archivos, los lee y los borra para verificar que la lógica del sistema funcione correctamente sin afectar tus archivos reales.  

  ```bash
  python fiunamfs.py selftest
  ```
### Nota importante sobre selftest:

El comando no está disponible en la interfaz del sistema de archivos (no aparece en la salida del comando help o menús).
Solo puede ejecutarse directamente desde el archivo `fiunamfs.py` mediante terminal.

Es decir:  
✔ Sí funciona en terminal.  
✘ No aparece como opción visible dentro de la interfaz del programa.

## Estructura del Proyecto
```text
.
├── fiunamfs.py           # Backend: Lógica del Sistema de Archivos (Clases y CLI)
├── interfaz_fiunamfs.py  # Frontend: Interfaz Gráfica de Usuario (Tkinter)
├── README.md             # Documentación del proyecto
└── .gitignore            # Configuración de exclusión para Git

