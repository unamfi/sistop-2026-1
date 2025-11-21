#!/usr/bin/env python3

import math
import os
import struct
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

#################################################################
#        Constantes generales para el formato FiUnamFS
##################################################################

CLUSTER_SIZE = 1024                         # Tamaño en bytes de cada cluster
TOTAL_CLUSTERS = 1440                       # Número total de clusters en la imagen
DIR_CLUSTER_START = 1                       # Primer cluster donde inicia el directorio
DIR_CLUSTER_END = 4                         # Último cluster reservado al directorio
ENTRIES_PER_CLUSTER = CLUSTER_SIZE // 64    # Cada entrada mide 64 bytes
ENTRY_SIZE = 64

#################################################################
#   Estructura binaria de una entrada del directorio:
#       tipo(1 byte), nombre(15 bytes), cluster inicial(4),
#       tamaño(4), fecha creación(14), fecha modificación(14),
#       padding(12)
################################################################

ENTRY_STRUCT = struct.Struct("<c15sII14s14s12x")

# Variable global 
VCListFiles = threading.Condition() # ayuda para que hilos de la gui avisen cambios


class FiUnamFS:
    ################################################################
    # Clase principal especializada para las opciones del disco 
    # Nos ayuda a definir las funcioens para leer el superbloque, listar
    #           directorio, copiar archivos, buscar espacio y eliminar.
    #############################################################

    # Constructor ###
    def __init__(self, disk_path):
        # Inicializa el sistema con la ruta a la imagen
        self.disk = disk_path
        self.lock = threading.Lock()   # evita condiciones de carrera
        self.archivos = None           

        # checa si la imagen existe
        if not os.path.exists(self.disk):
            raise FileNotFoundError(f"No existe imagen: {self.disk}")

    # ################################################################
    #                   LECTURA DEL SUPERBLOQUE 
    # ################################################################
    def leer_superbloque(self):
        
        # Lee y valida el superbloque del sistema de archivos. ###
        # + empieza al principio de la imagen.
        # + lee los primeros 54 bytes que contiene:
        #    - cadena "FiUnamFS"
        #    - versión del sistema de archivos (FS)
        #    - etiqueta del volumen
        #    - tamaño de cluster
        #    - cluster inicial del directorio
        #    - número total de clusters
        # + Se verifican los valores clave para confirmar que la imagen
        #  es válida y que corresponde al formato esperado.
        
        with open(self.disk, "rb") as f:
            f.seek(0)
            raw = f.read(54)
            if len(raw) < 54:
                raise RuntimeError("Superbloque demasiado corto")

            # Extraer campos del header
            nombre = raw[0:9].decode("ascii", errors="ignore").strip("\x00")
            version = raw[10:15].decode("ascii", errors="ignore").strip("\x00")
            etiqueta = raw[20:36].decode("ascii", errors="ignore").strip("\x00")
            tam_cluster = struct.unpack("<I", raw[40:44])[0]
            dir_clusters = struct.unpack("<I", raw[45:49])[0]
            total_clusters = struct.unpack("<I", raw[50:54])[0]

            ##### Checks para saber si estamos leyendo la imagen correcta jeje
            if nombre != "FiUnamFS":
                raise ValueError(f"No es FiUnamFS (nombre='{nombre}')")

            # Advertencia si la versión no es la esperada
            if version != "26-1":
                print(f"[ADVERTENCIA] Versión detectada: {version} (esperada: 26-1)")

            # regrasamos un diccionario con la informacion 
            return {
                "Nombre": nombre,
                "Version": version,
                "Etiqueta": etiqueta,
                "Tamano_Cluster": tam_cluster,
                "Clusters_Directorio": dir_clusters,
                "Total_Clusters": total_clusters,
            }

    # ################################################################
    #                      LISTAR DIRECTORIO 
    # ##############################################################
    def enlistar_directorio(self, mostrar_vacias=False):
        
        # enlista todas las entradas del directorio (clusters 1 a 4).
        # - El directorio está compuesto por 4 clusters.
        # - cada cluster contiene entradas de 64 bytes.
        # - Cada entrada representa un archivo o una entrada vacía.
        # - Esta función:
        #     > recorre cada cluster del directorio,
        #     > lee cada entrada,
        #     > decodifica los campos usando ENTRY_STRUCT,
        #     > determina si está vacía o no,
        #     > y construye un diccionario por entrada.
        # - Si mostrar_vacias=False, solo se devuelven entradas activas.
        
        archivos = [] # 
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
                        tipo_b, nombre_b, cluster, tam, creado_b, modif_b = (
                            ENTRY_STRUCT.unpack(entry)
                        )
                    except struct.error:
                        continue

                    # Convertir campos binarios a texto
                    tipo = tipo_b.decode("ascii", errors="ignore")
                    nombre = (
                        nombre_b.decode("ascii", errors="ignore").rstrip("\x00").strip()
                    )
                    creado = creado_b.decode("ascii", errors="ignore").strip("\x00")
                    modif = modif_b.decode("ascii", errors="ignore").strip("\x00")

                    # Detectar entrada vacía
                    es_vacia = (
                        tipo == "-" or nombre == "" or nombre.replace(".", "") == ""
                    )

                    # Mostrar o no entradas vacías
                    if not mostrar_vacias and es_vacia:
                        continue

                    # Agregar entrada
                    archivos.append(
                        {
                            "Nombre": nombre if nombre else "..............",
                            "Tamaño": tam,
                            "Cluster": cluster,
                            "Creado": creado,
                            "Modificado": modif,
                            "entry_pos": entry_pos,
                            "es_vacia": es_vacia,
                        }
                    )

        # Guardar solo archivos reales
        self.archivos = [a for a in archivos if not a.get("es_vacia", False)]
        return archivos

    # ################################################################
    #                   BUSCAR HUECO CONTIGUO 
    # ################################################################
    def hay_hueco_contiguo(self, tamaño):
        
        # Nos ayuda a buscar espacio contiguo libre en los clusters del disco
        # - Calcula cuántos clusters requiere un archivo del tamaño dado
        # - Recorre clusters desde el final del directorio hasta el final del disco
        # - Si encuentra una secuencia de clusters completamente en cero
        #   devuelve el cluster inicial donde se puede escribir el archivo
        # - Si no encuentra espacio suficiente regresa None
        
        clusters_necesarios = math.ceil(tamaño / CLUSTER_SIZE) if tamaño > 0 else 1

        with open(self.disk, "rb") as f:
            cont = 0
            inicio = None

            for c in range(DIR_CLUSTER_END + 1, TOTAL_CLUSTERS):
                f.seek(c * CLUSTER_SIZE)
                data = f.read(CLUSTER_SIZE)

                # Cluster libre == 1024 bytes en cero
                if len(data) < CLUSTER_SIZE:
                    return None

                if all(b == 0 for b in data):
                    if cont == 0:
                        inicio = c
                    cont += 1

                    # Si ya encontro un bloque contiguo suficiente
                    if cont >= clusters_necesarios:
                        return inicio
                else:
                    # Reiniciar conteo si se encuentra cluster ocupado
                    cont = 0
                    inicio = None

        return None

    # ################################################################
    #               COPIAR DESDE FS AL HOST 
    # ################################################################
    def copiar_desde(self, nombre_archivo, destino):
        # Nos ayuda a copiar archivos dentro de la imagen

        # Copia un archivo que está dentro del sistema hacia el host
        with self.lock:
            if self.archivos is None:
                self.enlistar_directorio()

        archivo = next(
            (a for a in self.archivos if a["Nombre"] == nombre_archivo), None
        )
        if not archivo:
            raise FileNotFoundError(f"'{nombre_archivo}' no encontrado")

        cluster = archivo["Cluster"]
        tamaño = archivo["Tamaño"]
        offset = cluster * CLUSTER_SIZE

        # Leer archivo del FS
        with open(self.disk, "rb") as f:
            f.seek(offset)
            datos = f.read(tamaño)

        # Determinar destino
        if os.path.isdir(destino):
            destino_path = os.path.join(destino, nombre_archivo)
        else:
            destino_path = destino

        # Escribir en el host
        with open(destino_path, "wb") as out:
            out.write(datos)

        return destino_path

    # ################################################################
    #                       COPIAR HACIA EL FS 
    # ################################################################
    def copiar_hacia(self, ruta_local):
        
        # Copia un archivo de la compu hacia la imagen
        # - Verifica que el archivo local exista.
        # - Valida que el nombre sea ASCII y <= 14 caracteres.
        # - Verifica que no exista ya un archivo con ese nombre en el FS.
        # - Busca espacio contiguo disponible.
        # - Busca una entrada vacía en el directorio.
        # - Escribe los metadatos de la entrada.
        # - Copia los clusters del archivo al FS.
        # - Notifica a la GUI que hubo cambios.
        
        if not os.path.exists(ruta_local):
            raise FileNotFoundError(f"Archivo local no existe: {ruta_local}")

        nombre_base = os.path.basename(ruta_local)

        # Nombre ASCII obligatorio
        try:
            nombre_base.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("El nombre contiene caracteres no-ASCII")

        if len(nombre_base) > 14:
            raise ValueError(f"Nombre muy largo (max 14): {nombre_base}")

        # si es que no encunetra archivos, los enlista
        with self.lock:
            if self.archivos is None:
                self.enlistar_directorio()

            # Verificar que no exista ya un archivo con ese nomrbe
            if any(a["Nombre"] == nombre_base for a in (self.archivos or [])):
                raise ValueError(f"Ya existe: '{nombre_base}'")

            # Tamaño y clusters requeridos
            tamaño = os.path.getsize(ruta_local)
            clusters_nec = math.ceil(tamaño / CLUSTER_SIZE) if tamaño > 0 else 1

            # Buscar espacio libre contiguo
            inicio = self.hay_hueco_contiguo(tamaño)
            if inicio is None:
                raise RuntimeError(f"No hay espacio para {clusters_nec} clusters")

            pos_entrada = None
            with open(self.disk, "r+b") as f:

                # Buscar entrada vacía en el directorio
                for cl in range(DIR_CLUSTER_START, DIR_CLUSTER_END + 1):
                    for idx in range(ENTRIES_PER_CLUSTER):
                        entry_pos = cl * CLUSTER_SIZE + idx * ENTRY_SIZE
                        f.seek(entry_pos)
                        entry = f.read(ENTRY_SIZE)

                        tipo_b, nombre_b, *_ = ENTRY_STRUCT.unpack(entry)
                        tipo = tipo_b.decode("ascii", errors="ignore")
                        nombre_slot = (
                            nombre_b.decode("ascii", errors="ignore")
                            .rstrip("\x00")
                            .strip()
                        )

                        if (
                            tipo == "-"
                            or nombre_slot == ""
                            or nombre_slot.replace(".", "") == ""
                        ):
                            pos_entrada = entry_pos
                            break

                    if pos_entrada is not None:
                        break

                if pos_entrada is None:
                    raise RuntimeError("No hay entradas libres en directorio")

                # Preparar campos para escribir entrada
                tipo_byte = b"."
                nombre_bytes = nombre_base.encode("ascii").ljust(15, b"\x00")
                ahora = datetime.now().strftime("%Y%m%d%H%M%S")
                creado = ahora.encode("ascii")
                modif = creado

                # Escribir entrada del directorio
                f.seek(pos_entrada)
                f.write(
                    ENTRY_STRUCT.pack(
                        tipo_byte, nombre_bytes, inicio, tamaño, creado, modif
                    )
                )

                # Copiar contenido del archivo en clusters contiguos
                with open(ruta_local, "rb") as src:
                    for i in range(clusters_nec):
                        chunk = src.read(CLUSTER_SIZE)
                        if not chunk:
                            chunk = b""

                        if len(chunk) < CLUSTER_SIZE:
                            chunk = chunk + b"\x00" * (CLUSTER_SIZE - len(chunk))

                        f.seek((inicio + i) * CLUSTER_SIZE)
                        f.write(chunk)

        # Borrar caché y notificar a GUI
        self.archivos = None
        with VCListFiles:
            VCListFiles.notify_all()

    # ################################################################
    #                   ELIMINAR ARCHIVO 
    # ################################################################
    def eliminar(self, nombre):
        
        # Elimina un archivo del sistema
        # - Busca la entrada del archivo por su nombre
        # - Marca la entrada como vacía estableciendo:
        #     tipo='-'
        #     nombre='--------------'
        #     tamaño=0
        #     cluster=0
        # - Limpia todos los clusters que ocupaba el archivo
        #   escribiendo bytes en cero.
        # - Notifica cambios a la interfaz gráfica.
        
        with self.lock:
            if self.archivos is None:
                self.enlistar_directorio()

            archivo = next((a for a in self.archivos if a["Nombre"] == nombre), None)
            if not archivo:
                raise FileNotFoundError(f"'{nombre}' no encontrado")

            entry_pos = archivo.get("entry_pos")

            tipo_byte = b"-"
            nombre_vacio = b"--------------".ljust(15, b"\x00")
            cero_fecha = b"00000000000000"

            with open(self.disk, "r+b") as f:
                # Marcar entrada como vacía
                f.seek(entry_pos)
                f.write(
                    ENTRY_STRUCT.pack(
                        tipo_byte, nombre_vacio, 0, 0, cero_fecha, cero_fecha
                    )
                )

                # Limpiar clusters ocupados
                inicio = archivo["Cluster"]
                clusters_nec = (
                    math.ceil(archivo["Tamaño"] / CLUSTER_SIZE)
                    if archivo["Tamaño"] > 0
                    else 1
                )

                for c in range(inicio, inicio + clusters_nec):
                    if c < TOTAL_CLUSTERS:
                        f.seek(c * CLUSTER_SIZE)
                        f.write(b"\x00" * CLUSTER_SIZE)

        self.archivos = None
        with VCListFiles:
            VCListFiles.notify_all()

class FiUnamFSGUI:
########################################################
# CLASE: FiUnamFSGUI
# Interfaz gráfica para interactuar con la imagen.
# Usa ttk.Treeview para listar archivos y diálogos Tkinter
# para copiar/abrir/eliminar.
########################################################

    # Constructor 
    def __init__(self, root):
        self.root = root
        self.root.title("FiUnamFS v26-1 - Sistema de Archivos") # Configuración del encabezado de la ventana    
        self.root.geometry("900x600")                           # Resolución de la ventana
        self.fs = None                                          # Instancia para la clase FiUnamFS
        self.monitor_thread = None                              # Hilo monitor

        # Construir widgets y abrir el disco por defecto
        self.crear_widgets()
        self.abrir_disco()

    # ###################################################
    #         CREAR LOS COMPONENTES PARA LA GUI   
    # ###################################################
    def crear_widgets(self):
        # Marco con info del sistema
        info_frame = ttk.LabelFrame(
            self.root, text="Informacion del Sistema", padding=10
        )
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.info_label = ttk.Label(
            info_frame, text="Sistema no cargado", font=("Courier", 9)
        )
        self.info_label.pack()

        # Marco que contendrá la tabla / treeview
        table_frame = ttk.LabelFrame(
            self.root, text="Contenido del Directorio", padding=10
        )
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollbar vertical para la tabla
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Columnas de la vista
        columns = ("nombre", "tamaño", "cluster", "creado", "modificado")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set
        )

        # Configurar encabezados y anchos
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

        # Empaquetar treeview y conectar scrollbar
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)

        # Botonera con acciones
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="Actualizar", command=self.actualizar_lista).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame, text="Copiar desde FS", command=self.copiar_desde_fs
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="Copiar hacia FS", command=self.copiar_hacia_fs
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Eliminar", command=self.eliminar_archivo).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            btn_frame, text="Ver Superbloque", command=self.mostrar_superbloque
        ).pack(side=tk.LEFT, padx=5)

    # ########################################################
    #                   CARGA DE IMAGEN 
    # ########################################################
    def abrir_disco(self):
        # Ruta por defecto: fiunamfs.img junto al script
        disk_path = os.path.join(os.path.dirname(__file__), "../fiunamfs.img")

        # Si no existe el archivo por defecto, preguntamos al usuario
        if not os.path.exists(disk_path):
            respuesta = messagebox.askyesno(
                "Disco no encontrado",
                "No se encontro 'fiunamfs.img' en el directorio actual.\n\n"
                "Desea seleccionar una imagen manualmente?",
            )
            if respuesta:
                disk_path = filedialog.askopenfilename(
                    title="Seleccionar imagen FiUnamFS",
                    filetypes=[("Imagenes de disco", "*.img"), ("Todos", "*.*")],
                )
                if not disk_path:
                    messagebox.showerror("Error", "No se selecciono ningun archivo")
                    self.root.quit()
                    return
            else:
                self.root.quit()
                return

        # Intentar inicializar el backend y leer superbloque
        try:
            self.fs = FiUnamFS(disk_path)
            info = self.fs.leer_superbloque()

            # Mostrar información condensada en la etiqueta superior
            self.info_label.config(
                text=f"{info['Nombre']} v{info['Version']} | "
                f"Etiqueta: {info['Etiqueta']} | "
                f"Clusters: {info['Total_Clusters']} | "
                f"Tamano Cluster: {info['Tamano_Cluster']} bytes"
            )

            # Arrancar hilo que espera notificaciones de cambios
            self.monitor_thread = threading.Thread(
                target=self.monitor_cambios, daemon=True
            )
            self.monitor_thread.start()

            # Lista inicial de archivos
            self.actualizar_lista()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el disco:\n{e}")
            self.root.quit()

    # ########################################################
    #           ACtAULIZAR LIStA DE ARCHIVOS
    # ########################################################
    def actualizar_lista(self):
        # Si no hay un FS cargado, salir pronto
        if not self.fs:
            return

        try:
            # Limpiar la tabla
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Obtener todas las entradas (incluye vacías para mostrar)
            archivos = self.fs.enlistar_directorio(mostrar_vacias=True)

            # Insertar cada entrada en el treeview
            for a in archivos:
                if a.get("es_vacia", False):
                    # Entradas vacías en gris
                    self.tree.insert(
                        "",
                        tk.END,
                        values=(
                            a["Nombre"],
                            a["Tamaño"],
                            a["Cluster"],
                            a["Creado"],
                            a["Modificado"],
                        ),
                        tags=("vacia",),
                    )
                else:
                    # Formatear fechas si es posible
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

                    # Mostrar tamaño con separador de miles y "bytes"
                    self.tree.insert(
                        "",
                        tk.END,
                        values=(
                            a["Nombre"],
                            f"{a['Tamaño']:,} bytes",
                            a["Cluster"],
                            creado,
                            modif,
                        ),
                    )

            # Configurar estilo para entradas vacías
            self.tree.tag_configure("vacia", foreground="gray")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo listar:\n{e}")

    # #################################################################
    #       FUNCION PARA COPIAR ARCHIVOS DE LA IMAGEN A TU COMPU
    # #############################################################
    def copiar_desde_fs(self):
        # Obtener selección del treeview
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un archivo primero")
            return

        item = self.tree.item(seleccion[0])
        nombre = item["values"][0]

        # Evitar copiar entradas vacías (nombre formado por puntos)
        if nombre.replace(".", "") == "":
            messagebox.showwarning("Advertencia", "No puede copiar una entrada vacia")
            return

        # Pedir carpeta destino
        destino = filedialog.askdirectory(title="Seleccionar destino")
        if not destino:
            return

        # Intentar copiar utilizando el backend
        try:
            ruta_final = self.fs.copiar_desde(nombre, destino)
            messagebox.showinfo("Exito", f"Archivo copiado:\n{ruta_final}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar:\n{e}")

    # ########################################################
    #       FUNCION PARA MOVER ARCHIVOS DE TU COMPU A LA IMAGEN 
    # ########################################################
    def copiar_hacia_fs(self):
        # Seleccionar archivo local
        archivo = filedialog.askopenfilename(title="Seleccionar archivo")
        if not archivo:
            return

        try:
            # Usar el método del backend para copiar
            self.fs.copiar_hacia(archivo)
            messagebox.showinfo(
                "Exito", f"Archivo '{os.path.basename(archivo)}' copiado al sistema"
            )
            # Refrescar lista para mostrar nuevo archivo
            self.actualizar_lista()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar:\n{e}")

    # ########################################################
    #       ELIMINAR ARCHIVOS DE LA IMAGEN
    # ########################################################
    def eliminar_archivo(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un archivo primero")
            return

        item = self.tree.item(seleccion[0])
        nombre = item["values"][0]

        if nombre.replace(".", "") == "":
            messagebox.showwarning("Advertencia", "No puede eliminar una entrada vacia")
            return

        confirmar = messagebox.askyesno(
            "Confirmar eliminacion", f"Esta seguro de eliminar '{nombre}'?"
        )

        if not confirmar:
            return

        try:
            self.fs.eliminar(nombre)
            messagebox.showinfo("Exito", f"Archivo '{nombre}' eliminado")
            self.actualizar_lista()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")

    # ########################################################
    #  FUNCIÓN PARA IMPRIMIR LA INFORMACIÓN DEL SUPERBLOQUE
    # ########################################################
    def mostrar_superbloque(self):
        if not self.fs:
            return

        try:
            info = self.fs.leer_superbloque()
            texto = "\n".join([f"{k}: {v}" for k, v in info.items()])
            messagebox.showinfo("Informacion del Superbloque", texto)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer:\n{e}")

    # ########################################################
    #       FUNCION PARA MONITOREAR LOS HILOS
    # ########################################################
    def monitor_cambios(self):
        # Este hilo se queda bloqueado esperando una notificación
        # sobre VCListFiles. Cuando recibe una, programa un refresh
        # en el hilo principal de la GUI (root.after).
        while True:
            with VCListFiles:
                VCListFiles.wait()
                # Ejecutar actualizar_lista desde hilo principal tras 100 ms
                self.root.after(100, self.actualizar_lista)

def main():
    root = tk.Tk()
    app = FiUnamFSGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()