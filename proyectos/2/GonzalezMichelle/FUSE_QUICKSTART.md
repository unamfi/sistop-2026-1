# Guía Rápida: Usar FiUnamFS con FUSE

Esta guía te ayuda a montar FiUnamFS como un directorio nativo en tu sistema.

## Prerrequisitos

### Ubuntu/Debian
```bash
sudo apt-get install fuse3 libfuse3-dev
pip3 install fusepy
```

### Fedora/RHEL
```bash
sudo dnf install fuse3 fuse3-devel
pip3 install fusepy
```

### macOS
```bash
brew install macfuse
pip3 install fusepy
```

## Uso Básico

### 1. Crear punto de montaje
```bash
mkdir -p /mnt/fiunamfs
```

### 2. Montar el filesystem
```bash
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs
```

### 3. Usar comandos nativos

#### Listar archivos
```bash
ls -lh /mnt/fiunamfs
```

#### Leer un archivo
```bash
cat /mnt/fiunamfs/README.TXT
head -10 /mnt/fiunamfs/data.txt
```

#### Copiar desde FiUnamFS
```bash
cp /mnt/fiunamfs/archivo.txt ~/Descargas/
cp -r /mnt/fiunamfs/* ~/backup/
```

#### Copiar a FiUnamFS
```bash
cp ~/Documentos/informe.txt /mnt/fiunamfs/
echo "Hola Mundo" > /mnt/fiunamfs/saludo.txt
```

#### Eliminar archivos
```bash
rm /mnt/fiunamfs/archivo_viejo.txt
```

#### Ver estadísticas del filesystem
```bash
df -h /mnt/fiunamfs
du -sh /mnt/fiunamfs/*
```

### 4. Desmontar

**Linux:**
```bash
fusermount -u /mnt/fiunamfs
```

**macOS:**
```bash
umount /mnt/fiunamfs
```

## Modo Debug

Para ver qué está haciendo FUSE:
```bash
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs -f -d
```

Esto ejecuta en primer plano (`-f`) con debug habilitado (`-d`).
Presiona Ctrl+C para desmontar.

## Limitaciones

### 1. No modificación parcial
FiUnamFS usa asignación contigua, por lo que **no puedes editar archivos in-place**.

❌ No funciona:
```bash
echo "nueva línea" >> /mnt/fiunamfs/archivo.txt  # Append
sed -i 's/foo/bar/' /mnt/fiunamfs/archivo.txt     # Edición in-place
```

✅ Funciona:
```bash
# Sobrescribir completo
echo "contenido nuevo" > /mnt/fiunamfs/archivo.txt

# Copiar archivo completo
cp ~/nuevo_archivo.txt /mnt/fiunamfs/archivo.txt
```

### 2. Solo directorio raíz
FiUnamFS es plano, no soporta subdirectorios.

❌ No funciona:
```bash
mkdir /mnt/fiunamfs/carpeta
cp archivo.txt /mnt/fiunamfs/carpeta/
```

### 3. Nombres de 14 caracteres
Máximo 14 caracteres ASCII para nombres de archivo.

❌ No funciona:
```bash
cp archivo_con_nombre_muy_largo.txt /mnt/fiunamfs/  # 33 caracteres
```

✅ Funciona:
```bash
cp archivo_con_nombre_muy_largo.txt /mnt/fiunamfs/nombre.txt  # 10 caracteres
```

## Solución de Problemas

### Error: "fusepy no está instalado"
```bash
pip3 install fusepy
```

### Error: "Transport endpoint is not connected"
El directorio quedó en estado inconsistente. Desmonta:
```bash
fusermount -u /mnt/fiunamfs
```

### Error: "Directory not empty"
FUSE requiere un directorio vacío:
```bash
rm -rf /mnt/fiunamfs/*
# O usa otro directorio:
mkdir /tmp/fiunamfs_mount
```

### El filesystem no se desmonta
Verifica que no haya procesos usando el directorio:
```bash
lsof /mnt/fiunamfs
fuser -m /mnt/fiunamfs
```

Luego desmonta forzosamente:
```bash
fusermount -uz /mnt/fiunamfs  # -z = lazy unmount
```

## Comparación: CLI vs FUSE

| Operación | CLI | FUSE |
|-----------|-----|------|
| Listar archivos | `python3 src/fiunamfs_manager.py list fs.img` | `ls /mnt/fiunamfs` |
| Leer archivo | `python3 src/fiunamfs_manager.py export fs.img FILE out.txt` | `cat /mnt/fiunamfs/FILE` |
| Crear archivo | `python3 src/fiunamfs_manager.py import fs.img file.txt` | `cp file.txt /mnt/fiunamfs/` |
| Eliminar archivo | `python3 src/fiunamfs_manager.py delete fs.img FILE` | `rm /mnt/fiunamfs/FILE` |

**FUSE** es más cómodo para uso interactivo.
**CLI** es mejor para scripts y automatización.

## Ejemplos Avanzados

### Backup completo
```bash
# Montar filesystem
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs

# Hacer backup de todos los archivos
mkdir -p ~/backup_fiunamfs
cp -v /mnt/fiunamfs/* ~/backup_fiunamfs/

# Desmontar
fusermount -u /mnt/fiunamfs
```

### Buscar archivos
```bash
# Montar
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs

# Buscar archivos que contienen "ERROR"
grep -r "ERROR" /mnt/fiunamfs/

# Buscar archivos por nombre
find /mnt/fiunamfs/ -name "*.txt"

# Desmontar
fusermount -u /mnt/fiunamfs
```

### Importar múltiples archivos
```bash
# Montar
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs

# Copiar todos los .txt de una carpeta
cp ~/Documentos/*.txt /mnt/fiunamfs/

# Desmontar
fusermount -u /mnt/fiunamfs
```
