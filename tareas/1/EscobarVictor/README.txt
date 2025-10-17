Ejercicio: Servidor Web (jefe–trabajador) — Versión Refinada
Lenguaje: Python 3.10+
Ejecución:
    python3 Tarea1_refinado.py

Requisitos:
    Python 3.x (sin librerías externas)
    Compatible con Linux, macOS o Windows

Estrategia de sincronización:
    Se usa la clase queue.Queue, que implementa internamente un monitor
    con exclusión mutua (mutex) y variables de condición, permitiendo
    sincronización segura entre los hilos productores (jefe) y
    consumidores (trabajadores).

Refinamientos implementados:
    - Clase Worker con métricas individuales (tiempo total y promedio)
    - Estadísticas globales al final de la ejecución
    - Apagado controlado mediante señales (None)
    - Interfaz de salida más clara y estética

Descripción:
    El programa simula un servidor web con un jefe que genera tareas
    (simulando conexiones entrantes) y un conjunto de trabajadores que
    procesan dichas tareas concurrentemente. Los trabajadores permanecen
    bloqueados cuando no hay tareas y se despiertan automáticamente al
    llegar nuevas solicitudes.
