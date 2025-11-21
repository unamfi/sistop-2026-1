import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import fiunamfs

#Colores de mis practicas (catppuccin)
MOCHA = {
    "bg": "#1E1E2E",        # mocha-bg
    "fg": "#CDD6F4",        # mocha-fg
    "blue": "#89B4FA",      # mocha-blue
    "surface0": "#313244",  # mocha-surface0
    "sky": "#89DCEB",       # mocha-sky
    "green": "#A6E3A1",     # mocha-green
    "peach": "#FAB387",     # mocha-peach
    "mauve": "#CBA6F7"      # mocha-mauve
}

class FiUnamFS_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FiUnamFS - Gestor de Archivos")
        self.root.geometry("1920x1080")
        
        self.archivo_img = "fiunamfs.img"
        
        #Validacion inicial
        if not os.path.exists(self.archivo_img):
            messagebox.showerror("Error", f"No se encuentra {self.archivo_img}")
            root.destroy()
            return

        # Configuracion de colores
        self.configurar_estilos()

        #Frame de arriba (titulo)
        frame_top = tk.Frame(root, bg=MOCHA["bg"], pady=15)
        frame_top.pack(fill=tk.X)
        
        lbl_titulo = tk.Label(frame_top, text="Sistema de Archivos FiUnamFS", 
                              font=("Segoe UI", 16, "bold"), 
                              bg=MOCHA["bg"], fg=MOCHA["mauve"])
        lbl_titulo.pack()

        #Frame del centro
        frame_list = tk.Frame(root, bg=MOCHA["bg"], padx=20, pady=10)
        frame_list.pack(fill=tk.BOTH, expand=True)
        
        #Definicion de columnas
        columns = ('nombre', 'tamano', 'cluster')
        self.tree = ttk.Treeview(frame_list, columns=columns, show='headings', style="Custom.Treeview")
        
        self.tree.heading('nombre', text='Nombre de Archivo')
        self.tree.heading('tamano', text='Tamaño (Bytes)')
        self.tree.heading('cluster', text='Cluster Inicial')
        
        self.tree.column('nombre', width=250)
        self.tree.column('tamano', width=120, anchor='e')
        self.tree.column('cluster', width=120, anchor='center')
        
        #Barrita lateral personalizada
        scrollbar = ttk.Scrollbar(frame_list, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        #Frame de abajo (botones)
        frame_btn = tk.Frame(root, bg=MOCHA["bg"], pady=20)
        frame_btn.pack(fill=tk.X)
        
        ttk.Button(frame_btn, text="📥 Importar (PC -> FS)", command=self.importar).pack(side=tk.LEFT, padx=20)
        ttk.Button(frame_btn, text="📤 Extraer (FS -> PC)", command=self.extraer).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_btn, text="🗑️ Eliminar", command=self.eliminar).pack(side=tk.LEFT, padx=5)
        
        #Boton refrescar a la derecha
        ttk.Button(frame_btn, text="🔄 Refrescar", command=self.cargar_datos).pack(side=tk.RIGHT, padx=20)

        #Se cargan los datos iniciales
        self.cargar_datos()

    def configurar_estilos(self):
        self.root.configure(bg=MOCHA["bg"])
        
        style = ttk.Style()
        style.theme_use('clam')

        #Estilo para frames y etiquetas
        style.configure("TFrame", background=MOCHA["bg"])
        style.configure("TLabel", background=MOCHA["bg"], foreground=MOCHA["fg"])

        #Estilo para latabla (treeview)
        style.configure("Custom.Treeview", 
                        background=MOCHA["bg"], 
                        fieldbackground=MOCHA["bg"], 
                        foreground=MOCHA["fg"],
                        borderwidth=0,
                        rowheight=25)
        
        # Color seleccion
        style.map("Custom.Treeview", 
                  background=[('selected', MOCHA["surface0"])],
                  foreground=[('selected', MOCHA["blue"])])

        #Estilo para los encabezados
        style.configure("Treeview.Heading", 
                        background=MOCHA["surface0"], 
                        foreground=MOCHA["blue"],
                        font=('Segoe UI', 10, 'bold'),
                        borderwidth=0)
        
        style.map("Treeview.Heading", 
                  background=[('active', MOCHA["surface0"])])

        #Estilo para botones
        style.configure("TButton", 
                        background=MOCHA["surface0"], 
                        foreground=MOCHA["fg"],
                        font=('Segoe UI', 9),
                        borderwidth=0,
                        focusthickness=3,
                        focuscolor=MOCHA["surface0"],
                        padding=6)
        
        #Efectos de botones (hover y cuando se presionan)
        style.map("TButton", 
                  background=[('active', MOCHA["blue"]), ('pressed', MOCHA["mauve"])],
                  foreground=[('active', MOCHA["bg"]), ('pressed', MOCHA["bg"])])
        
        style.configure("Vertical.TScrollbar", 
                        background=MOCHA["surface0"], 
                        troughcolor=MOCHA["bg"],
                        bordercolor=MOCHA["bg"],
                        arrowcolor=MOCHA["fg"])

    def cargar_datos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        archivos = fiunamfs.listar_contenido(self.archivo_img)
        
        for archivo in archivos:
            self.tree.insert('', tk.END, values=(archivo['nombre'], archivo['tamano'], archivo['cluster']))

    def importar(self):
        ruta_local = filedialog.askopenfilename(title="Seleccionar archivo para subir")
        if ruta_local:
            nombre = os.path.basename(ruta_local)
            if len(nombre) > 15:
                messagebox.showwarning("Nombre muy largo", "El nombre debe tener maximo 15 caracteres.")
                return
            try:
                #Se verifica que la funcion exista en el backend 
                fiunamfs.copiar_a_fiunamfs(self.archivo_img, ruta_local)
                messagebox.showinfo("Éxito", f"Archivo {nombre} importado correctamente.")
                self.cargar_datos()
            except Exception as e:
                messagebox.showerror("Error", f"Fallo al importar: {e}")

    def extraer(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Selecciona un archivo de la lista primero.")
            return
        item = self.tree.item(seleccion[0])
        nombre_archivo = item['values'][0]
        try:
            fiunamfs.copiar_de_fiunamfs(self.archivo_img, nombre_archivo)
            messagebox.showinfo("Éxito", f"Archivo {nombre_archivo} extraido a tu carpeta local.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al extraer: {e}")

    def eliminar(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Selecciona un archivo de la lista primero.")
            return
        item = self.tree.item(seleccion[0])
        nombre_archivo = item['values'][0]
        confirmar = messagebox.askyesno("Confirmar", f"¿Seguro que deseas eliminar '{nombre_archivo}'?")
        if confirmar:
            try:
                fiunamfs.eliminar_archivo(self.archivo_img, nombre_archivo)
                messagebox.showinfo("Éxito", "Archivo eliminado.")
                self.cargar_datos()
            except Exception as e:
                messagebox.showerror("Error", f"Fallo al eliminar: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FiUnamFS_GUI(root)
    root.mainloop()
