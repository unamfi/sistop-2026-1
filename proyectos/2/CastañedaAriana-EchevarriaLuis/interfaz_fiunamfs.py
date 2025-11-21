"""
Módulo de Interfaz Gráfica (Frontend) para FiUnamFS.

Este script implementa una GUI moderna utilizando Tkinter para interactuar
con el sistema de archivos. Su responsabilidad es manejar la entrada del usuario,
mostrar datos visualmente y delegar las operaciones lógicas a la clase FiUnamFS
en un hilo secundario para mantener la fluidez.

Autores: Castañeda Ariana, Echevarria Luis.
Materia: Sistemas Operativos
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import threading
from fiunamfs import FiUnamFS, EXPECTED_VERSION, OFF_VERSION, LEN_VERSION, ENTRY_SIZE

class FiUnamFS_Frontend:
    """
    Clase principal de la interfaz gráfica.
    
    Gestiona la ventana principal, la carga de imágenes de disco, la visualización
    del directorio en una tabla (Treeview) y la ejecución asíncrona de comandos.
    """

    def __init__(self, root):
        self.root = root
        self.root.title(f"Administrador FiUnamFS (v{EXPECTED_VERSION.decode()})")
        
        self.root.geometry("1400x900")
        try: self.root.state('zoomed') 
        except: pass 
        
        self.fs = None 

        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("Treeview", rowheight=40, font=('Segoe UI', 12))
        self.style.configure("Treeview.Heading", font=('Segoe UI', 12, 'bold'))
        self.style.configure("TButton", font=('Segoe UI', 11), padding=10)
        self.style.configure("TLabel", font=('Segoe UI', 11))
        self.style.configure("TLabelframe.Label", font=('Segoe UI', 12, 'bold'))

        # --- DEFINICIÓN DEL LAYOUT ---
        
        # 1. Barra Superior: Controles de carga y diagnóstico
        frame_top = ttk.LabelFrame(root, text="Sistema de Archivos", padding=10)
        frame_top.pack(fill='x', padx=20, pady=10)
        
        self.btn_load = ttk.Button(frame_top, text="📂 Cargar Disco (.img)", command=self.load_disk)
        self.btn_load.pack(side='left', padx=10)
        
        self.lbl_status_img = ttk.Label(frame_top, text="Ningún disco cargado", foreground="gray")
        self.lbl_status_img.pack(side='left', padx=20)

        # Botón información del disco
        self.btn_info = ttk.Button(frame_top, text="ℹ️ Ver Info Disco", command=self.show_info, state='disabled')
        self.btn_info.pack(side='right', padx=10)

        # 2. Tabla Central: Visualización de contenidos del directorio
        frame_tree = ttk.Frame(root, padding=(20, 0, 20, 0))
        frame_tree.pack(fill='both', expand=True)
        
        cols = ('index', 'name', 'size', 'cluster', 'date')
        self.tree = ttk.Treeview(frame_tree, columns=cols, show='headings')
        
        self.tree.heading('index', text='#')
        self.tree.heading('name', text='Nombre Archivo')
        self.tree.heading('size', text='Tamaño (Bytes)')
        self.tree.heading('cluster', text='Cluster Ini')
        self.tree.heading('date', text='Fecha Creación')
        
        self.tree.column('index', width=80, anchor='center')
        self.tree.column('name', width=500, anchor='w')
        self.tree.column('size', width=200, anchor='e')
        self.tree.column('cluster', width=150, anchor='center')
        self.tree.column('date', width=300, anchor='center')
        
        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 3. Panel Inferior: Botones de operación (Importar/Exportar/Borrar)
        frame_actions = ttk.LabelFrame(root, text="Operaciones", padding=20)
        frame_actions.pack(fill='x', padx=20, pady=20)

        frame_actions.columnconfigure(0, weight=1)
        frame_actions.columnconfigure(1, weight=1)
        frame_actions.columnconfigure(2, weight=1)

        self.btn_import = ttk.Button(frame_actions, text="⬇️ Importar (Copiar al Disco)", command=self.copy_in, state='disabled')
        self.btn_import.grid(row=0, column=0, padx=20, sticky='ew')

        self.btn_export = ttk.Button(frame_actions, text="⬆️ Exportar (Guardar en PC)", command=self.copy_out, state='disabled')
        self.btn_export.grid(row=0, column=1, padx=20, sticky='ew')

        self.btn_delete = ttk.Button(frame_actions, text="🗑️ Eliminar", command=self.delete_file, state='disabled')
        self.btn_delete.grid(row=0, column=2, padx=20, sticky='ew')

        # 4. Barra de Estado
        self.status_var = tk.StringVar(value="Sistema listo.")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief='sunken', anchor='w', padding=10, font=('Consolas', 11))
        status_bar.pack(side='bottom', fill='x')

    # --- LÓGICA ---

    def set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def toggle_controls(self, enable=True):
        state = 'normal' if enable else 'disabled'
        self.btn_import.config(state=state)
        self.btn_export.config(state=state)
        self.btn_delete.config(state=state)
        self.btn_info.config(state=state)
        self.btn_load.config(state='normal')

    def load_disk(self, path=None):
        """
        Solicita al usuario un archivo .img e intenta montarlo mediante el backend.
        
        Maneja excepciones específicas de versión para ofrecer un flujo de
        reparación automática en caso de detectar incompatibilidades (ej. v26-2).
        """

        if not path:
            path = filedialog.askopenfilename(title="Seleccionar Disco", filetypes=[("Archivo de Disco", "*.img"), ("Todos", "*.*")])
        if not path: return

        try:
            self.fs = FiUnamFS(path)
            self.lbl_status_img.config(text=f"✅ {os.path.basename(path)}", foreground="green")
            self.refresh_list()
            self.toggle_controls(True)
            
        except ValueError as e:
            err_msg = str(e)
            if "Versión inválida" in err_msg or "Identificador inválido" in err_msg:
                self.set_status("⚠️ Error de versión.")
                if messagebox.askyesno("Versión Incompatible", f"Error: {err_msg}\n\n¿Desea reparar el disco automáticamente?"):
                    self.auto_repair_and_load(path)
                else:
                    self.lbl_status_img.config(text="❌ Error Versión", foreground="red")
            else:
                messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error Crítico", f"No se pudo cargar:\n{e}")
            self.lbl_status_img.config(text="Error", foreground="red")

    def auto_repair_and_load(self, src_path):
        try:
            dir_name = os.path.dirname(src_path)
            base_name = os.path.basename(src_path)
            default_name = os.path.splitext(base_name)[0] + "_reparado.img"
            
            dest_path = filedialog.asksaveasfilename(
                title="Guardar Reparado", 
                initialdir=dir_name,
                initialfile=default_name,
                defaultextension=".img"
            )
            if not dest_path: 
                self.set_status("Reparación cancelada.")
                return

            self._perform_repair(src_path, dest_path)
            messagebox.showinfo("Éxito", "Disco reparado.")
            self.load_disk(dest_path)
        except Exception as e:
            messagebox.showerror("Error", f"Falló la reparación: {e}")

    def _perform_repair(self, src, dst):
        """
        Realiza una copia bit a bit del disco original y parchea la versión
        en el superbloque a la esperada (26-1).
        """
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
            fdst.write(fsrc.read())
        with open(dst, 'r+b') as f:
            f.seek(OFF_VERSION)
            f.write(EXPECTED_VERSION.ljust(LEN_VERSION, b'\x00'))
            f.flush(); os.fsync(f.fileno())

    def refresh_list(self):
        """
        Actualiza la tabla visual con los datos actuales del sistema de archivos.
        Calcula dinámicamente el uso de espacio y la ocupación del directorio.
        """

        for item in self.tree.get_children(): self.tree.delete(item)
        
        try:
            files = self.fs.list_files()
            total_bytes = 0
            for f in files:
                total_bytes += f['size']
                cts = f['created'].strftime('%Y-%m-%d %H:%M') if hasattr(f['created'], 'strftime') else str(f['created'])
                self.tree.insert('', 'end', values=(f['index'], f['name'], f'{f["size"]:,}', f['cluster_init'], cts))
            
            # --- CÁLCULOS DE ESTADO ---
            
            # 1. Capacidad del Directorio (Cuántos archivos caben máximo)
            dir_bytes = self.fs.dir_clusters * self.fs.cluster_size
            max_files = dir_bytes // ENTRY_SIZE
            
            # 2. Uso del Disco (Espacio de datos)
            total_cap = self.fs.total_clusters * self.fs.cluster_size
            free_bytes = total_cap - total_bytes
            percent = (total_bytes / total_cap) * 100 if total_cap > 0 else 0
            
            # Actualizar barra de estado con datos reales
            self.set_status(f"Archivos: {len(files)}/{max_files} | Usado: {total_bytes/1024:.1f} KB ({percent:.1f}%) | Libre: {free_bytes/1024:.1f} KB")
            
        except Exception as e:
            self.set_status(f"Error al listar contenido: {e}")

    def show_info(self):
        if not self.fs: return
        
        # Crear ventana personalizada
        info_win = tk.Toplevel(self.root)
        info_win.title("Info Disco")
        info_win.geometry("430x450")
        info_win.resizable(False, False)
        info_win.grab_set()

        frm = ttk.Frame(info_win, padding=20)
        frm.pack(fill='both', expand=True)

        font_lbl = ('Segoe UI', 10, 'bold')
        font_val = ('Segoe UI', 10)

        sb = self.fs.sb
        capacidad = self.fs.total_clusters * self.fs.cluster_size / 1024
        
        datos = [
            ("Identificador", sb['ident'].decode()),
            ("Versión", sb['version'].decode()),
            ("Etiqueta", sb['label'].decode()),
            ("---", "---"), 
            ("Tamaño Cluster", f"{self.fs.cluster_size} bytes"),
            ("Clusters Dir.", f"{self.fs.dir_clusters} (Reservados)"),
            ("Total Clusters", f"{self.fs.total_clusters}"),
            ("Capacidad Total", f"{capacidad:.2f} KB")
        ]

        row = 0
        for titulo, valor in datos:
            if titulo == "---":
                ttk.Separator(frm, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
            else:
                ttk.Label(frm, text=f"{titulo}:", font=font_lbl, anchor='w').grid(row=row, column=0, sticky='w', pady=2)
                ttk.Label(frm, text=valor, font=font_val, anchor='w').grid(row=row, column=1, sticky='w', pady=2, padx=10)
            row += 1

        ttk.Button(frm, text="Cerrar", command=info_win.destroy).grid(row=row+1, column=0, columnspan=2, pady=15)

    # --- HILOS Y ASYNC ---
    
    def run_async(self, target_func, success_msg):
        """
        Wrapper para ejecución asíncrona.
        
        Ejecuta una función bloqueante (operaciones de disco) en un hilo separado (Daemon)
        para evitar que la interfaz gráfica se congele.
        
        Argumentos:
            target_func (callable): La función del backend a ejecutar (ej. fs.write_file).
            success_msg (str): Mensaje a mostrar si la operación termina bien.
        """

        def wrapper():
            try:
                target_func()
                self.root.after(0, lambda: self.on_success(success_msg))
            except Exception as e:
                # Capturamos el error como string para evitar NameError
                msg_err = str(e)
                self.root.after(0, lambda: messagebox.showerror("Error de Operación", msg_err))
            finally:
                self.root.after(0, lambda: self.toggle_controls(True))

        self.toggle_controls(False)
        self.set_status("⏳ Procesando operación... espere.")
        threading.Thread(target=wrapper, daemon=True).start()

    def on_success(self, msg):
        messagebox.showinfo("Éxito", msg)
        self.refresh_list()

    def copy_in(self):
        """
        Manejador del botón Importar. Solicita ruta y nombre destino.
        """
        src = filedialog.askopenfilename()
        if not src: return
        name = simpledialog.askstring("Importar", "Nombre en disco:", initialvalue=os.path.basename(src), parent=self.root)
        if not name: return
        self.run_async(lambda: self.fs.write_file(src, name), f"Importado: {name}")

    def copy_out(self):
        """
        Manejador del botón Exportar. Verifica selección y solicita destino.
        """
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Ojo", "Seleccione un archivo.")
        name = self.tree.item(sel[0])['values'][1]
        dst = filedialog.asksaveasfilename(initialfile=name)
        if not dst: return
        self.run_async(lambda: self.fs.read_file(name, dst), f"Exportado a: {dst}")

    def delete_file(self):
        """
        Manejador del botón Eliminar. Pide confirmación antes de proceder.
        """
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Ojo", "Seleccione un archivo.")
        name = self.tree.item(sel[0])['values'][1]
        if messagebox.askyesno("Borrar", f"¿Eliminar '{name}'?"):
            self.run_async(lambda: self.fs.delete_file(name), f"Eliminado: {name}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FiUnamFS_Frontend(root)
    root.mainloop()