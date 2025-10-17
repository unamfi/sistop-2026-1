import threading
import time
import random
from queue import Queue

SILLAS = 3
NUM_ALUMNOS = 10
cola_espera = Queue() # Cola FIFO para manejar el orden de llegada de los alumnos

profesor = threading.Semaphore(0)  # Semáforo que indica que hay un alumno esperando
alumno_listo = threading.Semaphore(0)  # Semáforo que indica que el alumno puede ser atendido
atendidos_lock = threading.Lock() #actualizar el contador de alumnos que entran
atendidos = 0  # Contador global de alumnos atendidos

# Función del profesor
def asesor():
    global atendidos
    while True:
        profesor.acquire()  # Espera a que llegue un alumno
        alumno_id = cola_espera.get()
        print(f"Profesor despierta para atender al alumno {alumno_id}.")
        alumno_listo.release()
        print(f"Profesor atendiendo al alumno {alumno_id}...")
        time.sleep(random.uniform(0.05, 0.2))
        print(f"Profesor terminó con el alumno {alumno_id}.")
        with atendidos_lock:
            atendidos += 1
            if atendidos == NUM_ALUMNOS_QUE_ENTRAN:  # Termina si todos los que entraron fueron atendidos
                break
    print("Todos los alumnos atendidos. Profesor se va a casa.")

# Función del alumno
NUM_ALUMNOS_QUE_ENTRAN = 0
NUM_ALUMNOS_LOCK = threading.Lock()

def alumno(id):
    global NUM_ALUMNOS_QUE_ENTRAN
    time.sleep(random.uniform(0.01, 0.1))
    if cola_espera.qsize() < SILLAS:
        cola_espera.put(id)
        with NUM_ALUMNOS_LOCK:
            NUM_ALUMNOS_QUE_ENTRAN += 1
        print(f"Alumno {id} llegó y espera su turno. ({cola_espera.qsize()}/{SILLAS} sillas ocupadas)")
        profesor.release()
        alumno_listo.acquire()
        print(f"Alumno {id} está siendo atendido.")
    else:
        print(f"Alumno {id} se fue, no hay sillas disponibles.")

# Programa principal
if __name__ == "__main__":
    print("Iniciando simulación...\n")
    
    hilo_profesor = threading.Thread(target=asesor)
    hilo_profesor.start()

    hilos_alumnos = []
    for i in range(NUM_ALUMNOS):
        t = threading.Thread(target=alumno, args=(i+1,))
        t.start()
        hilos_alumnos.append(t)

    for t in hilos_alumnos:
        t.join()

    hilo_profesor.join()
    print("\nSimulación finalizada.")

