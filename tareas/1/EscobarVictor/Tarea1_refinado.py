import threading
import queue
import time
import random

# ----- Parámetros -----
NUM_WORKERS = 3       # cantidad de hilos trabajadores
NUM_TASKS = 10        # número total de "conexiones"
MAX_LATENCIA = 2.0    # segundos máximos de procesamiento simulado

# ----- Cola compartida -----
task_queue = queue.Queue()

# ----- Clase Worker -----
class Worker(threading.Thread):
    def __init__(self, worker_id):
        super().__init__()
        self.worker_id = worker_id
        self.processed = 0
        self.total_time = 0
        self.daemon = True

    def run(self):
        while True:
            tarea = task_queue.get()
            if tarea is None:
                print(f"🛑 Worker {self.worker_id} apagándose...")
                task_queue.task_done()
                break

            start = time.time()
            print(f"⚙️ Worker {self.worker_id} procesando {tarea}")
            time.sleep(random.uniform(0.5, MAX_LATENCIA))
            duracion = time.time() - start

            self.processed += 1
            self.total_time += duracion
            print(f"✅ Worker {self.worker_id} terminó {tarea} "
                  f"({duracion:.2f}s)")
            task_queue.task_done()

    def resumen(self):
        if self.processed == 0:
            prom = 0
        else:
            prom = self.total_time / self.processed
        return (f"👷 Worker {self.worker_id}: "
                f"{self.processed} tareas, "
                f"tiempo total {self.total_time:.2f}s, "
                f"promedio {prom:.2f}s/tarea")

# ----- Función del jefe -----
def boss_func():
    for i in range(NUM_TASKS):
        tarea = f"Conexión #{i}"
        print(f"🌐 Jefe: nueva {tarea}")
        task_queue.put(tarea)
        time.sleep(random.uniform(0.3, 1.0))  # simula llegada irregular

    # Enviar señal de apagado
    for _ in range(NUM_WORKERS):
        task_queue.put(None)

# ----- Programa principal -----
if __name__ == "__main__":
    print("\n🚀 Servidor Web con sincronización y métricas refinadas\n")

    # Crear trabajadores
    workers = [Worker(i) for i in range(NUM_WORKERS)]
    for w in workers:
        w.start()

    # Iniciar jefe
    boss = threading.Thread(target=boss_func)
    boss.start()

    # Esperar finalización
    boss.join()
    task_queue.join()

    print("\n📊 Estadísticas finales:\n")
    for w in workers:
        w.join()
        print(w.resumen())

    total_tareas = sum(w.processed for w in workers)
    total_tiempo = sum(w.total_time for w in workers)
    print(f"\n📦 Total de tareas procesadas: {total_tareas}")
    print(f"⏱️ Tiempo total combinado: {total_tiempo:.2f}s")
    print("\n🏁 Servidor detenido correctamente.\n")
