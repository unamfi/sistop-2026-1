#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui_fiunamfs.py
Interfaz gráfica para el sistema de archivos FiUnamFS usando PyQt5,
con tema oscuro y una interfaz más estilizada.

Reutiliza:
- EstadoFS (estado compartido entre hilos)
- FiUnamFS (lógica del sistema de archivos)
- iniciar_hilo_monitoreo (hilo monitor que corre en segundo plano)

Uso:
    python gui_fiunamfs.py                # intenta abrir 'fiunamfs.img' en el directorio actual
    python gui_fiunamfs.py ruta/imagen.img

Requiere:
    pip install PyQt5
"""

import os
import sys
from typing import Optional

from estado import EstadoFS
from fiunamfs import FiUnamFS
from monitor import iniciar_hilo_monitoreo

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QLabel,
    QStatusBar,
    QGroupBox,
    QToolBar,
    QAction,
    QStyle,
    QMenuBar,
)


# ----------------------------------------------------------------------
# Tema oscuro / estilos
# ----------------------------------------------------------------------
def apply_dark_theme(app: QApplication) -> None:
    """
    Aplica un tema oscuro simple usando el estilo 'Fusion' y un QPalette.
    No requiere librerías externas.

    Se modifican:
    - Colores de ventanas, texto y botones
    - Colores de selección en tablas
    - Apariencia básica de MainWindow, GroupBox, QTableWidget, etc.
    """
    # Estilo base de Qt que se lleva bien con temas manuales.
    app.setStyle("Fusion")

    palette = QPalette()

    # Colores base del tema.
    base_color = QColor(45, 45, 45)
    alt_base = QColor(53, 53, 53)
    text_color = QColor(220, 220, 220)
    disabled_text = QColor(127, 127, 127)
    highlight = QColor(42, 130, 218)

    # Ventanas, fondos y texto.
    palette.setColor(QPalette.Window, base_color)
    palette.setColor(QPalette.WindowText, text_color)
    palette.setColor(QPalette.Base, alt_base)
    palette.setColor(QPalette.AlternateBase, base_color)
    palette.setColor(QPalette.ToolTipBase, text_color)
    palette.setColor(QPalette.ToolTipText, text_color)
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.Button, base_color)
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, highlight)
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))

    # Textos deshabilitados (por ejemplo, botones inactivos).
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)

    app.setPalette(palette)

    # Un poco de stylesheet para pulir detalles visuales (bordes, padding, etc.).
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2d2d2d;
        }
        QLabel#TitleLabel {
            font-size: 18px;
            font-weight: bold;
            padding: 4px 0;
        }
        QLabel#SubtitleLabel {
            font-size: 12px;
            color: #bbbbbb;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 6px;
            margin-top: 10px;
            padding: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #dddddd;
            font-weight: bold;
        }
        QTableWidget {
            gridline-color: #555555;
            selection-background-color: #2a82da;
            selection-color: #000000;
        }
        QHeaderView::section {
            background-color: #3c3c3c;
            padding: 4px;
            border: 1px solid #222222;
            font-weight: bold;
        }
        QPushButton {
            border-radius: 4px;
            padding: 6px 12px;
            border: 1px solid #555555;
            background-color: #3c3c3c;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #2a82da;
        }
        QStatusBar {
            background-color: #262626;
        }
        QToolBar {
            background-color: #262626;
            border-bottom: 1px solid #444444;
        }
        QToolButton {
            padding: 4px;
            margin: 2px;
        }
    """)


# ----------------------------------------------------------------------
# Ventana principal
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación.

    Muestra:
    - Tabla con el contenido del directorio de FiUnamFS.
    - Botones y toolbar para:
        * refrescar directorio
        * copiar desde FS → local
        * copiar desde local → FS
        * eliminar una entrada

    Además:
    - Actualiza periódicamente la barra de estado con estadísticas
      del EstadoFS y espacio libre.
    """
    
    def __init__(self, fs: FiUnamFS, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Objeto que encapsula la lógica de FiUnamFS.
        self.fs = fs
        
        # Lista de entradas actualmente visibles en la tabla
        # (se filtran las entradas vacías).
        self.current_entries = []

        # Configuración básica de la ventana.
        self.setWindowTitle(f"FiUnamFS - {os.path.basename(self.fs.filename)}")
        self.resize(1000, 620)

        # Construimos menús, toolbar, layout central y timer.
        self._setup_menu()
        self._setup_toolbar()
        self._setup_ui()
        self._setup_timers()

        # Cargar el contenido del directorio al inicio.
        self.load_directory()
        # Refrescar estado (estadísticas + espacio libre).
        self.update_status()

    # ------------------------------------------------------------------
    # Menú y toolbar
    # ------------------------------------------------------------------
    def _setup_menu(self):
        """
        Crea la barra de menús con:
        - Archivo: Salir
        - Ayuda : Acerca de…
        """
        menubar: QMenuBar = self.menuBar()

        menu_archivo = menubar.addMenu("&Archivo")
        menu_ayuda = menubar.addMenu("&Ayuda")

        # Acción para salir de la aplicación.
        act_salir = QAction("Salir", self)
        act_salir.triggered.connect(self.close)
        menu_archivo.addAction(act_salir)

        # Acción para mostrar cuadro "Acerca de".
        act_acerca = QAction("Acerca de…", self)
        act_acerca.triggered.connect(self.show_about)
        menu_ayuda.addAction(act_acerca)

    def _setup_toolbar(self):
        """
        Crea la barra de herramientas con acciones rápidas:
        - Refrescar directorio
        - Copiar desde FS
        - Copiar hacia FS
        - Eliminar archivo
        """
        toolbar = QToolBar("Barra de herramientas", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        style = self.style()

        # Acción refrescar: vuelve a leer el directorio desde FiUnamFS.
        self.act_refresh = QAction(
            QIcon(style.standardIcon(QStyle.SP_BrowserReload)), "Refrescar directorio", self
        )
        self.act_refresh.triggered.connect(self.load_directory)
        toolbar.addAction(self.act_refresh)

        # Acción copiar desde FS → sistema local.
        self.act_from_fs = QAction(
            QIcon(style.standardIcon(QStyle.SP_DialogOpenButton)),
            "Copiar desde FiUnamFS → Local",
            self,
        )
        self.act_from_fs.triggered.connect(self.copy_from_fs)
        toolbar.addAction(self.act_from_fs)

        # Acción copiar desde el sistema local hacia FiUnamFS.
        self.act_to_fs = QAction(
            QIcon(style.standardIcon(QStyle.SP_DialogSaveButton)),
            "Copiar desde Local → FiUnamFS",
            self,
        )
        self.act_to_fs.triggered.connect(self.copy_to_fs)
        toolbar.addAction(self.act_to_fs)

        # Acción eliminar archivo dentro de FiUnamFS.
        self.act_delete = QAction(
            QIcon(style.standardIcon(QStyle.SP_TrashIcon)), "Eliminar archivo", self
        )
        self.act_delete.triggered.connect(self.delete_entry)
        toolbar.addAction(self.act_delete)

    # ------------------------------------------------------------------
    # UI central
    # ------------------------------------------------------------------
    def _setup_ui(self):
        """
        Construye el layout principal:
        - título y subtítulo
        - group box con tabla + botones de acción
        - barra de estado
        """
        central = QWidget(self)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        # Título principal de la ventana (parte superior).
        self.label_title = QLabel("Navegador FiUnamFS")
        self.label_title.setObjectName("TitleLabel")
        self.label_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Subtítulo con la ruta absoluta del archivo de imagen.
        self.label_subtitle = QLabel(
            f"Sistema de archivos: {os.path.abspath(self.fs.filename)}"
        )
        self.label_subtitle.setObjectName("SubtitleLabel")
        self.label_subtitle.setWordWrap(True)

        main_layout.addWidget(self.label_title)
        main_layout.addWidget(self.label_subtitle)

        # Grupo que contiene la tabla del directorio.
        group_dir = QGroupBox("Contenido del directorio")
        group_layout = QVBoxLayout()
        group_dir.setLayout(group_layout)
        main_layout.addWidget(group_dir)

        # Tabla donde se muestra cada entrada de directorio no vacía.
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Nombre", "Tipo", "Cluster inicio", "Tamaño (bytes)", "Creado", "Modificado"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        group_layout.addWidget(self.table)

        # Botones en la parte inferior (acciones duplicadas a la toolbar).
        buttons_layout = QHBoxLayout()

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_from_fs = QPushButton("Copiar desde FiUnamFS")
        self.btn_to_fs = QPushButton("Copiar hacia FiUnamFS")
        self.btn_delete = QPushButton("Eliminar")

        # Alineamos los botones a la derecha.
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.btn_refresh)
        buttons_layout.addWidget(self.btn_from_fs)
        buttons_layout.addWidget(self.btn_to_fs)
        buttons_layout.addWidget(self.btn_delete)

        group_layout.addLayout(buttons_layout)

        # Conexión de señales de los botones con los métodos correspondientes.
        self.btn_refresh.clicked.connect(self.load_directory)
        self.btn_from_fs.clicked.connect(self.copy_from_fs)
        self.btn_to_fs.clicked.connect(self.copy_to_fs)
        self.btn_delete.clicked.connect(self.delete_entry)

        # Barra de estado ubicada en la parte inferior de la ventana.
        status = QStatusBar()
        self.setStatusBar(status)

    def _setup_timers(self):
        """
        Configura el temporizador que actualiza periódicamente
        la barra de estado (estadísticas + espacio libre).
        """
        # Timer para actualizar estadísticas (estado + espacio libre).
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        # Intervalo de actualización: cada 5 segundos.
        self.timer.start(5000)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def load_directory(self):
        """
        Lee el directorio de FiUnamFS y lo muestra en la tabla.

        Se filtran las entradas vacías (is_empty() == False) y se
        almacenan en self.current_entries para que otras operaciones
        (copiar, eliminar) sepan qué entrada está seleccionada.
        """
        try:
            # Usamos el lock interno del FS por seguridad.
            with self.fs.lock:
                entries = self.fs.leer_directorio()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al leer directorio:\n{e}")
            return

        # Filtramos las entradas vacías (libres).
        visibles = [e for e in entries if not e.is_empty()]
        self.current_entries = visibles

        # Ajustamos el número de filas de la tabla.
        self.table.setRowCount(len(visibles))
        for row, e in enumerate(visibles):
            self.table.setItem(row, 0, QTableWidgetItem(e.name))
            self.table.setItem(row, 1, QTableWidgetItem(e.type))
            self.table.setItem(row, 2, QTableWidgetItem(str(e.start)))
            self.table.setItem(row, 3, QTableWidgetItem(str(e.size)))
            self.table.setItem(row, 4, QTableWidgetItem(e.created))
            self.table.setItem(row, 5, QTableWidgetItem(e.modified))

        # Ajustamos el ancho de columnas según el contenido.
        self.table.resizeColumnsToContents()

    def _get_selected_entry(self):
        """
        Devuelve la DirEntry correspondiente a la fila actualmente
        seleccionada en la tabla, o None si no hay selección válida.
        """
        row = self.table.currentRow()
        if row < 0 or row >= len(self.current_entries):
            return None
        return self.current_entries[row]

    # ------------------------------------------------------------------
    # Operaciones de archivo
    # ------------------------------------------------------------------
    def copy_from_fs(self):
        """
        Copiar archivo de la imagen FiUnamFS al sistema local.

        Flujo:
        - Tomar la entrada seleccionada en la tabla
        - Pedir ruta de destino al usuario (diálogo de guardar)
        - Llamar a fs.copiar_desde(...)
        """
        entry = self._get_selected_entry()
        if entry is None:
            QMessageBox.warning(
                self,
                "Selecciona un archivo",
                "Selecciona una fila del directorio primero.",
            )
            return

        # Proponemos el nombre de la entrada como nombre por defecto.
        default_name = entry.name.strip() or "archivo"
        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar archivo desde FiUnamFS",
            default_name,
            "Todos los archivos (*)",
        )
        if not dest_path:
            # Usuario canceló el diálogo.
            return

        try:
            # El método de FS ya se sincroniza con el lock interno.
            self.fs.copiar_desde(entry.name, dest_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al copiar:\n{e}")
            return

        # Si el archivo efectivamente existe, notificamos éxito.
        if os.path.exists(dest_path):
            QMessageBox.information(
                self,
                "Copiado",
                f"Archivo '{entry.name}' copiado a:\n{dest_path}",
            )

        # Actualizamos la barra de estado.
        self.update_status()

    def copy_to_fs(self):
        """
        Copiar archivo del sistema local hacia la imagen FiUnamFS.

        Flujo:
        - Pedir archivo local (diálogo de abrir)
        - Sugerir nombre dentro de FiUnamFS (máx. 14 caracteres)
        - Llamar a fs.copiar_hacia(...)
        - Recargar directorio y estado
        """
        local_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo local", "", "Todos los archivos (*)"
        )
        if not local_path:
            # Usuario canceló el diálogo.
            return

        # Obtenemos el nombre base del archivo (sin ruta).
        base = os.path.basename(local_path)
        # En FiUnamFS el nombre es de 14 caracteres máximo.
        default_name = base[:14]

        # Cuadro de entrada de texto para el nombre dentro del FS.
        name, ok = QInputDialog.getText(
            self,
            "Nombre en FiUnamFS",
            "Nombre dentro de FiUnamFS (máx. 14 caracteres, sin rutas):",
            text=default_name,
        )
        if not ok or not name.strip():
            # Cancelado o nombre vacío.
            return

        name = name.strip()
        if len(name) > 14:
            # Avisamos que el nombre será truncado.
            QMessageBox.warning(
                self,
                "Nombre truncado",
                "El nombre excedía 14 caracteres, se truncará automáticamente.",
            )
            name = name[:14]

        try:
            self.fs.copiar_hacia(local_path, name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al copiar:\n{e}")
            return

        # Recargamos directorio y estado después de la operación.
        self.load_directory()
        self.update_status()

    def delete_entry(self):
        """
        Eliminar un archivo de la imagen FiUnamFS.

        Flujo:
        - Tomar la entrada seleccionada
        - Confirmar con un QMessageBox
        - Llamar a fs.eliminar(...)
        - Recargar directorio y estado
        """
        entry = self._get_selected_entry()
        if entry is None:
            QMessageBox.warning(
                self,
                "Selecciona un archivo",
                "Selecciona una fila del directorio primero.",
            )
            return

        # Confirmación de eliminación (sí/no).
        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar definitivamente '{entry.name}' de FiUnamFS?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        try:
            self.fs.eliminar(entry.name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al eliminar:\n{e}")
            return

        # Refrescamos tabla y estado tras eliminar.
        self.load_directory()
        self.update_status()

    # ------------------------------------------------------------------
    # Estado / monitor
    # ------------------------------------------------------------------
    def update_status(self):
        """
        Lee estado compartido y espacio libre, y lo muestra en la barra de estado.

        Formato del mensaje:
        "Leídos: X | Escritos: Y | Eliminados: Z | Último: ... | Libres: N clusters (M KiB)"
        """
        try:
            # Protegemos la lectura de estado y el cálculo del espacio libre.
            with self.fs.lock:
                estado = self.fs.estado
                libres_clusters, libres_bytes = self.fs.calcular_espacio_libre()
        except Exception as e:
            self.statusBar().showMessage(f"Error al actualizar estado: {e}")
            return

        msg = (
            f"Leídos: {estado.leidos} | "
            f"Escritos: {estado.escritos} | "
            f"Eliminados: {estado.eliminados} | "
            f"Último: {estado.ultimo_evento or 'Ninguno'} | "
            f"Libres: {libres_clusters} clusters "
            f"({libres_bytes / 1024:.2f} KiB)"
        )
        self.statusBar().showMessage(msg)

    # ------------------------------------------------------------------
    # Acerca de
    # ------------------------------------------------------------------
    def show_about(self):
        """
        Muestra un mensaje informativo sobre la aplicación.
        """
        QMessageBox.information(
            self,
            "Acerca de FiUnamFS GUI",
            (
                "Interfaz gráfica para el microsistema de archivos FiUnamFS.\n\n"
                "Permite listar, copiar y eliminar archivos dentro de la imagen,\n"
                "cumpliendo con los requisitos de concurrencia del proyecto."
            ),
        )


# ----------------------------------------------------------------------
# Creación de FS
# ----------------------------------------------------------------------
def crear_fs_con_dialogo(app: QApplication) -> Optional[FiUnamFS]:
    """
    Intenta crear FiUnamFS usando la ruta de la línea de comandos o 'fiunamfs.img'.

    Flujo:
    - Si se pasó una ruta por línea de comandos, se intenta usar primero.
    - Si no existe, se muestra un diálogo para seleccionar la imagen.
    - Si el usuario cancela, se devuelve None.
    """
    estado = EstadoFS()
    # Tomamos imagen de argv o usamos la ruta por defecto.
    image_path = sys.argv[1] if len(sys.argv) > 1 else "fiunamfs.img"

    while True:
        try:
            # Si se logra construir el objeto, devolvemos inmediatamente.
            fs = FiUnamFS(image_path, estado)
            return fs
        except FileNotFoundError:
            # Imagen no encontrada: pedimos al usuario seleccionar otra.
            QMessageBox.warning(
                None,
                "Imagen no encontrada",
                f"No se encontró la imagen '{image_path}'. "
                "Selecciona la imagen FiUnamFS (archivo .img).",
            )
            path, _ = QFileDialog.getOpenFileName(
                None,
                "Seleccionar imagen FiUnamFS",
                "",
                "Imagenes FiUnamFS (*.img);;Todos los archivos (*)",
            )
            if not path:
                # Usuario canceló la selección.
                return None
            image_path = path
        except Exception as e:
            # Cualquier otro error al abrir la imagen.
            QMessageBox.critical(
                None,
                "Error al abrir imagen",
                f"No se pudo abrir la imagen '{image_path}':\n{e}",
            )
            return None


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main():
    """
    Punto de entrada de la aplicación GUI.

    Pasos:
    - Crear QApplication
    - Aplicar tema oscuro
    - Crear objeto FiUnamFS (con diálogo de selección si es necesario)
    - Lanzar hilo monitor
    - Mostrar ventana principal
    """
    app = QApplication(sys.argv)

    # Aplicamos tema oscuro estilizado.
    apply_dark_theme(app)

    fs = crear_fs_con_dialogo(app)
    if fs is None:
        # Si no se pudo seleccionar/abrir una imagen, salimos sin error.
        return

    # Lanzamos el hilo monitor para cumplir con el requisito de concurrencia.
    iniciar_hilo_monitoreo(fs)

    window = MainWindow(fs)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()