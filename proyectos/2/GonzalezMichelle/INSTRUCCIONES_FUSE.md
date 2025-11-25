# Instrucciones de Uso - Módulo FUSE

## Instalación de Dependencias

```bash
# Instalar fusepy (ya instalado en el sistema)
pip3 install fusepy --break-system-packages

# O si prefieres usar el paquete del sistema
sudo apt install python3-fusepy
```

## Uso Básico

### IMPORTANTE: Permisos del Punto de Montaje

⚠️ **Para montar sin sudo, usa un directorio en tu home** donde tengas permisos de escritura:

```bash
# ✓ CORRECTO - Usar directorio en home
mkdir -p ~/mnt/fiunamfs
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img ~/mnt/fiunamfs

# ✗ INCORRECTO - /mnt requiere permisos de root
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img /mnt/fiunamfs  # Error: sin permisos
```

### Montar el Filesystem

```bash
# En segundo plano (recomendado para uso normal)
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img ~/mnt/fiunamfs

# En primer plano (para ver logs y debugging)
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img ~/mnt/fiunamfs -f

# Con debug habilitado
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img ~/mnt/fiunamfs -f -d
```

### Usar el Filesystem Montado

```bash
# Listar archivos
ls -lh ~/mnt/fiunamfs/

# Leer archivos
cat ~/mnt/fiunamfs/README.org
head ~/mnt/fiunamfs/logo.png

# Crear archivos
echo "Contenido" > ~/mnt/fiunamfs/nuevo.txt
touch ~/mnt/fiunamfs/vacio.txt

# Copiar archivos fuera del filesystem
cp ~/mnt/fiunamfs/logo.png ~/Descargas/

# Eliminar archivos
rm ~/mnt/fiunamfs/archivo.txt

# Ver espacio disponible
df -h ~/mnt/fiunamfs/
```

### Desmontar el Filesystem

```bash
# Desmontar
fusermount -u ~/mnt/fiunamfs

# O con umount (si fusermount no funciona)
umount ~/mnt/fiunamfs
```

## Ejemplos Completos

### Ejemplo 1: Backup de todos los archivos

```bash
# Montar filesystem
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img ~/mnt/fiunamfs

# Crear directorio de backup
mkdir -p ~/backup_fiunamfs

# Copiar todos los archivos
cp ~/mnt/fiunamfs/* ~/backup_fiunamfs/

# Verificar
ls -lh ~/backup_fiunamfs/

# Desmontar
fusermount -u ~/mnt/fiunamfs
```

### Ejemplo 2: Agregar múltiples archivos

```bash
# Montar filesystem
python3 mount_fiunamfs.py fiunamfs/fiunamfs.img ~/mnt/fiunamfs

# Crear archivos de prueba
echo "Archivo 1" > ~/mnt/fiunamfs/file1.txt
echo "Archivo 2" > ~/mnt/fiunamfs/file2.txt
echo "Archivo 3" > ~/mnt/fiunamfs/file3.txt

# Verificar que se agregaron
ls ~/mnt/fiunamfs/

# Desmontar
fusermount -u ~/mnt/fiunamfs
```

## Limitaciones Conocidas

1. **Nombres de archivo**: Máximo 14 caracteres ASCII
2. **Tamaño máximo por archivo**: 1,469,440 bytes (~1.4 MB)
3. **Número máximo de archivos**: 64 archivos
4. **Escritura parcial no soportada**: Al escribir un archivo se reemplaza completamente
5. **Permisos**: Se requiere acceso de escritura al punto de montaje

## Solución de Problemas

### Error: "No such file or directory" al montar
- **Causa**: El archivo .img no existe o la ruta es incorrecta
- **Solución**: Verifica que `fiunamfs/fiunamfs.img` existe

### Error: "user has no write access to mountpoint"
- **Causa**: No tienes permisos de escritura en el punto de montaje
- **Solución**: Usa un directorio en tu home (ej: `~/mnt/fiunamfs`)

### Error: "Transport endpoint is not connected"
- **Causa**: El filesystem se desmontó incorrectamente
- **Solución**: `fusermount -u ~/mnt/fiunamfs` y vuelve a montar

### Error: "No space left on device" al crear archivos
- **Causa**: El directorio está lleno (64 archivos) o no hay clusters contiguos
- **Solución**: Elimina algunos archivos con `rm`

## Comparación: CLI vs FUSE

| Operación | CLI | FUSE |
|-----------|-----|------|
| Listar | `python3 src/fiunamfs_manager.py list fiunamfs.img` | `ls ~/mnt/fiunamfs/` |
| Exportar | `python3 src/fiunamfs_manager.py export fiunamfs.img archivo.txt /tmp/` | `cp ~/mnt/fiunamfs/archivo.txt /tmp/` |
| Importar | `python3 src/fiunamfs_manager.py import fiunamfs.img /tmp/file.txt` | `cp /tmp/file.txt ~/mnt/fiunamfs/` |
| Eliminar | `python3 src/fiunamfs_manager.py delete fiunamfs.img archivo.txt` | `rm ~/mnt/fiunamfs/archivo.txt` |

**Ventaja de FUSE**: Usar comandos nativos del sistema operativo (ls, cp, rm, cat, etc.)
