#@author: Jose Eduardo Martinez Garcia
#@date: 20/11/25

#importamos blibliotecas que se usan en el codigo
import os
import sys
import struct
import errno
import threading
from datetime import datetime



# 1. GUI (Tkinter)
GUI_AVAILABLE = False
try:
    import tkinter as tk
    from tkinter import messagebox, filedialog, simpledialog, scrolledtext
    GUI_AVAILABLE = True # Marcamos que sí hay interfaz gráfica en el codigo
except ImportError:
    pass

# 2. SECCION FUSE 
try:
    from fuse import FUSE, FuseOSError, Operations
    FUSE_AVAILABLE = True # Marcamos que sí hay FUSE
except ImportError:
    FUSE_AVAILABLE = False
    # Definimos Operations como una clase vacía para que no salga NameError si falta la librería
    class Operations: pass
    class FuseOSError(Exception): pass
    def FUSE(*args, **kwargs): pass

# ==========================================
# CONFIGURACION
# ==========================================
RUTA_DISK = "fiunamfs.img"
VER_REQ = "26-1" 
NOM_REQ = "FiUnamFS"

# ==========================================
# CLASE DRIVER: Lógica del Disco
# ==========================================
class FiUnamFS_Driver:
    def __init__(self, disk_path):
        self.disk_path = disk_path
        # >>> SINCRONIZACIÓN <<<
        self.lock = threading.Lock()
        
        if not os.path.exists(disk_path):
            print(f"[!] Error: No encuentro el archivo :({disk_path}")
        else:
            self.validar_superbloque()

    def validar_superbloque(self):
        # Usamos 'with self.lock' para adquirir el candado antes de leer
        with self.lock, open(self.disk_path, 'rb') as f:
            f.seek(0) # Nos vamos al inicio del disco (Cluster 0)
            data = f.read(1024) # Leemos el superbloque completo
            
            # Extraemos y limpiamos el nombre y la versión
            nombre = data[0:8].decode('ascii', errors='ignore').strip('\x00')
            version = data[10:15].decode('ascii', errors='ignore').strip('\x00')
            
            if nombre != NOM_REQ or version != VER_REQ:
                raise Exception(f"Versión incorrecta: {version} (Se requiere {VER_REQ})")
            print(f"[Ok] Disco cargado: {nombre} v{version}")

    def obtener_entradas(self):
        entradas = []
        with self.lock, open(self.disk_path, 'rb') as f:
            f.seek(1024) # El directorio inicia en el byte 1024
            
            # Recorremos las 64 entradas posibles
            for i in range(64): 
                raw = f.read(64) # Cada entrada mide 64 bytes
                if raw[0:1] == b'.': # Si el primer byte es '.', es un archivo activo
                    nombre = raw[1:16].decode('ascii', errors='ignore').strip('\x00').strip()
                    
               
                    cluster_ini = struct.unpack('<I', raw[16:20])[0]
                    tamano = struct.unpack('<I', raw[20:24])[0]
                    
                    # Leemos las fechas (cadenas de 14 bytes)
                    creacion = raw[24:38].decode('ascii', errors='ignore')
                    modif = raw[38:52].decode('ascii', errors='ignore')
                    
                    entradas.append({
                        'nombre': nombre, 'tamano': tamano,
                        'cluster_ini': cluster_ini, 'index': i,
                        'creacion': creacion, 'modificacion': modif
                    })
        return entradas

    def leer_archivo(self, nombre, offset=0, size=-1):
        entradas = self.obtener_entradas()
        target = next((e for e in entradas if e['nombre'] == nombre), None)
        if not target: raise FileNotFoundError("Archivo no encontrado")
        
        if size == -1: size = target['tamano']
        addr = target['cluster_ini'] * 1024 # Dirección física: Cluster * 1024
        
        with self.lock, open(self.disk_path, 'rb') as f:
            f.seek(addr + offset)
            return f.read(min(size, target['tamano'] - offset))

    def guardar_archivo(self, nombre, contenido):
        entradas = self.obtener_entradas()
        if any(e['nombre'] == nombre for e in entradas):
            raise FileExistsError("El archivo ya existe")

        idx_libre = -1
        with self.lock, open(self.disk_path, 'r+b') as f:
            # 1. Buscar hueco en directorio ('-' o null)
            f.seek(1024)
            for i in range(64):
                if f.read(64)[0:1] in [b'-', b'\x00']:
                    idx_libre = i
                    break
            if idx_libre == -1: raise Exception("Directorio lleno")

            # 2. Asignación contigua: Buscar el cluster más alto ocupado
            max_cluster = 4 
            for e in entradas:
                clusters_ocu = (e['tamano'] // 1024) + (1 if e['tamano'] % 1024 > 0 else 0)
                fin = e['cluster_ini'] + clusters_ocu
                if fin > max_cluster: max_cluster = fin
            
            nuevo_ini = max_cluster + 1 if max_cluster > 4 else 5
            
            # 3. escribir datos
            f.seek(nuevo_ini * 1024)
            f.write(contenido)
            
            # 4. Escribir metadatos en directorio
            f.seek(1024 + (idx_libre * 64))
            
            buf = b'.' + nombre.encode('ascii').ljust(15, b'\x00') # Tipo + Nombre
            buf += struct.pack('<I', nuevo_ini)     # Offset 16: Cluster
            buf += struct.pack('<I', len(contenido))# Offset 20: Tamaño
            
            fecha = datetime.now().strftime('%Y%m%d%H%M%S').encode('ascii')
            buf += fecha #   creacion
            buf += fecha # Modificacion
            
            f.write(buf.ljust(64, b'\x00')) # Relleno final

    def borrar_archivo(self, nombre):
        entradas = self.obtener_entradas()
        target = next((e for e in entradas if e['nombre'] == nombre), None)
        if not target: raise FileNotFoundError("No existe")
        
        with self.lock, open(self.disk_path, 'r+b') as f:
            f.seek(1024 + (target['index'] * 64))
            f.write(b'-' + b'.' * 15) # Marca de borrado

# ==========================================
# CLASE FUSE: Puente con Linux (implemenaciones de FUSE requeridas) :)
# ==========================================
class FiUnamFS_FUSE(Operations):
    def __init__(self, driver):
        self.driver = driver

    def getattr(self, path, fh=None):
        if path == '/':
            return {'st_mode': (0o040000 | 0o755), 'st_nlink': 2}
        
        nom = path.lstrip("/")
        item = next((e for e in self.driver.obtener_entradas() if e['nombre'] == nom), None)
        if item:
            return {
                'st_mode': (0o0100000 | 0o644),
                'st_size': item['tamano'], 'st_nlink': 1,
                'st_atime': datetime.now().timestamp(),
                'st_mtime': datetime.now().timestamp(),
                'st_ctime': datetime.now().timestamp()
            }
        raise FuseOSError(errno.ENOENT)

    def readdir(self, path, fh):
        lista = ['.', '..']
        if path == '/':
            lista.extend([e['nombre'] for e in self.driver.obtener_entradas()])
        return lista

    def read(self, path, size, offset, fh):
        return self.driver.leer_archivo(path.lstrip("/"), offset, size)

    def create(self, path, mode, fi=None):
        self.driver.guardar_archivo(path.lstrip("/"), b"")
        return 0

    def write(self, path, buf, offset, fh):
        nom = path.lstrip("/")
        if offset == 0: 
            try: self.driver.borrar_archivo(nom)
            except: pass
            self.driver.guardar_archivo(nom, buf)
        return len(buf)

    def unlink(self, path):
        self.driver.borrar_archivo(path.lstrip("/"))

# ==========================================
# INTERFAZ GRÁFICA (Tkinter) 
# ==========================================
def iniciar_gui(driver):
    if not GUI_AVAILABLE:
        print("\n[ERROR] Tkinter no disponible. Instala python3-tk") #Tuve problemas para implementarlo y esta parte del codigo que encontre me sirvio
        return

    root = tk.Tk()
    root.title("FiUnamFS 2026-1 - Manejador/admin")
    root.geometry("750x450")
    
    txt = scrolledtext.ScrolledText(root, height=15)
    txt.pack(pady=10, padx=10, fill=tk.BOTH)

    def update_list():
        txt.delete(1.0, tk.END)
        try:
            ents = driver.obtener_entradas()
            # Mostramos fecha de modificación en la lista
            header = f"{'NOMBRE':<16}|{'SIZE':<8}|{'CLUSTER':<8}|{'CREACION':<16}|{'MODIFICACION'}\n"
            txt.insert(tk.END, header + "-"*70 + "\n")
            for e in ents:
                row = f"{e['nombre']:<16}|{e['tamano']:<8}|{e['cluster_ini']:<8}|{e['creacion']:<16}|{e['modificacion']}\n"
                txt.insert(tk.END, row)
        except Exception as e: messagebox.showerror("Error", str(e))

    # >>> IMPLEMENTACIÓN DE HILOS CONCURRENTES <<<
    # Aquí cumplimos el requisito de "al menos dos hilos operando concurrentemente".
    def copy_out():
        nom = simpledialog.askstring("Exportar", "Nombre en FS:")
        dest = filedialog.askdirectory()
        if nom and dest:
            # creamos un nuevo Hilo (Thread) para la copia.
            # El hilo principal (GUI) sigue respondiendo mientras este hilo trabja.
            threading.Thread(target=lambda: _safe_copy(nom, dest)).start()

    def _safe_copy(n, d):
        try:
            # este proceso corre en paralelo al hilo principal
            data = driver.leer_archivo(n)
            with open(os.path.join(d, n), 'wb') as f: f.write(data)
            messagebox.showinfo("Info", "se copio al dispositivo correctamente correctamente")
        except Exception as e: messagebox.showerror("Error", str(e))

    def copy_in():
        ruta = filedialog.askopenfilename()
        if ruta:
            nom = os.path.basename(ruta)[:14]
            try:
                with open(ruta, 'rb') as f: content = f.read()
                driver.guardar_archivo(nom, content)
                update_list()
                messagebox.showinfo("Info", "se copio al fiunamfs correctamente")
            except Exception as e: messagebox.showerror("Error", str(e))
            
    def delete():
        nom = simpledialog.askstring("Eliminar", "Nombre archivo:")
        if nom:
            try:
                driver.borrar_archivo(nom)
                update_list()
                messagebox.showinfo("Info", "Eliminado")
            except Exception as e: messagebox.showerror("Error", str(e))

    # Botonera de opciones para modificar y agregar archivos en fiunam
    fr = tk.Frame(root)
    fr.pack(pady=5)
    tk.Button(fr, text="Refrescar", command=update_list).pack(side=tk.LEFT, padx=5)
    tk.Button(fr, text="Copiar de dispositivo a fiunamfs", command=copy_in).pack(side=tk.LEFT, padx=5)
    tk.Button(fr, text="Copiar de fiunamfs a dispositivo", command=copy_out).pack(side=tk.LEFT, padx=5)
    tk.Button(fr, text="Eliminar de fiunam", command=delete, bg="#636161").pack(side=tk.LEFT, padx=5)
    
    update_list()
    root.mainloop()

# ==========================================
#MAIN
# ==========================================

def main():
    print("Sistema iniciado.")
    try:
        drv = FiUnamFS_Driver(RUTA_DISK)
    except Exception as e:
        print(f"Error crítico: {e}")
        return

    if len(sys.argv) > 1:
        mnt = sys.argv[1]
        if FUSE_AVAILABLE:
            print(f">>>> MODO FUSE: {mnt} <<<<")
            try:
                FUSE(FiUnamFS_FUSE(drv), mnt, foreground=True, allow_other=True)
            except Exception as e: print(f"Error FUSE: {e}")
        else:
            print("[!] Falta 'fusepy'. Iniciando GUI...")
            iniciar_gui(drv)
    else:
        print(">>>> MODO GUI <<<<")
        iniciar_gui(drv)

if __name__ == "__main__":
    main()