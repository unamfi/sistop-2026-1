import struct
from threading import Thread, RLock, Condition, Event
import math
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ============================================================================
# CAPA DE ACCESO AL DISCO
# ============================================================================

class DiscoVirtual:
    SECTOR_SIZE = 512
    CLUSTER_SIZE = 1024
    SUPERBLOCK_CLUSTER = 0
    DIR_START_CLUSTER = 1
    DIR_CLUSTERS = 4  # Clusters 1-4 para directorio
    TOTAL_SIZE = 1440 * 1024  # 1440 KB

    def __init__(self, path):
        self.path = path
        self.lock = RLock()

    def leer_cluster(self, cluster_num):
        with self.lock:
            with open(self.path, 'rb') as f:
                f.seek(cluster_num * self.CLUSTER_SIZE)
                return f.read(self.CLUSTER_SIZE)

    def escribir_cluster(self, cluster_num, data):
        with self.lock:
            with open(self.path, 'r+b') as f:
                f.seek(cluster_num * self.CLUSTER_SIZE)
                f.write(data)

    def leer_bytes(self, offset, size):
        with self.lock:
            with open(self.path, 'rb') as f:
                f.seek(offset)
                return f.read(size)

    def escribir_bytes(self, offset, data):
        with self.lock:
            with open(self.path, 'r+b') as f:
                f.seek(offset)
                f.write(data)
    
    def leer_multiples_clusters(self, cluster_inicial, num_clusters):
        """Lee múltiples clusters contiguos"""
        with self.lock:
            data = b''
            for i in range(num_clusters):
                data += self.leer_cluster(cluster_inicial + i)
            return data
    
    def escribir_multiples_clusters(self, cluster_inicial, data):
        """Escribe datos en múltiples clusters contiguos"""
        with self.lock:
            num_clusters = math.ceil(len(data) / self.CLUSTER_SIZE)
            for i in range(num_clusters):
                inicio = i * self.CLUSTER_SIZE
                fin = min(inicio + self.CLUSTER_SIZE, len(data))
                cluster_data = data[inicio:fin]
                
                # Relleno del último cluster para que mida exactamente 1024 bytes
                if len(cluster_data) < self.CLUSTER_SIZE:
                    cluster_data += b'\x00' * (self.CLUSTER_SIZE - len(cluster_data))
                self.escribir_cluster(cluster_inicial + i, cluster_data)
                
# ============================================================================
# VALIDADOR Y METADATOS
# ============================================================================

class Superbloque:
    def __init__(self, disco):
        self.disco = disco
        self._cargar_y_validar()

    def _cargar_y_validar(self):
        sb_data = self.disco.leer_cluster(0)

        try:
            """
            La estructura del superbloque tiene valores separados por offsets
            fijos. Usamos struct.unpack para extraerlos.

            <  = little-endian
            9s = nombre (9 bytes)
            1x = byte reservado (skip)
            5s = versión
            5x = 5 bytes ignorados
            16s = etiqueta del volumen
            4x = ignorados
            I = uint32 (cluster size)
            1x
            I = directorio clusters
            1x
            I = total clusters
            """
            nombre, version, etiqueta, tam_cluster, dir_clusters, total_clusters = struct.unpack(
                '<9s1x5s5x16s4xI1xI1xI', sb_data[:54]
            )
            
            self.nombre = nombre.decode('ascii').strip('\x00')
            self.version = version.decode('ascii').strip('\x00')
            self.label = etiqueta.decode('ascii').strip('\x00')
            self.cluster_size = tam_cluster
            self.dir_clusters = dir_clusters
            self.total_clusters = total_clusters
            
        except:
            raise ValueError("Error leyendo superbloque")

        if self.nombre != 'FiUnamFS':
            raise ValueError(f"Sistema de archivos no válido: {self.nombre}")
        
        
        if self.version != '26-1':
            raise ValueError(f"Versión incorrecta: esperada 26-1, encontrada {self.version}")

    def obtener_info(self):
        """Retorna información formateada del superbloque"""
        return {
            "Nombre": self.nombre,
            "Versión": self.version,
            "Etiqueta de Volumen": self.label,
            "Tamaño de Cluster": f"{self.cluster_size} bytes",
            "Clusters de Directorio": self.dir_clusters,
            "Total de Clusters": self.total_clusters
        }
        
        
# ============================================================================
# GESTOR DE ENTRADAS DE DIRECTORIO
# ============================================================================

class EntradaDirectorio:
    SIZE = 64
    EMPTY_MARKER = b'-'  
    DELETED_MARKER = b'#'
    VALID_TYPE = b'.'  
    EMPTY_NAME = '...............'

    def __init__(self, raw_data=None):
        if raw_data:
            self._parse(raw_data)
        else:
            self.tipo = '-'
            self.nombre = self.EMPTY_NAME
            self.cluster_inicial = 0
            self.tamano = 0
            self.fecha_creacion = ''
            self.fecha_modificacion = ''

    def _parse(self, data):
        self.tipo = chr(data[0])
        # El nombre ocupa bytes [1:16], hay que quitar nulos y espacios.
        self.nombre = data[1:16].decode('ascii', errors='ignore').strip('\x00').strip()
        self.cluster_inicial = struct.unpack('<I', data[16:20])[0]
        self.tamano = struct.unpack('<I', data[20:24])[0]
        self.fecha_creacion = data[24:38].decode('ascii', errors='ignore').strip('\x00')
        self.fecha_modificacion = data[38:52].decode('ascii', errors='ignore').strip('\x00')

    def is_empty(self):
        # Reglas para determinar si la entrada es una entrada vacía o un archivo válido
        return (self.tipo == '-' or 
                self.tipo == '#' or
                self.nombre == self.EMPTY_NAME or 
                self.nombre == '' or
                '...............' in self.nombre)

    def to_bytes(self):
        """
        Aquí se crea manualmente la entrada de directorio,
        asegurando que cada campo mida exactamente lo que el FS requiere.
        """
        nombre_enc = self.nombre.encode('ascii')[:15].ljust(15, b'\x00')
        fecha_cr = self.fecha_creacion.encode('ascii')[:14].ljust(14, b'\x00')
        fecha_mod = self.fecha_modificacion.encode('ascii')[:14].ljust(14, b'\x00')

        return struct.pack('<c15sII14s14s12s',
                          self.tipo.encode('ascii') if self.tipo else b'.',
                          nombre_enc,
                          self.cluster_inicial,
                          self.tamano,
                          fecha_cr,
                          fecha_mod,
                          b'\x00' * 12)

class Directorio:
    def __init__(self, disco):
        self.disco = disco
        self.lock = RLock()
        self.entradas = self._cargar_entradas()

    def _cargar_entradas(self):
        """
        Cada cluster del directorio contiene 16 entradas de 64 bytes.
        Se recorren los clusters 1 a 4 y se construyen todas las entradas.
        """
        entradas = []
        for cluster in range(1, 5):
            for entrada_idx in range(16):
                offset = (cluster * DiscoVirtual.CLUSTER_SIZE) + (entrada_idx * EntradaDirectorio.SIZE)
                data = self.disco.leer_bytes(offset, EntradaDirectorio.SIZE)
                entrada = EntradaDirectorio(data)
                idx_global = (cluster - 1) * 16 + entrada_idx
                entradas.append((idx_global, entrada))
        return entradas

    def recargar(self):
        """Recarga las entradas del directorio desde disco"""
        with self.lock:
            self.entradas = self._cargar_entradas()

    def listar_archivos(self):
        with self.lock:
            return [(idx, e) for idx, e in self.entradas if not e.is_empty()]

    def buscar_por_nombre(self, nombre):
        with self.lock:
            for idx, entrada in self.entradas:
                if entrada.nombre == nombre and not entrada.is_empty():
                    return idx, entrada
            return None, None

    def encontrar_entrada_libre(self):
        with self.lock:
            for idx, entrada in self.entradas:
                if entrada.is_empty():
                    return idx
            return None

    def actualizar_entrada(self, indice, entrada):
        """
        Calcula el cluster y offset correcto de la entrada modificada
        para actualizarla en la imagen del FS.
        """
        with self.lock:
            cluster = 1 + (indice // 16)
            entrada_en_cluster = indice % 16
            offset = (cluster * DiscoVirtual.CLUSTER_SIZE) + (entrada_en_cluster * EntradaDirectorio.SIZE)
            
            self.disco.escribir_bytes(offset, entrada.to_bytes())
            self.entradas[indice] = (indice, entrada)

    def marcar_como_libre(self, indice):
        entrada = EntradaDirectorio()
        entrada.tipo = '-'  # Marcar como vacío con '-'
        entrada.nombre = '...............'
        self.actualizar_entrada(indice, entrada)

# ============================================================================
# GESTOR DE ESPACIO EN DISCO
# ============================================================================

class GestorEspacio:
    def __init__(self, disco, total_clusters):
        self.disco = disco
        self.total_clusters = total_clusters  # Guardamos el valor real del disco
        self.lock = RLock()
        
    def buscar_espacio_contiguo(self, num_clusters):
        """
        Se recorre el área del directorio buscando el num_clusters que estén llenos
        solo de ceros (indicando que están libres).
        Es necesario que sean contiguos.
        """
        with self.lock:
            inicio = DiscoVirtual.DIR_START_CLUSTER + DiscoVirtual.DIR_CLUSTERS
            total = self.total_clusters 
            
            clusters_libres_consecutivos = 0
            cluster_inicial = None
            
            for c in range(inicio, total):
                data = self.disco.leer_cluster(c)
                
                # Un cluster está libre si TODOS los bytes son 0
                if all(b == 0 for b in data):
                    if cluster_inicial is None:
                        cluster_inicial = c
                    clusters_libres_consecutivos += 1
                    
                    if clusters_libres_consecutivos == num_clusters:
                        return cluster_inicial
                else:
                    clusters_libres_consecutivos = 0
                    cluster_inicial = None
                    
            return None
    
    def liberar_clusters(self, cluster_inicial, num_clusters):
        """Libera clusters escribiendo ceros"""
        with self.lock:
            for i in range(num_clusters):
                self.disco.escribir_cluster(cluster_inicial + i, b'\x00' * DiscoVirtual.CLUSTER_SIZE)
    
    def obtener_espacio_disponible(self):
        """Retorna información de espacio disponible"""
        with self.lock:
            inicio = DiscoVirtual.DIR_START_CLUSTER + DiscoVirtual.DIR_CLUSTERS
            total = self.total_clusters
            clusters_libres = 0
            bytes_libres = 0 
            
            for c in range(inicio, total):
                data = self.disco.leer_cluster(c)
                if all(b == 0 for b in data):
                    clusters_libres += 1
                    bytes_libres += DiscoVirtual.CLUSTER_SIZE
            
            return {
                'clusters_libres': clusters_libres,
                'bytes_libres': bytes_libres,
                'clusters_totales': total - inicio,
                'bytes_totales': (total - inicio) * DiscoVirtual.CLUSTER_SIZE
            }

# ============================================================================
# OPERACIONES DEL SISTEMA DE ARCHIVOS
# ============================================================================

class FileSystemOps:
    def __init__(self, disco_path):
        self.disco = DiscoVirtual(disco_path)
        self.sb = Superbloque(self.disco)
        self.directorio = Directorio(self.disco)
        self.gestor_espacio = GestorEspacio(self.disco, self.sb.total_clusters)
        self.lock_ops = RLock()
        self.cambio_notificacion = Condition()

    def listar(self):
        with self.lock_ops:
            self.directorio.recargar()
            return self.directorio.listar_archivos()

    def extraer_archivo(self, nombre_fs, ruta_destino):
        """
        Extraer archivo:
        - Encuentra entrada del directorio
        - Lee los clusters asociados
        - Recorta al tamaño real (el último cluster puede tener relleno)
        """
        with self.lock_ops:
            idx, entrada = self.directorio.buscar_por_nombre(nombre_fs)

            if entrada is None:
                raise FileNotFoundError(f"Archivo '{nombre_fs}' no encontrado")

            clusters_necesarios = math.ceil(entrada.tamano / DiscoVirtual.CLUSTER_SIZE)
            
            data = self.disco.leer_multiples_clusters(
                entrada.cluster_inicial, 
                clusters_necesarios
            )
            
            data = data[:entrada.tamano]

            if os.path.isdir(ruta_destino):
                ruta_destino = os.path.join(ruta_destino, nombre_fs)

            with open(ruta_destino, 'wb') as f:
                f.write(data)

            return ruta_destino

    def agregar_archivo(self, ruta_origen, nombre_fs=None):
        """
        agregar_archivo:
        - Revisar si el archivo especificado existe
        - Leer archivo real
        - Calcular clusters necesarios para guardarlo
        - Buscar clusters contiguos
        - Escribir clusters en el IMG
        - Crear entrada de directorio
        """
        with self.lock_ops:
            if nombre_fs is None:
                nombre_fs = os.path.basename(ruta_origen)
            
            if len(nombre_fs) > 15:
                raise ValueError("Nombre demasiado largo (máx 15 caracteres)")

            idx_existente, _ = self.directorio.buscar_por_nombre(nombre_fs)
            if idx_existente is not None:
                raise ValueError(f"Ya existe un archivo con el nombre '{nombre_fs}'")

            with open(ruta_origen, 'rb') as f:
                contenido = f.read()

            tamano = len(contenido)
            clusters_necesarios = math.ceil(tamano / DiscoVirtual.CLUSTER_SIZE)

            espacio = self.gestor_espacio.obtener_espacio_disponible()
            if espacio['clusters_libres'] < clusters_necesarios:
                raise ValueError(f"Espacio insuficiente")

            idx_libre = self.directorio.encontrar_entrada_libre()
            if idx_libre is None:
                raise ValueError("Directorio lleno")

            cluster_inicial = self.gestor_espacio.buscar_espacio_contiguo(clusters_necesarios)
            if cluster_inicial is None:
                raise ValueError(f"No hay espacio contiguo suficiente")

            self.disco.escribir_multiples_clusters(cluster_inicial, contenido)

            nueva_entrada = EntradaDirectorio()
            nueva_entrada.tipo = '.'
            nueva_entrada.nombre = nombre_fs
            nueva_entrada.cluster_inicial = cluster_inicial
            nueva_entrada.tamano = tamano
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            nueva_entrada.fecha_creacion = timestamp
            nueva_entrada.fecha_modificacion = timestamp

            self.directorio.actualizar_entrada(idx_libre, nueva_entrada)
            
            with self.cambio_notificacion:
                self.cambio_notificacion.notify_all()

    def eliminar_archivo(self, nombre_fs):
        """
        Eliminar archivo:
        - Liberar clusters (llenarlos con ceros)
        - Marcar entrada como vacía
        """
        with self.lock_ops:
            idx, entrada = self.directorio.buscar_por_nombre(nombre_fs)

            if entrada is None:
                raise FileNotFoundError(f"Archivo '{nombre_fs}' no encontrado")

            clusters_a_liberar = math.ceil(entrada.tamano / DiscoVirtual.CLUSTER_SIZE)
            
            self.gestor_espacio.liberar_clusters(entrada.cluster_inicial, clusters_a_liberar)

            self.directorio.marcar_como_libre(idx)
            
            with self.cambio_notificacion:
                self.cambio_notificacion.notify_all()

    def obtener_info_superbloque(self):
        return self.sb.obtener_info()
    
    def obtener_info_espacio(self):
        return self.gestor_espacio.obtener_espacio_disponible()
      
# ============================================================================
# OPERACIONES CONCURRENTES
# ============================================================================

class OperacionConcurrente(Thread):
    def __init__(self, operacion, args, callback_exito=None, callback_error=None):
        super().__init__()
        self.operacion = operacion
        self.args = args
        self.callback_exito = callback_exito
        self.callback_error = callback_error
        self.daemon = True
        
    def run(self):
        """
        Wrapper para ejecutar operaciones en el FS sin congelar la GUI.
        """
        try:
            resultado = self.operacion(*self.args)
            if self.callback_exito:
                self.callback_exito(resultado)
        except Exception as e:
            if self.callback_error:
                self.callback_error(str(e))

# ============================================================================
# MONITOR EN SEGUNDO PLANO
# ============================================================================

class MonitorIntegridad(Thread):
    def __init__(self, fs_ops, gui_callback=None, intervalo=30):
        super().__init__(daemon=True)
        self.fs_ops = fs_ops
        self.gui_callback = gui_callback
        self.intervalo = intervalo
        self.activo = True
        self.evento_parada = Event()

    def run(self):
        """
        Cada cierto intervalo de tiempo:
        - Relee el superbloque
        - Consulta el espacio libre
        - Notifica a la GUI si algo cambió
        Este monitor detecta corrupción o modificaciones externas.
        """
        while self.activo:
            if self.evento_parada.wait(self.intervalo):
                break
                
            try:
                _ = Superbloque(self.fs_ops.disco)
                info_espacio = self.fs_ops.obtener_info_espacio()
                
                if self.gui_callback:
                    self.gui_callback(info_espacio)
                    
            except Exception as e:
                if self.gui_callback:
                    self.gui_callback({'error': str(e)})

    def detener(self):
        self.activo = False
        self.evento_parada.set()

# ============================================================================
# INTERFAZ GRÁFICA
# ============================================================================

class AplicacionFS:
    def __init__(self, root, fs_ops):
        self.root = root
        self.fs = fs_ops
        self.monitor = MonitorIntegridad(fs_ops, self.actualizar_info_espacio)
        
        # Hilo para actualización automática
        self.hilo_actualizacion = Thread(target=self._monitor_cambios, daemon=True)

        self.root.title("FiUnamFS Manager")
        self.root.geometry("900x600")

        self._crear_interfaz()
        self.monitor.start()
        self.hilo_actualizacion.start()
        
        # Actualizar lista al inicio
        self.root.after(100, self.actualizar_lista)

    def _crear_interfaz(self):
        # Frame para información del superbloque
        frame_info = tk.LabelFrame(self.root, text="Información del Sistema", padx=10, pady=5)
        frame_info.pack(fill=tk.X, padx=10, pady=5)
        
        self.label_info = tk.Label(frame_info, justify=tk.LEFT, font=('Courier', 10))
        self.label_info.pack()

        # Frame para botones de operación 
        frame_botones = tk.Frame(self.root, pady=10)
        frame_botones.pack(fill=tk.X)

        tk.Button(frame_botones, text="Extraer Archivo", command=self.extraer_multiple, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="Agregar Archivo", command=self.agregar_multiple, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="Eliminar Archivo", command=self.eliminar_multiple, width=15).pack(side=tk.LEFT, padx=5)

        # Frame para la lista de archivos
        frame_lista = tk.Frame(self.root)
        frame_lista.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview solo con archivos válidos
        cols = ("Nombre", "Tamaño", "Cluster Inicial", "Creación", "Modificación")
        self.tree = ttk.Treeview(frame_lista, columns=cols, show='headings', height=15, selectmode='extended')

        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Tamaño", text="Tamaño (bytes)")
        self.tree.heading("Cluster Inicial", text="Cluster Inicial")
        self.tree.heading("Creación", text="Creación")
        self.tree.heading("Modificación", text="Modificación")

        self.tree.column("Nombre", width=180)
        self.tree.column("Tamaño", width=120)
        self.tree.column("Cluster Inicial", width=100)
        self.tree.column("Creación", width=150)
        self.tree.column("Modificación", width=150)

        scroll_y = ttk.Scrollbar(frame_lista, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        scroll_y.grid(row=0, column=1, sticky='ns')

        frame_lista.grid_rowconfigure(0, weight=1)
        frame_lista.grid_columnconfigure(0, weight=1)

        self.status_bar = tk.Label(self.root, text="Listo", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _monitor_cambios(self):
        """
        Espera notificaciones (Condition) enviadas por las operaciones de FS.
        Esto evita estar refrescando la GUI constantemente.
        """
        while True:
            with self.fs.cambio_notificacion:
                self.fs.cambio_notificacion.wait()
                self.root.after(100, self.actualizar_lista)

    def actualizar_lista(self):
        """Actualiza la lista mostrando SOLO archivos válidos"""
        # Limpiar lista
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Obtener y mostrar solo archivos válidos
        archivos = self.fs.listar()
        
        for idx, entrada in archivos:
            # Solo mostramos archivos válidos, NO las entradas vacías
            tamano_fmt = f"{entrada.tamano}"
            
            # Mostrar fechas en formato AAAAMMDDHHMMSS como están en el disco
            self.tree.insert('', tk.END, values=(
                entrada.nombre,
                tamano_fmt,
                entrada.cluster_inicial,
                entrada.fecha_creacion,
                entrada.fecha_modificacion
            ))
        
        # Actualizar información del sistema
        self.actualizar_info_sistema()

    def actualizar_info_sistema(self):
        """Actualiza información del superbloque y espacio"""
        info = self.fs.obtener_info_superbloque()
        espacio = self.fs.obtener_info_espacio()
        
        texto = (
            f"Nombre: {info['Nombre']} | "
            f"Versión: {info['Versión']} | "
            f"Etiqueta: {info['Etiqueta de Volumen']}\n"
            f"Tamaño Cluster: {info['Tamaño de Cluster']} | "
            f"Clusters Dir: {info['Clusters de Directorio']} | "
            f"Espacio Libre: {espacio['bytes_libres']//1024} KB / {espacio['bytes_totales']//1024} KB"
        )
        self.label_info.config(text=texto)

    def actualizar_info_espacio(self, info_espacio):
        """Actualiza información de espacio en la barra de estado"""
        if 'error' in info_espacio:
            self.status_bar.config(text=f"Error: {info_espacio['error']}")
        else:
            kb_libres = info_espacio['bytes_libres'] // 1024
            kb_totales = info_espacio['bytes_totales'] // 1024
            porcentaje = (info_espacio['bytes_libres'] / info_espacio['bytes_totales']) * 100
            self.status_bar.config(
                text=f"Espacio libre: {kb_libres} KB / {kb_totales} KB ({porcentaje:.1f}%)"
            )

    def extraer_multiple(self):
        """Extrae múltiples archivos seleccionados"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione archivo(s) para copiar a PC")
            return

        destino = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if not destino:
            return

        archivos_extraidos = []
        errores = []

        for item in seleccion:
            valores = self.tree.item(item)['values']
            nombre = valores[0]
            
            def callback_exito(resultado):
                archivos_extraidos.append(resultado)
                
            def callback_error(error):
                errores.append(f"{nombre}: {error}")
            
            op = OperacionConcurrente(
                self.fs.extraer_archivo,
                (nombre, destino),
                callback_exito,
                callback_error
            )
            op.start()
            op.join()

        if archivos_extraidos:
            messagebox.showinfo("Éxito", f"Archivos copiados: {len(archivos_extraidos)}")
        
        if errores:
            messagebox.showerror("Errores", "\n".join(errores))

    def agregar_multiple(self):
        """Agrega múltiples archivos"""
        archivos = filedialog.askopenfilenames(title="Seleccionar archivo(s)")
        if not archivos:
            return

        agregados = []
        errores = []
        
        for archivo in archivos:
            nombre_base = os.path.basename(archivo)
            
            if len(nombre_base) > 15:
                nombre = simpledialog.askstring(
                    "Nombre largo",
                    f"El nombre '{nombre_base}' es muy largo.\nIngrese un nombre (máx 15 caracteres):",
                    initialvalue=nombre_base[:15]
                )
                if not nombre:
                    continue
            else:
                nombre = nombre_base

            def callback_exito(resultado):
                agregados.append(nombre)
                
            def callback_error(error):
                errores.append(f"{nombre}: {error}")

            op = OperacionConcurrente(
                self.fs.agregar_archivo,
                (archivo, nombre),
                callback_exito,
                callback_error
            )
            op.start()
            op.join()

        self.actualizar_lista()
        
        if agregados:
            messagebox.showinfo("Éxito", f"Archivos agregados: {len(agregados)}")
        
        if errores:
            messagebox.showerror("Errores", "\n".join(errores[:5]))

    def eliminar_multiple(self):
        """Elimina múltiples archivos seleccionados"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione archivo(s) para eliminar")
            return

        archivos_a_eliminar = []
        for item in seleccion:
            valores = self.tree.item(item)['values']
            nombre = valores[0]
            archivos_a_eliminar.append(nombre)

        if not archivos_a_eliminar:
            return

        msg = f"¿Eliminar {len(archivos_a_eliminar)} archivo(s)?"
        
        if not messagebox.askyesno("Confirmar eliminación", msg):
            return

        eliminados = []
        errores = []

        for nombre in archivos_a_eliminar:
            def callback_exito(resultado):
                eliminados.append(nombre)
                
            def callback_error(error):
                errores.append(f"{nombre}: {error}")

            op = OperacionConcurrente(
                self.fs.eliminar_archivo,
                (nombre,),
                callback_exito,
                callback_error
            )
            op.start()
            op.join()

        self.actualizar_lista()
        
        if eliminados:
            messagebox.showinfo("Éxito", f"Archivos eliminados: {len(eliminados)}")
        
        if errores:
            messagebox.showerror("Errores", "\n".join(errores))

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

def main():
    root = tk.Tk()
    root.withdraw()

    archivo_fs = filedialog.askopenfilename(
        title="Seleccionar archivo FiUnamFS",
        filetypes=[("Archivos IMG", "*.img"), ("Todos los archivos", "*.*")]
    )

    if not archivo_fs:
        return

    try:
        fs_ops = FileSystemOps(archivo_fs)
        root.deiconify()
        app = AplicacionFS(root, fs_ops)
        root.protocol("WM_DELETE_WINDOW", lambda: (app.monitor.detener(), root.destroy()))
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar el sistema de archivos:\n{str(e)}")

if __name__ == "__main__":
    main()