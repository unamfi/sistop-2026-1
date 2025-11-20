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
