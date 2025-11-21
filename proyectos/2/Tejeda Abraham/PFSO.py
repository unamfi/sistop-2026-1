import os
import struct
import threading
import math
import tkinter as tk
import sys
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

FS_NAME = "FiUnamFS"
FS_VERSION = "26-1"


FILE_TYPE_USED = b'.'   
FILE_TYPE_FREE = b'-'   
EMPTY_NAME_PATTERN = b'..............' 

VCListFiles = threading.Condition()

class FiUnamFS:
    """
    Implementación del micro-sistema de archivos FiUnamFS.
    Se encarga de operar directamente sobre la imagen de disco.
    """

    SUPERBLOCK_STRUCT = struct.Struct('<9s1x5s5x16s4xI1xI1xI')
    DIR_ENTRY_STRUCT = struct.Struct('<c15sII14s14s12x')

    def __init__(self, disk_path: str) -> None:
        self.disk_path = disk_path
        self.lock = threading.Lock()
        self.archivos = []
        self.fs_name = None
        self.version = None
        self.volume_label = None
        self.cluster_size = None
        self.dir_clusters = None
        self.total_clusters = None
        self.dir_start_cluster = 1
        self.data_start_cluster = None
        self._leer_superbloque()

    # -------------------------------------------------------------------------
    # SuperbLoque
    # -------------------------------------------------------------------------
    def _leer_superbloque(self) -> None:
        """Lee y valida el superbloque de FiUnamFS."""
        with open(self.disk_path, 'rb') as f:
            data = f.read(self.SUPERBLOCK_STRUCT.size)

        nombre_raw, version_raw, etiqueta_raw, tam_cluster, dir_clusters, total_clusters = \
            self.SUPERBLOCK_STRUCT.unpack(data)

        nombre = nombre_raw.decode('ascii', errors='ignore').strip('\x00')
        version = version_raw.decode('ascii', errors='ignore').strip('\x00')
        etiqueta = etiqueta_raw.decode('ascii', errors='ignore').strip('\x00')

        if nombre != FS_NAME:
            raise ValueError(
                f"Sistema de archivos inválido: se esperaba nombre '{FS_NAME}', se encontró '{nombre}'"
            )
        if version != FS_VERSION:
            raise ValueError(
                f"Versión inválida de FiUnamFS: se esperaba '{FS_VERSION}', se encontró '{version}'"
            )

        self.fs_name = nombre
        self.version = version
        self.volume_label = etiqueta
        self.cluster_size = tam_cluster
        self.dir_clusters = dir_clusters
        self.total_clusters = total_clusters
        self.data_start_cluster = self.dir_start_cluster + self.dir_clusters

    def get_superblock_info(self) -> dict:
        """Devuelve la información del superbloque en un diccionario amigable."""
        return {
            "Nombre": self.fs_name,
            "Versión": self.version,
            "Etiqueta de Volumen": self.volume_label,
            "Tamaño de Cluster": self.cluster_size,
            "Número de Clusters de Directorio": self.dir_clusters,
            "Total de Clusters": self.total_clusters,
        }

    # -------------------------------------------------------------------------
    # Directorio
    # -------------------------------------------------------------------------
    def listar_directorio(self):
        """Lee todas las entradas válidas del directorio y las guarda en self.archivos."""
        archivos = []
        entries_per_cluster = self.cluster_size // self.DIR_ENTRY_STRUCT.size

        with open(self.disk_path, 'rb') as f:
            for cluster in range(self.dir_start_cluster,
                                  self.dir_start_cluster + self.dir_clusters):
                base_offset = cluster * self.cluster_size
                f.seek(base_offset)

                for entry_index in range(entries_per_cluster):
                    entry_data = f.read(self.DIR_ENTRY_STRUCT.size)
                    if len(entry_data) < self.DIR_ENTRY_STRUCT.size:
                        break

                    tipo, nombre_raw, cluster_inicial, tamaño, creado_raw, modificado_raw = \
                        self.DIR_ENTRY_STRUCT.unpack(entry_data)
                    nombre_decoded = nombre_raw.decode('ascii', errors='ignore').rstrip('\x00')
                    if tipo == FILE_TYPE_FREE:
                        continue
                    if not nombre_decoded:
                        continue
                    if nombre_decoded.startswith(EMPTY_NAME_PATTERN.decode('ascii')):
                        continue
                    if tipo != FILE_TYPE_USED:
                        continue

                    creado_str = creado_raw.decode('ascii', errors='ignore').rstrip('\x00')
                    mod_str = modificado_raw.decode('ascii', errors='ignore').rstrip('\x00')

                    archivos.append({
                        "Nombre": nombre_decoded,
                        "Tamaño": tamaño,
                        "Creado": creado_str,
                        "Modificado": mod_str,
                        "Cluster Inicial": cluster_inicial,
                    })

        self.archivos = archivos
        return archivos

    def _buscar_entrada_directorio_libre(self):
        """
        Busca una entrada libre en el directorio y devuelve el offset absoluto
        dentro del archivo de imagen donde se puede escribir.
        """
        entries_per_cluster = self.cluster_size // self.DIR_ENTRY_STRUCT.size
        empty_name_str = EMPTY_NAME_PATTERN.decode('ascii')

        with open(self.disk_path, 'rb') as f:
            for cluster in range(self.dir_start_cluster,
                                  self.dir_start_cluster + self.dir_clusters):
                base_offset = cluster * self.cluster_size

                for entry_index in range(entries_per_cluster):
                    entry_offset = base_offset + entry_index * self.DIR_ENTRY_STRUCT.size
                    f.seek(entry_offset)
                    entry_data = f.read(self.DIR_ENTRY_STRUCT.size)
                    if len(entry_data) < self.DIR_ENTRY_STRUCT.size:
                        continue

                    tipo, nombre_raw, _, _, _, _ = self.DIR_ENTRY_STRUCT.unpack(entry_data)
                    nombre_decoded = nombre_raw.decode('ascii', errors='ignore').rstrip('\x00')

                    if tipo == FILE_TYPE_FREE or nombre_decoded.startswith(empty_name_str):
                        return entry_offset

        return None

    # -------------------------------------------------------------------------
    # Gestión de espacio en datos
    # -------------------------------------------------------------------------
    def _buscar_espacio_contiguo(self, tamaño_bytes: int):
        """
        Busca espacio contiguo suficiente en la zona de datos para almacenar
        'tamaño_bytes'. Devuelve el cluster inicial o None si no hay espacio.
        """
        clusters_necesarios = math.ceil(tamaño_bytes / self.cluster_size)

        with open(self.disk_path, 'rb') as f:
            run_start = None
            run_length = 0

            for cluster in range(self.data_start_cluster, self.total_clusters):
                f.seek(cluster * self.cluster_size)
                data = f.read(self.cluster_size)
                if len(data) < self.cluster_size:
                    break

                if all(b == 0 for b in data):
                    if run_length == 0:
                        run_start = cluster
                    run_length += 1

                    if run_length >= clusters_necesarios:
                        return run_start
                else:
                    run_start = None
                    run_length = 0

        return None

    # -------------------------------------------------------------------------
    # Operaciones de alto nivel
    # -------------------------------------------------------------------------
    def copiar_desde_fs(self, nombre_archivo: str, destino_pc: str):
        """
        Copia un archivo desde FiUnamFS hacia el sistema de archivos del host.
        """
        with self.lock:
            if not self.archivos:
                self.listar_directorio()

            archivo = next((f for f in self.archivos if f["Nombre"] == nombre_archivo), None)
            if archivo is None:
                messagebox.showerror("Error", f"Archivo '{nombre_archivo}' no encontrado en FiUnamFS.")
                return False

            cluster_inicial = archivo["Cluster Inicial"]
            tamaño = archivo["Tamaño"]

            with open(self.disk_path, 'rb') as disk_file:
                disk_file.seek(cluster_inicial * self.cluster_size)
                datos = disk_file.read(tamaño)

            with open(destino_pc, 'wb') as out_file:
                out_file.write(datos)

        messagebox.showinfo(
            "Éxito",
            f"Archivo '{nombre_archivo}' copiado exitosamente a '{destino_pc}'."
        )
        return True

    def copiar_a_fs(self, ruta_origen: str):
        """
        Copia un archivo desde el sistema del host hacia FiUnamFS.
        """
        nombre_base = os.path.basename(ruta_origen)

        if len(nombre_base) > 14:
            messagebox.showerror(
                "Error",
                f"El nombre del archivo '{nombre_base}' es demasiado largo (máx. 14 caracteres)."
            )
            return False

        try:
            tamaño = os.path.getsize(ruta_origen)
        except OSError as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo origen: {e}")
            return False

        nombre_bytes = nombre_base.encode('ascii', errors='ignore')
        nombre_padded = nombre_bytes.ljust(15, b'\x00')
        creado_str = datetime.now().strftime('%Y%m%d%H%M%S')
        creado_bytes = creado_str.encode('ascii')
        modificado_bytes = creado_bytes

        with self.lock:
            if not self.archivos:
                self.listar_directorio()

            for archivo in self.archivos:
                if archivo["Nombre"] == nombre_base:
                    messagebox.showerror(
                        "Error",
                        f"Ya existe un archivo con el mismo nombre en FiUnamFS: '{nombre_base}'."
                    )
                    return False

            cluster_inicial = self._buscar_espacio_contiguo(tamaño)
            if cluster_inicial is None:
                messagebox.showerror(
                    "Error",
                    f"Espacio insuficiente en FiUnamFS para '{nombre_base}'."
                )
                return False

            pos_directorio = self._buscar_entrada_directorio_libre()
            if pos_directorio is None:
                messagebox.showerror(
                    "Error",
                    "No hay entradas de directorio libres en FiUnamFS."
                )
                return False

            with open(self.disk_path, 'r+b') as disk_file:
                disk_file.seek(pos_directorio)
                entry_data = self.DIR_ENTRY_STRUCT.pack(
                    FILE_TYPE_USED,
                    nombre_padded,
                    cluster_inicial,
                    tamaño,
                    creado_bytes,
                    modificado_bytes,
                )
                disk_file.write(entry_data)

            clusters_necesarios = math.ceil(tamaño / self.cluster_size)
            with open(ruta_origen, 'rb') as src_file, \
                    open(self.disk_path, 'r+b') as disk_file:
                for offset in range(clusters_necesarios):
                    disk_file.seek((cluster_inicial + offset) * self.cluster_size)
                    data = src_file.read(self.cluster_size)
                    if not data:
                        break
                    disk_file.write(data)

            self.listar_directorio()

        with VCListFiles:
            VCListFiles.notify_all()

        messagebox.showinfo(
            "Éxito",
            f"Archivo '{nombre_base}' copiado exitosamente a FiUnamFS."
        )
        return True

    def eliminar_archivo(self, nombre_archivo: str):
        """
        Elimina un archivo de FiUnamFS: limpia su entrada de directorio y sus clusters de datos.
        """
        with self.lock:
            if not self.archivos:
                self.listar_directorio()

            archivo = next((f for f in self.archivos if f["Nombre"] == nombre_archivo), None)
            if archivo is None:
                messagebox.showerror("Error", f"Archivo '{nombre_archivo}' no encontrado en FiUnamFS.")
                return False

            cluster_inicial = archivo["Cluster Inicial"]
            tamaño = archivo["Tamaño"]
            clusters_necesarios = math.ceil(tamaño / self.cluster_size)

            entries_per_cluster = self.cluster_size // self.DIR_ENTRY_STRUCT.size
            empty_name = EMPTY_NAME_PATTERN.ljust(15, b'\x00')
            with open(self.disk_path, 'r+b') as disk_file:
                encontrado = False
                for cluster in range(self.dir_start_cluster,
                                      self.dir_start_cluster + self.dir_clusters):
                    base_offset = cluster * self.cluster_size
                    for entry_index in range(entries_per_cluster):
                        entry_offset = base_offset + entry_index * self.DIR_ENTRY_STRUCT.size
                        disk_file.seek(entry_offset)
                        entry_data = disk_file.read(self.DIR_ENTRY_STRUCT.size)
                        if len(entry_data) < self.DIR_ENTRY_STRUCT.size:
                            continue

                        tipo, nombre_raw, _, _, _, _ = self.DIR_ENTRY_STRUCT.unpack(entry_data)
                        nombre_decoded = nombre_raw.decode('ascii', errors='ignore').rstrip('\x00')
                        if tipo == FILE_TYPE_USED and nombre_decoded == nombre_archivo:
                            vacio_data = self.DIR_ENTRY_STRUCT.pack(
                                FILE_TYPE_FREE,
                                empty_name,
                                0,
                                0,
                                b'00000000000000',
                                b'00000000000000',
                            )
                            disk_file.seek(entry_offset)
                            disk_file.write(vacio_data)
                            encontrado = True
                            break
                    if encontrado:
                        break

                for cluster in range(cluster_inicial, cluster_inicial + clusters_necesarios):
                    if cluster >= self.total_clusters:
                        break
                    disk_file.seek(cluster * self.cluster_size)
                    disk_file.write(b'\x00' * self.cluster_size)

            self.archivos.remove(archivo)

        with VCListFiles:
            VCListFiles.notify_all()

        messagebox.showinfo("Éxito", f"Archivo '{nombre_archivo}' eliminado exitosamente.")
        return True


# -----------------------------------------------------------------------------
# Interfaz gráfica
# -----------------------------------------------------------------------------
class FiUnamFSApp:
    def __init__(self, root, fs: FiUnamFS):
        self.fs = fs
        self.root = root
        self.root.title("FiUnamFS")

        self.superblock_info = tk.Label(root, text="", justify='left')
        self.superblock_info.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.tree = ttk.Treeview(
            root,
            columns=("Nombre", "Tamaño", "Creado", "Cluster Inicial", "Modificado"),
            show='headings'
        )
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Tamaño", text="Tamaño (bytes)")
        self.tree.heading("Creado", text="Creado")
        self.tree.heading("Cluster Inicial", text="Cluster Inicial")
        self.tree.heading("Modificado", text="Modificado")

        self.tree.column("Nombre", width=200)
        self.tree.column("Tamaño", width=120, anchor='e')
        self.tree.column("Creado", width=150)
        self.tree.column("Cluster Inicial", width=120, anchor='e')
        self.tree.column("Modificado", width=150)

        self.tree_scroll = ttk.Scrollbar(root, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)

        self.tree_scroll.grid(row=1, column=2, sticky='ns')
        self.tree.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        self.list_button = tk.Button(root, text="Listar archivos", command=self.notify_list_files)
        self.list_button.grid(row=2, column=0, padx=10, pady=5)

        self.copy_to_pc_button = tk.Button(root, text="Copiar a PC", command=self.copy_to_pc)
        self.copy_to_pc_button.grid(row=2, column=1, padx=10, pady=5)

        self.copy_to_fs_button = tk.Button(root, text="Copiar a FiUnamFS", command=self.copy_to_fs)
        self.copy_to_fs_button.grid(row=3, column=0, padx=10, pady=5)

        self.delete_button = tk.Button(root, text="Eliminar archivo", command=self.delete_file)
        self.delete_button.grid(row=3, column=1, padx=10, pady=5)

        self.show_superblock_info()

        self.list_thread = threading.Thread(target=self.list_files_loop, daemon=True)
        self.list_thread.start()

    # ------------------------------------------------------------------
    # SuperbLoque en GUI
    # ------------------------------------------------------------------
    def show_superblock_info(self):
        info = self.fs.get_superblock_info()
        texto = (
            f"Nombre: {info['Nombre']}\n"
            f"Versión: {info['Versión']}\n"
            f"Etiqueta de Volumen: {info['Etiqueta de Volumen']}\n"
            f"Tamaño de Cluster: {info['Tamaño de Cluster']} bytes\n"
            f"Número de Clusters de Directorio: {info['Número de Clusters de Directorio']}\n"
            f"Total de Clusters: {info['Total de Clusters']}"
        )
        self.superblock_info.config(text=texto)

    # ------------------------------------------------------------------
    # Listado de archivos (concurrente)
    # ------------------------------------------------------------------
    def notify_list_files(self):
        """Despierta al hilo enlistador para refrescar el listado."""
        with VCListFiles:
            VCListFiles.notify_all()

    def list_files_loop(self):
        """Hilo que espera notificaciones y actualiza la tabla de archivos."""
        while True:
            with VCListFiles:
                VCListFiles.wait()

            with self.fs.lock:
                files = self.fs.listar_directorio()
            def actualizar_tree():
                self.tree.delete(*self.tree.get_children())
                for file in files:
                    creado_fmt = self._formatear_fecha(file["Creado"])
                    mod_fmt = self._formatear_fecha(file["Modificado"])
                    self.tree.insert(
                        "",
                        "end",
                        values=(
                            file["Nombre"],
                            file["Tamaño"],
                            creado_fmt,
                            file["Cluster Inicial"],
                            mod_fmt,
                        ),
                    )

            self.root.after(0, actualizar_tree)

    @staticmethod
    def _formatear_fecha(fecha_raw: str) -> str:
        """Convierte AAAAMMDDHHMMSS a 'YYYY-MM-DD HH:MM:SS'."""
        try:
            dt = datetime.strptime(fecha_raw, "%Y%m%d%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return fecha_raw or "-"

    # ------------------------------------------------------------------
    # Operaciones GUI
    # ------------------------------------------------------------------
    def copy_to_pc(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Atención", "Selecciona al menos un archivo para copiar.")
            return

        def worker(nombre_archivo, destino):
            self.fs.copiar_desde_fs(nombre_archivo, destino)

        for item in selected_items:
            nombre_archivo = self.tree.item(item)["values"][0]
            destino = filedialog.asksaveasfilename(initialfile=nombre_archivo)
            if not destino:
                continue
            hilo = threading.Thread(target=worker, args=(nombre_archivo, destino), daemon=True)
            hilo.start()

    def copy_to_fs(self):
        rutas = filedialog.askopenfilenames()
        if not rutas:
            return

        def worker(ruta):
            self.fs.copiar_a_fs(ruta)

        hilos = []
        for ruta in rutas:
            hilo = threading.Thread(target=worker, args=(ruta,), daemon=True)
            hilos.append(hilo)
            hilo.start()

    def delete_file(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Atención", "Selecciona al menos un archivo para eliminar.")
            return

        def worker(nombre_archivo):
            self.fs.eliminar_archivo(nombre_archivo)

        hilos = []
        for item in selected_items:
            nombre_archivo = self.tree.item(item)["values"][0]
            confirmar = messagebox.askyesno(
                "Confirmar eliminación",
                f"¿Seguro que deseas eliminar '{nombre_archivo}' de FiUnamFS?"
            )
            if confirmar:
                hilo = threading.Thread(target=worker, args=(nombre_archivo,), daemon=True)
                hilos.append(hilo)
                hilo.start()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_img = os.path.join(script_dir, "fiunamfs.img")

    if os.path.exists(default_img):
        disk_image_path = default_img
    else:

        messagebox.showinfo(
            "Seleccionar imagen de FiUnamFS",
            "No se encontró 'fiunamfs.img' junto a PFSO.py.\n\n"
            "Selecciona el archivo de imagen de FiUnamFS."
        )
        disk_image_path = filedialog.askopenfilename(
            title="Selecciona fiunamfs.img",
            initialdir=script_dir,
            filetypes=[("Imagen FiUnamFS", "*.img"), ("Todos los archivos", "*.*")]
        )

        if not disk_image_path:
            messagebox.showerror(
                "Error",
                "No se seleccionó ninguna imagen de FiUnamFS. El programa se cerrará."
            )
            root.destroy()
            sys.exit(1)

    try:
        fs = FiUnamFS(disk_image_path)
    except Exception as e:
        messagebox.showerror("Error inicializando FiUnamFS", str(e))
        root.destroy()
        sys.exit(1)

    root.deiconify()
    app = FiUnamFSApp(root, fs)
    root.mainloop()