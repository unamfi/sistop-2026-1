import math
import os
import struct
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# Constantes
CLUSTER_SIZE = 1024
TOTAL_CLUSTERS = 1440
DIR_CLUSTER_START = 1
DIR_CLUSTER_END = 4
ENTRIES_PER_CLUSTER = CLUSTER_SIZE // 64
ENTRY_SIZE = 64

ENTRY_STRUCT = struct.Struct("<c15sII14s14s12x")
# Variable global 
VCListFiles = threading.Condition() # ayuda para que hilos de la gui avisen cambios

class FiUnamFS:
    def __init__(self, disk_path):
        self.disk = disk_path
        self.lock = threading.Lock()  # Mutex para operaciones concurrentes
        self.archivos = None
        
        if not os.path.exists(self.disk):
            raise FileNotFoundError(f"No existe imagen: {self.disk}")
    
    def leer_superbloque(self):
        """Lee y valida el superbloque"""
        with open(self.disk, "rb") as f:
            f.seek(0)
            raw = f.read(54)
            
            nombre = raw[0:9].decode("ascii", errors="ignore").strip("\x00")
            version = raw[10:15].decode("ascii", errors="ignore").strip("\x00")
            etiqueta = raw[20:36].decode("ascii", errors="ignore").strip("\x00")
            tam_cluster = struct.unpack("<I", raw[40:44])[0]
            dir_clusters = struct.unpack("<I", raw[45:49])[0]
            total_clusters = struct.unpack("<I", raw[50:54])[0]
            
            if nombre != "FiUnamFS":
                raise ValueError(f"No es FiUnamFS")
            
            if version != "26-1":
                print(f"[ADVERTENCIA] Versión: {version}")
            
            return {
                "Nombre": nombre,
                "Version": version,
                "Etiqueta": etiqueta,
                "Tamano_Cluster": tam_cluster,
                "Clusters_Directorio": dir_clusters,
                "Total_Clusters": total_clusters,
            }
    
    def enlistar_directorio(self, mostrar_vacias=False):
        """Enlista todas las entradas del directorio"""
        archivos = []
        
        with open(self.disk, "rb") as f:
            for cl in range(DIR_CLUSTER_START, DIR_CLUSTER_END + 1):
                f.seek(cl * CLUSTER_SIZE)
                
                for entry_index in range(ENTRIES_PER_CLUSTER):
                    entry_pos = cl * CLUSTER_SIZE + entry_index * ENTRY_SIZE
                    f.seek(entry_pos)
                    entry = f.read(ENTRY_SIZE)
                    
                    if len(entry) < ENTRY_SIZE:
                        continue
                    
                    try:
                        tipo_b, nombre_b, cluster, tam, creado_b, modif_b = \
                            ENTRY_STRUCT.unpack(entry)
                    except struct.error:
                        continue
                    
                    tipo = tipo_b.decode("ascii", errors="ignore")
                    nombre = nombre_b.decode("ascii", errors="ignore") \
                                   .rstrip("\x00").strip()
                    creado = creado_b.decode("ascii", errors="ignore").strip("\x00")
                    modif = modif_b.decode("ascii", errors="ignore").strip("\x00")
                    
                    es_vacia = (tipo == "-" or nombre == "" or 
                               nombre.replace(".", "") == "")
                    
                    if not mostrar_vacias and es_vacia:
                        continue
                    
                    archivos.append({
                        "Nombre": nombre if nombre else "..............",
                        "Tamaño": tam,
                        "Cluster": cluster,
                        "Creado": creado,
                        "Modificado": modif,
                        "entry_pos": entry_pos,
                        "es_vacia": es_vacia,
                    })
        
        self.archivos = [a for a in archivos if not a.get("es_vacia", False)]
        return archivos
    
    def hay_hueco_contiguo(self, tamaño):
        """Busca espacio contiguo libre"""
        clusters_necesarios = math.ceil(tamaño / CLUSTER_SIZE) if tamaño > 0 else 1
        
        with open(self.disk, "rb") as f:
            cont = 0
            inicio = None
            
            for c in range(DIR_CLUSTER_END + 1, TOTAL_CLUSTERS):
                f.seek(c * CLUSTER_SIZE)
                data = f.read(CLUSTER_SIZE)
                
                if len(data) < CLUSTER_SIZE:
                    return None
                
                # Cluster libre = todos bytes en cero
                if all(b == 0 for b in data):
                    if cont == 0:
                        inicio = c
                    cont += 1
                    
                    if cont >= clusters_necesarios:
                        return inicio
                else:
                    cont = 0
                    inicio = None
        
        return None
    
    def copiar_desde(self, nombre_archivo, destino):
        """Copia archivo desde FiUnamFS al host"""
        with self.lock:
            if self.archivos is None:
                self.enlistar_directorio()
        
        archivo = next((a for a in self.archivos 
                       if a["Nombre"] == nombre_archivo), None)
        if not archivo:
            raise FileNotFoundError(f"'{nombre_archivo}' no encontrado")
        
        cluster = archivo["Cluster"]
        tamaño = archivo["Tamaño"]
        offset = cluster * CLUSTER_SIZE
        
        with open(self.disk, "rb") as f:
            f.seek(offset)
            datos = f.read(tamaño)
        
        if os.path.isdir(destino):
            destino_path = os.path.join(destino, nombre_archivo)
        else:
            destino_path = destino
        
        with open(destino_path, "wb") as out:
            out.write(datos)
        
        return destino_path
    
    def copiar_hacia(self, ruta_local):
        """Copia archivo del host hacia FiUnamFS"""
        if not os.path.exists(ruta_local):
            raise FileNotFoundError(f"Archivo local no existe: {ruta_local}")
        
        nombre_base = os.path.basename(ruta_local)
        
        try:
            nombre_base.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("El nombre contiene caracteres no-ASCII")
        
        if len(nombre_base) > 14:
            raise ValueError(f"Nombre muy largo (max 14): {nombre_base}")
        
        with self.lock:
            if self.archivos is None:
                self.enlistar_directorio()
            
            if any(a["Nombre"] == nombre_base for a in (self.archivos or [])):
                raise ValueError(f"Ya existe: '{nombre_base}'")
            
            tamaño = os.path.getsize(ruta_local)
            clusters_nec = math.ceil(tamaño / CLUSTER_SIZE) if tamaño > 0 else 1
            
            inicio = self.hay_hueco_contiguo(tamaño)
            if inicio is None:
                raise RuntimeError(f"No hay espacio para {clusters_nec} clusters")
            
            pos_entrada = None
            
            with open(self.disk, "r+b") as f:
                for cl in range(DIR_CLUSTER_START, DIR_CLUSTER_END + 1):
                    for idx in range(ENTRIES_PER_CLUSTER):
                        entry_pos = cl * CLUSTER_SIZE + idx * ENTRY_SIZE
                        f.seek(entry_pos)
                        entry = f.read(ENTRY_SIZE)
                        
                        tipo_b, nombre_b, *_ = ENTRY_STRUCT.unpack(entry)
                        tipo = tipo_b.decode("ascii", errors="ignore")
                        nombre_slot = nombre_b.decode("ascii", errors="ignore") \
                                            .rstrip("\x00").strip()
                        
                        if (tipo == "-" or nombre_slot == "" or 
                            nombre_slot.replace(".", "") == ""):
                            pos_entrada = entry_pos
                            break
                    
                    if pos_entrada is not None:
                        break
                
                if pos_entrada is None:
                    raise RuntimeError("No hay entradas libres en directorio")
                
                tipo_byte = b"."
                nombre_bytes = nombre_base.encode("ascii").ljust(15, b"\x00")
                ahora = datetime.now().strftime("%Y%m%d%H%M%S")
                creado = ahora.encode("ascii")
                modif = creado
                
                f.seek(pos_entrada)
                f.write(ENTRY_STRUCT.pack(
                    tipo_byte, nombre_bytes, inicio, tamaño, creado, modif
                ))
                
                with open(ruta_local, "rb") as src:
                    for i in range(clusters_nec):
                        chunk = src.read(CLUSTER_SIZE)
                        if not chunk:
                            chunk = b""
                        
                        if len(chunk) < CLUSTER_SIZE:
                            chunk = chunk + b"\x00" * (CLUSTER_SIZE - len(chunk))
                        
                        f.seek((inicio + i) * CLUSTER_SIZE)
                        f.write(chunk)
        
        self.archivos = None
        with VCListFiles:
            VCListFiles.notify_all()
    
    def eliminar(self, nombre):
        """Elimina un archivo del sistema"""
        with self.lock:
            if self.archivos is None:
                self.enlistar_directorio()
            
            archivo = next((a for a in self.archivos 
                           if a["Nombre"] == nombre), None)
            
            if not archivo:
                raise FileNotFoundError(f"'{nombre}' no encontrado")
            
            entry_pos = archivo.get("entry_pos")
            
            tipo_byte = b"-"
            nombre_vacio = b"--------------".ljust(15, b"\x00")
            cero_fecha = b"00000000000000"
            
            with open(self.disk, "r+b") as f:
                f.seek(entry_pos)
                f.write(ENTRY_STRUCT.pack(
                    tipo_byte, nombre_vacio, 0, 0, cero_fecha, cero_fecha
                ))
                
                inicio = archivo["Cluster"]
                clusters_nec = math.ceil(archivo["Tamaño"] / CLUSTER_SIZE) \
                              if archivo["Tamaño"] > 0 else 1
                
                for c in range(inicio, inicio + clusters_nec):
                    if c < TOTAL_CLUSTERS:
                        f.seek(c * CLUSTER_SIZE)
                        f.write(b"\x00" * CLUSTER_SIZE)
        
        self.archivos = None
        with VCListFiles:
            VCListFiles.notify_all()


class FiUnamFSGUI:
    """Interfaz gráfica para FiUnamFS"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("FiUnamFS v26-2 - Sistema de Archivos")
        self.root.geometry("900x600")
        
        self.fs = None
        self.monitor_thread = None
        
        self.crear_widgets()
        self.abrir_disco()
    
    def crear_widgets(self):
        """Crea todos los componentes de la GUI"""
        # Panel de información
        info_frame = ttk.LabelFrame(
            self.root, text="Informacion del Sistema", padding=10
        )
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.info_label = ttk.Label(
            info_frame, text="Sistema no cargado", font=("Courier", 9)
        )
        self.info_label.pack()
        
        # Tabla de archivos
        table_frame = ttk.LabelFrame(
            self.root, text="Contenido del Directorio", padding=10
        )
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("nombre", "tamaño", "cluster", "creado", "modificado")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", 
            yscrollcommand=scrollbar.set
        )
        
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("tamaño", text="Tamaño")
        self.tree.heading("cluster", text="Cluster")
        self.tree.heading("creado", text="Creado")
        self.tree.heading("modificado", text="Modificado")
        
        self.tree.column("nombre", width=150)
        self.tree.column("tamaño", width=100, anchor=tk.E)
        self.tree.column("cluster", width=80, anchor=tk.E)
        self.tree.column("creado", width=180)
        self.tree.column("modificado", width=180)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Botones de acción
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Actualizar", 
                  command=self.actualizar_lista).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Copiar desde FS", 
                  command=self.copiar_desde_fs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Copiar hacia FS", 
                  command=self.copiar_hacia_fs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Eliminar", 
                  command=self.eliminar_archivo).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Ver Superbloque", 
                  command=self.mostrar_superbloque).pack(side=tk.LEFT, padx=5)
    
    def abrir_disco(self):
        """Carga la imagen del disco"""
        disk_path = os.path.join(os.path.dirname(__file__), "../fiunamfs.img")
        
        if not os.path.exists(disk_path):
            respuesta = messagebox.askyesno(
                "Disco no encontrado",
                "No se encontro 'fiunamfs.img' en el directorio actual.\n\n"
                "Desea seleccionar una imagen manualmente?"
            )
            if respuesta:
                disk_path = filedialog.askopenfilename(
                    title="Seleccionar imagen FiUnamFS",
                    filetypes=[("Imagenes de disco", "*.img"), ("Todos", "*.*")]
                )
                if not disk_path:
                    messagebox.showerror("Error", "No se selecciono ningun archivo")
                    self.root.quit()
                    return
            else:
                self.root.quit()
                return
        
        try:
            self.fs = FiUnamFS(disk_path)
            info = self.fs.leer_superbloque()
            
            self.info_label.config(
                text=f"{info['Nombre']} v{info['Version']} | "
                     f"Etiqueta: {info['Etiqueta']} | "
                     f"Clusters: {info['Total_Clusters']} | "
                     f"Tamano Cluster: {info['Tamano_Cluster']} bytes"
            )
            
            # Iniciar hilo monitor
            self.monitor_thread = threading.Thread(
                target=self.monitor_cambios, daemon=True
            )
            self.monitor_thread.start()
            
            self.actualizar_lista()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el disco:\n{e}")
            self.root.quit()
    
    def actualizar_lista(self):
        """Actualiza la tabla de archivos"""
        if not self.fs:
            return
        
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            archivos = self.fs.enlistar_directorio(mostrar_vacias=True)
            
            for a in archivos:
                if a.get("es_vacia", False):
                    self.tree.insert(
                        "", tk.END,
                        values=(a["Nombre"], a["Tamaño"], a["Cluster"],
                               a["Creado"], a["Modificado"]),
                        tags=("vacia",)
                    )
                else:
                    try:
                        creado = datetime.strptime(
                            a["Creado"], "%Y%m%d%H%M%S"
                        ).strftime("%Y-%m-%d %H:%M:%S")
                        modif = datetime.strptime(
                            a["Modificado"], "%Y%m%d%H%M%S"
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        creado = a["Creado"]
                        modif = a["Modificado"]
                    
                    self.tree.insert(
                        "", tk.END,
                        values=(a["Nombre"], f"{a['Tamaño']:,} bytes",
                               a["Cluster"], creado, modif)
                    )
            
            self.tree.tag_configure("vacia", foreground="gray")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo listar:\n{e}")
    
    def copiar_desde_fs(self):
        """Copia archivo desde FiUnamFS al host"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un archivo primero")
            return
        
        item = self.tree.item(seleccion[0])
        nombre = item["values"][0]
        
        if nombre.replace(".", "") == "":
            messagebox.showwarning("Advertencia", 
                                  "No puede copiar una entrada vacia")
            return
        
        destino = filedialog.askdirectory(title="Seleccionar destino")
        if not destino:
            return
        
        try:
            ruta_final = self.fs.copiar_desde(nombre, destino)
            messagebox.showinfo("Exito", f"Archivo copiado:\n{ruta_final}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar:\n{e}")
    
    def copiar_hacia_fs(self):
        """Copia archivo del host hacia FiUnamFS"""
        archivo = filedialog.askopenfilename(title="Seleccionar archivo")
        if not archivo:
            return
        
        try:
            self.fs.copiar_hacia(archivo)
            messagebox.showinfo(
                "Exito", 
                f"Archivo '{os.path.basename(archivo)}' copiado al sistema"
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar:\n{e}")
    
    def eliminar_archivo(self):
        """Elimina archivo del FiUnamFS"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un archivo primero")
            return
        
        item = self.tree.item(seleccion[0])
        nombre = item["values"][0]
        
        if nombre.replace(".", "") == "":
            messagebox.showwarning("Advertencia", 
                                  "No puede eliminar una entrada vacia")
            return
        
        confirmar = messagebox.askyesno(
            "Confirmar eliminacion", 
            f"Esta seguro de eliminar '{nombre}'?"
        )
        
        if not confirmar:
            return
        
        try:
            self.fs.eliminar(nombre)
            messagebox.showinfo("Exito", f"Archivo '{nombre}' eliminado")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")
    
    def mostrar_superbloque(self):
        """Muestra información del superbloque"""
        if not self.fs:
            return
        
        try:
            info = self.fs.leer_superbloque()
            texto = "\n".join([f"{k}: {v}" for k, v in info.items()])
            messagebox.showinfo("Informacion del Superbloque", texto)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer:\n{e}")
    
    def monitor_cambios(self):
        """Hilo que monitorea cambios y actualiza la GUI"""
        while True:
            with VCListFiles:
                VCListFiles.wait()
                self.root.after(100, self.actualizar_lista)


def main():
    root = tk.Tk()
    app = FiUnamFSGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()