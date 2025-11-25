# monitor.py
# Hilo secundario que consulta periódicamente el estado del sistema
# de archivos y muestra estadísticas simples.

import threading
import time


def _hilo_monitoreo(fs):
    """
    Hilo que corre en segundo plano, consulta el estado compartido
    y muestra información cada cierto intervalo.

    Parámetros:
    - fs: instancia de FiUnamFS, que expone:
          * fs.estado              (EstadoFS con contadores)
          * fs.calcular_espacio_libre()
          * fs.lock                (para sincronizar acceso)
    """
    while True:
        # Esperamos un intervalo fijo antes de cada muestreo.    
        time.sleep(5)
        
        # Proteger el acceso al estado y a calcular_espacio_libre()
        # para evitar que otra operación lo modifique en medio de la lectura.
        with fs.lock:
            libres_clusters, libres_bytes = fs.calcular_espacio_libre()
            estado = fs.estado
            
            # Reporte de operaciones acumuladas.
            print("\n[MONITOR] Operaciones: "
                  f"leídos={estado.leidos}, "
                  f"escritos={estado.escritos}, "
                  f"eliminados={estado.eliminados}")
            # Último evento registrado en el EstadoFS.
            print("[MONITOR] Último evento:",
                  estado.ultimo_evento or "Ninguno")
            # Estimación de espacio libre en clusters y KiB.
            print("[MONITOR] Clusters libres aprox.: "
                  f"{libres_clusters} "
                  f"({libres_bytes / 1024:.2f} KiB)")


def iniciar_hilo_monitoreo(fs):
    """
    Lanza el hilo monitor como demonio.

    El hilo:
    - se ejecuta en segundo plano
    - termina automáticamente cuando el programa principal finaliza
    """
    # Creamos el hilo apuntando a _hilo_monitoreo y lo marcamos como daemon.
    t = threading.Thread(target=_hilo_monitoreo, args=(fs,), daemon=True)
    t.start()
